/* ═══════════════════════════════════════════════════════════════════════
   모델
   ═══════════════════════════════════════════════════════════════════════ */
const S={execs:[], squads:[], sel:null, tab:"overview", mode:"exec", cards:false, cut:Infinity,
         sideOpen:true, sideW:310, showSum:false,
         rosterOf:()=>[], squadOf:()=>null};
const ms=iso=>{const v=Date.parse(iso); return Number.isNaN(v)?null:v;};

function build(){
  const byExec=new Map();
  const push=(id,e)=>{ if(!byExec.has(id)) byExec.set(id,[]); byExec.get(id).push(e); };

  // 1차 — payload.executionId 가 있는 것.
  // agent-state-changed / task-status-changed / workspace-file-changed / token-usage-update
  // 에는 executionId 가 없다(실측: 50개 중 23개). 그냥 버리면 태스크 시작 시각이 사라져
  // 재생을 만들 수 없다. 그래서 아래에서 taskId 와 시간창으로 귀속시킨다.
  const orphans=[];
  for(const e of RAW.ev.values()){
    const id=e?.payload?.executionId;
    if(id) push(id,e); else orphans.push(e);
  }

  // taskId → executionId (history 의 tasks, plan-ready 의 waves 양쪽에서 모은다)
  const taskOwner=new Map();
  for(const [id,h] of RAW.hist) for(const t of (h.tasks||[])) if(t.taskId) taskOwner.set(t.taskId,id);
  for(const [id,list] of byExec) for(const e of list){
    const p=e.payload||{};
    for(const w of (p.waves||[])) for(const tid of w) taskOwner.set(tid,id);
    for(const tid of (p.taskIds||[])) taskOwner.set(tid,id);
    if(p.taskId) taskOwner.set(p.taskId,id);
  }

  // 실행별 시간창 — taskId 로도 못 붙는 이벤트(agent-state-changed 등)의 귀속 근거
  const win=[...byExec].map(([id,list])=>{
    const ts=list.map(e=>ms(e.timestamp)).filter(Number.isFinite);
    return {id, a:Math.min(...ts), b:Math.max(...ts)};
  }).sort((x,y)=>x.a-y.a);

  for(const e of orphans){
    const p=e.payload||{};
    let id=p.taskId?taskOwner.get(p.taskId):null;
    if(!id){
      const t=ms(e.timestamp);
      // 시간창 안에 들어가면 그 실행, 아니면 가장 가까운 실행에 붙인다
      id=(win.find(w=>t>=w.a&&t<=w.b)||win.reduce((best,w)=>{
        const d=t<w.a?w.a-t:t-w.b;
        return (!best||d<best.d)?{...w,d}:best;
      },null)||{}).id;
    }
    if(id) push(id,e);
  }
  // RAW.log 까지 포함한다. history/events 가 없어도 <executionId>.jsonl 하나만으로
  // 최소한의 실행 뷰는 세운다 — 파일이 일부만 들어왔을 때 전부 실패시키지 않기 위해서다.
  const ids=new Set([...RAW.hist.keys(), ...byExec.keys(), ...RAW.log.keys()]);
  S.execs=[...ids].map(id=>{
    const h=RAW.hist.get(id)||{};
    const partial=!RAW.hist.has(id);      // events 에만 있고 history 에서 잘려나간 실행
    const evs=(byExec.get(id)||[]).sort((a,b)=>(a.id??0)-(b.id??0));
    const pick=t=>evs.find(e=>e.eventType==="squad:"+t);
    const planReady=pick("plan-ready");
    // history 가 없으면 요청 원문을 planning-started 이벤트에서 줍는다
    const request=h.request||pick("planning-started")?.payload?.request||"";

    const contract=contractOf(request);
    const track=trackOf(request);
    const options=optionsOf(request);       // 객관식이면 보기 목록. 아니면 빈 배열

    // 태스크 구간 — 재생의 뼈대. task-status-changed(in_progress) 가 시작,
    // task-completed 가 끝이다. 없으면 원문 로그의 "assigned to agent" 줄, 그것도
    // 없으면 completedAt - durationMs 로 되짚는다.
    const span=new Map();
    const at=id=>span.get(id)||span.set(id,{}).get(id);
    for(const e of evs){
      const p=e.payload||{}, t=ms(e.timestamp);
      if(!p.taskId) continue;
      if(e.eventType==="squad:task-status-changed"&&p.newStatus==="in_progress") at(p.taskId).start=t;
      if(e.eventType==="squad:task-completed"){ const s=at(p.taskId); s.end=t; s.ok=p.success!==false; }
    }

    const tasks=(h.tasks||[]).map(t=>{
      const s=span.get(t.taskId)||{};
      const end=s.end??ms(t.completedAt);
      const start=s.start??(end&&t.durationMs?end-t.durationMs:null);
      return {
        ...t, start, end,
        meta:RAW.task.get(t.taskId)||null,
        answer:inspectAnswer(t.output,contract,options),
        fail:t.status==="failed"||t.error?classify(t.error):null
      };
    });
    // history 가 없고 이벤트만 있는 실행도 태스크를 세운다
    if(!tasks.length){
      for(const e of evs) if(e.eventType==="squad:task-completed"){
        const p=e.payload||{};
        tasks.push({taskId:p.taskId, title:p.taskTitle, status:p.success?"completed":"failed",
          output:"", error:p.error, agentName:null, durationMs:null,
          meta:RAW.task.get(p.taskId)||null, answer:inspectAnswer("",contract,options),
          fail:p.success?null:classify(p.error)});
      }
    }
    // 그것도 없으면 원문 로그 문장에서 세운다. 응답 본문은 못 얻지만 무엇이 돌았는지는 보인다.
    const logLines=[...(RAW.log.get(id)||new Map()).values()]
      .sort((a,b)=>String(a.timestamp).localeCompare(String(b.timestamp)));
    if(!tasks.length&&logLines.length){
      const seen=new Map();
      for(const l of logLines){
        const m=String(l.message||"").match(/^Task '([\s\S]*?)' (assigned to agent '(.*)'|completed by '(.*)'|failed: ([\s\S]*))$/);
        if(!m) continue;
        const title=m[1];
        if(!seen.has(title)) seen.set(title,{taskId:null, title, agentName:m[3]||m[4]||null,
          status:"running", output:"", error:null, durationMs:null, meta:null,
          answer:inspectAnswer("",contract,options), fail:null, partial:true});
        const t=seen.get(title);
        if(m[4]){ t.status="completed"; t.agentName=m[4]; }
        if(m[5]){ t.status="failed"; t.error=m[5]; t.fail=classify(m[5]); }
      }
      tasks.push(...seen.values());
    }

    // 구간이 비면 원문 로그의 배정/완료 문장에서 시각을 줍는다
    for(const t of tasks){
      if(t.start&&t.end) continue;
      for(const l of logLines){
        const msg=String(l.message||"");
        if(!t.title||msg.indexOf("Task '"+t.title+"'")!==0) continue;
        const at2=ms(l.timestamp);
        if(/assigned to agent/.test(msg)) t.start??=at2;
        if(/completed by|failed:/.test(msg))  t.end??=at2;
      }
    }

    // 누적 토큰 곡선 — 재생 중 비용이 실제로 언제 발생했는지 보여준다
    const tokenCurve=evs
      .filter(e=>e.eventType==="squad:execution-token-usage")
      .map(e=>({t:ms(e.timestamp), total:e.payload?.total??0,
                inTok:e.payload?.promptTokens??0, outTok:e.payload?.completionTokens??0}))
      .filter(p=>Number.isFinite(p.t))
      .sort((a,b)=>a.t-b.t);

    // 에이전트별 토큰 — 로그의 perAgentTokenUsage 와 태스크별 tokenUsage 는 전부 {0,0} 이고
    // token-usage-update 는 에이전트의 "평생 누적"이라 실행별 귀속에 못 쓴다.
    // 그래서 누적 곡선의 증분을 그 시각에 돌고 있던 태스크에 귀속시킨다. 이건 추정이다.
    // 두 태스크가 동시에 돌던 구간의 증분은 나누지 않고 '미귀속'으로 남긴다 —
    // 지어낸 숫자를 화면에 올리지 않기 위해서다.
    let tokUnattributed=0;
    for(let i=0;i<tokenCurve.length;i++){
      const p=tokenCurve[i], prev=tokenCurve[i-1];
      const d=p.total-(prev?.total??0), di=p.inTok-(prev?.inTok??0), dout=p.outTok-(prev?.outTok??0);
      if(d<=0) continue;
      const run=tasks.filter(t=>t.start!=null&&t.end!=null&&t.start<=p.t&&p.t<=t.end);
      if(run.length===1){ const t=run[0];
        t.tok=(t.tok||0)+d; t.tokIn=(t.tokIn||0)+di; t.tokOut=(t.tokOut||0)+dout;
        (t.tokAt||=[]).push({t:p.t, tok:t.tok, tokIn:t.tokIn, tokOut:t.tokOut});
      } else tokUnattributed+=d;
    }
    const tokEstimated=tokenCurve.length>0;

    const final=inspectAnswer(h.finalResult,contract,options);

    // 스쿼드가 스스로 남긴 라우팅 표시.
    // LEDGER Squad 의 응답 끝에 {"a":"Reasoner","track":"math","conf":0.99} 형태로 붙는다.
    // 스쿼드가 문항을 어느 트랙으로 봤는지가 여기 적혀 있고, 그게 곧 어느 출력 계약을
    // 쓸지를 정한다. 트랙을 잘못 찍으면 형식이 통째로 어긋나 0점이 된다.
    // 지문에서 우리가 찍은 트랙과 나란히 놓는 것이 이 값의 쓸모다.
    const routeText=[h.finalResult||"", ...tasks.map(t=>t.output||"")].filter(Boolean).join("\n");
    const marks=[...routeText.matchAll(/\{"a":"([^"]*)","track":"([^"]*)","conf":([0-9.]+)\}/g)]
      .map(m=>({who:m[1], track:m[2], conf:Number(m[3])}));
    const route=marks.length?marks[marks.length-1]:null;   // 마지막 것이 최종 판단
    const t0=ms(h.startedAt)??ms(evs[0]?.timestamp)??ms(logLines[0]?.timestamp);
    const t1=ms(h.completedAt)??ms(evs[evs.length-1]?.timestamp)??ms(logLines[logLines.length-1]?.timestamp);
    const tu=h.totalTokenUsage||pick("execution-completed")?.payload?.tokenUsage||{promptTokens:0,completionTokens:0};

    // 채점 적격: finalResult 든 어느 태스크 output 이든 패치가 하나라도 있으면 적격
    const carriers=[{who:"finalResult",a:final},...tasks.map(t=>({who:t.title||t.taskId,a:t.answer}))];
    const grad=carriers.find(c=>c.a.gradable)||null;

    // 채점 불가의 원인을 구분한다.
    //   blocked    — 호출 자체가 거부됐다. 컨텍스트 초과·인프라 오류. 우리가 고칠 수 없는 영역
    //   notitem    — 벤치마크 문항이 아니다. 고칠 것도 없고 채점 대상도 아니다
    //   unknown    — 트랙도 계약도 못 알아봤다. 검사기를 고칠 쪽
    //   markers    — 계약도 보냈고 실행도 됐는데 형식이 안 나왔다. ★ 프롬프트로 고칠 영역
    // 이것들을 한 숫자로 합치면 "무엇을 고쳐야 하는가"가 화면에서 사라진다.
    // 출력 유무로 판단하면 안 된다 — 실패한 태스크도 output 에
    // "Task assigned to `X` failed." 라는 자리표시 문자열이 들어간다. 상태로 판단한다.
    const anyDone=tasks.some(t=>t.status==="completed"||t.status==="done");
    const blocker=grad?null
      :contract==="none"?"notitem"                                // 벤치마크 문항이 아니다
      :contract==="unknown"?"unknown"                             // 계약을 못 알아봤다
      :(!anyDone&&tasks.some(t=>t.fail))?"blocked":"markers";

    const counts=pick("execution-completed")?.payload?.taskCounts
      ||{total:tasks.length,completed:tasks.filter(t=>t.status==="completed"||t.status==="done").length,
         failed:tasks.filter(t=>t.status==="failed").length};

    // 웨이브 — events.jsonl 에는 시작만, <executionId>.jsonl 에는 "Wave n/m completed" 만 있다.
    // 둘을 합쳐야 구간이 닫힌다. plan-ready 의 waves 는 계획이고 이건 실제로 돈 시각이다.
    const waveEv=evs.filter(e=>e.eventType==="squad:task-wave-started")
      .map(e=>({i:e.payload?.waveIndex??0, total:e.payload?.totalWaves??0,
                taskIds:e.payload?.taskIds||[], start:ms(e.timestamp), end:null}));
    for(const l of logLines){
      const m=String(l.message||"").match(/^Wave (\d+)\/(\d+) completed/);
      if(!m) continue;
      const w=waveEv.find(x=>x.i===+m[1]-1); if(w) w.end=ms(l.timestamp);
    }
    // 이벤트가 없고 로그만 있으면 로그 문장만으로 세운다
    if(!waveEv.length) for(const l of logLines){
      const m=String(l.message||"").match(/^Starting wave (\d+)\/(\d+) with (\d+) task/);
      if(m) waveEv.push({i:+m[1]-1, total:+m[2], taskIds:[], start:ms(l.timestamp), end:null, n:+m[3]});
    }

    // 워크스페이스 파일 쓰기 — 답이 응답이 아니라 파일로 나간 순간이 여기 찍힌다
    const fileWrites=evs.filter(e=>e.eventType==="squad:workspace-file-changed")
      .map(e=>({t:ms(e.timestamp), path:e.payload?.path||"", how:e.payload?.changeType||""}))
      .filter(f=>Number.isFinite(f.t));

    const idx=RAW.logIndex.get(id)||null;
    const squadId=h.squadId||evs.find(e=>e.squadId)?.squadId||idx?.squadId||null;
    const ws=RAW.execWs.get(id)||"(단일)";
    // 스쿼드 단위 키. 워크스페이스 하나에 스쿼드가 여럿일 수 있으므로 ws 만으로는 못 나눈다.
    const sq=squadId?ws+"·"+squadId:ws;

    return {
      id, ws, squadId, sq,
      squadName:h.squadName||RAW.squad.get(squadId)?.name||RAW.report.get(id)?.squad||"—",
      waveEv, fileWrites, report:RAW.report.get(id)||null,
      logIndex:idx&&idx.entryCount!=null?{...idx, actual:logLines.length}:null,
      request, planTitle:h.planTitle||"", partial,
      aigoStatus:h.status||pick("execution-completed")?"completed":"unknown",
      tasks, final, carriers, gradable:!!grad, gradCarrier:grad, blocker, contract, track,
      route, routeMarks:marks, options,
      blockKind:blocker==="blocked"?(tasks.find(t=>t.fail)?.fail.kind||"—"):null,
      counts, tokens:tu, t0, t1, tokenCurve, tokUnattributed, tokEstimated,
      durationMs:h.durationMs??((t0&&t1)?t1-t0:null),
      waves:planReady?.payload?.waves||[],
      plannerWarning:planReady?.payload?.plannerWarning||null,
      autoApprove:planReady?.payload?.autoApprove,
      events:evs, logs:[...(RAW.log.get(id)||new Map()).values()].sort((a,b)=>String(a.timestamp).localeCompare(String(b.timestamp))),
      phases:phasesOf(evs)
    };
  }).sort((a,b)=>(a.t0??0)-(b.t0??0));

  buildRoster();
}

