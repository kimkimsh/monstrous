#!/usr/bin/env bash
# viz/src/app.html 에 샘플 로그를 끼워 넣어 단일 파일 산출물을 만든다.
#
# 왜 끼워 넣는가 — file:// 로 연 페이지는 CORS 때문에 옆 파일을 fetch 하지 못한다.
# 심사 자리에서 "더블클릭하면 바로 뜬다"를 보장하려면 샘플이 파일 안에 있어야 한다.
# 06-시각화-설계-가이드.md §7: "시연 환경이 오프라인일 수 있다. CDN 의존을 없앨 것."
#
# 평소 사용은 폴더를 고르는 쪽이다. 이 샘플은 데모와 회귀 확인용이다.
#
#   usage: bash viz/tools/build.sh [logs디렉토리]
set -euo pipefail

cd "$(dirname "$0")/../.."
SRC="viz/src/app.html"
LOGS="${1:-squad/test/logs}"
OUT="viz/trace-visualizer.html"

[ -f "$SRC" ] || { echo "no template: $SRC" >&2; exit 1; }
for f in history.json events.jsonl; do
  [ -f "$LOGS/$f" ] || { echo "no $f in $LOGS" >&2; exit 1; }
done

# 임베드 안전성: 내용에 </script 가 있으면 페이지가 깨진다.
for f in history.json events.jsonl; do
  if grep -qi '</script' "$LOGS/$f"; then
    echo "거부: $LOGS/$f 안에 '</script' 가 있어 인라인 임베드가 안전하지 않다" >&2; exit 1
  fi
done

# 마커는 정확히 한 줄씩만 있어야 한다.
# 소스 코드 안에 마커 문자열을 적으면 sed 가 그 줄까지 치환 대상으로 잡아
# 데이터를 두 번 끼워 넣는다 (실제로 한 번 당했다). 그래서 개수를 먼저 확인한다.
for m in @HISTORY@ @EVENTS@; do
  n=$(grep -c -- "$m" "$SRC" || true)
  [ "$n" = "1" ] || { echo "마커 $m 가 $n 번 나온다. 정확히 1번이어야 한다." >&2; exit 1; }
done

sed -e "/@HISTORY@/{r ${LOGS}/history.json" -e "d}" \
    -e "/@EVENTS@/{r ${LOGS}/events.jsonl"  -e "d}" "$SRC" > "$OUT"

# 산출물 크기 검산 — 템플릿 + 두 로그 파일에 근접해야 한다
exp=$(( $(wc -c < "$SRC") + $(wc -c < "$LOGS/history.json") + $(wc -c < "$LOGS/events.jsonl") ))
got=$(wc -c < "$OUT")
if [ "$got" -gt $(( exp + exp / 10 )) ]; then
  echo "경고: 산출물이 예상($exp)보다 훨씬 크다($got). 마커가 중복 치환됐을 수 있다." >&2
fi

echo "built  $OUT"
echo "  sample : $LOGS"
echo "  size   : $(wc -c < "$OUT") bytes"
