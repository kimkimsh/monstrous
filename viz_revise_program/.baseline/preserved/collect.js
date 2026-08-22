/* ═══════════════════════════════════════════════════════════════════════
   수집 — 폴더 안의 파일을 이름으로 분류해 병합한다
   ═══════════════════════════════════════════════════════════════════════ */
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const RAW={hist:new Map(), ev:new Map(), task:new Map(), log:new Map(), artifact:new Map(),
           taskmd:new Map(), squad:new Map(), execWs:new Map(),
           logIndex:new Map(), report:new Map()};
const SEEN={files:0, kinds:{}, skipped:[], ws:new Set()};

function ndjson(text){
  const out=[];
  for(const line of String(text).split(/\r?\n/)){
    const s=line.trim(); if(!s) continue;
    const j=s.indexOf("{"); if(j<0) continue;
    try{ out.push(JSON.parse(s.slice(j))); }catch{}
  }
  return out;
}
function bump(k){ SEEN.kinds[k]=(SEEN.kinds[k]||0)+1; }

/* 경로에서 워크스페이스 이름을 뽑는다.
   "ikkim/logs/history.json" -> "ikkim",  "squad/test_2/.squad.json" -> "test_2".
   워크스페이스를 구분해야 스쿼드끼리 비교할 수 있다. 로그 안에는 이 정보가 없다. */
