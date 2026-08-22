"""Reads the sample files the generator writes under test_sample/<track>/<id>.json.

A sample pairs one request with the gold object copied verbatim out of
example_task/<track>/gold/answers.jsonl, so grading never has to reach back into
example_task for an answer.

Loading is total: a file that is unparseable or fails validation is reported against
its path instead of raising, because the GUI has to list what broke next to what
loaded rather than show nothing at all.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1
TRACKS = ("coding", "generic", "math")

FIELD_TYPES = {
    "id": str,
    "track": str,
    "kind": str,
    "gradable": bool,
    "prompt": str,
    "expected": dict,
    "meta": dict,
}


@dataclass(frozen=True)
class Sample:
    id: str
    track: str
    kind: str
    gradable: bool
    ungradable_reason: str | None
    prompt: str
    expected: dict
    meta: dict


@dataclass(frozen=True)
class LoadReport:
    samples: list[Sample]
    errors: list[tuple[Path, list[str]]]


def validate_sample(data: dict) -> list[str]:
    """Problems with one decoded sample object, empty when it is clean."""
    if not isinstance(data, dict):
        return [f"top-level JSON is {type(data).__name__}, expected an object"]

    problems = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version is {data.get('schema_version')!r}, "
                        f"expected {SCHEMA_VERSION}")

    for key, expected_type in FIELD_TYPES.items():
        if key not in data:
            problems.append(f"missing key {key!r}")
        elif not isinstance(data[key], expected_type):
            problems.append(f"{key} is {type(data[key]).__name__}, "
                            f"expected {expected_type.__name__}")

    track = data.get("track")
    if isinstance(track, str) and track not in TRACKS:
        problems.append(f"track {track!r} is not one of {', '.join(TRACKS)}")
    if data.get("prompt") == "":
        problems.append("prompt is empty")
    if data.get("expected") == {}:
        problems.append("expected is empty")

    problems.extend(_gradable_problems(data))
    problems.extend(_digest_problems(data))
    return problems


def _gradable_problems(data):
    if "ungradable_reason" not in data:
        return ["missing key 'ungradable_reason'"]
    reason = data["ungradable_reason"]
    gradable = data.get("gradable")
    if reason is not None and not isinstance(reason, str):
        return [f"ungradable_reason is {type(reason).__name__}, expected str or null"]
    if not isinstance(gradable, bool):
        return []
    if gradable and reason is not None:
        return [f"gradable is true but ungradable_reason is set to {reason!r}"]
    if not gradable and not reason:
        return ["gradable is false but ungradable_reason is missing"]
    return []


def _digest_problems(data):
    meta, prompt = data.get("meta"), data.get("prompt")
    if not isinstance(meta, dict) or not isinstance(prompt, str):
        return []
    recorded = meta.get("prompt_sha256")
    if recorded is None:
        return ["meta.prompt_sha256 is missing"]
    actual = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if recorded != actual:
        return [f"meta.prompt_sha256 {recorded} does not match the prompt, which hashes "
                f"to {actual}"]
    return []


def load_report(root: Path) -> LoadReport:
    """Every sample under root/<track>/, plus the (path, problems) pairs that did not load."""
    root = Path(root)
    samples, errors = [], []
    for track in TRACKS:
        for path in sorted((root / track).glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                errors.append((path, [f"unreadable: {exc}"]))
                continue
            problems = validate_sample(data)
            if problems:
                errors.append((path, problems))
                continue
            samples.append(Sample(
                id=data["id"],
                track=data["track"],
                kind=data["kind"],
                gradable=data["gradable"],
                ungradable_reason=data["ungradable_reason"],
                prompt=data["prompt"],
                expected=data["expected"],
                meta=data["meta"],
            ))
    samples.sort(key=lambda sample: (sample.track, sample.id))
    return LoadReport(samples, errors)


def load_samples(root: Path) -> list[Sample]:
    return load_report(root).samples
