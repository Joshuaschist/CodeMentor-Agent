# Assessment JSON format

The baseline returns one JSON object with this shape:

```json
{
  "score": 0,
  "score_rationale": "Why this score follows the rubric.",
  "requirements": [
    {
      "requirement": "Rubric requirement text",
      "status": "met | partially_met | not_met | unclear",
      "evidence": "Observed source-code evidence only",
      "points_awarded": 0
    }
  ],
  "identified_problems": ["Potential or directly observable issue"],
  "student_feedback": "Clear, constructive guidance for the student.",
  "evidence_limitations": "Explains that no code was run and no test evidence exists."
}
```

`score` is on a 0--100 scale. The structured response is constrained by the
schema defined in `baseline/schema.py`.
