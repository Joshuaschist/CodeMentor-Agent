"""A small, single-agent orchestration loop with validated evidence tools."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict, List, Mapping, Optional, Protocol

from .tools import ToolResult, inspect_code, parse_test_cases, read_assignment, run_python_tests
from .ai_mentor import generate_ai_feedback
from trajectories.logger import RUNTIME_EVIDENCE, TrajectoryLogger, emit_agent_event


@dataclass(frozen=True)
class ToolRequest:
    """The only shape a future model/planner may use to request an action."""
    tool_name: str
    arguments: Dict[str, Any]


class ToolPlanner(Protocol):
    """Future LLM adapters return structured requests through this interface."""
    def next_request(self, evidence: List[ToolResult]) -> ToolRequest:
        ...


def calculator_test_cases() -> List[Dict[str, Any]]:
    """Application-owned tests for the included calculator assignment."""
    return [
        {"name": "addition", "function": "calculate", "args": [2, 3, "+"], "expected": 5, "rubric_index": 1},
        {"name": "subtraction", "function": "calculate", "args": [7, 2, "-"], "expected": 5, "rubric_index": 1},
        {"name": "multiplication", "function": "calculate", "args": [4, 3, "*"], "expected": 12, "rubric_index": 1},
        {"name": "division", "function": "calculate", "args": [8, 2, "/"], "expected": 4, "rubric_index": 1},
        {"name": "unsupported operation", "function": "calculate", "args": [1, 2, "%"], "expected_exception": "ValueError", "rubric_index": 2},
        {"name": "division by zero", "function": "calculate", "args": [1, 0, "/"], "expected_exception": "ValueError", "rubric_index": 3},
    ]


class CodeMentorAgent:
    """Coordinates trusted tools; it never executes a command supplied by a model."""

    def _execute(self, request: ToolRequest, assignment: Mapping[str, Any], source: str) -> ToolResult:
        if request.tool_name == "read_assignment":
            if request.arguments:
                raise ValueError("read_assignment accepts no arguments")
            return read_assignment(assignment)
        if request.tool_name == "inspect_code":
            if request.arguments:
                raise ValueError("inspect_code accepts no arguments")
            return inspect_code(source)
        if request.tool_name == "run_python_tests":
            if set(request.arguments) - {"test_cases", "timeout_seconds"}:
                raise ValueError("run_python_tests received unsupported arguments")
            cases = parse_test_cases(request.arguments.get("test_cases"))
            timeout = request.arguments.get("timeout_seconds", 3.0)
            if not isinstance(timeout, (int, float)):
                raise ValueError("timeout_seconds must be numeric")
            return run_python_tests(source, cases, float(timeout))
        raise ValueError(f"Tool is not available: {request.tool_name}")

    def run(self, assignment: Mapping[str, Any], student_source: str, rubric: Optional[List[Mapping[str, Any]]] = None, verification_cases: Optional[List[Mapping[str, Any]]] = None, *, case_id: Optional[str] = None, trajectory_logger: Optional[TrajectoryLogger] = None, use_ai: Optional[bool] = None, ai_model: Optional[str] = None) -> Dict[str, Any]:
        """Run the deterministic first loop and return baseline-compatible JSON."""
        logger = trajectory_logger
        if logger and case_id and not logger.case_id:
            logger.case_id = case_id
        emit_agent_event(logger, "agent_started", details={"agent": "CodeMentorAgent"})
        normalized = dict(assignment)
        if rubric is not None:
            normalized["rubric"] = rubric
        emit_agent_event(logger, "assignment_loaded", result_summary={"title": normalized.get("title"), "rubric_count": len(normalized.get("rubric", []))})

        def execute_traced(request: ToolRequest) -> ToolResult:
            emit_agent_event(logger, "tool_requested", tool_name=request.tool_name, tool_arguments=request.arguments)
            emit_agent_event(logger, "tool_validated", tool_name=request.tool_name, success=True)
            try:
                result = self._execute(request, normalized, student_source)
            except Exception as exc:
                emit_agent_event(logger, "tool_executed", tool_name=request.tool_name, success=False, result_summary={"error_type": type(exc).__name__})
                raise
            summary = {"result_keys": list(result.data)}
            if request.tool_name == "run_python_tests":
                summary["cases"] = [{"name": row["case"]["name"], "passed": row["passed"], "exit_code": row["exit_code"], "timed_out": row["timed_out"]} for row in result.data["results"]]
            execution_id = logger.record_tool_execution(request.tool_name, summary, success=True) if logger else None
            if request.tool_name == "inspect_code":
                emit_agent_event(logger, "code_inspected", result_summary={"parseable": result.data.get("parseable"), "function_count": len(result.data.get("functions", []))})
                if logger:
                    logger.record_static_evidence({"parseable": result.data.get("parseable"), "functions": [item["name"] for item in result.data.get("functions", [])]})
            if request.tool_name == "run_python_tests" and logger and execution_id:
                logger.record_runtime_evidence(execution_id, {"observed": [{"case": row["case"]["name"], "exception_type": (row["observed"] or {}).get("exception_type"), "passed": row["passed"]} for row in result.data["results"]]})
            return result

        try:
            evidence = [execute_traced(ToolRequest("read_assignment", {})), execute_traced(ToolRequest("inspect_code", {}))]
            cases = verification_cases
            if cases is None and normalized.get("title") == "Simple Calculator":
                cases = calculator_test_cases()
            emit_agent_event(logger, "verification_needed", result_summary={"needed": cases is not None, "case_count": len(cases or [])})
            if cases is not None:
                evidence.append(execute_traced(ToolRequest("run_python_tests", {"test_cases": cases})))
            assessment = self._compose_assessment(normalized, evidence)
            emit_agent_event(logger, "assessment_generated", result_summary={"score": assessment["score"], "requirement_statuses": [item["status"] for item in assessment["requirements"]]})

            # AI is an explanation layer over trusted evidence; it never controls
            # the score or invents runtime results.
            ai_enabled = use_ai if use_ai is not None else bool(os.environ.get("OPENAI_API_KEY"))
            if ai_enabled:
                try:
                    ai_feedback = generate_ai_feedback(normalized, assessment, model=ai_model)
                    assessment["ai_mentor_feedback"] = ai_feedback
                    emit_agent_event(
                        logger,
                        "ai_feedback_generated",
                        result_summary={"provider": "OpenAI", "model": ai_model or os.environ.get("CODEMENTOR_MODEL", "gpt-5.6-luna")},
                    )
                except Exception as exc:
                    assessment["ai_mentor_feedback"] = {
                        "summary": "AI explanation was unavailable; the evidence-backed assessment is still valid.",
                        "strengths": [],
                        "issues": [],
                        "next_steps": [],
                        "status": "unavailable",
                    }
                    emit_agent_event(logger, "ai_feedback_generated", success=False, result_summary={"error_type": type(exc).__name__})

            emit_agent_event(logger, "agent_finished", success=True)
            return assessment
        except Exception:
            emit_agent_event(logger, "agent_finished", success=False)
            raise

    @staticmethod
    def _compose_assessment(assignment: Mapping[str, Any], evidence: List[ToolResult]) -> Dict[str, Any]:
        inspection = next(item.data for item in evidence if item.tool_name == "inspect_code")
        test_data = next((item.data for item in evidence if item.tool_name == "run_python_tests"), None)
        tests_by_rubric: Dict[int, List[Dict[str, Any]]] = {}
        if test_data:
            for result in test_data["results"]:
                rubric_index = result["case"].get("rubric_index")
                if rubric_index is not None:
                    tests_by_rubric.setdefault(rubric_index, []).append(result)
        requirements, problems, total = [], [], 0.0
        for index, rubric_item in enumerate(assignment.get("rubric", [])):
            points = float(rubric_item.get("points", 0))
            cases = tests_by_rubric.get(index, [])
            if cases:
                passed = all(case["passed"] for case in cases)
                status, awarded = ("met", points) if passed else ("not_met", 0.0)
                evidence_text = "; ".join(f"{case['case']['name']}: {'passed' if case['passed'] else 'failed'} (observed subprocess result)" for case in cases)
                if not passed:
                    problems.append(f"Verification did not satisfy: {rubric_item.get('requirement', 'rubric requirement')}")
            elif index == 0 and inspection.get("parseable"):
                matching = any(fn["name"] == "calculate" and fn["parameters"] == ["a", "b", "operation"] for fn in inspection["functions"])
                status, awarded = ("met", points) if matching else ("not_met", 0.0)
                evidence_text = "Static source inspection found the required calculate(a, b, operation) signature." if matching else "Static source inspection did not find the required calculate(a, b, operation) signature."
                if not matching:
                    problems.append("Required calculate(a, b, operation) function was not found by static inspection.")
            else:
                status, awarded, evidence_text = "unclear", 0.0, "No approved evidence was gathered for this requirement."
            total += awarded
            requirements.append({"requirement": rubric_item.get("requirement", ""), "status": status, "evidence": evidence_text, "points_awarded": awarded})
        max_score = float(assignment.get("maximum_score", sum(item.get("points", 0) for item in assignment.get("rubric", [])) or 100))
        score = min(100.0, (total / max_score * 100.0) if max_score else 0.0)
        feedback = "Review the identified requirements and revise the code using the observed evidence." if problems else "The gathered static and subprocess evidence supports the assessed requirements."
        limitations = "Static inspection does not prove runtime behavior. Only listed approved subprocess cases were executed; no other tests or commands were run."
        return {"score": score, "score_rationale": "Score is the sum of rubric points supported by static inspection or observed approved test results.", "requirements": requirements, "identified_problems": problems, "student_feedback": feedback, "evidence_limitations": limitations}
