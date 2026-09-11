# Judges Cheat Sheet

## Four numbers to emphasize
**12 cases | 100% requirement accuracy | 100% defect detection | 0% unsupported runtime claims**

## Core message
CodeMentor does not trust an LLM's claim that code ran. It separates model assistance from host-observed evidence.

## Strongest demo case
`division_by_zero`: static inspection sees the calculator function; runtime verification observes that `/` with a zero divisor raises `ZeroDivisionError` instead of the required `ValueError`.

## What not to claim
- Do not call FIXTURE results live model performance.
- Do not claim the subprocess runner is a complete security sandbox.
- Do not reveal the OpenAI API key.
