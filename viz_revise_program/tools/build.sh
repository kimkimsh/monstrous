#!/usr/bin/env bash
# src/app.html 을 산출물 trace-visualizer.html 로 낸다.
#
# 이 스크립트가 하는 일은 복사와 검사다. 검사가 본체다 — 넘어가면 안 되는 것들을
# 여기서 막지 않으면 개편이 조용히 퇴행한다.
#
#   usage: bash tools/build.sh
set -euo pipefail

cd "$(dirname "$0")/.."
SRC="src/app.html"
OUT="trace-visualizer.html"
BASE=".baseline/preserved"

fail(){ echo "FAIL: $1" >&2; exit 1; }
ok(){ printf '  ok   %s\n' "$1"; }

# 검사 두 개는 파이썬으로 쓰였다. 파이썬이 없는 자리에서 그 검사가 조용히 건너뛰어지면
# 검사가 아니라 장식이 된다. 그래서 같은 규칙의 Perl 판을 같이 두고 둘 중 되는 쪽을 쓴다.
# 윈도우의 python3 는 스토어 안내문만 찍고 끝나는 껍데기일 수 있어 실제로 돌려 보고 고른다.
py_or_perl(){
  local py="$1" pl="$2"; shift 2
  if command -v python3 >/dev/null 2>&1 && python3 -c "import sys,re" >/dev/null 2>&1; then
    python3 "$py" "$@"
  else
    perl "$pl" "$@"
  fi
}

[ -f "$SRC" ] || fail "no source: $SRC"
echo "checking $SRC"

# ── 단일 파일 · 오프라인 ──────────────────────────────────────────────
# 치환 마커가 남아 있으면 예전 빌드 방식의 잔재다. 화면에 그대로 새어 나간다.
grep -q '@HISTORY@\|@EVENTS@' "$SRC" && fail "치환 마커가 남아 있다"
# 외부 요청이 있으면 오프라인 시연에서 깨진다. CDN·폰트·이미지 전부 금지.
grep -qE '(src|href)="https?://|XMLHttpRequest' "$SRC" && fail "외부 요청이 있다"
grep -qE '\bfetch\(' "$SRC" && fail "fetch( 가 있다 — 외부 요청 0 원칙"
ok "외부 요청 0 · 잔재 마커 0"

# ── 토큰 규율 ─────────────────────────────────────────────────────────
# 글자 크기는 '토큰이 7종인가' 로 센다. 사용처는 전부 var(--fs-*) 라서
# 'font-size:...px' 로 세면 언제나 0 이 나오는 — 절대 실패하지 않는 — 검사가 된다.
n=$(grep -oE '^[[:space:]]*--fs-[a-z]+:[0-9.]+px' "$SRC" | sort -u | wc -l | tr -d ' ')
[ "$n" -eq 7 ] || fail "글자 크기 토큰 $n 종 (정확히 7)"
ok "글자 크기 토큰 7종"

# 사용처에 리터럴이 없는지 따로 본다. SVG 속성형("font-size":9)까지 잡는다 —
# 현행 파일에 그 형태가 14개 있었고 예전 검사는 그걸 통째로 놓쳤다.
if grep -oE '(font-size:|"font-size":)[[:space:]]*[0-9.]+' "$SRC" | grep -q .; then
  grep -noE '(font-size:|"font-size":)[[:space:]]*[0-9.]+' "$SRC" | head >&2
  fail "font-size 리터럴 (var(--fs-*) 만 허용)"
fi
ok "font-size 리터럴 0"

# '(padding|margin|gap):' 는 '--cell-gap:2px' 안의 'gap:' 에도 걸린다 —
# 앞 경계를 넣지 않으면 검사가 자기 토큰을 위반으로 신고한다.
if grep -oE '(^|[;{[:space:]])(padding|margin|gap|row-gap|column-gap):[^;}]*' "$SRC" \
   | grep -oE '[0-9]+px' | sort -u \
   | grep -vE '^(0|1|2|4|8|12|16|24|32|48|64)px$' | grep -q .; then
  grep -oE '(^|[;{[:space:]])(padding|margin|gap|row-gap|column-gap):[^;}]*' "$SRC" \
   | grep -oE '[0-9]+px' | sort -u \
   | grep -vE '^(0|1|2|4|8|12|16|24|32|48|64)px$' >&2
  fail "4px 격자를 벗어난 간격"
fi
ok "간격은 4px 격자 위"

if grep -o 'border-radius:[^;}]*' "$SRC" | sort -u \
   | grep -vE 'border-radius:(0|50%)$' | grep -q .; then
  grep -o 'border-radius:[^;}]*' "$SRC" | sort -u | grep -vE 'border-radius:(0|50%)$' >&2
  fail "border-radius 는 0 또는 50% 만"
fi
ok "border-radius 0 만"

