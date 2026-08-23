#!/usr/bin/env bash
# Assemble the deck, refuse to ship a slide whose content spills, then render the PDF.
set -euo pipefail
cd "$(dirname "$0")"
OUT=../build
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

python3 build.py
mkdir -p "$OUT"

# The layout gate needs playwright. Point NODE_PATH at wherever it lives, or
# `npm i playwright` in this directory (node_modules is gitignored).
if node -e "require.resolve('playwright')" 2>/dev/null; then
  node check.js monstrous-deck.html || { echo "layout check failed"; exit 1; }
else
  echo "note: playwright not resolvable, skipping the layout gate"
fi

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT/monstrous-deck-ko.pdf" \
  "file://$PWD/monstrous-deck.html" 2>/dev/null

python3 - "$OUT/monstrous-deck-ko.pdf" <<'PY'
import re,sys
d=open(sys.argv[1],'rb').read()
n=len(re.findall(rb'/Type\s*/Page(?![s])',d))
box=set(re.findall(rb'/MediaBox\s*\[([^\]]+)\]',d))
print(f"{sys.argv[1]}: {n} pages, MediaBox {[b.decode() for b in box]}")
assert n==19, f"expected 19 pages, got {n}"
PY
