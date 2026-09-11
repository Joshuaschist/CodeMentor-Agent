# CodeMentor Agent: Stage 2 architecture

## Inputs

`CodeMentorAgent.run()` accepts an assignment JSON object, student Python source,
an optional separate rubric (which overrides the assignment rubric), and optional
application-approved verification cases.

## Agent loop

The first version is a single deterministic loop: it calls `read_assignment`,
then `inspect_code`, and requests `run_python_tests` only for explicit cases.
It uses application-owned calculator cases for the included sample assignment, or
caller-supplied validated cases otherwise. Future LLM planners return a
`ToolRequest` with a tool name and arguments; the host validates it before use.

## Available tools

- `read_assignment` returns the provided description and rubric.
- `inspect_code` parses the source with `ast` and reports syntax, functions, and
  imports without executing it.
- `run_python_tests` invokes a fixed runner in a temporary directory for each
  approved function-call case and returns actual return/exception, stdout,
  stderr, exit code, timeout state, and pass/fail comparison.

## Evidence and safety

The assessment labels static observations separately from observed subprocess
results. A test passes only when its subprocess result matches the declared
expected value or exception. The runner uses an argument vector with
`shell=False`, a temporary working directory, isolated Python mode, captured
output, and a timeout. Unknown tools and arguments are rejected. This process
isolation is not a complete sandbox for hostile Python; future deployment should
use a stronger OS/container sandbox.

## Difference from the baseline

The baseline only asks an LLM to review source text and cannot execute code. This
single agent adds controlled evidence collection and execution while producing
the same assessment fields. It does not add benchmarking, an evaluation system,
or multi-agent orchestration.
