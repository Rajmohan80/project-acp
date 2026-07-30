"""
AbhavTech Agentic Control Plane — search_wxcc_corpus tool.
LAB PROTOTYPE — not production ready.

The first REAL governed tool (Track C). Same governance path as echo:
runs _check_governance() -> on refusal returns the refusal dict (audit line
already written by _check_governance); on allow, retrieves from the WxCC
corpus and returns the chunks.

Requires scope: knowledge:read
Blocked for group: viewers   (proves refusal type A — TOOL_BLOCKED)
"""

from __future__ import annotations

from src.core.common.logging import get_logger
from src.domains.contact_center import corpus_client

log = get_logger(__name__)

TOOL_NAME = "search_wxcc_corpus"


def run_search(query: str, token: str, k: int = 5, *, check_governance) -> dict:
    """
    Governed corpus search. `check_governance` is injected from app.py
    (the server's _check_governance) so this module does not import the
    server and create a cycle.

    Returns:
        Refused: {"allowed": False, "refusal_reason": ..., "detail": ...}
        Allowed: {"allowed": True, "query": ..., "count": N, "chunks": [...]}
    """
    allowed, reason, detail, presented, required = check_governance(
        token=token,
        tool_name=TOOL_NAME,
    )

    if not allowed:
        return {
            "allowed": False,
            "refusal_reason": reason.value,
            "detail": detail,
        }

    try:
        chunks = corpus_client.search(query=query, k=k)
    except RuntimeError as exc:
        # Missing-credential / config failure — surface cleanly, do not crash
        # the server. (Audit already recorded ALLOWED; this is an exec error.)
        log.error("wxcc_search_error", error=str(exc))
        return {
            "allowed": True,
            "error": str(exc),
            "query": query,
            "count": 0,
            "chunks": [],
        }

    return {
        "allowed": True,
        "query": query,
        "count": len(chunks),
        "chunks": chunks,
        "detail": "Tool call allowed — governance passed",
    }
