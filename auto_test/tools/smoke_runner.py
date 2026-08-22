"""Exercise AigoClient against a live headless aigo-server and print what came back.

Endpoint and token come from --endpoint/--token or from BACKEND_AI_GO_ENDPOINT /
BACKEND_AI_GO_TOKEN; nothing is baked in. Squad and agent default to the first
of each, so the run adapts to whatever server it is pointed at.

    uv run python tools/smoke_runner.py
    uv run python tools/smoke_runner.py --squad <id> --agent <id>

The cancellation check sends a prompt long enough to still be generating after
the first poll, sets the event, and reports the elapsed time — which has to be
near --cancel-after rather than near --timeout. The abandoned turn keeps running
on the server; nothing reads it.
"""
import argparse
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.runner import STATUS_CANCELLED, AigoClient

CANCEL_PROMPT = "Count from 1 to 100, one number per line."


def show_poll(elapsed):
    print(f"    ... polling, {elapsed:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default=os.environ.get("BACKEND_AI_GO_ENDPOINT", ""))
    ap.add_argument("--token", default=os.environ.get("BACKEND_AI_GO_TOKEN", ""))
    ap.add_argument("--squad", help="defaults to the first squad")
    ap.add_argument("--agent", help="defaults to the first agent of that squad")
    ap.add_argument("--prompt", default="Reply with exactly one word: PONG")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--cancel-after", type=float, default=3.0)
    ap.add_argument("--skip-cancel", action="store_true")
    args = ap.parse_args()

    client = AigoClient(args.endpoint, args.token)

    print("== health ==")
    print(client.health())

    print("\n== squads ==")
    squads = client.squads()
    for squad in squads:
        print(f"  {squad.id}  {squad.name!r}  agents={squad.agent_count}  status={squad.status}")
    if not squads:
        print("  none — nothing to ask")
        return 1

    squad_id = args.squad or squads[0].id
    print(f"\n== agents of {squad_id} ==")
    agents = client.agents(squad_id)
    for agent in agents:
        print(f"  {agent.id}  {agent.name!r}  role={agent.role!r}  model={agent.model_id}")
    if not agents:
        print("  none — nothing to ask")
        return 1
    agent_id = args.agent or agents[0].id

    print("\n== loaded models ==")
    for model in client.loaded_models():
        print(f"  {model}")

    print(f"\n== ask ==\n  squad {squad_id}\n  agent {agent_id}\n  prompt {args.prompt!r}")
    result = client.ask(squad_id, agent_id, args.prompt, args.timeout, on_poll=show_poll)
    print(f"  status={result.status}  seconds={result.seconds:.1f}  "
          f"tokens={result.prompt_tokens}in/{result.completion_tokens}out  error={result.error}")
    print(f"  text={result.text!r}")

    if args.skip_cancel:
        return 0

    print(f"\n== cancellation ==\n  prompt {CANCEL_PROMPT!r}"
          f"\n  timeout {args.timeout:.0f}s, cancelling after {args.cancel_after:.1f}s")
    cancel = threading.Event()
    box = {}

    def run_ask():
        box["result"] = client.ask(squad_id, agent_id, CANCEL_PROMPT, args.timeout,
                                   cancel=cancel, on_poll=show_poll)

    started = time.monotonic()
    worker = threading.Thread(target=run_ask)
    worker.start()
    time.sleep(args.cancel_after)
    print(f"  set() at {time.monotonic() - started:.1f}s", flush=True)
    cancel.set()
    worker.join(timeout=args.timeout)
    elapsed = time.monotonic() - started
    cancelled = box.get("result")
    if worker.is_alive():
        print(f"  FAIL: ask still running after {elapsed:.1f}s")
        return 1
    print(f"  returned at {elapsed:.1f}s  status={cancelled.status}  "
          f"seconds={cancelled.seconds:.1f}  error={cancelled.error}")
    if cancelled.status != STATUS_CANCELLED:
        print(f"  FAIL: expected {STATUS_CANCELLED}")
        return 1
    print(f"  OK: cancelled {elapsed:.1f}s in, timeout was {args.timeout:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
