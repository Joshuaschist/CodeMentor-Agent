"""Prompts and response contracts for an optional tool-calling model."""

from __future__ import annotations

import json
from typing import Any, Mapping

TOOL_REQUEST_FORMAT = {"tool_name": "read_assignment | inspect_code | run_python_tests", "arguments": "object"}


def build_tool_planning_prompt(context: Mapping[str, Any]) -> str:
    """The host validates and executes any model-selected tool request."""
    instruction = """You are a coding-assignment review planner. Return one JSON object with
tool_name and arguments, or {\"tool_name\": \"finalize\", \"arguments\": {}}.
Allowed tools are read_assignment, inspect_code, and run_python_tests. Never request
shell commands, file-system paths, network access, or arbitrary code. Tests require
an explicit bounded test_cases list. Outcomes are evidence only after host results."""
    return instruction + "\n\nContext:\n" + json.dumps(context, indent=2)


ASSESSMENT_INSTRUCTION = """Produce score, score_rationale, requirements, identified_problems,
student_feedback, and evidence_limitations. Distinguish static observations from
observed subprocess evidence; never claim a test passed without tool evidence."""
