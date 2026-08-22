function t(s){ return LANG==="en"?(EN[s]??s):s; }

/* 자리표시자가 든 사전 키를 숫자로 채운다.
   "실행 불가 4건 제외 · 계약 불명 6건 제외 · 답 형식 없음 6건" 처럼 조각이 조건부로 붙는 라벨은
   문장을 통째로 사전에 넣으면 조각 조합마다 키가 하나씩 필요해진다. 조각 단위로 바꾼다. */
function tn(key,...v){ return t(key).replace(/\{(\d+)\}/g,(_,i)=>v[i]??""); }

/* 오프닝의 상태 줄. 읽는 도중에도 언어가 바뀔 수 있으므로
   "무엇을 쓸지"를 함수로 들고 있다가 그때그때 다시 그린다. */
let DF=null, DE=null;
function renderDfiles(){ const f=$("#dfiles"), e=$("#derr");
  if(f) f.textContent=DF?DF():"";
  if(e) e.textContent=DE?DE():""; }
function setDfiles(fn){ DF=fn; renderDfiles(); }
function setDerr(fn){ DE=fn; renderDfiles(); }

/* 헤더의 출처 줄. 언어를 바꾸면 다시 그려야 하므로 finish() 밖으로 빼 둔다. */
function renderSrc(){
  const p=S.srcParts; if(!p) return;
  const wsPart=p.ws>1?`${p.ws} ${t("워크스페이스")} · `:"";
  const kinds=p.kinds.split("(무시)").join(t("(무시)"));
  $("#src").textContent=`${p.files} files · ${wsPart}${kinds}`;
}

/* 렌더된 DOM 을 훑어 문장 단위로 바꾼다.
   설명문이 템플릿 문자열 안에 ${} 와 섞여 있어 호출부마다 감싸는 방식으로는 계속 빠진다.
   대신 그려진 뒤 텍스트 노드를 한 번 훑는다. 사전에 없으면 그대로 두므로 손해가 없다.

   데이터는 건드리지 않는다 — 요청 원문·응답·에러·에이전트 이름은 로그의 내용이지 UI 가 아니다.
   pre / code / .scroll / [data-raw] 안은 통째로 건너뛴다. */
const NOLANG=new Set(["PRE","CODE","SCRIPT","STYLE","TEXTAREA","OPTION"]);

/* 설명 문단은 ${} 와 <b> 로 잘려 텍스트 노드가 조각난다. 조각을 사전에 넣어봐야 뜻이 없다.
   그래서 문단은 요소 단위로 통째 바꾼다. 공백을 접어 키로 삼고, 번역문에는 마크업을 넣어 둔다.
   숫자가 섞인 문단은 {0} 자리표시자로 잡아 원래 숫자를 도로 끼워 넣는다. */
const PARA_SEL=".q,.note,.tip,.sm-src,.sm-cap>span:first-child,.lead,.err,.drop-files .muted";
function paraKey(el){ return el.textContent.replace(/\s+/g," ").trim(); }

/* 치환은 파괴적이다. 원문을 기억해 두지 않으면 한국어로 되돌릴 수 없다.
   패널은 매번 다시 그려지지만 오프닝 화면은 정적이라 특히 그렇다. */
const ORIG_HTML=new WeakMap(), ORIG_TEXT=new WeakMap();

function translateParas(root){
  // root 자신이 문단일 수 있다. 감시자가 붙은 조각을 그대로 넘겨주기 때문이다.
  const els=[...root.querySelectorAll(PARA_SEL)];
  if(root.matches&&root.matches(PARA_SEL)) els.unshift(root);
  els.forEach(el=>{
    if(LANG!=="en"){ const o=ORIG_HTML.get(el); if(o!=null) el.innerHTML=o; return; }
    const key=paraKey(el);
    if(!key||!/[가-힣]/.test(key)) return;
    const put=html=>{ if(!ORIG_HTML.has(el)) ORIG_HTML.set(el,el.innerHTML); el.innerHTML=html; };
    if(EN[key]!=null){ put(EN[key]); return; }
    // 숫자를 자리표시자로 바꿔 한 번 더 찾는다
    const nums=[]; const gen=key.replace(/\d+(?:\.\d+)?/g,m=>{nums.push(m);return `{${nums.length-1}}`;});
    if(EN[gen]!=null) put(EN[gen].replace(/\{(\d+)\}/g,(_,i)=>nums[i]??""));
  });
}

