"""Assessment output contract and validation helpers."""

from __future__ import annotations

from typing import Any, Dict


ASSESSMENT_SCHEMA: Dict[str, Any] = {
    "name": "coding_assignment_assessment",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "score",
            "score_rationale",
            "requirements",
            "identified_problems",
            "student_feedback",
            "evidence_limitations",
        ],
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "score_rationale": {"type": "string"},
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["requirement", "status", "evidence", "points_awarded"],
                    "properties": {
                        "requirement": {"type": "string"},
                        "status": {"type": "string", "enum": ["met", "partially_met", "not_met", "unclear"]},
                        "evidence": {"type": "string"},
                        "points_awarded": {"type": "number", "minimum": 0},
                    },
                },
            },
            "identified_problems": {"type": "array", "items": {"type": "string"}},
            "student_feedback": {"type": "string"},
            "evidence_limitations": {"type": "string"},
        },
    },
}