/* 스쿼드 구성(로스터).
   로그에는 "태스크를 배정받은 에이전트"만 나온다. 한 번도 일하지 않은 구성원과
   플래너는 로그만으로 존재를 알 수 없다 — 실측: 로그의 에이전트는 3명인데
   실제 스쿼드는 4명이었다. 그래서 두 가지를 한다.
     1) 전 실행에 걸쳐 등장한 에이전트를 합집합으로 모은다 (한 실행만 봐도 전원이 보이게)
     2) Squad Template JSON 이 들어오면 그것을 권위 있는 로스터로 삼는다 */
/* 로스터를 스쿼드별로 만든다.
   처음에는 워크스페이스 하나가 스쿼드 하나라고 봤는데 아니었다. 실측을 보고 고친 자리다. */
function buildRoster(){
  const per=new Map();
  // 워크스페이스가 아니라 스쿼드 단위로 묶는다.
  // 실측: squad/ikkim 한 워크스페이스에서 스쿼드 4개가 돌았다(코드 리뷰 스쿼드2 ×7,
  // 풀스택 개발 스쿼드 ×4, 코드 리뷰 스쿼드 ×1, 풀스택 개발 스쿼드2 ×1).
  // ws 로 묶으면 13개 실행이 한 스쿼드로 합쳐지고, 로스터도 남의 것이 붙는다.
  const keys=[...new Set(S.execs.map(e=>e.sq))];
  // 설정 파일만 들어오고 실행이 하나도 없는 스쿼드도 목록에는 세운다
  for(const [k,c] of RAW.squad) if(!keys.some(x=>x.endsWith("·"+k))) keys.push(c.ws+"·"+k);

  for(const sq of keys){
    const m=new Map();
    const put=(name,src)=>{
      if(!name) return null;
      if(!m.has(name)) m.set(name,{sq, name, id:null, role:"", model:"", icon:"", tools:[], prompt:"", src,
        minCtx:null, memory:false, execs:new Set(), tasks:0, done:0, failed:0, tok:0});
      return m.get(name);
    };
    const mine=S.execs.filter(e=>e.sq===sq);
    for(const e of mine) for(const t of e.tasks){
      const r=put(t.agentName||t.agentId||null,"log"); if(!r) continue;
      r.id||=t.agentId||null; r.execs.add(e.id); r.tasks++;
      if(t.status==="failed"||t.fail) r.failed++; else r.done++;
      r.tok+=t.tok||0;
    }
    const sid=(mine[0]?.squadId)||sq.split("·")[1]||null;
    const cfg=(sid&&RAW.squad.get(sid))||null;
    if(cfg){
      const byId=new Map([...m.values()].filter(r=>r.id).map(r=>[r.id,r]));
      for(const a of cfg.agents){
        const r=(a.id&&byId.get(a.id))||put(a.name,"config");
        if(!r) continue;
        r.name=a.name; r.id||=a.id; r.icon=a.icon; r.role=a.role||r.role;
        r.model=a.model; r.tools=a.tools; r.prompt=a.prompt; r.src="config";
        r.minCtx=a.minCtx; r.memory=a.memory; r.needsTools=a.needsTools; r.mode=a.mode;
      }
    }else{
      // 설정이 없으면 플래너 자리만 추론한다. 플래너는 태스크를 배정받지 않아 로그에 이름이 없다.
      const planned=mine.filter(e=>e.events.some(v=>v.eventType==="squad:plan-ready"));
      if(planned.length&&!m.has("(플래너)")) m.set("(플래너)",{sq, name:"(플래너)", id:null, role:"Planner",
        model:"", icon:"", tools:[], prompt:"", src:"inferred", minCtx:null, memory:false,
        execs:new Set(planned.map(e=>e.id)), tasks:0, done:0, failed:0, tok:0});
    }
    per.set(sq,{sq, ws:mine[0]?.ws||cfg?.ws||sq.split("·")[0], squadId:sid,
                name:cfg?.name||mine[0]?.squadName||sq.split("·")[0],
                source:cfg?"config":"log", cfg, agents:[...m.values()], execs:mine});
  }
  S.squads=[...per.values()].sort((a,b)=>(a.ws+a.name).localeCompare(b.ws+b.name));
  // 실행 하나를 볼 때 쓰는 값은 그 실행이 속한 스쿼드 것을 가리킨다.
  S.rosterOf=sq=>per.get(sq)?.agents||[];
  S.squadOf =sq=>per.get(sq)||null;
}

function phasesOf(evs){
  const at=t=>{const e=evs.find(x=>x.eventType==="squad:"+t);return e?ms(e.timestamp):null;};
  const p=at("planning-started"), r=at("plan-ready"), s=at("execution-started"),
        g=at("aggregation-started"), c=at("execution-completed");
  const seg=[];
  if(p&&r) seg.push({k:"플래닝",   ms:r-p, c:"var(--prog)"});
  if(r&&s) seg.push({k:"승인 대기", ms:s-r, c:"var(--fg-faint)"});
  if(s&&g) seg.push({k:"실행",     ms:g-s, c:"var(--accent)"});
  if(g&&c) seg.push({k:"집계",     ms:c-g, c:"var(--warn)"});
  return seg;
}
