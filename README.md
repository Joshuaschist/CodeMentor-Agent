# CodeMentor Agent

CodeMentor Agent helps instructors assess programming assignments consistently.
It keeps an LLM-only **baseline** separate from a tool-using **agent**, then
compares both with explicit, human-authored benchmark ground truth.

## Architecture

- `baseline/` is the control: an LLM reviews assignment, rubric, and source text.
  It never executes student code or invents test results.
- `agents/` is the single CodeMentor agent. It statically inspects code and uses
  validated, application-approved test calls when runtime verification is needed.
- `evaluation/` compares assessments with independent ground truth using fixtures
  or separately labeled live runs.
- `trajectories/` records sanitized, auditable events. Static and runtime
  evidence are distinct; runtime evidence exists only after tool execution.
- `app/` exposes the end-to-end CLI.

## Setup

Python 3.9+ is required:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Only the LLM baseline and `benchmark --mode live` need `OPENAI_API_KEY`. Do not
place credentials in project files.

## OpenAI-powered mentor explanation

The core assessment is evidence-first: static inspection and bounded subprocess
tests determine the score. When `OPENAI_API_KEY` is configured, CodeMentor can
add an OpenAI-generated mentor explanation grounded only in that evidence. The
model cannot change the score or invent runtime results.

Configure the key in your shell rather than committing it:

```powershell
$env:OPENAI_API_KEY="your-key-here"
$env:CODEMENTOR_MODEL="gpt-5.6-luna"
```

Then run:

```powershell
python -m app.cli assess `
  --assignment data/calculator_assignment.json `
  --student-code data/submissions/calculator_divide_by_zero.py `
  --ai
```

For live benchmarking, the OpenAI-backed baseline and the AI mentor explanation
use the configured key. Fixture mode remains credential-free.

## Assess one submission

The agent assessment and trajectory log require no API key:

```powershell
python -m app.cli assess `
  --assignment data/calculator_assignment.json `
  --student-code data/submissions/calculator_divide_by_zero.py `
  --output outputs/assessments/assessment.json
```

By default, the assessment is saved under `outputs/assessments/` and its matching
run-id trajectory is saved under `outputs/trajectories/`.

## Evidence and runtime testing

The agent parses source without executing it, then runs a fixed Python subprocess
only for approved function-call test cases. The runner uses `shell=False`, a
temporary directory, captured output, and a timeout. This is process isolation,
not a complete sandbox for hostile code; production use should add OS/container
isolation.

## Trajectories

Trajectory logs record decisions, tool requests, validation, execution, and
evidence summaries. They redact secret-like fields and omit full student source.
See [the trajectory format](docs/trajectory_format.md).

## Fixture evaluation

Run the credential-free, predetermined fixture benchmark:

```powershell
python -m app.cli benchmark --mode fixture
```

This writes explicitly labeled `FIXTURE` JSON and Markdown reports under
`outputs/benchmarks/`. The current benchmark contains 12 cases: the original
eight calculator cases plus four independently specified cases. Fixture results
exercise the benchmark pipeline; they are not claims about live model performance.

## Live evaluation

After securely configuring `OPENAI_API_KEY`, run:

```powershell
python -m app.cli benchmark --mode live
```

Live mode runs the actual baseline separately from the actual CodeMentor agent
for every benchmark case. It fails instead of substituting fixtures when
credentials are unavailable. Reports are labeled `LIVE`.

## Interpreting benchmark results

Lower score errors are better. Higher requirement accuracy and defect-detection
rates are better. The unsupported-runtime-claim rate should be low: it measures
claims about execution without observed execution evidence. Ground truth is
defined in `evaluation/cases/calculator_cases.json`, independently of model
responses.

## Limitations

The agent currently targets Python function-call submissions and calculator
examples. Tests are bounded but not a complete security sandbox. LLM output can
still be imperfect, which is why the benchmark and evidence trail are separate
from assessment generation.
