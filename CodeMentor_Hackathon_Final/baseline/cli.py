"""Command-line entry point for the baseline reviewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .reviewer import review_submission


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a Python submission without executing it.")
    parser.add_argument("--assignment", required=True, type=Path, help="Assignment JSON containing description and rubric.")
    parser.add_argument("--student-code", required=True, type=Path, help="Student source file to review.")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
    parser.add_argument("--output", type=Path, help="Optional JSON file for the assessment.")
    args = parser.parse_args()

    try:
        assignment = json.loads(args.assignment.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Could not read assignment JSON: {exc}")
    try:
        student_code = args.student_code.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(f"Could not read student code: {exc}")

    assessment = review_submission(assignment, student_code, args.model)
    rendered = json.dumps(assessment, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