# grep -c 는 '줄 수' 다. 한 줄에 두 개 있으면 하나로 샌다 (현행: 선언 89 / 줄 85).
n=$(grep -o 'style="' "$SRC" | wc -l | tr -d ' ')
[ "$n" -le 20 ] || fail "인라인 style $n 개 (최대 20)"
ok "인라인 style $n 개 (최대 20)"

grep -q 'transition:all' "$SRC" && fail "transition: all 금지"
ok "transition: all 없음"

# 이징은 cubic-bezier 4종(--ease · --ease-pop · --ease-move · --ease-exit)뿐.
n=$(grep -o 'cubic-bezier([^)]*)' "$SRC" | sort -u | wc -l | tr -d ' ')
[ "$n" -le 4 ] || { grep -o 'cubic-bezier([^)]*)' "$SRC" | sort -u >&2; fail "이징 $n 종 (최대 4)"; }
ok "이징 $n 종"

# 키워드 이징이 섞이면 위 검사가 못 잡는다. 긴 것부터 늘어놓아야 ease-out 이
# 'ease' 로 먼저 걸려 통과하는 일이 없다 (스펙 §11 의 \b 판은 var(--ease-pop) 도 잡는다).
grep -qE '(transition|animation)[^;}]*[ :,]ease(-in-out|-in|-out)?([ ,;}]|$)' "$SRC" \
  && fail "이징 키워드 금지 — var(--ease*) 를 쓴다"
ok "이징 키워드 없음"

# ── 셀 게이지 ─────────────────────────────────────────────────────────
# background-image 는 애니메이션 되지 않는 속성이라 이 조합은 조용히 아무것도 안 한다.
grep -qE 'transition:[^;}]*background[^;}]*steps' "$SRC" \
  && fail "게이지는 --on 을 전이한다 (background 는 discrete)"
grep -q "@property --on" "$SRC" || fail "@property --on 등록이 없다"
ok "셀 게이지는 --on 을 전이한다"

# ── 색 리터럴 ─────────────────────────────────────────────────────────
# CSS 변수 정의와 인쇄용 흑백 말고는 hex 가 나오면 안 된다. 주석 안의 hex 는 세지
# 않는다 — 왜 그 값인지 적어 둔 설명까지 위반으로 신고하면 검사가 주석을 쫓아낸다.
py_or_perl tools/colorlit.py tools/colorlit.pl "$SRC" || fail "CSS 변수 밖에 색 리터럴이 있다"
ok "색 리터럴은 토큰 정의 안에만"

# ── 보존 경계 ─────────────────────────────────────────────────────────
# 줄 번호는 리팩터링 한 번에 무너진다. 마커로 감싸고 마커로 검사한다.
# 기준선은 개편 전 viz/src/app.html 에서 그대로 떠 온 일곱 조각이다.
for k in contract failure collect model i18n load export; do
  [ -f "$BASE/$k.js" ] || fail "보존 기준선 $BASE/$k.js 가 없다"
  awk "/@preserve:begin $k \*\//{f=1;next} /@preserve:end $k \*\//{f=0} f" "$SRC" > "/tmp/new.$k"
  [ -s "/tmp/new.$k" ] || fail "보존 마커 $k 를 소스에서 못 찾았다"
  # 줄끝은 체크아웃 설정이 정한다. CRLF 로 받은 자리에서 이 검사가 전부 실패하면
  # 판정이 바뀐 것과 줄끝이 바뀐 것을 구분할 수 없다. 내용만 본다.
  tr -d '\r' < "$BASE/$k.js" > "/tmp/base.$k"
  tr -d '\r' < "/tmp/new.$k" > "/tmp/cmp.$k"
  diff -q "/tmp/base.$k" "/tmp/cmp.$k" >/dev/null || {
    diff "/tmp/base.$k" "/tmp/cmp.$k" | head -20 >&2
    fail "보존 구간 $k 가 변경됨"
  }
done
ok "보존 구간 7개 바이트 동일 (contract failure collect model i18n load export)"

# ── 명암비 ────────────────────────────────────────────────────────────
py_or_perl tools/contrast.py tools/contrast.pl "$SRC" || fail "명암비 미달"

# ── 문법 ──────────────────────────────────────────────────────────────
if command -v node >/dev/null 2>&1; then
  awk '/^<script>$/{f=1;next} /^<\/script>$/{f=0} f' "$SRC" > /tmp/appjs.js
  node --check /tmp/appjs.js || fail "JavaScript 문법 오류"
  ok "JavaScript 문법"
fi

cp "$SRC" "$OUT"
echo
echo "built  $OUT"
echo "  size : $(wc -c < "$OUT" | tr -d ' ') bytes  (예산 400000)"
[ "$(wc -c < "$OUT" | tr -d ' ')" -le 400000 ] || fail "파일 크기 예산 초과"
