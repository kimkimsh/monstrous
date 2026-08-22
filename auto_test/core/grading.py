"""Grades one sample's output by calling example_task/tools/grade.py.

The judge's extraction and comparison rules live in that file and nowhere else. This
module only reshapes our arguments into what grade_one expects and forwards the call,
because a second implementation here could drift and disagree with the one the run
tooling already uses.

grade.py sits outside this package and is imported by path, resolved from this file so
the working directory does not matter.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

GRADE_TOOLS_DIR = (Path(__file__).resolve().parents[2]
                   / "docs" / "resource" / "example_task" / "tools")

# Appended, not prepended: that directory also holds compose.py and extract.py, whose
# names are generic enough to shadow something else if they came first.
if str(GRADE_TOOLS_DIR) not in sys.path:
    sys.path.append(str(GRADE_TOOLS_DIR))

import grade as grade_tool  # noqa: E402

HAVE_MATH_VERIFY = grade_tool.HAVE_MATH_VERIFY


@dataclass(frozen=True)
class GradeResult:
    outcome: str
    correct: bool | None
    detail: str


def grade(sample, output: str, timeout: float = 30.0) -> GradeResult:
    """outcome is one of graded, extraction_failed, format_ok, skipped.

    correct is None whenever no verdict exists: a skipped sample, or a SWE-bench patch
    that parses but can only be settled by the judge's container."""
    if not sample.gradable:
        return GradeResult("skipped", None, sample.ungradable_reason)
    gold = {sample.track: {sample.id: sample.expected}}
    outcome, correct, detail = grade_tool.grade_one(sample.id, output, gold, timeout,
                                                    track=sample.track)
    return GradeResult(outcome, correct, detail)