function wsOf(path){
  const p=String(path||"").replace(/\\/g,"/");
  const m=p.match(/^(.*?)\/(logs|tasks|artifacts)\//)||p.match(/^(.*?)\/\.squad\.json$/);
  const dir=m?m[1]:p.replace(/\/[^/]*$/,"");
  const seg=dir.split("/").filter(Boolean);
  return seg[seg.length-1]||"(단일)";
}

function addFile(path,name,text){
  SEEN.files++;
  SEEN.ws.add(wsOf(path));
  const base=name.replace(/\.[^.]+$/,"");
  const WS=wsOf(path);
  try{
    if(name==="history.json"){
      const arr=JSON.parse(text);
      for(const e of (Array.isArray(arr)?arr:[arr])) if(e&&e.executionId){
        const p=RAW.hist.get(e.executionId);
        // 스냅샷이 겹칠 때: 태스크 output 을 더 많이 가진 쪽을 남긴다
        if(!p||JSON.stringify(e).length>JSON.stringify(p).length) RAW.hist.set(e.executionId,e);
        RAW.execWs.set(e.executionId,WS);      // 이 실행이 어느 워크스페이스 것인지
      }
      bump("history.json"); return;
    }
    if(name==="events.jsonl"){
      for(const e of ndjson(text)){
        const ex=e?.payload?.executionId ?? "-";
        RAW.ev.set(ex+"#"+e.id, e);                  // executionId+id 로 중복 제거
        if(ex!=="-"&&!RAW.execWs.has(ex)) RAW.execWs.set(ex,WS);
      }
      bump("events.jsonl"); return;
    }
    // logs/index.json — 실행 목록. 값 자체는 못 믿는다: 실행 도중에 쓰이고 끝난 뒤 갱신되지
    // 않아서 entryCount 가 실제 줄 수보다 늘 적다(실측: 21개 실행 전부). 그래서 시간이나
    // 개수의 근거로는 쓰지 않고, 실행이 어느 스쿼드 것인지와 "얼마나 어긋났는지"만 가져온다.
    if(name==="index.json"&&/\/logs\//.test(path)){
      try{
        for(const r of JSON.parse(text)) if(r&&r.executionId){
          RAW.logIndex.set(r.executionId,{squadId:r.squadId||null, entryCount:r.entryCount??null,
            startedAt:r.startedAt||null, lastUpdatedAt:r.lastUpdatedAt||null});
          if(!RAW.execWs.has(r.executionId)) RAW.execWs.set(r.executionId,WS);
        }
      }catch{}
      bump("logs/index.json"); return;
    }
    if(name==="index.json"){ bump("tasks/index.json"); return; }
    // artifacts/reports/*.md — AI:GO 가 스스로 낸 실행 요약.
    // 에이전트가 쓴 산출물이 아니므로 artifacts 로 세지 않는다. 대신 "AI:GO 는 뭐라고 했나"를
    // 우리 판정 옆에 놓기 위해 따로 읽는다. 둘이 갈리는 지점이 이 도구의 논점이다.
    if(/\/artifacts\/reports\//.test(path)&&name.endsWith(".md")){
      const one=re=>((text.match(re)||[])[1]||"").trim();
      const id=one(/^\|\s*Execution ID\s*\|\s*`([^`]+)`/m)||base.replace(/-report$/,"");
      RAW.report.set(id,{
        id, squad:one(/^\*\*Squad:\*\*\s*(.+)$/m),
        status:one(/^\|\s*Status\s*\|\s*(.+?)\s*\|/m),
        duration:one(/^\|\s*Duration\s*\|\s*(.+?)\s*\|/m),
        tokens:+((text.match(/^\|\s*Total Tokens\s*\|\s*([\d,]+)/m)||[])[1]||"").replace(/,/g,"")||0,
        // 태스크 표: | # | Title | Agent | Status | Duration | Tokens |
        tasks:[...text.matchAll(/^\|\s*(\d+)\s*\|([\s\S]*?)\|\s*([^|]*?)\s*\|\s*([✓✗×]?\s*\w+)\s*\|\s*([^|]*?)\s*\|\s*(\d+)\s*\|\s*$/gm)]
          .map(m=>({n:+m[1], title:m[2].replace(/\s+/g," ").trim(), agent:m[3].trim(),
                    status:m[4].replace(/[✓✗×]/g,"").trim(), dur:m[5].trim(), tok:+m[6]})),
        text});
      bump("artifacts/reports/*.md"); return;
    }
    // .squad.json — 스쿼드 구성(로스터)의 유일한 출처다.
    // 로그에는 "태스크를 배정받은 에이전트"만 나오므로, 한 번도 일하지 않은 구성원과
    // 플래너는 로그만으로는 존재 자체를 알 수 없다. 모델 이름도 로그에는 없고 여기에만 있다.
    //
    // 여기서 JSON.parse 가 던지면 바깥 catch 로 빠져 그 파일이 통째로 버려진다.
    // 뒤에 오는 <executionId>.jsonl 은 JSON 이 아니므로 반드시 자체 try 로 막는다.
    if(name.endsWith(".json")) try {
      const j=JSON.parse(text);
      const cfg=j?.config||j?.squad||j?.template||j;
      const arr=cfg?.agents;
      if(Array.isArray(arr)&&arr.length&&arr.some(a=>a&&(a.name||a.role))){
        const plannerId=cfg.plannerAgentId||null;
        // 워크스페이스가 아니라 squadId 로 건다. 워크스페이스 하나에서 스쿼드가 여러 번
        // 바뀔 수 있고(실측: ikkim 한 곳에서 스쿼드 4개), .squad.json 은 그중 마지막으로
        // 초기화된 하나만 담는다. ws 로 걸면 예전 실행에 남의 로스터가 붙는다.
        RAW.squad.set(j.squadId||cfg.id||WS,{
          ws:WS, squadId:j.squadId||cfg.id||null,
          appVersion:j.appVersion||"", initializedAt:j.initializedAt||"",
          executionMode:cfg.executionMode||"", instructions:(cfg.instructions||"").trim(),
          name:j.squadName||cfg.name||"(스쿼드)",
          description:cfg.description||"",
          plannerId,
          agents:arr.map(a=>{
            // role 은 {type:"planner"} 이거나 {type:"custom", value:"Backend Developer"} 형태다.
            const rt=a.role&&typeof a.role==="object"?a.role:null;
            const role=rt?(rt.value||rt.type||""):(typeof a.role==="string"?a.role:"");
            return {
              id:a.id||null, name:a.name||a.id||"agent", icon:a.icon||"",
              role:(a.id&&a.id===plannerId)?"Planner":role,
              model:a.modelPreferences?.preferredModelId||a.model||a.modelId||"",
              tools:a.toolConfig?.enabledTools||[],
              prompt:a.systemPrompt||"",
              // 컨텍스트 하한이 안 걸려 있으면 4096 짜리 모델에 긴 지문이 그대로 간다.
              // HTTP 400 으로 죽는 실행들의 설정 쪽 근거가 여기다.
              minCtx:a.modelPreferences?.minContextWindow??null,
              memory:a.memoryEnabled===true,
              mode:a.executionMode||"",
              needsTools:a.modelPreferences?.requiresToolCalling===true
            };
          })});
        bump("squad config"); return;
      }
    } catch { /* 스쿼드 설정이 아니면 아래 판별로 넘어간다 */ }
    // tasks/*.md — 시도 단위 기록. "[08:31] Started execution (attempt 1)" 형태다.
    // events.jsonl 에는 시도 번호가 없어서 재시도가 몇 번째였는지는 여기에만 있다.
    if(/\/tasks\//.test(path)&&name.endsWith(".md")){
      const id=(text.match(/^ID:\s*(\S+)/m)||[])[1];
      const log=[...text.matchAll(/^-\s*\[(\d{2}:\d{2})\]\s*(.+)$/gm)]
        .map(m=>({at:m[1], what:m[2].trim(),
                  attempt:+((m[2].match(/attempt (\d+)/)||[])[1]||0) || null}));
      if(id) RAW.taskmd.set(id,{id, title:(text.match(/^# Task:\s*(.+)$/m)||[])[1]||"", log,
        deps:((text.match(/^Dependencies:\s*(.+)$/m)||[])[1]||"").split(/,\s*/).filter(Boolean)});
      bump("tasks/*.md"); return;
    }
    if(/\/tasks\//.test(path)&&name.endsWith(".json")){
      const t=JSON.parse(text);
      for(const x of (Array.isArray(t)?t:[t])) if(x&&x.id) RAW.task.set(x.id,x);
      bump("tasks/*.json"); return;
    }
    // artifacts/ — 에이전트가 워크스페이스에 쓴 파일.
    // judge 는 워크스페이스를 읽지 않는다. 답이 여기에만 있고 응답 텍스트에 없으면 0점이다.
    // 실측: test_2/artifacts/final_answer.txt 에 답이 있는데 응답에는 \boxed{} 가 없었다.
    // reports/ 는 AI:GO 가 만든 실행 요약이라 제외한다. 에이전트가 쓴 것이 아니다.
    if(/\/artifacts\//.test(path)&&!/\/artifacts\/reports\//.test(path)){
      RAW.artifact.set(path,{path, name, text, chars:text.length});
      bump("artifacts/*"); return;
    }
    if(name.endsWith(".jsonl")&&UUID.test(base)){
      const cur=RAW.log.get(base)||new Map();
      for(const l of ndjson(text)) cur.set((l.timestamp||"")+"|"+(l.message||""), l);
      RAW.log.set(base,cur); bump("<executionId>.jsonl"); return;
    }
    SEEN.skipped.push(path);
  }catch(err){ SEEN.skipped.push(path+" ("+err.message+")"); }
}
