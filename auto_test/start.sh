#!/usr/bin/env bash
# Bring up everything auto_test needs, in order, and open the window.
#
#   ./start.sh          headless server -> local model -> GUI
#   ./start.sh stop     stop the headless server and its children
#
# Each step is skipped when it is already done, so re-running is cheap and safe.
set -euo pipefail

BIN_DIR="$HOME/.local/share/aigo-headless"
DATA_DIR="$HOME/Library/Application Support/ai.backend.go"
MODELS_DIR="$HOME/backend_ai"
LOG="$BIN_DIR/server.log"
ENDPOINT="http://127.0.0.1:8001"

MODEL_ID="unsloth/gpt-oss-20b-gguf/gpt-oss-20b-q8_0.gguf"
MODEL_ALIAS="unsloth/gpt-oss-20b"
CONTEXT_LENGTH=32768

RELEASE=https://github.com/lablup/backend.ai-go-releases/releases/download/v1.12.1
SERVER_ZIP_SHA=0b9ab0de7b66eea91889377e5639b797176dbc9985fe78b03cf5a593d19368ef
CLI_ZIP_SHA=f311986e22f92ff64272362ab8481b0957890c861df2a460c5cbee1f064942bc

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say()  { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

stop_server() {
  pkill -f "aigo-headless/aigo-server" 2>/dev/null || true
  pkill -f "aigo-headless/continuum-router" 2>/dev/null || true
  pkill -f "engines/llama-cpp-metal/bin/llama-server" 2>/dev/null || true
  say "중지됨"
}

[ "${1:-}" = "stop" ] && { stop_server; exit 0; }

fetch() { # url sha256 destination-zip
  say "  받는 중: $(basename "$1")"
  curl -fsSL -o "$3" "$1" || fail "다운로드 실패: $1"
  local got
  got=$(shasum -a 256 "$3" | awk '{print $1}')
  [ "$got" = "$2" ] || fail "체크섬 불일치: $(basename "$3")
  기대 $2
  실제 $got"
}

# ---------------------------------------------------------------- 0. binaries
# The `aigo-server` inside Backend.AI GO.app cannot spawn child processes: it
# fails with "Cannot spawn router without an initialized runtime" and no model
# ever loads. The release build is a different binary and works. Never point
# this script at the app bundle.
mkdir -p "$BIN_DIR"
if [ ! -x "$BIN_DIR/aigo-server" ] || [ ! -x "$BIN_DIR/continuum-router" ]; then
  say "[0/3] 헤드리스 서버 설치"
  tmp=$(mktemp -d)
  fetch "$RELEASE/aigo-server-macos-aarch64.zip" "$SERVER_ZIP_SHA" "$tmp/s.zip"
  unzip -q -o "$tmp/s.zip" -d "$BIN_DIR"
  rm -rf "$tmp"
  chmod +x "$BIN_DIR/aigo-server" "$BIN_DIR/continuum-router"
  xattr -c "$BIN_DIR/aigo-server" "$BIN_DIR/continuum-router" 2>/dev/null || true
fi

if ! command -v aigo >/dev/null 2>&1; then
  say "[0/3] aigo CLI 설치 -> ~/.local/bin/aigo"
  tmp=$(mktemp -d)
  fetch "$RELEASE/aigo-cli-macos-aarch64.zip" "$CLI_ZIP_SHA" "$tmp/c.zip"
  unzip -q -o "$tmp/c.zip" -d "$tmp"
  mkdir -p "$HOME/.local/bin"
  install -m 755 "$tmp/aigo" "$HOME/.local/bin/aigo"
  rm -rf "$tmp"
  export PATH="$HOME/.local/bin:$PATH"
fi

# Auth off, so nothing has to carry a token. The server binds 127.0.0.1 only.
if [ ! -f "$BIN_DIR/aigo-server.toml" ]; then
  "$BIN_DIR/aigo-server" --generate-config > "$BIN_DIR/aigo-server.toml"
  /usr/bin/sed -i '' 's/^require_api_key = true/require_api_key = false/' \
    "$BIN_DIR/aigo-server.toml"
fi

# ------------------------------------------------------------------ 1. server
say "[1/3] 헤드리스 서버"
if curl -fsS -m 2 "$ENDPOINT/api/v1/health" >/dev/null 2>&1; then
  echo "  이미 떠 있음"
else
  # Both processes manage the same data directory, and they overwrite each
  # other's router_config.yaml. Observed symptom: the router ends up with a
  # placeholder backend and serves no models at all.
  if pgrep -f "MacOS/backend-ai-go" >/dev/null 2>&1; then
    echo "  데스크톱 앱 종료 (같은 data-dir을 두 프로세스가 만지면 라우터 설정이 깨진다)"
    osascript -e 'tell application "Backend.AI GO" to quit' || true
    for _ in $(seq 20); do
      pgrep -f "MacOS/backend-ai-go" >/dev/null 2>&1 || break
      sleep 0.5
    done
  fi

  ( cd "$BIN_DIR" && ./aigo-server \
      --config "$BIN_DIR/aigo-server.toml" \
      --data-dir "$DATA_DIR" \
      --port 8001 \
      --models-dir "$MODELS_DIR" > "$LOG" 2>&1 & )

  for _ in $(seq 60); do
    curl -fsS -m 2 "$ENDPOINT/api/v1/health" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS -m 2 "$ENDPOINT/api/v1/health" >/dev/null 2>&1 \
    || fail "  서버가 안 뜬다. 로그: $LOG"
  echo "  올라옴 — $ENDPOINT"
fi

export BACKEND_AI_GO_ENDPOINT="$ENDPOINT"
unset BACKEND_AI_GO_TOKEN 2>/dev/null || true

# ------------------------------------------------------------------- 2. model
say "[2/3] 로컬 모델 $MODEL_ALIAS"
if aigo -o json loaded list 2>/dev/null | grep -q "$MODEL_ALIAS"; then
  echo "  이미 로드됨"
else
  aigo loaded load "$MODEL_ID" \
    -c "$CONTEXT_LENGTH" --gpu-layers=-1 --tool-calling --alias "$MODEL_ALIAS" \
    >/dev/null || fail "  모델 로드 실패. 로그: $LOG"
  echo "  로드됨 — context $CONTEXT_LENGTH"
fi

health=$(curl -fsS "$ENDPOINT/api/v1/health")
echo "  health: $health"
case "$health" in
  *'"status":"healthy"'*) ;;
  *) echo "  경고 — 일부 구성요소가 죽어 있다. 실행은 되지만 결과가 이상하면 로그를 봐라: $LOG" ;;
esac

# --------------------------------------------------------------------- 3. GUI
say "[3/3] GUI"
cd "$HERE"
command -v uv >/dev/null 2>&1 || fail "  uv 가 없다. https://docs.astral.sh/uv/ 참고"
uv sync --quiet
exec uv run python app.py
