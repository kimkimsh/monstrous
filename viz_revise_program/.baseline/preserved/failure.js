/* 실패 분류 — 규칙표를 화면에 그대로 노출한다. 추측이 아니라 규칙임을 보이기 위해. */
const RULES=[
  {re:/exceeds the available context size/i, kind:"context_overflow", owner:"configuration",
   why:"컨텍스트 상한 초과. 설정에서 늘리면 해결됩니다. 우리가 고칠 수 있습니다"},
  {re:/HTTP 5\d\d/,                          kind:"upstream_error",   owner:"organizer",
   why:"모델 서버 오류. 팀 책임이 아닙니다"},
  {re:/HTTP 429|rate.?limit/i,               kind:"rate_limit",       owner:"policy",
   why:"요청 제한에 걸렸습니다"},
  {re:/timeout|timed out|deadline/i,         kind:"wallclock_cap",    owner:"policy",
   why:"시간 상한에 걸렸습니다"},
];
function classify(err){
  const e=String(err||"");
  for(const r of RULES) if(r.re.test(e)) return {...r, http:(e.match(/HTTP (\d{3})/)||[])[1]||null, raw:e};
  return {kind:"unclassified", owner:"—", why:"규칙표에 없는 오류. 규칙을 추가해야 합니다", http:null, raw:e};
}
