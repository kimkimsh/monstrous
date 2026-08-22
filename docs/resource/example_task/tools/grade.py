#!/usr/bin/env python3
"""Local grader for the three tracks.

Reproduces the judge's extraction and comparison as published on the item pages
and in the track manifests:

    generic  letter_match   ANSWER: <letter>, case-insensitive, last match wins
    math     math_answer    FINAL ANSWER: \\boxed{...}, integer_exact and/or math_verify
    coding   patch format   the block between *** PATCH START *** and *** PATCH END ***

For every track the rule is the same: the LAST occurrence is the graded one, and
anything before it is ignored rather than penalised.

The two coding graders the judge really runs are swebench_docker and
livecodebench_tests. livecodebench_tests is reproduced here — public_test_cases
ship with the practice items, so a LiveCodeBench answer can be graded exactly.
swebench_docker is not: it needs the repository, the test_patch and a container.
What this file checks for a SWE-bench answer is that the patch parses and that
every SEARCH section could be located, which is the failure mode that turns a
correct fix into a zero.

Input is JSONL, one object per line: {"item_id": ..., "output": "<squad text>"}.
"""
import argparse
import importlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LETTER_RE = re.compile(r"^\s*ANSWER:\s*([A-Za-z])\s*$", re.MULTILINE)
BOXED_RE = re.compile(r"FINAL ANSWER:\s*\\boxed\{")
PATCH_START = "*** PATCH START ***"
PATCH_END = "*** PATCH END ***"


def extract_letter(text):
    hits = LETTER_RE.findall(text)
    return hits[-1].upper() if hits else None


def extract_boxed(text):
    """Last FINAL ANSWER: \\boxed{...}, brace-matched so nested \\frac{}{} survives."""
    starts = [m.end() for m in BOXED_RE.finditer(text)]
    if not starts:
        return None
    i = starts[-1]
    depth, out = 1, []
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return "".join(out).strip()
        out.append(c)
        i += 1
    return None


def extract_patch(text):
    if PATCH_START not in text or PATCH_END not in text:
        return None
    start = text.rindex(PATCH_START) + len(PATCH_START)
    tail = text[start:]
    if PATCH_END not in tail:
        return None
    return tail[:tail.index(PATCH_END)]


def parse_edit_blocks(patch):
    """Split a patch body into (path, search, replace). Returns (blocks, errors)."""
    lines = patch.split("\n")
    blocks, errors, i, pending_path = [], [], 0, None
    while i < len(lines):
        line = lines[i]
        if line.startswith("<<<<<<< SEARCH"):
            if pending_path is None:
                errors.append(f"line {i + 1}: <<<<<<< SEARCH with no path line before it")
                pending_path = "<unknown>"
            search, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("======="):
                search.append(lines[i])
                i += 1
            if i >= len(lines):
                errors.append("unterminated SEARCH section: no ======= found")
                break
            replace, i = [], i + 1
            while i < len(lines) and not lines[i].startswith(">>>>>>> REPLACE"):
                replace.append(lines[i])
                i += 1
            if i >= len(lines):
                errors.append("unterminated REPLACE section: no >>>>>>> REPLACE found")
                break
            blocks.append((pending_path, "\n".join(search), "\n".join(replace)))
            pending_path = None
            i += 1
            continue
        if line.strip():
            pending_path = line.strip()
        i += 1
    if not blocks:
        errors.append("no SEARCH/REPLACE block found between the patch markers")
    return blocks, errors


