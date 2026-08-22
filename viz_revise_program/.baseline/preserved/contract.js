/* ═══════════════════════════════════════════════════════════════════════
   출력 계약 — judge 가 무엇을 읽는지. 문항 지문에서 그대로 옮겼다.
   "Only what lies between *** PATCH START *** and *** PATCH END *** is graded.
    If more than one appears, the last one is used."
   ═══════════════════════════════════════════════════════════════════════ */
const PS="*** PATCH START ***", PE="*** PATCH END ***";

/* 벤치마크는 트랙이 셋이고, 트랙마다 출력 계약이 다르다.
   auto_test/test_sample 실측 (121문항):

     coding   20 — kind: swebench 13 / livecodebench 7,  계약: patch
     math     59 — kind: math,                            계약: boxed
     generic  42 — kind: letter_match,                    계약: letter

   swebench 13개는 데이터셋 자체가 gradable:false 다. 로컬에 Docker 이미지가 없어
   채점이 불가능하다고 파일에 적혀 있다. 그건 우리가 어떻게 할 수 있는 영역이 아니다.

   트랙은 지문의 생김새로 찍는다. 계약이 있으면 계약이 곧 트랙이고,
   계약이 잘려 나갔어도 지문의 모양으로는 알아볼 수 있다 — 그 구분이 필요한 이유가 아래에 있다. */
