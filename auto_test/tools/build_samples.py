#!/usr/bin/env python3
"""Build test_sample/<track>/<item_id>.json from the example_task source data.

The source lives outside this repository and is read-only. Every request file is
checked against the request_sha256 published in that track's index.json before a
sample is written, so a sample can never carry a prompt the judge would not send.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1

TRACKS = ("coding", "math", "generic")

# item_count declared by each track's index.json; used as a cross-check only.
EXPECTED_ITEM_COUNTS = {"coding": 20, "math": 59, "generic": 42}

UNGRADABLE_KIND = "swebench"
UNGRADABLE_REASON = (
    "swebench_docker grading requires Docker images that are not available locally; "
    "the run still records the patch and token usage"
)

GENERIC_KIND_FALLBACK = "mmlu_pro"

SAMPLE_KEYS = (
    "schema_version",
    "id",
    "track",
    "kind",
    "gradable",
    "ungradable_reason",
    "prompt",
    "expected",
    "meta",
)

META_KEYS = ("dataset", "native_id", "prompt_bytes", "prompt_sha256", "source")

# Prefix written into meta.source, relative to the workspace root that holds both
# this repository and docs/.
SOURCE_PREFIX = "docs/resource/example_task"


class BuildError(Exception):
    pass


def defaultSourceRoot(scriptPath):
    # <workspace>/auto_test/tools/build_samples.py -> <workspace>/docs/resource/example_task
    workspaceRoot = scriptPath.resolve().parents[2]
    return workspaceRoot / "docs" / "resource" / "example_task"


def defaultOutRoot(scriptPath):
    return scriptPath.resolve().parents[1] / "test_sample"


def loadIndex(sourceRoot, track):
    indexPath = sourceRoot / track / "index.json"
    if not indexPath.is_file():
        raise BuildError("missing index: {}".format(indexPath))
    with indexPath.open(encoding="utf-8") as handle:
        return json.load(handle)


def loadGold(sourceRoot, track):
    goldPath = sourceRoot / track / "gold" / "answers.jsonl"
    if not goldPath.is_file():
        raise BuildError("missing gold answers: {}".format(goldPath))
    byItem = {}
    with goldPath.open(encoding="utf-8") as handle:
        for lineNumber, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            itemId = row.get("item_id")
            if itemId is None:
                raise BuildError("{}:{}: gold row has no item_id".format(goldPath, lineNumber))
            if itemId in byItem:
                raise BuildError("{}:{}: duplicate gold row for {}".format(goldPath, lineNumber, itemId))
            byItem[itemId] = row
    return byItem


def requestPath(sourceRoot, track, item):
    # Only coding filenames carry the evaluation-kind suffix.
    if track == "coding":
        name = "{}.{}.txt".format(item["item_id"], item["kind"])
    else:
        name = "{}.txt".format(item["item_id"])
    return sourceRoot / track / "requests" / name


def readPrompt(path, itemId, expectedSha, expectedBytes):
    if not path.is_file():
        raise BuildError("{}: request file not found: {}".format(itemId, path))
    rawBytes = path.read_bytes()
    actualSha = hashlib.sha256(rawBytes).hexdigest()
    if actualSha != expectedSha:
        raise BuildError(
            "{}: request file sha256 mismatch\n  file     {}\n  expected {}\n  actual   {}".format(
                itemId, path, expectedSha, actualSha
            )
        )
    if expectedBytes is not None and len(rawBytes) != expectedBytes:
        raise BuildError(
            "{}: request file is {} bytes, index.json says {}".format(itemId, len(rawBytes), expectedBytes)
        )
    prompt = rawBytes.decode("utf-8")
    # A sample stores text, not bytes; the round trip must not change anything.
    reEncoded = prompt.encode("utf-8")
    if reEncoded != rawBytes:
        raise BuildError("{}: request bytes do not survive a utf-8 round trip".format(itemId))
    if hashlib.sha256(reEncoded).hexdigest() != expectedSha:
        raise BuildError("{}: prompt sha256 does not match request_sha256 after decode".format(itemId))
    return prompt, actualSha, len(rawBytes)


def resolveKind(track, item, gold):
    if track == "generic":
        return gold.get("kind") or GENERIC_KIND_FALLBACK
    kind = item.get("kind")
    if not kind:
        raise BuildError("{}: index.json entry has no kind".format(item.get("item_id")))
    return kind


def buildSample(sourceRoot, track, item, gold):
    itemId = item["item_id"]
    path = requestPath(sourceRoot, track, item)
    prompt, promptSha, promptBytes = readPrompt(
        path, itemId, item["request_sha256"], item.get("request_bytes")
    )
    kind = resolveKind(track, item, gold)
    gradable = kind != UNGRADABLE_KIND
    return {
        "schema_version": SCHEMA_VERSION,
        "id": itemId,
        "track": track,
        "kind": kind,
        "gradable": gradable,
        "ungradable_reason": None if gradable else UNGRADABLE_REASON,
        "prompt": prompt,
        "expected": gold,
        "meta": {
            "dataset": item.get("dataset"),
            "native_id": item.get("native_id"),
            "prompt_bytes": promptBytes,
            "prompt_sha256": promptSha,
            "source": "{}/{}/requests/{}".format(SOURCE_PREFIX, track, path.name),
        },
    }


def renderSample(sample):
    return json.dumps(sample, ensure_ascii=False, indent=2) + "\n"


def collectTrack(sourceRoot, track):
    index = loadIndex(sourceRoot, track)
    gold = loadGold(sourceRoot, track)
    items = index["items"]

    declaredCount = index.get("item_count")
    if declaredCount is not None and declaredCount != len(items):
        raise BuildError(
            "{}: index.json item_count is {} but it lists {} items".format(track, declaredCount, len(items))
        )
    knownCount = EXPECTED_ITEM_COUNTS.get(track)
    if knownCount is not None and len(items) != knownCount:
        raise BuildError("{}: expected {} items, index.json has {}".format(track, knownCount, len(items)))

    indexIds = {item["item_id"] for item in items}
    orphanGold = sorted(set(gold) - indexIds)
    if orphanGold:
        raise BuildError("{}: gold rows with no index entry: {}".format(track, ", ".join(orphanGold)))

    samples = []
    for item in items:
        itemId = item["item_id"]
        if itemId not in gold:
            raise BuildError("{}: no gold answer for {}".format(track, itemId))
        samples.append(buildSample(sourceRoot, track, item, gold[itemId]))
    return samples


def writeTrack(outRoot, track, samples):
    trackDir = outRoot / track
    trackDir.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        target = trackDir / "{}.json".format(sample["id"])
        target.write_text(renderSample(sample), encoding="utf-8")


def validateShape(sample, path, track):
    """Structural check for a sample this script did not generate."""
    problems = []

    def flag(message):
        problems.append("{}: {}".format(path, message))

    if not isinstance(sample, dict):
        flag("top level is not a JSON object")
        return problems

    missing = [key for key in SAMPLE_KEYS if key not in sample]
    if missing:
        flag("missing key(s): {}".format(", ".join(missing)))
    unknown = [key for key in sample if key not in SAMPLE_KEYS]
    if unknown:
        flag("unknown key(s): {}".format(", ".join(unknown)))
    if missing:
        return problems

    if sample["schema_version"] != SCHEMA_VERSION:
        flag("schema_version must be {}".format(SCHEMA_VERSION))
    if not isinstance(sample["id"], str) or not sample["id"]:
        flag("id must be a non-empty string")
    elif sample["id"] != path.stem:
        flag("id {!r} does not match the file name".format(sample["id"]))
    if sample["track"] != track:
        flag("track {!r} does not match the directory".format(sample["track"]))
    if not isinstance(sample["kind"], str) or not sample["kind"]:
        flag("kind must be a non-empty string")
    if not isinstance(sample["gradable"], bool):
        flag("gradable must be true or false")
    elif sample["gradable"]:
        if sample["ungradable_reason"] is not None:
            flag("gradable samples must have ungradable_reason null")
    else:
        if not isinstance(sample["ungradable_reason"], str) or not sample["ungradable_reason"].strip():
            flag("ungradable samples must give a non-empty ungradable_reason")
    if not isinstance(sample["prompt"], str) or not sample["prompt"]:
        flag("prompt must be a non-empty string")
    if not isinstance(sample["expected"], dict) or not sample["expected"]:
        flag("expected must be a non-empty JSON object")

    meta = sample["meta"]
    if not isinstance(meta, dict):
        flag("meta must be a JSON object")
        return problems
    metaMissing = [key for key in META_KEYS if key not in meta]
    if metaMissing:
        flag("meta is missing key(s): {}".format(", ".join(metaMissing)))
        return problems

    if isinstance(sample["prompt"], str):
        promptBytes = sample["prompt"].encode("utf-8")
        if meta["prompt_bytes"] != len(promptBytes):
            flag("meta.prompt_bytes is {}, prompt is {} bytes".format(meta["prompt_bytes"], len(promptBytes)))
        actualSha = hashlib.sha256(promptBytes).hexdigest()
        if meta["prompt_sha256"] != actualSha:
            flag("meta.prompt_sha256 is {}, prompt hashes to {}".format(meta["prompt_sha256"], actualSha))
    if not isinstance(meta["source"], str) or not meta["source"]:
        flag("meta.source must be a non-empty string")
    return problems


def checkTrack(outRoot, track, samples):
    trackDir = outRoot / track
    problems = []
    handWritten = []
    if not trackDir.is_dir():
        return ["{}: sample directory does not exist: {}".format(track, trackDir)], handWritten

    expectedNames = set()
    for sample in samples:
        target = trackDir / "{}.json".format(sample["id"])
        expectedNames.add(target.name)
        if not target.is_file():
            problems.append("{}: missing sample file {}".format(sample["id"], target))
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != renderSample(sample):
            problems.append("{}: {} differs from the source data".format(sample["id"], target))

    # Anything else in the directory is either a hand-written sample, which is only
    # shape-checked, or a generated file whose source item is gone, which is drift.
    for extra in sorted(trackDir.glob("*.json")):
        if extra.name in expectedNames:
            continue
        try:
            sample = json.loads(extra.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            problems.append("{}: not readable as UTF-8 JSON: {}".format(extra, error))
            continue
        source = sample.get("meta", {}).get("source") if isinstance(sample, dict) else None
        if isinstance(source, str) and source.startswith(SOURCE_PREFIX):
            problems.append(
                "{}: claims a {} source but has no item in index.json".format(extra, SOURCE_PREFIX)
            )
            continue
        shapeProblems = validateShape(sample, extra, track)
        if shapeProblems:
            problems.extend(shapeProblems)
        else:
            handWritten.append(extra)
    return problems, handWritten


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="example_task directory to read (default: <workspace>/docs/resource/example_task)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory to write samples into (default: <repo>/test_sample)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify existing samples against the source without writing; non-zero exit on any drift",
    )
    args = parser.parse_args(argv)

    scriptPath = Path(__file__)
    sourceRoot = (args.source or defaultSourceRoot(scriptPath)).resolve()
    outRoot = (args.out or defaultOutRoot(scriptPath)).resolve()

    if not sourceRoot.is_dir():
        print("source directory not found: {}".format(sourceRoot), file=sys.stderr)
        return 2

    try:
        byTrack = {track: collectTrack(sourceRoot, track) for track in TRACKS}
    except BuildError as error:
        print("build failed: {}".format(error), file=sys.stderr)
        return 1

    handWrittenCount = 0
    if args.check:
        problems = []
        for track in TRACKS:
            trackProblems, handWritten = checkTrack(outRoot, track, byTrack[track])
            problems.extend(trackProblems)
            handWrittenCount += len(handWritten)
        if problems:
            print("check failed: {} problem(s)".format(len(problems)), file=sys.stderr)
            for problem in problems:
                print("  {}".format(problem), file=sys.stderr)
            return 1
    else:
        for track in TRACKS:
            writeTrack(outRoot, track, byTrack[track])

    verb = "checked" if args.check else "wrote"
    total = 0
    ungradable = 0
    for track in TRACKS:
        samples = byTrack[track]
        total += len(samples)
        ungradable += sum(1 for sample in samples if not sample["gradable"])
        print("{:<8} {} {} sample(s)".format(track, verb, len(samples)))
    print("total    {} {} sample(s) ({} ungradable) -> {}".format(verb, total, ungradable, outRoot))
    if args.check and handWrittenCount:
        print("         plus {} hand-written sample(s), shape-checked only".format(handWrittenCount))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
