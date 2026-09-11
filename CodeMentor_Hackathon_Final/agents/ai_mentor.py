"""OpenAI-powered mentor explanation layer for CodeMentor.

The model explains evidence already gathered by trusted host tools. It never
determines whether a test passed and never receives an API key in the prompt.
If the API is unavailable, the core deterministic assessment remains valid.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Mapping



AI_SYSTEM_PROMPT = """You are CodeMentor, an AI mentor helping an instructor review
a programming assignment. The host application has already gathered trusted
static inspection and bounded subprocess evidence. Do not invent tests, execution
results, scores, or defects. Explain only what the supplied evidence supports.

Return valid JSON with exactly these keys:
summary: string
strengths: array of short strings
issues: array of short strings
next_steps: array of short strings

Be concise, specific, and student-friendly. If evidence is missing, say so."""


def generate_ai_feedback(
    assignment: Mapping[str, Any],
    assessment: Mapping[str, Any],
    *,
    model: str | None = None,
) -> Dict[str, Any]:
    """Generate an AI explanation grounded only in the host-produced assessment."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI()
    payload = {
        "assignment": assignment,
        "assessment": assessment,
    }
    response = client.responses.create(
        model=model or os.environ.get("CODEMENTOR_MODEL", "gpt-5.6-luna"),
        instructions=AI_SYSTEM_PROMPT,
        input=json.dumps(payload, indent=2),
    )
    text = response.output_text.strip()
    if not text:
        raise RuntimeError("OpenAI returned no mentor explanation")

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI mentor explanation was not valid JSON") from exc

    required = {"summary", "strengths", "issues", "next_steps"}
    if set(result) != required:
        raise RuntimeError("OpenAI mentor explanation did not match the expected schema")
    if not all(isinstance(result[key], list) for key in ("strengths", "issues", "next_steps")):
        raise RuntimeError("OpenAI mentor explanation contains invalid list fields")
    return result
