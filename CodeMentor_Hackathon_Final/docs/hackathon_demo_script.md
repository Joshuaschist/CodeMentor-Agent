# CodeMentor — 5-Minute Hackathon Demo

## Recording setup
- Open the project in VS Code.
- Open one PowerShell terminal.
- Do not show the real `OPENAI_API_KEY`; only show that the variable is configured or show `.env.example`.
- Use 125–150% terminal font zoom.
- Record at 1080p if possible.

## Screen-by-screen plan

### 0:00–0:30 — Problem
Screen: `README.md` with the CodeMentor architecture section.

Say:
> “CodeMentor is an evidence-first AI coding-assessment agent for instructors. The problem is simple: an LLM can read code and sound confident, but a reviewer needs evidence that the code actually works. CodeMentor separates static inspection from runtime verification and keeps an auditable trajectory of what the agent actually observed.”

### 0:30–1:20 — Show the benchmark
Screen: PowerShell. Run:
```powershell
python -m app.cli benchmark --mode fixture
```
Show the 12-case table.

Say:
> “We evaluate CodeMentor against twelve explicitly specified benchmark cases. The benchmark includes the original eight calculator cases plus four independently specified cases. The ground truth is human-authored and independent of the model.”

Then point to:
- Agent: 0.00 average score error
- Requirement accuracy: 100%
- Defect detection: 100%
- Unsupported runtime claims: 0%

Say:
> “The important result is not just accuracy. CodeMentor detects every seeded defect while making zero unsupported runtime claims in this fixture benchmark. The baseline has 28.33 average score error, 68.75 percent requirement accuracy, and 25 percent defect detection.”

### 1:20–2:10 — Demonstrate a real defect
Screen: `data/submissions/calculator_divide_by_zero.py` beside the terminal.

Say:
> “Here is a deliberately defective student submission. It implements the calculator operations, but division by zero is not converted into the required ValueError.”

Run:
```powershell
python -m app.cli assess `
  --assignment data/calculator_assignment.json `
  --student-code data/submissions/calculator_divide_by_zero.py `
  --case-id division_by_zero
```

Show the resulting assessment JSON.

Say:
> “Notice the distinction: static inspection confirms the required function exists, while the approved subprocess test supplies runtime evidence. CodeMentor therefore awards the supported points and flags the division-by-zero requirement as not met.”

### 2:10–3:00 — Show the evidence trail
Screen: the generated trajectory JSON.

Point to:
- `tool_requested`
- `tool_validated`
- `tool_executed`
- `STATIC_EVIDENCE`
- `RUNTIME_EVIDENCE`
- `assessment_generated`

Say:
> “Every important decision is traceable. The trajectory records what tool was requested, whether it was validated, what was executed, and whether the evidence was static or runtime. Runtime evidence can only be recorded after a successful tool execution event. Student source and secret-like values are sanitized from the trajectory.”

### 3:00–3:45 — Show the AI layer
Screen: `agents/ai_mentor.py` and `.env.example`. Never reveal the real key.

Say:
> “The OpenAI model is used as a mentor explanation layer over trusted evidence. This is intentional: the model does not decide whether a test passed, does not invent execution results, and cannot change the deterministic score. It turns the verified evidence into concise strengths, issues, and next steps for the instructor and student.”

If the API key is configured, run:
```powershell
$env:OPENAI_API_KEY="YOUR_KEY"
$env:CODEMENTOR_MODEL="gpt-5.6-luna"

python -m app.cli assess `
  --assignment data/calculator_assignment.json `
  --student-code data/submissions/calculator_divide_by_zero.py `
  --case-id division_by_zero `
  --ai
```

Open the assessment JSON and show `ai_mentor_feedback`.

### 3:45–4:30 — Explain why the design matters
Screen: `agents/mentor_agent.py`, `agents/tools.py`.

Say:
> “The key design choice is that the model is not given arbitrary shell access. CodeMentor exposes a small set of validated tools: read the assignment, inspect the source, and run bounded JSON-defined Python test cases. The host application validates every request before execution. That gives us an agent that is useful without allowing the model to turn assessment into arbitrary command execution.”

### 4:30–5:00 — Close on the results
Screen: benchmark summary, then README.

Say:
> “So CodeMentor is not just an LLM that reviews code. It combines AI assistance with reproducible verification, independent benchmark ground truth, and an auditable evidence trail. In our twelve-case fixture benchmark it achieves 100 percent requirement accuracy and defect detection with zero unsupported runtime claims. That combination of accuracy, evidence, and auditability is why CodeMentor deserves the points.”

## Final recording rule
Do not spend time typing code live. The judges should see the finished system working. Keep the benchmark result on screen long enough to read the four headline metrics.
