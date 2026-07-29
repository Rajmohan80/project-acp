"""
AbhavTech Agentic Control Plane — audit trail writer.
LAB PROTOTYPE — not production ready.

Writes every tool call, refusal, and governance decision to audit.log.
Separate from stdout logging — this is the governance record.
Queryable via TinyDB.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from tinydb import TinyDB, Query

from src.core.common.config import get_settings


class AuditOutcome(str, Enum):
    ALLOWED  = "ALLOWED"
    REFUSED  = "REFUSED"
    ERROR    = "ERROR"


class RefusalReason(str, Enum):
    TOOL_BLOCKED      = "TOOL_BLOCKED_IN_CONTROL_HUB"
    SCOPE_MISSING     = "TOKEN_MISSING_REQUIRED_SCOPE"
    REAUTH_REQUIRED   = "REAUTH_REQUIRED_SERVER_DATA_CHANGED"
    NONE              = "NONE"


def _get_db() -> TinyDB:
    """Return the TinyDB instance backed by audit.log."""
    settings = get_settings()
    return TinyDB(settings.audit_log_path)


def write_audit(
    *,
    actor: str,
    tool: str,
    scopes_presented: list[str],
    scopes_required: list[str],
    autonomy_level: str,
    outcome: AuditOutcome,
    refusal_reason: RefusalReason = RefusalReason.NONE,
    detail: str = "",
) -> dict:
    """
    Write one audit record and return it.

    Every MCP tool call — allowed or refused — must call this.
    Refusals must supply a refusal_reason so audit lines are distinct.
    """
    record = {
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "actor":            actor,
        "tool":             tool,
        "scopes_presented": scopes_presented,
        "scopes_required":  scopes_required,
        "autonomy_level":   autonomy_level,
        "outcome":          outcome.value,
        "refusal_reason":   refusal_reason.value,
        "detail":           detail,
    }

    # Write to TinyDB (JSON file)
    db = _get_db()
    db.insert(record)
    db.close()

    # Also write a human-readable line to the same file path + .readable
    _append_readable(record)

    return record


def _append_readable(record: dict) -> None:
    """Append a single readable JSON line alongside the TinyDB store."""
    settings = get_settings()
    readable_path = Path(settings.audit_log_path).with_suffix(".readable.log")
    with readable_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def query_audit(
    *,
    actor: str | None = None,
    tool: str | None = None,
    outcome: AuditOutcome | None = None,
) -> list[dict]:
    """
    Query audit records by actor, tool, or outcome.
    Returns all records if no filters supplied.
    """
    db = _get_db()
    A = Query()

    if actor and tool and outcome:
        results = db.search(
            (A.actor == actor) &
            (A.tool == tool) &
            (A.outcome == outcome.value)
        )
    elif actor and tool:
        results = db.search((A.actor == actor) & (A.tool == tool))
    elif actor:
        results = db.search(A.actor == actor)
    elif tool:
        results = db.search(A.tool == tool)
    elif outcome:
        results = db.search(A.outcome == outcome.value)
    else:
        results = db.all()

    db.close()
    return results