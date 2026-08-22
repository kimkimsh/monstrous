#!/usr/bin/env python3
"""Compose the exact bytes the judge sends for one item.

The composition rule is published by the submission server on every item page at
/practice-sets/requests/{item_id}. Reproduced here verbatim:

    replace every occurrence of {{TASK}} with the item content;
    normalise line endings, so \r\n and a lone \r become \n throughout;
    strip trailing whitespace from the result;
    append a blank line, then the track's REQUIRED OUTPUT block verbatim,
    then a final newline.

Writing {{TASK}} twice yields the item twice. A prompt that is nothing but
{{TASK}} composes byte-for-byte what requests/<item_id>.txt already holds, and
--verify checks that against the SHA-256 the server published.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "{{TASK}}"


def normalise(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compose(one_shot_prompt, task_content, required_output):
    body = normalise(one_shot_prompt).replace(PLACEHOLDER, normalise(task_content))
    return body.rstrip() + "\n\n" + required_output.rstrip("\n") + "\n"


def find_task(item_id):
    """Locate an item's task file. Coding files carry the payload kind in the name
    (coding-visible-0001.swebench.txt), so match on the stem rather than the whole
    filename and let the suffix say what the item is."""
    for track in ("coding", "math", "generic"):
        hits = sorted((ROOT / track / "tasks").glob(f"{item_id}.txt")) or \
               sorted((ROOT / track / "tasks").glob(f"{item_id}.*.txt"))
        if hits:
            return track, hits[0]
    return None, None


def track_of(item_id):
    return require_task(item_id)[0]


def require_task(item_id):
    track, path = find_task(item_id)
    if track is None or path is None:
        raise SystemExit(f"unknown item_id: {item_id}")
    return track, path


def load_item(item_id):
    track, path = require_task(item_id)
    task = path.read_text(encoding="utf-8")
    block = (ROOT / track / "required_output.txt").read_text(encoding="utf-8")
    return track, task, block


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("item_id")
    ap.add_argument("--prompt", help="one-shot prompt file; defaults to prompts/<track>.txt")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--verify", action="store_true",
                    help="prompt must be exactly {{TASK}}; compare digest with the published one")
    args = ap.parse_args()

    track, task, block = load_item(args.item_id)
    if args.verify:
        prompt = PLACEHOLDER
    else:
        path = Path(args.prompt) if args.prompt else ROOT / "prompts" / f"{track}.txt"
        prompt = path.read_text(encoding="utf-8")
        if PLACEHOLDER not in prompt:
            raise SystemExit(f"{path} contains no {PLACEHOLDER} — the item would be dropped")

    composed = compose(prompt, task, block)
    if args.verify:
        published = json.loads((ROOT / "raw" / "request-digests.json").read_text())
        want = published[args.item_id]["sha_published"]
        got = hashlib.sha256(composed.encode()).hexdigest()
        print(f"{args.item_id}  {'OK ' if want == got else 'MISMATCH'}  {got}")
        return 0 if want == got else 1

    if args.out:
        Path(args.out).write_text(composed, encoding="utf-8", newline="")
    else:
        sys.stdout.write(composed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
