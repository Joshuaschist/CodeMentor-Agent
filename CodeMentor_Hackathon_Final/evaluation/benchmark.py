"""Benchmark runner supporting fixture assessments and injected real systems."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping

from .metrics import aggregate_metrics, evaluate_assessment


CASES_PATH = Path(__file__).with_name("cases") / "calculator_cases.json"


def load_cases(path: Path = CASES_PATH) -> List[Dict[str, Any]]:
    """Load explicit benchmark ground truth; no model is involved."""
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def fixture_assessment(case: Mapping[str, Any], system: str) -> Dict[str, Any]:
    """Create a fixed offline assessment from the predetermined case fixture."""
    fixture = case["fixtures"][system]
    requirement_rows = []
    for truth, status, points in zip(case["expected_rubric_outcomes"], fixture["statuses"], fixture["points"]):
        evidence = "Static source observation only."
        if fixture.get("execution_evidence"):
            evidence = "Observed subprocess result from an approved verification case."
        requirement_rows.append({"requirement": truth["requirement"], "status": status, "evidence": evidence, "points_awarded": points})
    rationale = "Fixture assessment based on source review."
    if fixture.get("runtime_claim"):
        rationale = "Tests passed according to the review."
    return {"score": fixture["score"], "score_rationale": rationale, "requirements": requirement_rows, "identified_problems": fixture["problems"], "student_feedback": fixture.get("feedback", "Address the identified issues."), "evidence_limitations": "Fixture mode: no live LLM call was made."}


class BenchmarkRunner:
    """Runs identical metric logic over fixtures or caller-supplied systems."""

    def __init__(self, cases: List[Dict[str, Any]] | None = None) -> None:
        self.cases = cases or load_cases()

    def run_fixture(self) -> Dict[str, Any]:
        return self.compare({system: lambda case, name=system: fixture_assessment(case, name) for system in ("baseline", "agent")})

    def compare(self, systems: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]]) -> Dict[str, Any]:
        report: Dict[str, Any] = {"case_count": len(self.cases), "systems": {}}
        for name, produce_assessment in systems.items():
            per_case = []
            for case in self.cases:
                metrics = evaluate_assessment(produce_assessment(case), case)
                per_case.append({"case_id": case["case_id"], **metrics})
            report["systems"][name] = {"summary": aggregate_metrics(per_case), "per_case": per_case}
        return report


if __name__ == "__main__":
    print(json.dumps(BenchmarkRunner().run_fixture(), indent=2))
