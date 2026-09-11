"""Offline tests for trajectory structure, provenance, and sanitization."""

from __future__ import annotations

import json
import unittest

from trajectories.logger import RUNTIME_EVIDENCE, STATIC_EVIDENCE, TrajectoryLogger


class TrajectoryLoggerTests(unittest.TestCase):
    def test_event_has_required_structure(self) -> None:
        logger = TrajectoryLogger(run_id="run-1", case_id="case-1")
        logger.record("agent_started")
        event = logger.events[0]
        self.assertEqual(event["event_type"], "agent_started")
        self.assertEqual(event["run_id"], "run-1")
        self.assertIn("timestamp", event)
        self.assertTrue(event["success"])

    def test_runtime_evidence_requires_execution(self) -> None:
        logger = TrajectoryLogger()
        with self.assertRaises(ValueError):
            logger.record_runtime_evidence("invented-event", {"claim": "test passed"})
        failed = logger.record_tool_execution("run_python_tests", {"error_type": "TimeoutExpired"}, success=False)
        with self.assertRaises(ValueError):
            logger.record_runtime_evidence(failed, {"claim": "test passed"})
        executed = logger.record_tool_execution("run_python_tests", {"case_count": 1}, success=True)
        logger.record_runtime_evidence(executed, {"exception_type": "ZeroDivisionError"})
        self.assertEqual(logger.events[-1]["evidence_type"], RUNTIME_EVIDENCE)

    def test_secrets_and_source_are_not_logged(self) -> None:
        logger = TrajectoryLogger()
        logger.record("tool_requested", tool_arguments={"api_key": "do-not-log", "student_source": "print('secret source')"})
        rendered = logger.to_json()
        self.assertNotIn("do-not-log", rendered)
        self.assertNotIn("print('secret source')", rendered)
        self.assertIn("[redacted]", rendered)
        self.assertIn("[omitted source content", rendered)

    def test_json_serialization_and_static_evidence(self) -> None:
        logger = TrajectoryLogger()
        logger.record_static_evidence({"function_count": 1})
        payload = json.loads(logger.to_json())
        self.assertEqual(payload["events"][0]["evidence_type"], STATIC_EVIDENCE)

    def test_failed_tool_call_is_represented(self) -> None:
        logger = TrajectoryLogger()
        logger.record_tool_execution("run_python_tests", {"error_type": "TimeoutExpired"}, success=False)
        event = logger.events[-1]
        self.assertFalse(event["success"])
        self.assertEqual(event["tool_name"], "run_python_tests")


if __name__ == "__main__":
    unittest.main()
