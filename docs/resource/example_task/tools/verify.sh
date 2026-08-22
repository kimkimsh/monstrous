#!/usr/bin/env bash
# Re-check that what this folder holds is what the submission server published.
#
# Two independent checks:
#   1. raw/ source files against raw/SHA256SUMS, the digest list the server ships.
#   2. every composed request against the per-item SHA-256 each item page publishes,
#      by recomposing it from tasks/ + required_output.txt rather than hashing the
#      stored copy — so a broken composition rule fails here, not on a scored run.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

echo "== raw source files =="
( cd raw && shasum -a 256 -c <(python3 - <<'PY'
import re
mapping = {
    "coding/items.jsonl": "coding.items.jsonl",
    "coding/manifest.json": "coding.manifest.json",
    "coding/context.jsonl": "../coding/gold/context.jsonl",
    "coding/context.manifest.json": "coding.context.manifest.json",
    "math/items.jsonl": "math.items.jsonl",
    "math/manifest.json": "math.manifest.json",
    "generic/items.jsonl": "generic.items.jsonl",
    "generic/manifest.json": "generic.manifest.json",
    "set.manifest.json": "set.manifest.json",
}
for line in open("SHA256SUMS", encoding="utf-8"):
    digest, _, path = line.strip().partition("  ")
    path = path.lstrip("*").strip()
    if path in mapping:
        print(f"{digest}  {mapping[path]}")
PY
) )

echo
echo "== composed requests (121 items) =="
fail=0
for track in coding math generic; do
  for f in "$track"/tasks/*.txt; do
    # coding files are <item_id>.<kind>.txt; the other tracks are <item_id>.txt
    id="$(basename "$f" .txt)"
    id="${id%.swebench}"
    id="${id%.livecodebench}"
    if ! python3 tools/compose.py "$id" --verify | grep -q " OK "; then
      echo "MISMATCH  $id"
      fail=1
    fi
  done
done
if [ "$fail" -eq 0 ]; then
  echo "all 121 composed requests match the digests the server published"
fi
exit "$fail"
