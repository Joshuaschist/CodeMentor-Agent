"""End-to-end, credential-safe CLI for CodeMentor assessment and benchmarking."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

from agents import CodeMentorAgent
from evaluation.benchmark import BenchmarkRunner
from trajectories import TrajectoryLogger


class UserFacingError(Exception):
    """Expected input or integration errors displayed without a traceback."""


def _load_assignment(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UserFacingError(f"Assignment file was not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UserFacingError(f"Assignment JSON is invalid: {exc.msg}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rubric"), list):
        raise UserFacingError("Assignment JSON must be an object with a rubric list.")
    return data


def _load_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise UserFacingError(f"Student source file was not found: {path}") from exc
    except OSError as exc:
        raise UserFacingError(f"Student source could not be read: {exc}") from exc


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise UserFacingError("Live mode requires OPENAI_API_KEY. Configure it and retry; fixture mode does not need it.")


def _assignment_for_case(case: Mapping[str, Any]) -> Dict[str, Any]:
    """Adapt benchmark inputs without changing their independent ground truth."""
    return {
        "title": "Simple Calculator",
        "description": "Implement calculate(a, b, operation) for +, -, *, and /; raise ValueError for unsupported operations and division by zero.",
        "rubric": [{"requirement": item["requirement"], "points": item["max_points"]} for item in case["expected_rubric_outcomes"]],
        "maximum_score": case["maximum_score"],
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    lines = [f"# CodeMentor Benchmark — {report['mode']}", "", f"Cases: {report['comparison']['case_count']}", "", "| System | Avg score error | Requirement accuracy | Avg requirement score error | Defect detection | Unsupported runtime claims |", "|---|---:|---:|---:|---:|---:|"]
    for name, values in report["comparison"]["systems"].items():
        summary = values["summary"]
        lines.append(f"| {name} | {summary['average_score_error']:.2f} | {summary['requirement_accuracy']:.2%} | {summary['average_requirement_score_error']:.2f} | {summary['defect_detection_rate']:.2%} | {summary['unsupported_runtime_claim_rate']:.2%} |")
    return "\n".join(lines) + "\n"


def run_assess(args: argparse.Namespace) -> int:
    assignment, source = _load_assignment(args.assignment), _load_source(args.student_code)
    run_id = str(uuid.uuid4())
    logger = TrajectoryLogger(run_id=run_id, case_id=args.case_id)
    assessment = CodeMentorAgent().run(assignment, source, case_id=args.case_id, trajectory_logger=logger, use_ai=args.ai, ai_model=args.ai_model)
    output = args.output or Path("outputs/assessments") / f"{run_id}.json"
    trajectory_output = args.trajectory_output or Path("outputs/trajectories") / f"{run_id}.json"
    _write_json(output, assessment)
    trajectory_output.parent.mkdir(parents=True, exist_ok=True)
    trajectory_output.write_text(logger.to_json() + "\n", encoding="utf-8")
    print(f"Assessment saved: {output}")
    print(f"Trajectory saved: {trajectory_output}")
    print(f"Run ID: {run_id}")
    return 0


def run_benchmark(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    if args.mode == "fixture":
        comparison = BenchmarkRunner().run_fixture()
        label = "FIXTURE"
    else:
        _require_api_key()
        from baseline.reviewer import review_submission  # Imported only in live mode.

        agent = CodeMentorAgent()
        trajectories: Dict[str, str] = {}

        def run_agent(case: Mapping[str, Any]) -> Mapping[str, Any]:
            logger = TrajectoryLogger(case_id=case["case_id"])
            assessment = agent.run(_assignment_for_case(case), case["student_submission"], case_id=case["case_id"], trajectory_logger=logger, use_ai=True, ai_model=args.model)
            trajectory_path = output_dir / "trajectories" / f"{logger.run_id}.json"
            trajectory_path.parent.mkdir(parents=True, exist_ok=True)
            trajectory_path.write_text(logger.to_json() + "\n", encoding="utf-8")
            trajectories[case["case_id"]] = str(trajectory_path)
            return assessment

        def run_baseline(case: Mapping[str, Any]) -> Mapping[str, Any]:
            return review_submission(_assignment_for_case(case), case["student_submission"], args.model)

        comparison = BenchmarkRunner().compare({"baseline": run_baseline, "agent": run_agent})
        label = "LIVE"
    report = {"mode": label, "generated_at": datetime.now(timezone.utc).isoformat(), "comparison": comparison}
    report_path = output_dir / f"{args.mode}_report.json"
    summary_path = output_dir / f"{args.mode}_summary.md"
    _write_json(report_path, report)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_render_summary(report), encoding="utf-8")
    print(f"{label} benchmark report saved: {report_path}")
    print(f"{label} benchmark summary saved: {summary_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodeMentor assessment and benchmark CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    assess = commands.add_parser("assess", help="Assess one Python submission with the CodeMentor agent")
    assess.add_argument("--assignment", type=Path, required=True)
    assess.add_argument("--student-code", type=Path, required=True)
    assess.add_argument("--output", type=Path)
    assess.add_argument("--trajectory-output", type=Path)
    assess.add_argument("--case-id")
    assess.add_argument("--ai", action="store_true", help="Add an OpenAI mentor explanation grounded in the evidence")
    assess.add_argument("--ai-model", default=None, help="OpenAI model for the optional mentor explanation")
    assess.set_defaults(handler=run_assess)
    benchmark = commands.add_parser("benchmark", help="Compare systems against benchmark ground truth")
    benchmark.add_argument("--mode", choices=("fixture", "live"), required=True)
    benchmark.add_argument("--output-dir", type=Path, default=Path("outputs/benchmarks"))
    benchmark.add_argument("--model", default="gpt-4.1-mini", help="Used by the baseline in live mode only")
    benchmark.set_defaults(handler=run_benchmark)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except UserFacingError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Error: invalid assessment, tool request, or model output: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: assessment failed safely ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
