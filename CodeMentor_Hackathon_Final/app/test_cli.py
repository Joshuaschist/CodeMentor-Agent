"""Offline integration tests for the CodeMentor CLI."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from app.cli import main


ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = ROOT / "data" / "calculator_assignment.json"
SUBMISSION = ROOT / "data" / "submissions" / "calculator_divide_by_zero.py"


class CliTests(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(arguments)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_fixture_benchmark_works_without_key_and_is_labeled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.pop("OPENAI_API_KEY", None)
            try:
                status, _, error = self.invoke(["benchmark", "--mode", "fixture", "--output-dir", directory])
            finally:
                if previous is not None:
                    os.environ["OPENAI_API_KEY"] = previous
            self.assertEqual(status, 0, error)
            report = json.loads((Path(directory) / "fixture_report.json").read_text())
            self.assertEqual(report["mode"], "FIXTURE")
            self.assertEqual(report["comparison"]["case_count"], 12)

    def test_assessment_validates_inputs(self) -> None:
        status, _, error = self.invoke(["assess", "--assignment", "missing.json", "--student-code", str(SUBMISSION)])
        self.assertEqual(status, 2)
        self.assertIn("Assignment file was not found", error)

    def test_live_refuses_to_use_fixtures_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.pop("OPENAI_API_KEY", None)
            try:
                status, _, error = self.invoke(["benchmark", "--mode", "live", "--output-dir", directory])
            finally:
                if previous is not None:
                    os.environ["OPENAI_API_KEY"] = previous
            self.assertEqual(status, 2)
            self.assertIn("Live mode requires OPENAI_API_KEY", error)
            self.assertFalse((Path(directory) / "live_report.json").exists())

    def test_assessment_writes_linked_trajectory_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original = Path.cwd()
            os.chdir(directory)
            try:
                status, _, error = self.invoke(["assess", "--assignment", str(ASSIGNMENT), "--student-code", str(SUBMISSION), "--case-id", "division_by_zero"])
            finally:
                os.chdir(original)
            self.assertEqual(status, 0, error)
            assessment_paths = list((Path(directory) / "outputs" / "assessments").glob("*.json"))
            trajectory_paths = list((Path(directory) / "outputs" / "trajectories").glob("*.json"))
            self.assertEqual(len(assessment_paths), 1)
            self.assertEqual(assessment_paths[0].stem, trajectory_paths[0].stem)
            trajectory = json.loads(trajectory_paths[0].read_text())
            self.assertEqual(trajectory["case_id"], "division_by_zero")

    def test_reports_contain_no_environment_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secret = "not-a-real-key-should-not-appear"
            previous = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = secret
            try:
                status, _, error = self.invoke(["benchmark", "--mode", "fixture", "--output-dir", directory])
            finally:
                if previous is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = previous
            self.assertEqual(status, 0, error)
            self.assertNotIn(secret, (Path(directory) / "fixture_report.json").read_text())


if __name__ == "__main__":
    unittest.main()
