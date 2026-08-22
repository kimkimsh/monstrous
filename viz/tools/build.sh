#!/usr/bin/env bash
# viz/src/app.html 을 산출물 viz/trace-visualizer.html 로 낸다.
#
# 예전에는 샘플 로그를 파일 안에 끼워 넣었다. 지금은 워크스페이스 폴더를 직접 고르는
# 방식이라 샘플이 필요 없다. 그 덕에 산출물이 400KB 대에서 100KB 아래로 줄었다.
#
# 이 스크립트가 하는 일은 복사와 검사뿐이다. 그래도 남겨두는 이유는
# 산출물 경로를 한 곳에 고정하고, 넘어가면 안 되는 것들을 여기서 막기 위해서다.
#
#   usage: bash viz/tools/build.sh
set -euo pipefail

cd "$(dirname "$0")/../.."
SRC="viz/src/app.html"
OUT="viz/trace-visualizer.html"

[ -f "$SRC" ] || { echo "no source: $SRC" >&2; exit 1; }

# 치환 마커가 남아 있으면 예전 빌드 방식의 잔재다. 화면에 그대로 새어 나간다.
if grep -q '@HISTORY@\|@EVENTS@' "$SRC"; then
  echo "거부: $SRC 에 치환 마커가 남아 있다. 샘플 주입은 폐지됐다." >&2; exit 1
fi

# 외부 요청이 있으면 오프라인 시연에서 깨진다. CDN·폰트·이미지 전부 금지.
if grep -qE '(src|href)="https?://|fetch\(|XMLHttpRequest' "$SRC"; then
  echo "거부: $SRC 에 외부 요청이 있다. 단일 파일·오프라인 원칙을 깬다." >&2; exit 1
fi

cp "$SRC" "$OUT"

echo "built  $OUT"
echo "  size : $(wc -c < "$OUT") bytes"