const TRACK={
  coding :{label:"coding",  contract:"patch",  c:"var(--accent)"},
  math   :{label:"math",    contract:"boxed",  c:"var(--ok)"},
  generic:{label:"generic", contract:"letter", c:"var(--prog)"},
  unknown:{label:"—",       contract:"unknown",c:"var(--fg-faint)"}
};
function trackOf(request){
  const r=String(request||"");
  if(r.includes(PS)||/resolving an issue in an existing repository/i.test(r)) return "coding";
  if(/ANSWER: <letter>/.test(r)||/^Options:\s*$/m.test(r)) return "generic";
  if(/\\+boxed/.test(r)) return "math";
  // 계약 절이 잘려 나간 지문. 남은 꼬리와 수식으로 math 를 알아본다.
  if(/This problem's answer is an integer|Express your answer|\$\$|\\frac|\\sqrt/.test(r)) return "math";
  return "unknown";
}

/* 출력 계약은 문항마다 다르다. 요청 지문의 "=== REQUIRED OUTPUT ===" 절이 알려준다.
     patch  — *** PATCH START *** … SEARCH/REPLACE … *** PATCH END ***   (coding)
     boxed  — FINAL ANSWER: \boxed{<answer>}                              (math)
     letter — ANSWER: <letter>                                            (generic)
   계약을 안 보고 patch 마커만 검사하면 math 문항이 전부 "마커 없음"으로 오판된다.

   "계약 없음"과 "계약 불명"은 다르다.
     missing — 지문에 === REQUIRED OUTPUT === 절 자체가 없다. 모델은 형식을 들은 적이 없다.
     unknown — 절은 있는데 우리가 못 알아봤다. 검사기를 고쳐야 할 쪽.
   실측: ikkim 의 실행 13개 중 6개가 missing 이었다. 원본 문항에는 boxed 계약이 붙어 있는데
   실행에 들어간 지문에서만 잘려 있었다. 이건 "판정 보류"가 아니라 러너 쪽에서 고칠 일이다. */
const CONTRACT={
  patch  :{label:"패치 마커",     spec:"*** PATCH START *** … *** PATCH END ***"},
  boxed  :{label:"FINAL ANSWER",  spec:"FINAL ANSWER: \\boxed{<answer>}"},
  letter :{label:"ANSWER: <보기>", spec:"ANSWER: <letter> (줄에 다른 것 없이)"},
  missing:{label:"계약 미전송",   spec:"요청 지문에 === REQUIRED OUTPUT === 절이 없음"},
  unknown:{label:"출력 계약 불명", spec:"요청 지문에서 계약을 찾지 못함"}
};
const REQOUT="=== REQUIRED OUTPUT ===";
/* 실제 형식을 가리키는 계약. missing·unknown 은 형식 이름이 아니라 상태라서
   "응답에 X 가 없다" 같은 문장에 그대로 끼워 넣으면 말이 안 된다. */
const REAL_CONTRACT=new Set(["patch","boxed","letter"]);
function contractOf(request){
  const r=String(request||"");
  if(r.includes(PS)) return "patch";
  if(/FINAL ANSWER:\s*\\+boxed\s*\{/.test(r)||/\\+boxed\{<answer>\}/.test(r)) return "boxed";
  if(/ANSWER:\s*<letter>/.test(r)) return "letter";
  if(/\boption letter\b|\bsingle letter\b|answer letter/i.test(r)) return "letter";
  // 객관식 문항은 보기 목록이 곧 계약이다. 계약 절이 잘려 나갔어도 요구되는 것은
  // 보기 중 하나의 문자 하나이고, 채점기(letter_match)가 보는 것도 그것뿐이다.
  // 그래서 이 경우는 판정을 미루지 않는다.
  if(/^Options:\s*$/m.test(r)&&optionsOf(r).length>=2) return "letter";
  // 계약 절이 통째로 없으면 모델이 형식을 들은 적이 없다는 뜻이다. 못 알아본 것과 구분한다.
  if(!r.includes(REQOUT)) return "missing";
  return "unknown";
}

/* generic(객관식) 문항의 보기 목록. 지문의 "Options:" 절에 A. … J. 로 붙어 있다.
   이 절이 있다는 것 자체가 계약이다 — 보기 중 하나의 문자를 내면 된다.
   그래서 === REQUIRED OUTPUT === 절이 잘려 나갔어도 무엇을 요구하는지는 알 수 있고,
   "계약 미전송"으로 판정을 미룰 이유가 없다. */
function optionsOf(request){
  const r=String(request||"");
  const i=r.search(/^Options:\s*$/m);
  if(i<0) return [];
  return [...r.slice(i).matchAll(/^\s*([A-Z])\.\s+(.+?)\s*$/gm)].map(m=>({letter:m[1], text:m[2]}));
}

/* generic(객관식)의 출력 계약. 지문이 그대로 적어 준다:

     End your answer with a line of exactly this form:
     ANSWER: <letter>
     Replace <letter> with the single letter of the option you choose,
     and write nothing else on that line.
     If more than one appears, the last one is used.
     Anything before it is ignored, not penalised.

   그래서 검사는 네 가지다.
     1) "ANSWER:" 로 시작하는 줄이 있는가            — 여러 개면 마지막 것
     2) 그 줄에 보기 문자 하나만 있는가              — "write nothing else on that line"
     3) 그 문자가 보기 목록 안에 있는가
     4) 대문자인가                                    — 권장. 채점기가 구분하는지 확인 안 됨

   앞에 다른 텍스트가 오는 것은 계약이 명시적으로 허용한다("ignored, not penalised").
   반대로 ANSWER: 줄 없이 문자만 덜렁 있는 것은 계약이 아니다 — "a line of exactly this form"
   이라고 못박혀 있다. 그래서 그건 통과로 세지 않고 아래에서 따로 짚어 준다. */
function inspectLetter(text,options){
  const t=String(text||""), checks=[], opts=options||[];

  const tagged=[...t.matchAll(/^[ \t]*ANSWER:[ \t]*(.*)$/gmi)];
  const tag=tagged.length?tagged[tagged.length-1]:null;      // 규칙: 여러 개면 마지막 것
  const body=tag?tag[1].trim():"";
  checks.push({k:"ANSWER: 줄", ok:!!tag,
    d:tag?(tagged.length>1?`${tagged.length}개 중 마지막 것 사용`:"발견"):"없음. judge 가 추출할 것이 없습니다"});

  const one=/^[A-Za-z]$/.test(body);
  checks.push({k:"그 줄에 문자 하나만", ok:one,
    d:tag?(one?`"${body}"`:`"${body.slice(0,24)}" — 줄에 다른 것이 같이 있습니다`):"—"});

  if(opts.length){
    const inSet=one&&opts.some(o=>o.letter===body.toUpperCase());
    checks.push({k:"보기 목록 안", ok:one?inSet:false,
      d:one?(inSet?`${opts.length}개 보기 중 하나`:`목록에 ${body.toUpperCase()} 가 없습니다`):"—"});
  }
  const required=checks.every(c=>c.ok);

  // 계약을 못 맞춘 응답이 얼마나 가까웠는지 짚는다. 둘 다 "형식 하나 때문에 0점"인 자리다.
  //   near   — ANSWER: 줄 없이 문자만 있다. 계약은 줄 형태를 요구하므로 통과가 아니다.
  //   hint   — 값은 보기와 같은데 문자를 안 냈다. 실측: 보기 D. $1,680 인데 \boxed{1680} 을 냄.
  const lines=t.split(/\r?\n/);
  let near=null;
  if(!tag) for(let i=lines.length-1;i>=0;i--){
    const s=lines[i].trim(); if(!s) continue;
    const m=s.match(/^\(?([A-Za-z])[).:]?$/);
    if(m&&(!opts.length||opts.some(o=>o.letter===m[1].toUpperCase()))) near={letter:m[1], raw:s};
    break;
  }
  if(near) checks.push({k:"ANSWER: 없이 문자만", ok:null,
    d:`마지막 줄이 "${near.raw}" 입니다. 지문은 "ANSWER: ${near.letter.toUpperCase()}" 라는 줄을 요구합니다`});

  let hint=null;
  if(!required&&!near&&opts.length){
    const norm=s=>String(s).toLowerCase().replace(/[\s,$]/g,"");
    const cand=[];
    const b=lastBoxed(t); if(b&&b.body) cand.push(b.body);
    for(let i=lines.length-1;i>=0&&cand.length<4;i--){ const s=lines[i].trim(); if(s) cand.push(s); }
    for(const c of cand){
      const hitOpt=opts.find(o=>norm(o.text)===norm(c)||(norm(o.text).includes(norm(c))&&norm(c).length>2));
      if(hitOpt){ hint={letter:hitOpt.letter, text:hitOpt.text, gave:c}; break; }
    }
  }
  if(hint) checks.push({k:"값은 보기와 일치", ok:null,
    d:`"${hint.gave.slice(0,24)}" 는 보기 ${hint.letter} (${hint.text.slice(0,24)}) 와 같습니다. 문자만 냈으면 채점됐습니다`});

  // 보기는 A. … J. 로 대문자다. 채점기가 대소문자를 구분하는지는 확인되지 않았으므로
  // 이것 하나로 "채점 불가"를 단정하지 않는다. boxed 의 "FINAL ANSWER:" 접두사와 같은 취급이다.
  const upper=one&&/^[A-Z]$/.test(body);
  checks.push({k:"대문자 (권장)", ok:one?(upper||null):null,
    d:!one?"—":upper?"보기 표기 그대로":"소문자입니다. 채점기가 구분하는지는 확인되지 않았습니다"});

  const si=tag?tag.index:-1;
  return {gradable:required, advisory:!upper, hint, near, checks, body, si,
          ei:si>=0?si+tag[0].length:-1, text:t, kind:"letter"};
}

/* 채점 판정 한 줄. 같은 분기를 곳곳에 복사해 두면 분류가 하나 늘 때마다 어긋난다.
   실제로 "계약 미전송"을 넣으면서 여덟 군데가 동시에 틀렸다. */
const UNDECIDED=new Set(["blocked","unknown","nocontract"]);
function verdictOf(e){
  if(e.gradable)               return {k:"ok",  label:"채점 적격"};
  if(e.blocker==="blocked")    return {k:"warn",label:"실행 불가"};
  if(e.blocker==="nocontract") return {k:"warn",label:"계약 미전송"};
  if(e.partial)                return {k:"",    label:"부분 기록"};
  if(e.blocker==="unknown")    return {k:"",    label:"판정 보류"};
  return {k:"bad", label:"답 형식 없음"};
}

/* 마지막 \boxed{ 의 내용을 짝 맞는 중괄호까지 읽는다. 중첩 중괄호(\frac{a}{b})가 흔해서
   정규식으로는 못 자른다. 규칙상 여러 개면 마지막 것이 채점된다. */
function lastBoxed(t){
  const i=t.lastIndexOf("\\boxed{");
  if(i<0) return null;
  let d=0;
  for(let j=i+6;j<t.length;j++){
    if(t[j]==="{") d++;
    else if(t[j]==="}"){ d--; if(!d) return {start:i, end:j+1, body:t.slice(i+7,j)}; }
  }
  return {start:i, end:-1, body:null};      // 닫히지 않음
}

function inspectBoxed(text){
  const t=String(text||""), checks=[];
  const b=lastBoxed(t);
  checks.push({k:"\\boxed{} 존재", ok:!!b, d:b?"발견 (마지막 것 사용)":"없음. judge 가 추출할 것이 없습니다"});
  checks.push({k:"중괄호 짝", ok:!!(b&&b.end>0), d:b?(b.end>0?"닫힘":"열린 채로 끝남"):"—"});
  const body=b&&b.body!=null?b.body.trim():"";
  checks.push({k:"답이 비어있지 않음", ok:body.length>0, d:body?`"${body.slice(0,28)}"`:"빈 값"});

  // 여기까지가 필수. 아래는 권장이다.
  // 지문은 "FINAL ANSWER: \boxed{…}" 형태의 줄을 요구하지만, "여러 개면 마지막 것을 쓴다"는
  // 규칙이 \boxed{} 를 가리키는 것으로 읽히고 math_verify 계열 채점기는 보통 마지막 \boxed{} 만
  // 뽑는다. 접두사가 실제로 필수인지는 확인되지 않았다.
  // 그래서 이것 때문에 "채점 불가"로 단정하지 않는다 — 확인 안 된 것을 확정으로 적으면 안 된다.
  const prefix=/FINAL ANSWER:\s*\\boxed\{/.test(t);
  const required=checks.every(c=>c.ok);
  checks.push({k:"FINAL ANSWER: 접두사 (권장)", ok:prefix||null,
    d:prefix?"있음":"없음. 지문은 요구하지만 채점기가 실제로 요구하는지는 확인되지 않았습니다"});
  return {gradable:required, advisory:!prefix, checks, body,
          si:b?b.start:-1, ei:b?b.end:-1, text:t, kind:"boxed"};
}

function inspectAnswer(text,kind,options){
  if(kind==="boxed")  return inspectBoxed(text);
  if(kind==="letter") return inspectLetter(text,options);
  if(kind==="unknown"||kind==="missing"){
    // 계약을 모르면 판정하지 않는다. 모르는 것을 "불합격"으로 적으면 화면이 거짓말을 한다.
    // 다만 두 경우의 이유는 다르다 — 못 알아본 것과, 애초에 보내지 않은 것.
    const t=String(text||"");
    return {gradable:null, kind, text:t, si:-1, ei:-1, body:"",
      checks:[{k:CONTRACT[kind].label, ok:null,
        d:kind==="missing"?"요청 지문에 출력 계약이 없어 모델이 형식을 들은 적이 없습니다"
                          :"이 문항의 출력 계약을 확인하지 못해 판정을 보류합니다"}]};
  }
  const t=String(text||""), checks=[];
  const si=t.lastIndexOf(PS);                       // 규칙: 여러 개면 마지막 것
  checks.push({k:"*** PATCH START *** 마커", ok:si>=0, d:si>=0?"발견 (마지막 것 사용)":"없음. judge 가 추출할 것이 없습니다"});
  const ei=si>=0?t.indexOf(PE,si+PS.length):-1;
  checks.push({k:"*** PATCH END *** 마커", ok:ei>=0, d:ei>=0?"START 뒤에 있음":"없음"});
  const body=(si>=0&&ei>=0)?t.slice(si+PS.length,ei):"";
  const nS=(body.match(/<{7} SEARCH/g)||[]).length;
  const nM=(body.match(/^={7}\s*$/gm)||[]).length;
  const nR=(body.match(/>{7} REPLACE/g)||[]).length;
  checks.push({k:"SEARCH / ======= / REPLACE 짝", ok:nS>0&&nS===nM&&nS===nR, d:`${nS} / ${nM} / ${nR}`});
  // 모든 <<<<<<< SEARCH 앞에는 경로 줄이 하나 있어야 한다
  let paths=0, bad=0;
  const lines=body.split(/\r?\n/);
  lines.forEach((ln,i)=>{
    if(!/^<{7} SEARCH/.test(ln)) return;
    let j=i-1; while(j>=0&&!lines[j].trim()) j--;
    if(j>=0&&lines[j].trim()&&!/^[<>=]{7}/.test(lines[j])) paths++; else bad++;
  });
  checks.push({k:"블록마다 경로 줄", ok:nS>0&&bad===0, d:nS?`경로 ${paths} · 누락 ${bad}`:"블록 없음"});
  // ei 는 강조 구간의 '끝 다음' 위치로 통일한다 — boxed 쪽과 같은 규약이어야
  // 장부 대조에서 한 코드로 하이라이트할 수 있다. PE 마커까지 포함한다.
  return {gradable:checks.every(c=>c.ok), checks, body, si,
          ei:ei>=0?ei+PE.length:-1, text:t, kind:"patch"};
}
