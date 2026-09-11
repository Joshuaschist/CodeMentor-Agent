"""Safe, explicit evidence-gathering tools for the first CodeMentor agent."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class TestCase:
    name: str
    function: str
    args: List[Any]
    kwargs: Dict[str, Any]
    expected: Any = None
    expected_exception: Optional[str] = None
    rubric_index: Optional[int] = None


@dataclass
class ToolResult:
    tool_name: str
    data: Dict[str, Any]


def read_assignment(assignment: Mapping[str, Any]) -> ToolResult:
    """Return assignment content exactly as provided by the caller."""
    return ToolResult("read_assignment", {"title": assignment.get("title"), "description": assignment.get("description"), "rubric": assignment.get("rubric", []), "maximum_score": assignment.get("maximum_score")})


def inspect_code(source_code: str) -> ToolResult:
    """Parse source without importing or executing it."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return ToolResult("inspect_code", {"parseable": False, "syntax_error": f"{exc.msg} (line {exc.lineno})", "functions": [], "imports": []})
    functions, imports = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({"name": node.name, "parameters": [arg.arg for arg in node.args.args], "line": node.lineno})
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return ToolResult("inspect_code", {"parseable": True, "functions": functions, "imports": imports})


def parse_test_cases(raw_cases: List[Mapping[str, Any]]) -> List[TestCase]:
    """Validate the restricted, JSON-only test-case language."""
    if not isinstance(raw_cases, list) or not raw_cases or len(raw_cases) > 20:
        raise ValueError("test_cases must be a non-empty list with at most 20 cases")
    cases = []
    allowed = {"name", "function", "args", "kwargs", "expected", "expected_exception", "rubric_index"}
    for raw in raw_cases:
        if not isinstance(raw, Mapping) or set(raw) - allowed:
            raise ValueError("Each test case must contain only supported fields")
        if not isinstance(raw.get("name"), str) or not raw["name"] or len(raw["name"]) > 160:
            raise ValueError("Each test case needs a short name")
        if not isinstance(raw.get("function"), str) or not raw["function"].isidentifier():
            raise ValueError("function must be a Python identifier")
        if not isinstance(raw.get("args", []), list) or not isinstance(raw.get("kwargs", {}), dict):
            raise ValueError("args must be a list and kwargs must be an object")
        if ("expected" in raw) == ("expected_exception" in raw):
            raise ValueError("Specify exactly one of expected or expected_exception")
        if "expected_exception" in raw and not isinstance(raw["expected_exception"], str):
            raise ValueError("expected_exception must be an exception class name")
        try:
            json.dumps(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Test case values must be JSON serializable") from exc
        values = {"args": raw.get("args", []), "kwargs": raw.get("kwargs", {})}
        values.update({field: raw[field] for field in raw if field in TestCase.__dataclass_fields__})
        cases.append(TestCase(**values))
    return cases


_RUNNER = r'''import importlib.util
import json
import sys
import traceback
MARKER = "__CODEMENTOR_RESULT__="
case = json.loads(sys.argv[1])
try:
    spec = importlib.util.spec_from_file_location("student_submission", "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observed = {"kind": "return", "value": getattr(module, case["function"])(*case["args"], **case["kwargs"])}
except BaseException as exc:
    observed = {"kind": "exception", "exception_type": type(exc).__name__, "message": str(exc)}
    traceback.print_exc(file=sys.stderr)
print(MARKER + json.dumps(observed, default=repr))
'''


def run_python_tests(source_code: str, test_cases: List[TestCase], timeout_seconds: float = 3.0) -> ToolResult:
    """Run approved function-call cases via a fixed subprocess runner, never a shell."""
    if not 0 < timeout_seconds <= 10:
        raise ValueError("timeout_seconds must be greater than 0 and at most 10")
    results = []
    with tempfile.TemporaryDirectory(prefix="codementor_") as directory:
        workdir = Path(directory)
        (workdir / "submission.py").write_text(source_code, encoding="utf-8")
        (workdir / "runner.py").write_text(_RUNNER, encoding="utf-8")
        for case in test_cases:
            payload = {"function": case.function, "args": case.args, "kwargs": case.kwargs}
            try:
                completed = subprocess.run([sys.executable, "-I", "runner.py", json.dumps(payload)], cwd=workdir, capture_output=True, text=True, timeout=timeout_seconds, shell=False)
                markers = [line for line in completed.stdout.splitlines() if line.startswith("__CODEMENTOR_RESULT__=")]
                observed = json.loads(markers[-1].split("=", 1)[1]) if markers else None
                passed = bool(observed and ((observed["kind"] == "return" and case.expected_exception is None and observed.get("value") == case.expected) or (observed["kind"] == "exception" and observed.get("exception_type") == case.expected_exception)))
                results.append({"case": asdict(case), "passed": passed, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "observed": observed, "timed_out": False})
            except subprocess.TimeoutExpired as exc:
                results.append({"case": asdict(case), "passed": False, "exit_code": None, "stdout": exc.stdout or "", "stderr": exc.stderr or "", "observed": None, "timed_out": True})
    return ToolResult("run_python_tests", {"results": results, "timeout_seconds": timeout_seconds})
