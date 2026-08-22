/* ═══════════════════════════════════════════════════════════════════════
   로드
   ═══════════════════════════════════════════════════════════════════════ */
function finish(){
  build();
  if(!S.execs.length){
    const got=Object.keys(SEEN.kinds);
    throw new Error(SEEN.files
      ? `파일 ${SEEN.files}개를 읽었지만 실행을 세우지 못했습니다. 읽힌 것: ${got.join(", ")||"없음"}. `+
        `logs/ 폴더째로 고르거나, 최소한 history.json 과 events.jsonl 을 함께 넣어주세요.`
      : "파일을 하나도 읽지 못했습니다.");
  }
  // 부분 로드 경고 — 되는 만큼은 그리되, 무엇이 빠졌는지 화면에 남긴다
  const miss=[];
  if(!SEEN.kinds["history.json"]) miss.push("history.json (응답 본문과 에이전트 이름. 없으면 장부 대조와 채점 적격성 검사를 못 합니다)");
  if(!SEEN.kinds["events.jsonl"]) miss.push("events.jsonl (웨이브·위상·토큰 시계열)");
  S.missing=miss;
  S.sel=null;
  const k=Object.entries(SEEN.kinds).map(([a,b])=>`${a} ×${b}`).join(" · ");
  const ws=[...new Set(S.execs.map(e=>e.ws))];
  S.srcParts={files:SEEN.files,ws:ws.length,kinds:k}; renderSrc();
  // 워크스페이스 필터 채우기. 하나뿐이면 굳이 보여주지 않는다.
  const sel=$("#f-ws");
  sel.innerHTML=`<option value="">모든 스쿼드</option>`+
    (S.squads||[]).map(s=>`<option value="${esc(s.sq)}">${esc(s.name)} (${s.execs.length})</option>`).join("");
  sel.style.display=ws.length>1?"":"none";
  sel.onchange=()=>{renderList();syncHash();};
  // 스쿼드가 둘 이상이면 비교 탭이 의미가 있다는 것을 버튼에 표시한다.
  const cmpBtn=document.querySelector('[data-mode="cmp"]');
  if(cmpBtn){ cmpBtn.dataset.count=(S.squads||[]).length>1?String(S.squads.length):""; }
  $("#drop").hidden=true;
  renderHeader(); renderList(); renderPane();
  applyHash();
}
function reset(){ RAW.hist.clear();RAW.ev.clear();RAW.task.clear();RAW.log.clear();RAW.artifact.clear();RAW.taskmd.clear();RAW.squad.clear();RAW.execWs.clear();
  RAW.logIndex.clear();RAW.report.clear();
  SEEN.files=0;SEEN.kinds={};SEEN.skipped=[];SEEN.ws=new Set(); }

/* 파일 하나를 텍스트로 읽는다.
   FileReader 는 onload/onerror 중 어느 것도 안 부르는 경우가 있어(중단·권한 등)
   콜백 카운터로 완료를 세면 조용히 멈춘다 — 실제로 "읽는 중…"에서 멈췄다.
   그래서 프로미스로 감싸고 onabort 까지 잡고 타임아웃을 건다. */
function readText(file){
  const p=file.text ? file.text() : new Promise((res,rej)=>{
    const r=new FileReader();
    r.onload =()=>res(String(r.result));
    r.onerror=()=>rej(new Error("읽기 실패"));
    r.onabort=()=>rej(new Error("읽기 중단"));
    try{ r.readAsText(file); }catch(e){ rej(e); }
  });
  return Promise.race([p,
    new Promise((_,rej)=>setTimeout(()=>rej(new Error("시간 초과")),20000))]);
}

