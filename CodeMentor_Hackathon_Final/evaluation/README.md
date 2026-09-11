# Evaluation benchmark

This benchmark compares **Baseline** and **CodeMentor Agent** against explicit,
human-authored ground truth in `cases/calculator_cases.json`. It never treats an
LLM response as truth.

Each case contains source code, expected rubric outcomes and score, known defects,
and applicable verification cases. `fixtures` holds predetermined offline outputs
for each system. Fixture mode does not import OpenAI or read `OPENAI_API_KEY`.

Run the fixture comparison:

```powershell
python -m evaluation.benchmark
```

The report includes average score error, requirement accuracy, average requirement
score error, defect detection rate, and unsupported runtime-claim rate. For real
systems, pass functions that accept a case and return the normal structured
assessment to `BenchmarkRunner.compare()`. Metric and validation paths are the
same in fixture mode.
