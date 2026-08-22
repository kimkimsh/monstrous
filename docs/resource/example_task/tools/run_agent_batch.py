#!/usr/bin/env python3
"""Run practice items through a single squad agent with the `aigo` CLI.

Why not `run_batch.py`. That one drives `aigo squad execute`, the planner path.
In AI:GO 1.12.1 the planner never runs outside the desktop app: the headless
Management API accepts the execution, writes an empty plan, and sits in
`executing` with `taskCounts.total = 0` forever. The router request counter does
not move, so no LLM call is made at all. See `04-CLI-운영.md` section 4.

This drives one agent instead — `squad message` in, `squad conversation` out.
That path works headless, and it is closer to what the judge does anyway: one
request, one answer, no planning turn to pay for.

Each item gets a fresh session. Without that the agent's context carries every
previous item, which inflates prompt tokens item over item and lets an earlier
answer leak into a later question. Measured on three math items: 7,635 tokens
shared-session against 2,940 isolated.

Point --endpoint/--token at a running headless server (BACKEND_AI_GO_ENDPOINT /
BACKEND_AI_GO_TOKEN are read if the flags are omitted). `aigo squad list` gives
the squad id, `aigo squad show <id>` the agent ids.
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLL_SECONDS = 5.0
MATCH_PREFIX_CHARS = 60


def build_env(endpoint, token):
    env = dict(os.environ)
    if endpoint:
        env["BACKEND_AI_GO_ENDPOINT"] = endpoint
    if token:
        env["BACKEND_AI_GO_TOKEN"] = token
    return env


def aigo(env, *args, timeout=300.0):
    proc = subprocess.run(["aigo", "-o", "json", *args],
                          capture_output=True, text=True, timeout=timeout, env=env)
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        return {"_stdout": proc.stdout, "_stderr": proc.stderr}


def select_items(tracks, limit, only):
    if only:
        return [i.strip() for i in only.split(",") if i.strip()]
    picked = []
    for track in tracks:
        index = json.loads((ROOT / track / "index.json").read_text(encoding="utf-8"))
        ids = [row["item_id"] for row in index["items"]]
        picked.extend(ids[:limit] if limit else ids)
    return picked


def track_of(item_id):
    return item_id.split("-", 1)[0]


def request_path(item_id):
    """coding requests carry an evaluation-kind suffix; math and generic do not."""
    track = track_of(item_id)
    direct = ROOT / track / "requests" / f"{item_id}.txt"
    if direct.exists():
        return direct
    matches = sorted((ROOT / track / "requests").glob(f"{item_id}.*.txt"))
    if not matches:
        raise FileNotFoundError(f"no request file for {item_id}")
    return matches[0]


def ask(env, squad_id, agent_id, request, timeout):
    """One item, one session. Returns (answer_text, token_usage, seconds)."""
    aigo(env, "squad", "session", "new", squad_id, agent_id)
    started = time.time()
    aigo(env, "squad", "message", squad_id, agent_id, request)

    # `squad conversation` can still report the previous session for a moment after
    # `session new`, so a message count is not a reliable "my turn landed" signal.
    # Match on the request text instead.
    head = request[:MATCH_PREFIX_CHARS]
    deadline = started + timeout
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        conversation = aigo(env, "squad", "conversation", squad_id, agent_id)
        messages = conversation.get("messages") or []
        if not isinstance(messages, list):
            continue
        mine = any(m.get("role") == "user" and m.get("content", "").startswith(head)
                   for m in messages)
        if mine and messages and messages[-1].get("role") == "assistant":
            return (messages[-1]["content"], conversation.get("tokenUsage", {}),
                    time.time() - started)
    return "", {}, time.time() - started


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("squad_id")
    ap.add_argument("agent_id")
    ap.add_argument("--tracks", default="math,generic,coding")
    ap.add_argument("--limit", type=int, help="first N items of each track")
    ap.add_argument("--only", help="comma-separated item ids, overrides --tracks/--limit")
    ap.add_argument("--endpoint", help="overrides BACKEND_AI_GO_ENDPOINT")
    ap.add_argument("--token", help="overrides BACKEND_AI_GO_TOKEN")
    ap.add_argument("--timeout", type=float, default=300.0, help="per item, seconds")
    ap.add_argument("--out", default="results.jsonl")
    args = ap.parse_args()

    env = build_env(args.endpoint, args.token)
    items = select_items([t.strip() for t in args.tracks.split(",")], args.limit, args.only)
    print(f"{len(items)} item(s) -> squad {args.squad_id} agent {args.agent_id}")

    with open(args.out, "w", encoding="utf-8") as out:
        for n, item_id in enumerate(items, 1):
            request = request_path(item_id).read_text(encoding="utf-8")
            try:
                text, usage, elapsed = ask(env, args.squad_id, args.agent_id,
                                           request, args.timeout)
            except subprocess.TimeoutExpired:
                text, usage, elapsed = "", {}, args.timeout
            row = {
                "item_id": item_id,
                "track": track_of(item_id),
                "output": text,
                "status": "completed" if text else "no_reply",
                "request_chars": len(request),
                "prompt_tokens": usage.get("promptTokens"),
                "completion_tokens": usage.get("completionTokens"),
                "wallclock_seconds": round(elapsed, 1),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            tail = (text.strip().splitlines() or [""])[-1][:70]
            print(f"[{n}/{len(items)}] {item_id}  {row['status']}  "
                  f"{row['prompt_tokens']}in/{row['completion_tokens']}out  "
                  f"{row['wallclock_seconds']}s  {tail}")

    print(f"\nwrote {args.out} — grade it with:  python3 tools/grade.py {args.out}")


if __name__ == "__main__":
    main()
