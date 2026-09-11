"""OpenAI-backed reviewer that analyzes code without executing it."""

from __future__ import annotations

import json
from typing import Any, Dict

from openai import OpenAI

from .schema import ASSESSMENT_SCHEMA


SYSTEM_PROMPT = """You are CodeMentor Agent's baseline coding-assignment reviewer.
Assess only the assignment description, grading rubric, and student code supplied.
Do not execute code, simulate execution, invent tests, or claim test results.
You may identify likely static-code issues, but label conclusions carefully when
runtime behavior is uncertain. Score consistently against the rubric. Return only
JSON that follows the requested schema. In evidence_limitations, clearly state that
this is a code review without execution or test evidence."""


def review_submission(
    assignment: Dict[str, Any], student_code: str, model: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    """Return a structured, non-executing assessment for one submission."""
    client = OpenAI()
    user_prompt = (
        "Assignment and rubric (JSON):\n"
        + json.dumps(assignment, indent=2)
        + "\n\nStudent code:\n```python\n"
        + student_code
        + "\n```"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_schema", "json_schema": {"name": ASSESSMENT_SCHEMA["name"], "strict": True, "schema": ASSESSMENT_SCHEMA["schema"]}},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The model returned no assessment content.")
    return json.loads(content)
