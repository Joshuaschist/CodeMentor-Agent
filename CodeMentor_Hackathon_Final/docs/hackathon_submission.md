# CodeMentor — Hackathon Submission

## One-line pitch
CodeMentor is an evidence-first AI coding-assessment agent that combines OpenAI-generated mentoring with deterministic, auditable runtime verification.

## Problem
LLM-only code review can produce confident but unsupported claims about whether a student program works. Instructors need assessment that is consistent, explainable, and backed by observable evidence.

## Solution
CodeMentor:
1. Reads the assignment and rubric.
2. Statically inspects the student's Python source without executing it.
3. Uses a small, validated tool interface for bounded verification tests.
4. Records static and runtime evidence separately in a sanitized trajectory.
5. Computes the rubric score from observed evidence.
6. Uses OpenAI to turn that evidence into concise mentor feedback without allowing the model to invent test results or change the score.
7. Compares the system against independently authored benchmark ground truth.

## Benchmark
The fixture benchmark contains 12 cases: the original eight calculator cases plus four independently specified cases.

Headline fixture results:
- Average score error: 0.00
- Requirement accuracy: 100%
- Average requirement score error: 0.00
- Defect detection: 100%
- Unsupported runtime claims: 0%

The benchmark is explicitly labeled FIXTURE and is not presented as live model performance.

## Why it is different
CodeMentor is designed around evidence provenance. A runtime claim is not accepted merely because an LLM says it happened. Runtime evidence is recorded only after the host executes an approved test tool successfully. This creates a stronger boundary between model reasoning and facts observed by the application.

## AI use
OpenAI powers the mentor explanation layer. The model receives the assignment and the already-generated evidence-backed assessment and returns structured strengths, issues, and next steps. The deterministic assessment remains authoritative.

## Safety and reliability
The model cannot request arbitrary shell commands. Test cases use a restricted JSON format, are bounded by a timeout, and execute through a fixed subprocess runner with `shell=False`. Trajectory logs redact secret-like fields and omit student source bodies.

## Limitations
The current prototype targets Python function-call assignments and uses bounded subprocess verification. It is not a complete security sandbox for hostile code. Production deployment should add stronger OS/container isolation and broader language support.

## Repository
Key directories:
- `agents/` — CodeMentor orchestration and OpenAI mentor layer
- `baseline/` — LLM-only comparison baseline
- `evaluation/` — independent benchmark ground truth and metrics
- `trajectories/` — auditable evidence logs
- `app/` — CLI
- `outputs/` — benchmark and demo artifacts
