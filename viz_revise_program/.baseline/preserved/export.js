/* ── 내보내기 ──
   CSP 없이 순수 브라우저 기능만 쓴다. Blob + a[download] 면 라이브러리가 필요 없다. */
function download(name,text,type){
  const b=new Blob([text],{type:type||"application/octet-stream"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(b); a.download=name; a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
$("#btn-export").onclick=()=>{
  // 지금 화면에서 가장 큰 그림 하나를 고른다. 스쿼드 맵이 있으면 그것.
  const host=S.mode==="exec"?$("#pane"):S.mode==="all"?$("#pane-all"):$("#pane-cmp");
  const svgs=[...host.querySelectorAll("svg")];
  if(!svgs.length){ alert("이 화면에는 내보낼 그림이 없습니다."); return; }
  const svg=svgs.sort((a,b)=>b.getBoundingClientRect().width*b.getBoundingClientRect().height
                           -a.getBoundingClientRect().width*a.getBoundingClientRect().height)[0];
  const c=svg.cloneNode(true);
  // 화면 밖에서 열리므로 CSS 변수가 안 먹는다. 실제 색으로 굳혀서 내보낸다.
  const cs=getComputedStyle(document.documentElement);
  const vars=["--bg","--panel","--panel-2","--line","--fg","--fg-dim","--fg-faint",
              "--accent","--ok","--warn","--bad","--prog"];
  let css=":root{"+vars.map(v=>`${v}:${cs.getPropertyValue(v).trim()}`).join(";")+"}";
  css+="text{font-family:ui-monospace,Consolas,monospace}";
  const st=document.createElementNS(NS,"style"); st.textContent=css;
  c.insertBefore(st,c.firstChild);
  c.setAttribute("xmlns",NS);
  const rect=svg.getBoundingClientRect();
  if(!c.getAttribute("viewBox")&&rect.width) c.setAttribute("viewBox",`0 0 ${rect.width} ${rect.height}`);
  c.setAttribute("style",`background:${cs.getPropertyValue("--bg").trim()}`);
  download("monstrous-chart.svg",new XMLSerializer().serializeToString(c),"image/svg+xml");
};
$("#btn-json").onclick=()=>{
  const out={
    generatedFrom:"AI:GO workspace logs",
    squads:(S.squads||[]).map(s=>({ws:s.ws,name:s.name,source:s.source,
      agents:s.agents.map(a=>({name:a.name,role:a.role,model:a.model,tools:a.tools,
        tasks:a.tasks,failed:a.failed,tokenEstimated:a.tok}))})),
    executions:S.execs.map(e=>({
      id:e.id, workspace:e.ws, squad:e.squadName, contract:e.contract,
      gradable:e.gradable, blocker:e.blocker, partial:!!e.partial,
      aigoStatus:e.aigoStatus, taskCounts:e.counts,
      tokens:e.tokens, billed:billed(e), durationMs:e.durationMs,
      phases:e.phases.map(p=>({phase:p.k,ms:p.ms})),
      tasks:e.tasks.map(t=>({title:t.title,agent:t.agentName,status:t.status,
        durationMs:t.durationMs,tokenEstimated:t.tok||0,gradable:t.answer.gradable,
        checks:t.answer.checks.map(k=>({check:k.k,ok:k.ok,detail:k.d}))}))
    }))};
  download("monstrous-normalized.json",JSON.stringify(out,null,2),"application/json");
};
