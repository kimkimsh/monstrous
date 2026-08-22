"""Covers sample validation and the grade.py wrapper against the fixtures next door.

fixtures/ holds four real samples plus one deliberately malformed file, so a load over
that directory exercises both halves of the load report.
"""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.grading import grade  # noqa: E402
from core.samples import load_report, load_samples, validate_sample  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

MATH_TAIL = "\n\nFINAL ANSWER: \\boxed{%s}\n"
GENERIC_TAIL = "\n\nANSWER: %s\n"


def sample_by_id(item_id):
    for sample in load_samples(FIXTURES):
        if sample.id == item_id:
            return sample
    raise AssertionError(f"fixture {item_id} not found")


class MathGrading(unittest.TestCase):
    def setUp(self):
        self.sample = sample_by_id("math-visible-0001")

    def test_gold_form_is_correct(self):
        result = grade(self.sample, "reasoning" + MATH_TAIL % "\\frac{11}{2}")
        self.assertEqual(result.outcome, "graded")
        self.assertTrue(result.correct, result.detail)

    def test_decimal_equals_the_fraction_gold(self):
        result = grade(self.sample, "reasoning" + MATH_TAIL % "5.5")
        self.assertEqual(result.outcome, "graded")
        self.assertTrue(result.correct, result.detail)

    def test_wrong_value(self):
        result = grade(self.sample, "reasoning" + MATH_TAIL % "3")
        self.assertEqual(result.outcome, "graded")
        self.assertFalse(result.correct)

    def test_missing_boxed_line(self):
        result = grade(self.sample, "The answer is 11/2.")
        self.assertEqual(result.outcome, "extraction_failed")
        self.assertFalse(result.correct)


class GenericGrading(unittest.TestCase):
    def setUp(self):
        self.sample = sample_by_id("generic-visible-mmlu-pro-10088")

    def test_correct_letter(self):
        result = grade(self.sample, "working" + GENERIC_TAIL % "B")
        self.assertEqual(result.outcome, "graded")
        self.assertTrue(result.correct, result.detail)

    def test_wrong_letter(self):
        result = grade(self.sample, "working" + GENERIC_TAIL % "C")
        self.assertEqual(result.outcome, "graded")
        self.assertFalse(result.correct)

    def test_missing_answer_line(self):
        result = grade(self.sample, "I think it is option B.")
        self.assertEqual(result.outcome, "extraction_failed")
        self.assertFalse(result.correct)


class CodingGrading(unittest.TestCase):
    def test_swebench_sample_is_skipped(self):
        sample = sample_by_id("coding-visible-0020")
        result = grade(sample, "*** PATCH START ***\nfoo.py\n*** PATCH END ***")
        self.assertEqual(result.outcome, "skipped")
        self.assertIsNone(result.correct)
        self.assertEqual(result.detail, sample.ungradable_reason)

    def test_livecodebench_without_patch_markers(self):
        sample = sample_by_id("coding-visible-0041")
        result = grade(sample, "```python\nprint(2024)\n```")
        self.assertEqual(result.outcome, "extraction_failed")
        self.assertFalse(result.correct)

    def test_livecodebench_edit_without_a_new_file_block(self):
        patch = ("*** PATCH START ***\n"
                 "solution.py\n"
                 "<<<<<<< SEARCH\n"
                 "print(0)\n"
                 "=======\n"
                 "print(2024)\n"
                 ">>>>>>> REPLACE\n"
                 "*** PATCH END ***\n")
        result = grade(sample_by_id("coding-visible-0041"), patch)
        self.assertEqual(result.outcome, "graded")
        self.assertFalse(result.correct)
        self.assertIn("no new-file block", result.detail)


class SampleValidation(unittest.TestCase):
    def clean(self):
        prompt = "two plus two\n"
        return {
            "schema_version": 1,
            "id": "math-visible-0002",
            "track": "math",
            "kind": "math",
            "gradable": True,
            "ungradable_reason": None,
            "prompt": prompt,
            "expected": {"grader": "math_answer", "gold": "4"},
            "meta": {"prompt_sha256":
                     hashlib.sha256(prompt.encode("utf-8")).hexdigest()},
        }

    def test_clean_sample_has_no_problems(self):
        self.assertEqual(validate_sample(self.clean()), [])

    def test_digest_mismatch(self):
        data = self.clean()
        data["prompt"] = data["prompt"] + "\n"
        problems = validate_sample(data)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("prompt_sha256", problems[0])

    def test_gradable_true_with_a_reason(self):
        data = self.clean()
        data["ungradable_reason"] = "swebench_docker is not run locally"
        problems = validate_sample(data)
        self.assertTrue(any("gradable is true but ungradable_reason is set" in p
                            for p in problems), problems)

    def test_gradable_false_without_a_reason(self):
        data = self.clean()
        data["gradable"] = False
        problems = validate_sample(data)
        self.assertTrue(any("gradable is false but ungradable_reason is missing" in p
                            for p in problems), problems)

    def test_unknown_track(self):
        data = self.clean()
        data["track"] = "physics"
        self.assertTrue(any("is not one of" in p for p in validate_sample(data)))

    def test_empty_expected(self):
        data = self.clean()
        data["expected"] = {}
        self.assertTrue(any("expected is empty" in p for p in validate_sample(data)))


class Loading(unittest.TestCase):
    def test_malformed_file_does_not_stop_the_load(self):
        report = load_report(FIXTURES)
        self.assertEqual([s.id for s in report.samples],
                         ["coding-visible-0020", "coding-visible-0041",
                          "generic-visible-mmlu-pro-10088", "math-visible-0001"])
        self.assertEqual([path.name for path, _ in report.errors],
                         ["math-visible-9999.json"])
        self.assertIn("unreadable:", report.errors[0][1][0])


if __name__ == "__main__":
    unittest.main()
