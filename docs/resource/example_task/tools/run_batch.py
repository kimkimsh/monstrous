#!/usr/bin/env python3
"""Run a set of practice items through an AI:GO squad and collect the answers.

One item is one squad execution — that is the shape a scored run has, so it is
the shape to rehearse. For each item this composes the request the judge would
send (compose.py's rule), submits it with

    aigo-cli squad execute <squad_id> <request> --auto-approve --wait

then reads the squad's answer back out of the workspace with extract.py's rule
and writes one JSONL row grade.py can consume.

The CLI lives inside the desktop bundle and is not on PATH by default:
    /Applications/Backend.AI GO.app/Contents/MacOS/aigo-cli
Point --cli somewhere else if yours differs. `aigo-cli squad list` gives the id.

Nothing here retries a failed execution on its own. AI:GO reports a connection
failure as "execution completed, all tasks failed", which grading would read as
a wrong answer rather than an outage, so a retry that is not recorded as one
quietly turns infrastructure noise into your accuracy. Failures are written to
the output with status carried through; decide what to re-run by looking at it.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from compose import compose, load_item          # noqa: E402
from extract import extract, wave_order         # noqa: E402

DEFAULT_CLI = "/Applications/Backend.AI GO.app/Contents/MacOS/aigo-cli"


def select_items(tracks, limit, only):
    if only:
        return [i.strip() for i in only.split(",") if i.strip()]
    picked = []
    for track in tracks:
        index = json.loads((ROOT / track / "index.json").read_text(encoding="utf-8"))
        ids = [row["item_id"] for row in index["items"]]
        picked.extend(ids[:limit] if limit else ids)
    return picked


def run_one(cli, squad_id, request, timeout):
    started = time.time()
    proc = subprocess.run(
        [cli, "-o", "json", "squad", "execute", squad_id, request, "--auto-approve", "--wait"],
        capture_output=True, text=True, timeout=timeout,
    )
    elapsed = time.time() - started
    execution_id = None
    for chunk in (proc.stdout, proc.stderr):
        try:
            data = json.loads(chunk)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            execution_id = data.get("executionId") or data.get("execution_id") or execution_id
    return execution_id, proc, elapsed


def latest_execution(workspace, execution_id):
    history = json.loads((workspace / "logs" / "history.json").read_text(encoding="utf-8"))
    if execution_id:
        for entry in history:
            if entry.get("executionId") == execution_id:
                return entry
    return history[-1] if history else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("squad_id")
    ap.add_argument("workspace", help="that squad's workspace directory")
    ap.add_argument("--tracks", default="math,generic,coding")
    ap.add_argument("--limit", type=int, help="first N items of each track")
    ap.add_argument("--only", help="comma-separated item ids, overrides --tracks/--limit")
    ap.add_argument("--prompt-dir", default=str(ROOT / "prompts"))
    ap.add_argument("--cli", default=DEFAULT_CLI)
    ap.add_argument("--timeout", type=float, default=900.0, help="per execution, seconds")
    ap.add_argument("--out", default="results.jsonl")
    args = ap.parse_args()

    workspace = Path(args.workspace)
    items = select_items([t.strip() for t in args.tracks.split(",")], args.limit, args.only)
    print(f"{len(items)} item(s) -> squad {args.squad_id}")

    with open(args.out, "w", encoding="utf-8") as out:
        for n, item_id in enumerate(items, 1):
            track, task, block = load_item(item_id)
            prompt_path = Path(args.prompt_dir) / f"{track}.txt"
            request = compose(prompt_path.read_text(encoding="utf-8"), task, block)

            try:
                execution_id, proc, elapsed = run_one(args.cli, args.squad_id, request, args.timeout)
            except subprocess.TimeoutExpired:
                row = {"item_id": item_id, "track": track, "output": "",
                       "status": "runner_timeout", "wallclock_seconds": args.timeout}
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                print(f"[{n}/{len(items)}] {item_id}  TIMEOUT")
                continue

            entry = latest_execution(workspace, execution_id)
            if entry is None:
                row = {"item_id": item_id, "track": track, "output": "",
                       "status": "no_history_entry", "stderr": proc.stderr[-500:],
                       "wallclock_seconds": round(elapsed, 2)}
            else:
                text, source = extract(entry, wave_order(workspace / "logs" / "events.jsonl"))
                usage = entry.get("totalTokenUsage") or {}
                row = {
                    "item_id": item_id, "track": track, "output": text,
                    "extracted_from": source, "status": entry.get("status"),
                    "execution_id": entry.get("executionId"),
                    "request_chars": len(request),
                    "prompt_tokens": usage.get("promptTokens"),
                    "completion_tokens": usage.get("completionTokens"),
                    "wallclock_seconds": round(elapsed, 2),
                }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            print(f"[{n}/{len(items)}] {item_id}  {row.get('status')}  "
                  f"{row.get('prompt_tokens')}in/{row.get('completion_tokens')}out  "
                  f"{row.get('wallclock_seconds')}s")

    print(f"\nwrote {args.out} — grade it with:  python3 tools/grade.py {args.out}")


if __name__ == "__main__":
    main()