async function loadEntries(entries){
  reset();
  if(!entries.length){ setDfiles(null); setDerr(()=>t("파일이 없습니다. 폴더를 고르거나 파일을 끌어다 놓으세요.")); return; }
  setDerr(null);
  let done=0;
  const tick=()=>{ done++; renderDfiles(); };
  setDfiles(()=>`${t("읽는 중…")} ${done} / ${entries.length}`);

  // allSettled 라서 개별 실패가 전체를 멈추지 못한다.
  const res=await Promise.allSettled(entries.map(async ({file,path})=>{
    try{ addFile(path||file.name, file.name, await readText(file)); }
    catch(e){ SEEN.skipped.push(`${file.name} (${e.message})`); throw e; }
    finally{ tick(); }
  }));
  const bad=res.filter(r=>r.status==="rejected").length;

  try{ finish(); if(bad) console.warn("읽지 못한 파일",SEEN.skipped); }
  catch(err){ showLoadError(err,bad); }
}

function showLoadError(err,bad){
  setDerr(()=>err.message);        // 예외 메시지는 로그 쪽 값이라 번역하지 않는다
  setDfiles(()=>{
    const kinds=Object.entries(SEEN.kinds).map(([a,b])=>`${a} ×${b}`).join(" · ")||t("인식된 파일 없음");
    return t("읽은 것:")+" "+kinds+
      (bad?"  |  "+tn("읽기 실패 {0}개",bad):"")+
      (SEEN.skipped.length?"  |  "+t("건너뜀:")+" "+SEEN.skipped.slice(0,8).join(", "):"");
  });
}

const asEntries=fileList=>[...fileList].map(f=>({file:f, path:f.webkitRelativePath||f.name}));

/* 폴더 드롭 — DataTransferItem 을 재귀로 훑는다.
   readEntries / entry.file 은 실패 콜백을 안 주면 조용히 끝나지 않으므로 전부 채워 둔다.
   어떤 경로로 실패하든 반드시 resolve 한다 — 여기서 멈추면 화면이 "읽는 중"에 갇힌다. */
function walk(entry, out, prefix=""){
  return new Promise(res=>{
    if(!entry) return res();
    if(entry.isFile){
      entry.file(f=>{ out.push({file:f, path:prefix+entry.name}); res(); }, ()=>res());
      return;
    }
    if(!entry.isDirectory) return res();
    const rd=entry.createReader(), all=[];
    (function next(){
      rd.readEntries(es=>{
        if(!es.length){ Promise.all(all).then(()=>res(),()=>res()); return; }
        for(const e of es) all.push(walk(e,out,prefix+entry.name+"/"));
        next();
      }, ()=>{ Promise.all(all).then(()=>res(),()=>res()); });
    })();
  });
}

$("#btn-dir").onclick=()=>$("#in-dir").click();
$("#btn-file").onclick=()=>$("#in-file").click();
$("#in-dir").onchange=e=>loadEntries(asEntries(e.target.files));
$("#in-file").onchange=e=>loadEntries(asEntries(e.target.files));
/* 폴더 다시 고르기 = 처음 화면으로. 주소에 붙은 인자는 이전 폴더의 실행 id 를 가리키고 있어
   새 폴더에서는 맞지 않는다. 그대로 두면 링크를 건넸을 때 없는 실행을 찾는다. */
$("#btn-load").onclick=()=>{
  $("#drop").hidden=false; setDerr(null);
  try{ history.replaceState(null,"",location.pathname+location.search); }catch{}
};
["dragenter","dragover"].forEach(t=>document.addEventListener(t,ev=>{
  ev.preventDefault(); $("#drop").hidden=false; $("#drop").classList.add("over");}));
document.addEventListener("dragleave",ev=>{ev.preventDefault();$("#drop").classList.remove("over");});
document.addEventListener("drop",async ev=>{
  ev.preventDefault(); $("#drop").classList.remove("over"); setDerr(null);
  setDfiles(()=>t("폴더를 훑는 중…"));
  try{
    // getAsEntry 는 drop 이벤트가 끝나기 전에 동기로 불러야 한다
    const items=[...(ev.dataTransfer.items||[])]
      .map(i=>i.webkitGetAsEntry&&i.webkitGetAsEntry()).filter(Boolean);
    if(items.length){
      const out=[];
      await Promise.all(items.map(e=>walk(e,out)));
      if(out.length) return loadEntries(out);
    }
  }catch(e){ console.warn("폴더 훑기 실패, 파일 목록으로 대체",e); }
  loadEntries(asEntries(ev.dataTransfer.files||[]));
});
