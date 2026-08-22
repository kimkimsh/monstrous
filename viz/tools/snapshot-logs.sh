#!/usr/bin/env bash
# AI:GO 워크스페이스의 logs/ 를 스냅샷해서 보관한다.
#
# 왜 필요한가 — index.json / events.jsonl / history.json 은 append 가 아니라
# 롤링 윈도우로 덮어써진다. 실측: 이벤트 id 0~50 을 담고 있던 파일이
# id 51~100 으로 통째로 갈렸고, history.json 에는 실행 3개만 남았다.
# 실행 하나당 이벤트 9개이므로, 42문항을 돌리면 끝났을 때 마지막 몇 문항만 남는다.
# 응답 본문(output)은 history.json 에만 있고 그게 채점 적격성 검사의 유일한 원천이다.
#
# 설계 — bash 는 파일 복사만 한다. 스냅샷 사이의 중복 제거(executionId 기준 병합)는
# 뷰어가 JavaScript 로 한다. JSON 병합을 셸에서 하지 않는 이유는 그게 셸이
# 잘 못하는 일이고, 여기서 깨지면 원본까지 잃기 때문이다.
#
#   bash viz/tools/snapshot-logs.sh <워크스페이스> [보관디렉토리]
#   bash viz/tools/snapshot-logs.sh <워크스페이스> [보관디렉토리] --watch [초]
#
# 예)
#   bash viz/tools/snapshot-logs.sh squad/test
#   bash viz/tools/snapshot-logs.sh squad/test viz/runs --watch 5
set -euo pipefail

WS="${1:-}"
ARCHIVE="${2:-viz/runs}"
MODE="${3:-once}"
INTERVAL="${4:-5}"

[ -n "$WS" ] || { echo "usage: bash viz/tools/snapshot-logs.sh <워크스페이스> [보관디렉토리] [--watch [초]]" >&2; exit 1; }
[ -d "$WS/logs" ] || { echo "logs/ 가 없다: $WS/logs" >&2; exit 1; }

mkdir -p "$ARCHIVE"
STATE="$ARCHIVE/.fingerprint"

# logs/ 의 상태 지문. 파일명·크기·mtime 을 합친다.
# 내용 해시가 아니라 메타데이터를 쓰는 이유는 history.json 이 140KB 를 넘어
# 매 초 해시를 뜨면 낭비이기 때문이다. 롤링 덮어쓰기는 항상 크기나 mtime 을 바꾼다.
fingerprint() {
  find "$WS/logs" -type f -printf '%f %s %T@\n' 2>/dev/null | sort
}

# index.json 에서 executionId 를 뽑는다 (jq 없이).
exec_ids() {
  grep -o '"executionId"[[:space:]]*:[[:space:]]*"[^"]*"' "$WS/logs/index.json" 2>/dev/null \
    | sed 's/.*"\([^"]*\)"$/\1/' | sort -u
}

snapshot() {
  local fp now dest n ids
  fp=$(fingerprint)
  if [ -f "$STATE" ] && [ "$fp" = "$(cat "$STATE")" ]; then
    return 1                      # 안 바뀜
  fi

  now=$(date -u +"%Y%m%dT%H%M%SZ")
  dest="$ARCHIVE/$now"
  # 같은 초에 두 번 도는 경우 대비
  local i=1
  while [ -e "$dest" ]; do dest="$ARCHIVE/$now-$i"; i=$((i+1)); done

  mkdir -p "$dest"
  cp -r "$WS/logs" "$dest/logs"
  # tasks/ 는 dependsOn(태스크 의존 관계)의 유일한 출처다. 있으면 같이 뜬다.
  [ -d "$WS/tasks" ] && cp -r "$WS/tasks" "$dest/tasks"
  # 실행 리포트는 로테이션을 타지 않지만, 스냅샷을 자기완결적으로 만들어 둔다.
  [ -d "$WS/artifacts/reports" ] && { mkdir -p "$dest/artifacts"; cp -r "$WS/artifacts/reports" "$dest/artifacts/reports"; }

  ids=$(exec_ids | tr '\n' ' ')
  n=$(exec_ids | wc -l)
  printf '{"snapshotAt":"%s","source":"%s","executionCount":%s,"executionIds":[%s]}\n' \
    "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$WS" "$n" \
    "$(exec_ids | sed 's/.*/"&"/' | paste -sd, -)" > "$dest/snapshot.json"

  printf "%s  실행 %s개  [%s]\n" "$dest" "$n" "${ids% }"
  fingerprint > "$STATE"
  return 0
}

if [ "$MODE" = "--watch" ]; then
  echo "watching $WS/logs  ->  $ARCHIVE  (${INTERVAL}초 간격, Ctrl+C 로 종료)"
  snapshot || echo "(변화 없음 — 대기)"
  while true; do
    sleep "$INTERVAL"
    snapshot || true
  done
else
  snapshot || echo "변화 없음. 스냅샷을 건너뛴다."
fi