function translateDOM(root){
  if(!root) return;
  // 원문 덤프 안쪽이면 통째로 건너뛴다. 아래 순회는 조상을 root 까지만 훑으므로
  // 덤프 안의 노드가 root 로 들어오면 제외 규칙이 걸리지 않는다. 22개 실행에서 1초가 걸렸다.
  if(root.closest&&root.closest(I18N_SKIP)) return;
  translateParas(root);
  if(LANG!=="en"){                      // 한국어로 되돌리기
    const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    while(w.nextNode()){ const o=ORIG_TEXT.get(w.currentNode); if(o!=null) w.currentNode.nodeValue=o; }
    return;
  }
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{
    acceptNode(n){
      for(let p=n.parentElement;p&&p!==root.parentElement;p=p.parentElement){
        if(NOLANG.has(p.tagName)) return NodeFilter.FILTER_REJECT;
        if(p.classList&&(p.classList.contains("scroll")||p.dataset&&p.dataset.raw!=null)) return NodeFilter.FILTER_REJECT;
      }
      return /[가-힣]/.test(n.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;
    }});
  const nodes=[]; while(w.nextNode()) nodes.push(w.currentNode);
  for(const n of nodes){
    const raw=n.nodeValue;
    // 템플릿 문자열의 들여쓰기 때문에 줄바꿈과 공백이 그대로 들어온다.
    // 사전 키는 공백을 접은 형태이므로 조회할 때도 접어야 맞는다.
    const key=raw.replace(/\s+/g," ").trim();
    if(!key) continue;
    const keep=()=>{ if(!ORIG_TEXT.has(n)) ORIG_TEXT.set(n,raw); };
    const pad=[raw.match(/^\s*/)[0], raw.match(/\s*$/)[0]];
    // 번역문이 문장부호로 시작하면 앞 공백을 버린다. 조각 앞에 다른 표현식이 있던 자리라
    // 공백을 그대로 두면 "verbatim ." 처럼 부호 앞이 벌어진다.
    const put=v=>{ n.nodeValue=(/^['.,;:!?)]/.test(v)?"":pad[0])+v+pad[1]; };
    const hit=EN[key];
    if(hit!=null){ keep(); put(hit); continue; }
    // 숫자가 섞인 라벨("답 형식 없음 3건")은 자리표시자 형태로 한 번 더 찾는다
    const nums=[]; const gen=key.replace(/\d+(?:\.\d+)?/g,m=>{nums.push(m);return `{${nums.length-1}}`;});
    if(nums.length&&EN[gen]!=null){ keep();
      put(EN[gen].replace(/\{(\d+)\}/g,(_,i)=>nums[i]??"")); continue; }
    // 숫자와 단위가 자유롭게 섞이는 라벨은 규칙으로 바꾼다. 자리표시자로는 조합이 너무 많다.
    let done=false;
    for(const [re,to] of EN_RE){ if(re.test(key)){ keep(); put(key.replace(re,to)); done=true; break; } }
    if(done) continue;
    // 문장이 조각나 있으면(앞뒤에 다른 표현식이 붙어 잘린 경우) 부분 일치로 한 번 더 시도한다.
    // 접은 문자열에서 찾는다. 원문에 남은 줄바꿈과 들여쓰기 때문에 조각이 어긋나는 일을 막는다.
    let s=key, any=false;
    for(const [k,v] of EN_LONG){ if(s.includes(k)){ s=s.split(k).join(v); any=true; } }
    if(any){ keep(); put(s); }
  }
}

/* 숫자와 단위 조합이 자유로운 라벨. 사전 키로는 경우의 수를 감당할 수 없다. */
const EN_RE=[
  [/^누적 (.+) \(in (.+) · out (.+)\)$/,"cumulative $1 (in $2 · out $3)"],
  [/^([\d,.]+)자$/,"$1 chars"],
  [/^(.*) · 태스크 (\d+)\/(\d+) 성공$/,"$1 · $2/$3 tasks succeeded"],
  [/^waves: (.+) ⚠ 플래너 폴백$/,"waves: $1 ⚠ planner fallback"],
  [/^(.*) · 로그에서 추정( ·)?$/,"$1 · inferred from the log$2"],
  // 객관식 판정의 설명문 — 보기 문자와 값이 그대로 끼어 있다
  [/^"(.+)" 는 보기 ([A-Z]) \((.+)\) 와 같습니다\. 문자만 냈으면 채점됐습니다$/,
   "“$1” equals option $2 ($3) — the letter alone would have been graded"],
  [/^마지막 줄이 "(.+)" 입니다\. 지문은 "ANSWER: ([A-Z])" 라는 줄을 요구합니다$/,
   "the last line is “$1”; the prompt asks for a line reading “ANSWER: $2”"],
  [/^목록에 ([A-Z]) 가 없습니다$/,"$1 is not in the list"],
  [/^"(.+)" — 문자 하나가 아닙니다$/,"“$1” — not a single letter"],
  // 출력 계약 이름이 가운데 끼는 문장. 계약이 넷이라 통짜 키로는 넷씩 늘어난다.
  [/^에는 결과가 들어 있는데 응답 텍스트에는 (.+) 가 없습니다\. judge 가 가져갈 것이 없으므로 0점입니다\.$/,
   "holds the result, but the response text has no $1. The judge has nothing to take, so it scores 0."],
  [/^\. 어떤 응답에도 (.+) 가 없습니다$/,". No response contains $1"],
  // 짧은 라벨만 잡는다. 문장 끝의 "없음" 까지 삼키면 "no 부분 기록. history.json 에" 같은 게 나온다.
  [/^([^.,·]{1,24}) 없음$/,"no $1"],
  [/^W\d+: \d+개( · W\d+: \d+개)*$/,m=>m.replace(/개/g,"")],
];
/* 긴 문장부터 시도해야 짧은 조각이 먼저 걸려 문장을 반쪽만 바꾸는 일이 없다. */
let EN_LONG=[];
function rebuildLong(){ EN_LONG=Object.entries(EN).filter(([k])=>k.length>=12)
  .sort((a,b)=>b[0].length-a[0].length); }
rebuildLong();

/* 지금 화면에 남은 한국어를 뽑는다. 사전을 채울 때 쓴다. */
/* 늦게 그려지는 조각을 위한 안전망.
   화면을 새로 붙일 때마다 호출부에서 translateDOM 을 부르는 방식은 반드시 빠뜨린다.
   접힌 카드를 펴는 순간처럼 처음 그릴 때는 DOM 에 없던 조각이 특히 그렇다.
   그래서 붙는 것을 보고 바꾼다. 이미 영어인 조각은 사전에 걸리지 않으므로 두 번 돌아도 그대로다. */
const I18N_SKIP=".scroll,[data-raw],pre,code,script,style,textarea";
let I18N_BUSY=false;
const i18nWatch=new MutationObserver(ms=>{
  if(LANG!=="en"||I18N_BUSY) return;
  const roots=new Set();
  for(const m of ms) for(const n of m.addedNodes){
    // 붙은 것만 훑는다. m.target 을 훑으면 이미 바꾼 형제까지 매번 다시 돈다.
    const r=n.nodeType===1?n:m.target;
    if(r&&r.nodeType===1&&r.isConnected) roots.add(r);
  }
  if(!roots.size) return;
  I18N_BUSY=true;
  // 조상이 이미 목록에 있으면 자손은 버린다. 같은 자리를 두 번 돌 이유가 없다.
  try{ for(const r of roots){
    let nested=false;
    for(const o of roots) if(o!==r&&o.contains(r)){ nested=true; break; }
    if(!nested) translateDOM(r);
  } } finally{ I18N_BUSY=false; }
});
i18nWatch.observe(document.body,{childList:true,subtree:true});

function i18nAudit(){
  const out=new Set();
  for(const root of [document.querySelector("header"),document.querySelector(".modes"),
                     $("#pane"),$("#pane-all"),$("#pane-cmp"),$("#drop"),document.querySelector(".side")]){
    if(!root||root.hidden) continue;
    const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{
      acceptNode(n){
        for(let p=n.parentElement;p&&p!==root.parentElement;p=p.parentElement){
          if(NOLANG.has(p.tagName)) return NodeFilter.FILTER_REJECT;
          if(p.classList&&(p.classList.contains("scroll")||p.dataset&&p.dataset.raw!=null)) return NodeFilter.FILTER_REJECT;
        }
        return /[가-힣]/.test(n.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;
      }});
    while(w.nextNode()){ const s=w.currentNode.nodeValue.trim(); if(s) out.add(s); }
  }
  return [...out];
}
function tp(s){ return LANG==="en"?(PHASE_EN[s]??s):s; }
const esc=s=>String(s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const fmt=n=>n>=1e6?(n/1e6).toFixed(2)+"M":n>=1e3?(n/1e3).toFixed(1)+"k":String(Math.round(n||0));
const secs=m=>m==null?"—":(m/1000).toFixed(1)+"s";
const one=s=>String(s||"").replace(/\s+/g," ").trim();
const pct=n=>(n*100).toFixed(1)+"%";
