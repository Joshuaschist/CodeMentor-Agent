"""Structured trajectory events with evidence provenance and secret redaction."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional


STATIC_EVIDENCE = "STATIC_EVIDENCE"
RUNTIME_EVIDENCE = "RUNTIME_EVIDENCE"
EVENT_TYPES = {"agent_started", "assignment_loaded", "code_inspected", "verification_needed", "tool_requested", "tool_validated", "tool_executed", "evidence_observed", "assessment_generated", "ai_feedback_generated", "agent_finished"}
SENSITIVE_KEY = re.compile(r"(api.?key|secret|token|password|credential|environment|env)", re.IGNORECASE)
SOURCE_KEY = re.compile(r"(source|student.code|submission)", re.IGNORECASE)


def sanitize(value: Any, key: str = "") -> Any:
    """Redact secret-like values and replace source bodies with size-only summaries."""
    if SENSITIVE_KEY.search(key):
        return "[redacted]"
    if SOURCE_KEY.search(key) and isinstance(value, str):
        return f"[omitted source content: {len(value)} chars]"
    if isinstance(value, Mapping):
        return {str(item_key): sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…[truncated]"
    return value


class TrajectoryLogger:
    """In-memory logger that can be disabled by simply not supplying an instance."""

    def __init__(self, run_id: Optional[str] = None, case_id: Optional[str] = None) -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.case_id = case_id
        self.events: List[Dict[str, Any]] = []

    def record(self, event_type: str, *, success: bool = True, tool_name: Optional[str] = None, tool_arguments: Optional[Mapping[str, Any]] = None, result_summary: Optional[Any] = None, evidence_type: Optional[str] = None, details: Optional[Mapping[str, Any]] = None) -> str:
        """Record one sanitized event and return its event id."""
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unsupported trajectory event: {event_type}")
        if evidence_type and evidence_type not in {STATIC_EVIDENCE, RUNTIME_EVIDENCE}:
            raise ValueError("Unknown evidence type")
        event = {"event_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type, "run_id": self.run_id, "success": bool(success)}
        if self.case_id:
            event["case_id"] = self.case_id
        if tool_name:
            event["tool_name"] = tool_name
        if tool_arguments is not None:
            event["tool_arguments"] = sanitize(tool_arguments)
        if result_summary is not None:
            event["result_summary"] = sanitize(result_summary)
        if evidence_type:
            event["evidence_type"] = evidence_type
        if details:
            event["details"] = sanitize(details)
        self.events.append(event)
        return event["event_id"]

    def record_tool_execution(self, tool_name: str, result_summary: Any, *, success: bool) -> str:
        return self.record("tool_executed", tool_name=tool_name, result_summary=result_summary, success=success)

    def record_static_evidence(self, summary: Any) -> str:
        return self.record("evidence_observed", evidence_type=STATIC_EVIDENCE, result_summary=summary, success=True)

    def record_runtime_evidence(self, tool_execution_event_id: str, summary: Any) -> str:
        """Runtime evidence is legal only after a successful real tool execution event."""
        execution = next((event for event in self.events if event["event_id"] == tool_execution_event_id), None)
        if not execution or execution["event_type"] != "tool_executed" or not execution["success"]:
            raise ValueError("Runtime evidence requires a successful tool execution result")
        return self.record("evidence_observed", evidence_type=RUNTIME_EVIDENCE, result_summary=summary, success=True, details={"tool_execution_event_id": tool_execution_event_id})

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps({"run_id": self.run_id, "case_id": self.case_id, "events": self.events}, indent=indent)


def emit_agent_event(logger: Optional[TrajectoryLogger], event_type: str, **kwargs: Any) -> Optional[str]:
    """Optional adapter used by the agent; a missing logger is a no-op."""
    return logger.record(event_type, **kwargs) if logger else None
