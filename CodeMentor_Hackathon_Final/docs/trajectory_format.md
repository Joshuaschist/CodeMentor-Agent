# Trajectory format

Each trajectory is a JSON object containing a `run_id`, optional `case_id`, and
ordered events. Every event has an ISO-8601 timestamp, event type, success flag,
and event id. Optional fields include tool name, sanitized arguments, result
summary, and evidence type.

Evidence types are deliberately distinct:

- `STATIC_EVIDENCE` comes from non-executing inspection.
- `RUNTIME_EVIDENCE` can only be emitted after a successful `tool_executed`
  event. A model statement or a planner request cannot create it.

The logger redacts values associated with secret-like keys (`api_key`, `token`,
`password`, and similar) and replaces source-code values with a character-count
placeholder. It should receive source summaries, not raw source, in normal use.

`TrajectoryLogger` is optional. Pass it to `CodeMentorAgent.run()` with a case id
to collect events; omit it to keep normal agent behavior unchanged. Logs remain
in memory until `to_json()` is called, allowing another sink to replace it later.
