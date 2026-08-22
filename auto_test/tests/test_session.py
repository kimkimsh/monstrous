"""Tests for the run-result arithmetic.

This is the code most likely to be silently wrong: every denominator produces a
plausible-looking percentage, so a mistake here does not announce itself. The
cases below pin the classification table in PLAN.md — which outcomes land in the
accuracy denominator, which are excluded, and which still contribute tokens.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.session import ItemResult, RunLog, summarize


def result(item_id: str = "x", status: str = "completed", outcome: str = "graded",
           correct: bool | None = True, prompt: int | None = 100,
           completion: int | None = 50, seconds: float = 1.0, gradable: bool = True,
           squad: str = "sq", agent: str = "ag", model: str = "m") -> ItemResult:
    return ItemResult(
        item_id=item_id, track="math", kind="math", gradable=gradable,
        status=status, outcome=outcome, correct=correct, detail="",
        output="out", prompt_tokens=prompt, completion_tokens=completion,
        seconds=seconds, squad_id=squad, agent_id=agent, model_id=model,
    )


class Denominators(unittest.TestCase):
    def test_correct_and_wrong_both_count_as_graded(self):
        agg = summarize([result(correct=True), result(correct=False)])
        self.assertEqual(agg.graded, 2)
        self.assertEqual(agg.correct, 1)
        self.assertEqual(agg.scored, 2)
        self.assertEqual(agg.accuracy, 0.5)

    def test_extraction_failure_is_a_real_zero(self):
        """The portal scores a format miss as 0, so it belongs in the denominator."""
        agg = summarize([result(correct=True),
                         result(outcome="extraction_failed", correct=False)])
        self.assertEqual(agg.extraction_failed, 1)
        self.assertEqual(agg.scored, 2)
        self.assertEqual(agg.accuracy, 0.5)

    def test_swebench_is_excluded_not_counted_wrong(self):
        agg = summarize([result(correct=True),
                         result(outcome="skipped", correct=None, gradable=False)])
        self.assertEqual(agg.ungradable, 1)
        self.assertEqual(agg.scored, 1)
        self.assertEqual(agg.accuracy, 1.0)

    def test_format_ok_is_also_ungradable(self):
        agg = summarize([result(outcome="format_ok", correct=None)])
        self.assertEqual(agg.ungradable, 1)
        self.assertEqual(agg.scored, 0)
        self.assertIsNone(agg.accuracy)

    def test_infrastructure_failure_does_not_lower_accuracy(self):
        """An outage is not a wrong answer. Counting it as one would make a bad
        server look like a bad prompt."""
        agg = summarize([result(correct=True),
                         result(status="error", outcome="not_run", correct=None),
                         result(status="no_reply", outcome="not_run", correct=None)])
        self.assertEqual(agg.failed, 2)
        self.assertEqual(agg.scored, 1)
        self.assertEqual(agg.accuracy, 1.0)

    def test_cancelled_counts_as_failed_not_wrong(self):
        agg = summarize([result(status="cancelled", outcome="not_run", correct=None)])
        self.assertEqual(agg.failed, 1)
        self.assertEqual(agg.scored, 0)

    def test_accuracy_is_none_when_nothing_was_scored(self):
        self.assertIsNone(summarize([]).accuracy)


class Tokens(unittest.TestCase):
    def test_tokens_count_every_attempt_including_failures(self):
        """Spent is spent. The token denominator is wider than accuracy's."""
        agg = summarize([
            result(prompt=100, completion=50),
            result(status="error", outcome="not_run", correct=None,
                   prompt=80, completion=0),
            result(outcome="skipped", correct=None, gradable=False,
                   prompt=200, completion=300),
        ])
        self.assertEqual(agg.prompt_tokens, 380)
        self.assertEqual(agg.completion_tokens, 350)
        self.assertEqual(agg.total_tokens, 730)
        self.assertEqual(agg.scored, 1)

    def test_missing_token_counts_are_treated_as_zero(self):
        agg = summarize([result(prompt=None, completion=None)])
        self.assertEqual(agg.total_tokens, 0)


class Conditions(unittest.TestCase):
    def test_one_condition_is_not_mixed(self):
        agg = summarize([result(item_id="a"), result(item_id="b")])
        self.assertFalse(agg.mixed_conditions)

    def test_changing_the_agent_marks_the_run_mixed(self):
        agg = summarize([result(agent="ag1"), result(agent="ag2")])
        self.assertTrue(agg.mixed_conditions)

    def test_changing_the_model_marks_the_run_mixed(self):
        agg = summarize([result(model="local"), result(model="remote")])
        self.assertTrue(agg.mixed_conditions)


class Log(unittest.TestCase):
    def test_rows_are_written_as_each_item_lands(self):
        """A full sweep takes tens of minutes; a crash at minute 30 must not cost
        the first 29."""
        with tempfile.TemporaryDirectory() as tmp:
            log = RunLog(tmp, stamp="test")
            log.append(result(item_id="first"))
            partial = Path(tmp, "test.jsonl").read_text(encoding="utf-8")
            self.assertEqual(len(partial.strip().splitlines()), 1)
            log.append(result(item_id="second"))
            log.close()

            rows = [json.loads(line) for line in
                    Path(tmp, "test.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["item_id"] for r in rows], ["first", "second"])

    def test_row_shape_is_what_grade_py_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = RunLog(tmp, stamp="shape")
            log.append(result(item_id="only", seconds=12.34))
            log.close()
            row = json.loads(Path(tmp, "shape.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(set(row), set(RunLog.FIELDS))
        self.assertEqual(row["wallclock_seconds"], 12.3)
        self.assertEqual(row["output"], "out")


if __name__ == "__main__":
    unittest.main()
