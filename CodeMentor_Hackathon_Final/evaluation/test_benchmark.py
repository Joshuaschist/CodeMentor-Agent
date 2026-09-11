"""Offline unit tests for benchmark validation, metrics, and reports."""

from __future__ import annotations

import copy
import os
import unittest

from evaluation.benchmark import BenchmarkRunner, fixture_assessment, load_cases
from evaluation.metrics import AssessmentValidationError, evaluate_assessment, validate_assessment


class BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = load_cases()[1]
        self.assessment = fixture_assessment(self.case, "agent")

    def test_metrics_are_calculated_correctly(self) -> None:
        metrics = evaluate_assessment(self.assessment, self.case)
        self.assertEqual(metrics["score_error"], 0)
        self.assertEqual(metrics["requirement_accuracy"], 1)
        self.assertEqual(metrics["defect_detection"], 1)

    def test_malformed_assessment_is_rejected(self) -> None:
        broken = copy.deepcopy(self.assessment)
        del broken["score"]
        with self.assertRaises(AssessmentValidationError):
            validate_assessment(broken, self.case)

    def test_scores_and_requirement_points_are_bounded(self) -> None:
        excessive_score = copy.deepcopy(self.assessment)
        excessive_score["score"] = 101
        with self.assertRaises(AssessmentValidationError):
            validate_assessment(excessive_score, self.case)
        excessive_points = copy.deepcopy(self.assessment)
        excessive_points["requirements"][0]["points_awarded"] = 21
        with self.assertRaises(AssessmentValidationError):
            validate_assessment(excessive_points, self.case)

    def test_comparison_report_is_generated(self) -> None:
        report = BenchmarkRunner().run_fixture()
        self.assertEqual(report["case_count"], 12)
        self.assertEqual(set(report["systems"]), {"baseline", "agent"})
        self.assertIn("average_score_error", report["systems"]["agent"]["summary"])

    def test_fixture_mode_needs_no_api_key(self) -> None:
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            report = BenchmarkRunner().run_fixture()
            self.assertEqual(report["systems"]["agent"]["summary"]["average_score_error"], 0)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