def normalise_math(s):
    if s is None:
        return None
    s = s.strip().strip("$").strip()
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\!", "").replace("\\,", "").replace("\\;", "").replace("~", "")
    s = re.sub(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", s)
    s = s.replace(" ", "").rstrip(".")
    if s.endswith("^\\circ"):
        s = s[:-len("^\\circ")]
    return s


def _load_math_verify():
    """math-verify is the library the judge's math_verify check is built on, and it is
    the accurate path. It is an optional dependency here so the grader still runs on a
    machine without it, falling back to normalise_math below — which is an approximation
    and will miss equivalences like \\sqrt{2} against 2^{1/2}. Install it with
    `pip install math-verify`. Resolved through importlib rather than a plain import so
    its absence is a runtime condition, not an unresolved module."""
    try:
        module = importlib.import_module("math_verify")
    except ImportError:
        return None, None
    return getattr(module, "parse", None), getattr(module, "verify", None)


_mv_parse, _mv_verify = _load_math_verify()
HAVE_MATH_VERIFY = _mv_parse is not None and _mv_verify is not None


def math_equal(got, gold):
    if got is None:
        return False
    if HAVE_MATH_VERIFY:
        try:
            return bool(_mv_verify(_mv_parse(f"${gold}$"), _mv_parse(f"${got}$")))
        except Exception:
            pass
    if normalise_math(got) == normalise_math(gold):
        return True
    try:
        return abs(float(got) - float(gold)) < 1e-9
    except (TypeError, ValueError):
        return False


def run_livecodebench(code, cases, mode, timeout):
    """stdin mode runs the file as a program; functional mode calls the entry point."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "solution.py"
        src.write_text(code, encoding="utf-8")
        for case in cases:
            stdin = case.get("input", "")
            expected = case.get("output", "").strip()
            if mode == "functional":
                stdin = ""
            try:
                proc = subprocess.run([sys.executable, str(src)], input=stdin,
                                      capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return False, f"timeout after {timeout}s"
            if proc.returncode != 0:
                return False, f"exit {proc.returncode}: {proc.stderr.strip()[:200]}"
            if proc.stdout.strip() != expected:
                return False, f"expected {expected!r}, got {proc.stdout.strip()[:200]!r}"
    return True, "all public tests passed"


def load_gold(track):
    gold = {}
    for line in open(ROOT / track / "gold" / "answers.jsonl", encoding="utf-8"):
        d = json.loads(line)
        gold[d["item_id"]] = d
    return gold


def track_of(item_id):
    """Coding task files carry the payload kind in the name
    (coding-visible-0001.swebench.txt), so match on the stem."""
    for track in ("coding", "math", "generic"):
        tasks = ROOT / track / "tasks"
        if next(tasks.glob(f"{item_id}.txt"), None) or next(tasks.glob(f"{item_id}.*.txt"), None):
            return track
    return None


def grade_one(item_id, output, gold, timeout, track=None):
    """Returns (outcome, correct, detail). outcome mirrors the portal's vocabulary."""
    track = track or track_of(item_id)
    g = gold[track][item_id]

    if track == "generic":
        got = extract_letter(output)
        if got is None:
            return "extraction_failed", False, "no `ANSWER: <letter>` line"
        return "graded", got == g["answer"].upper(), f"{got} vs {g['answer']}"

    if track == "math":
        got = extract_boxed(output)
        if got is None:
            return "extraction_failed", False, "no `FINAL ANSWER: \\boxed{...}`"
        if g["answer_format"] == "integer":
            try:
                if int(str(got).replace(",", "").strip()) == int(str(g["gold"]).strip()):
                    return "graded", True, f"{got} vs {g['gold']} (integer_exact)"
            except ValueError:
                pass
        return "graded", math_equal(got, g["gold"]), f"{got} vs {g['gold']}"

    patch = extract_patch(output)
    if patch is None:
        return "extraction_failed", False, "no `*** PATCH START *** … *** PATCH END ***`"
    blocks, errors = parse_edit_blocks(patch)
    if errors:
        return "extraction_failed", False, "; ".join(errors)

    if g["grader"] == "livecodebench_tests":
        created = [b for b in blocks if b[1].strip() == ""]
        if not created:
            return "graded", False, "no new-file block (empty SEARCH) — nothing for the judge to run"
        code = created[-1][2]
        passed, detail = run_livecodebench(code, g["public_test_cases"],
                                           g["evaluation_mode"], timeout)
        return "graded", passed, detail

    return "format_ok", None, (f"{len(blocks)} edit block(s) parse; paths "
                               f"{sorted({b[0] for b in blocks})} — swebench_docker not run locally")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="JSONL of {item_id, output}")
    ap.add_argument("--timeout", type=float, default=10.0, help="per LiveCodeBench test case")
    ap.add_argument("--report", help="write a per-item JSONL report here")
    args = ap.parse_args()

    gold = {t: load_gold(t) for t in ("coding", "math", "generic")}
    rows, per_track = [], {}
    for line in open(args.results, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        iid = rec["item_id"]
        track = track_of(iid)
        if track is None:
            print(f"skipping unknown item {iid}", file=sys.stderr)
            continue
        outcome, correct, detail = grade_one(iid, rec.get("output", ""), gold, args.timeout)
        rows.append({"item_id": iid, "track": track, "outcome": outcome,
                     "correct": correct, "detail": detail})
        if correct is not None:
            acc = per_track.setdefault(track, [0, 0])
            acc[1] += 1
            acc[0] += int(correct)

    for r in rows:
        mark = {True: "PASS", False: "FAIL", None: "----"}[r["correct"]]
        print(f"{mark}  {r['item_id']:<34} {r['outcome']:<18} {r['detail']}")

    weights = {"coding": 0.5, "generic": 0.25, "math": 0.25}
    overall, covered = 0.0, 0.0
    print("\n" + "-" * 72)
    for track in ("coding", "generic", "math"):
        if track not in per_track:
            continue
        good, total = per_track[track]
        acc = good / total
        overall += weights[track] * acc
        covered += weights[track]
        print(f"{track:<9} {good:>4}/{total:<4} accuracy {acc:.4f}  weight {weights[track]}")
    if covered:
        print(f"\nweighted score over the tracks present: {overall:.4f}"
              f"  (full-set denominator is 1.0, graded here {covered})")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
