#!/usr/bin/env python3
"""Read a squad's answer out of an AI:GO run the way the judge does.

The rule is published at /practice-sets/requests/{item_id} and points at
docs/contracts/answer-extraction.md §1: aggregated result first, then task
outputs from the last wave backwards, and the status summary refused as an
answer.

That last clause is the one that costs runs. AI:GO's aggregated result on a
finished execution is a deterministic status line the runtime composes:

    **Execution complete** — 5 task(s) processed in 2 wave(s).
    1. ✅ **Design Slot Machine API Spec**
       Agent: `Backend Developer`

The task titles inside it come from the prompt, not from the model, so a squad
whose real answer lives in a task output looks answered while grading finds
nothing. This refuses that text and walks the waves instead.

Reads a squad workspace: <workspace>/logs/history.json for outputs and
<workspace>/logs/events.jsonl for the wave order recorded in squad:plan-ready.
Writes the JSONL grade.py consumes.
"""
import argparse
import json
import re
from pathlib import Path

STATUS_SUMMARY = re.compile(r"^\s*\*\*Execution (complete|failed)\*\*\s*—", re.MULTILINE)


def is_status_summary(text):
    if not text or not text.strip():
        return True
    return bool(STATUS_SUMMARY.search(text[:200]))


def wave_order(events_path):
    """taskId -> wave index, from squad:plan-ready. Missing file means no ordering."""
    order = {}
    if not events_path.exists():
        return order
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("eventType") == "squad:plan-ready":
            for i, wave in enumerate(ev["payload"].get("waves", [])):
                for tid in wave:
                    order[tid] = i
        elif ev.get("eventType") == "squad:task-wave-started":
            p = ev["payload"]
            for tid in p.get("taskIds", []):
                order[tid] = p.get("waveIndex", 0)
    return order


def extract(execution, order):
    """Returns (text, source). source names where the graded text came from."""
    final = execution.get("finalResult") or ""
    if not is_status_summary(final):
        return final, "aggregated_result"

    tasks = execution.get("tasks", [])
    ranked = sorted(
        enumerate(tasks),
        key=lambda pair: (order.get(pair[1].get("taskId"), 0), pair[0]),
        reverse=True,
    )
    for _, task in ranked:
        out = task.get("output") or ""
        if task.get("status") == "completed" and not is_status_summary(out):
            wave = order.get(task.get("taskId"))
            return out, f"task_output(wave={wave}, title={task.get('title')!r})"
    return "", "nothing_extractable"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workspace", help="AI:GO squad workspace directory")
    ap.add_argument("--item-id", help="tag every execution with this item id")
    ap.add_argument("--map", help="JSON mapping executionId or request text -> item_id")
    ap.add_argument("--out", help="write JSONL here instead of stdout")
    args = ap.parse_args()

    ws = Path(args.workspace)
    history = json.loads((ws / "logs" / "history.json").read_text(encoding="utf-8"))
    order = wave_order(ws / "logs" / "events.jsonl")
    mapping = json.loads(Path(args.map).read_text(encoding="utf-8")) if args.map else {}

    rows = []
    for execution in history:
        item_id = (args.item_id
                   or mapping.get(execution.get("executionId"))
                   or mapping.get(execution.get("request")))
        text, source = extract(execution, order)
        usage = execution.get("totalTokenUsage") or {}
        rows.append({
            "item_id": item_id,
            "execution_id": execution.get("executionId"),
            "output": text,
            "extracted_from": source,
            "status": execution.get("status"),
            "prompt_tokens": usage.get("promptTokens"),
            "completion_tokens": usage.get("completionTokens"),
            "duration_ms": execution.get("durationMs"),
        })

    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        missing = [r["execution_id"] for r in rows if not r["item_id"]]
        print(f"{len(rows)} execution(s) -> {args.out}"
              + (f"; {len(missing)} without an item_id" if missing else ""))
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
