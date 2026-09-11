"""Ground-truth-based validation and metrics for CodeMentor assessments."""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping


class AssessmentValidationError(ValueError):
    """Raised when an assessment cannot be compared fairly."""


REQUIRED_FIELDS = {"score", "score_rationale", "requirements", "identified_problems", "student_feedback", "evidence_limitations"}
VALID_STATUSES = {"met", "partially_met", "not_met", "unclear"}
RUNTIME_LANGUAGE = re.compile(r"\b(test(?:s|ed|ing)?|executed|ran|runtime)\b", re.IGNORECASE)


def validate_assessment(assessment: Mapping[str, Any], case: Mapping[str, Any]) -> None:
    """Validate schema essentials and rubric bounds before calculating metrics."""
    if not isinstance(assessment, Mapping) or set(assessment) != REQUIRED_FIELDS:
        raise AssessmentValidationError("Assessment must contain exactly the required top-level fields")
    maximum = case["maximum_score"]
    if not isinstance(assessment["score"], (int, float)) or not 0 <= assessment["score"] <= maximum:
        raise AssessmentValidationError("score must be within the assignment maximum")
    expected = case["expected_rubric_outcomes"]
    requirements = assessment["requirements"]
    if not isinstance(requirements, list) or len(requirements) != len(expected):
        raise AssessmentValidationError("Assessment requirements must match rubric length")
    for item, truth in zip(requirements, expected):
        if not isinstance(item, Mapping) or set(item) != {"requirement", "status", "evidence", "points_awarded"}:
            raise AssessmentValidationError("Each requirement has an invalid shape")
        if item["status"] not in VALID_STATUSES:
            raise AssessmentValidationError("Requirement status is invalid")
        if not isinstance(item["points_awarded"], (int, float)) or not 0 <= item["points_awarded"] <= truth["max_points"]:
            raise AssessmentValidationError("Requirement points exceed the rubric maximum")


def _has_execution_evidence(assessment: Mapping[str, Any]) -> bool:
    return any("observed subprocess result" in requirement["evidence"].lower() for requirement in assessment["requirements"])


def _runtime_claim_is_unsupported(assessment: Mapping[str, Any]) -> bool:
    claim_text = " ".join([assessment["score_rationale"], assessment["student_feedback"], *assessment["identified_problems"]])
    has_runtime_claim = bool(RUNTIME_LANGUAGE.search(claim_text))
    return has_runtime_claim and not _has_execution_evidence(assessment)


def _feedback_claim_is_unsupported(assessment: Mapping[str, Any]) -> bool:
    has_runtime_claim = bool(RUNTIME_LANGUAGE.search(assessment["student_feedback"]))
    return has_runtime_claim and not _has_execution_evidence(assessment)


def evaluate_assessment(assessment: Mapping[str, Any], case: Mapping[str, Any]) -> Dict[str, float]:
    """Compare a system assessment only with explicit case ground truth."""
    validate_assessment(assessment, case)
    truth = case["expected_rubric_outcomes"]
    requirements = assessment["requirements"]
    matches = sum(item["status"] == expected["status"] for item, expected in zip(requirements, truth))
    point_error = sum(abs(item["points_awarded"] - expected["points_awarded"]) for item, expected in zip(requirements, truth))
    known_defects = case.get("known_defects", [])
    problems = " ".join(assessment["identified_problems"]).lower()
    detected = sum(defect.lower() in problems for defect in known_defects)
    return {
        "score_error": abs(assessment["score"] - case["expected_score"]),
        "requirement_accuracy": matches / len(truth) if truth else 1.0,
        "requirement_score_error": point_error,
        "defect_detection": detected / len(known_defects) if known_defects else 1.0,
        "unsupported_runtime_claim": float(_runtime_claim_is_unsupported(assessment)),
        "feedback_runtime_claim_without_evidence": float(_feedback_claim_is_unsupported(assessment)),
    }


def aggregate_metrics(rows: list[Mapping[str, float]]) -> Dict[str, float]:
    """Return report-ready averages across benchmark cases."""
    if not rows:
        return {"average_score_error": 0.0, "requirement_accuracy": 0.0, "average_requirement_score_error": 0.0, "defect_detection_rate": 0.0, "unsupported_runtime_claim_rate": 0.0}
    count = len(rows)
    return {
        "average_score_error": sum(row["score_error"] for row in rows) / count,
        "requirement_accuracy": sum(row["requirement_accuracy"] for row in rows) / count,
        "average_requirement_score_error": sum(row["requirement_score_error"] for row in rows) / count,
        "defect_detection_rate": sum(row["defect_detection"] for row in rows) / count,
        "unsupported_runtime_claim_rate": sum(row["unsupported_runtime_claim"] for row in rows) / count,
    }
