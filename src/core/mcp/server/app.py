"""
AbhavTech Agentic Control Plane — governed MCP server.
LAB PROTOTYPE — not production ready.

FastMCP server hosting one demo tool (echo).
Enforces two distinct refusal types on every call:
  A — tool Blocked in control_hub.yaml for the caller's group
  B — token missing the required scope for the tool
Both refusals write a distinct audit line with the reason.
Runs on port 8100 (Option B — uvicorn direct, not docker-compose).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastmcp import FastMCP
from jose import JWTError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.core.audit.writer import AuditOutcome, RefusalReason, write_audit
from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger
from src.core.mcp.oauth.issuer import decode_token
from src.domains.contact_center.tool import run_search

configure_logging()
log = get_logger(__name__)

# ------------------------------------------------------------------ #
# Load control_hub.yaml once at startup
# ------------------------------------------------------------------ #
_HUB_PATH = Path(__file__).resolve().parents[1] / "control_hub.yaml"


def _load_hub() -> dict:
    with _HUB_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


_HUB = _load_hub()


# ------------------------------------------------------------------ #
# Governance helpers
# ------------------------------------------------------------------ #

def _check_governance(
    token: str,
    tool_name: str,
    actor: str = "unknown",
) -> tuple[bool, RefusalReason, str, list[str], list[str]]:
    """
    Run both governance checks for a tool call.

    Returns:
        (allowed, refusal_reason, detail, scopes_presented, scopes_required)
    """
    tool_cfg = _HUB.get("tools", {}).get(tool_name, {})
    required_scope: str = tool_cfg.get("required_scope", "knowledge:read")

    # Decode token
    try:
        payload = decode_token(token)
    except JWTError as exc:
        return (
            False,
            RefusalReason.SCOPE_MISSING,
            f"Invalid or expired token: {exc}",
            [],
            [required_scope],
        )

    group: str = payload.get("group", "unknown")
    scopes_presented: list[str] = payload.get("scopes", [])
    actor = payload.get("sub", actor)

    # Check A — is the tool Blocked for this group in control_hub.yaml?
    group_policy = tool_cfg.get("groups", {}).get(group, "Blocked")
    if group_policy == "Blocked":
        detail = (
            f"Tool '{tool_name}' is Blocked in control_hub.yaml "
            f"for group '{group}'"
        )
        write_audit(
            actor=actor,
            tool=tool_name,
            scopes_presented=scopes_presented,
            scopes_required=[required_scope],
            autonomy_level="supervised",
            outcome=AuditOutcome.REFUSED,
            refusal_reason=RefusalReason.TOOL_BLOCKED,
            detail=detail,
        )
        log.warning("tool_blocked", actor=actor, tool=tool_name, group=group)
        return (False, RefusalReason.TOOL_BLOCKED, detail,
                scopes_presented, [required_scope])

    # Check B — does the token carry the required scope?
    if required_scope not in scopes_presented:
        detail = (
            f"Token missing required scope '{required_scope}' "
            f"for tool '{tool_name}'"
        )
        write_audit(
            actor=actor,
            tool=tool_name,
            scopes_presented=scopes_presented,
            scopes_required=[required_scope],
            autonomy_level="supervised",
            outcome=AuditOutcome.REFUSED,
            refusal_reason=RefusalReason.SCOPE_MISSING,
            detail=detail,
        )
        log.warning(
            "scope_missing",
            actor=actor,
            tool=tool_name,
            required=required_scope,
            presented=scopes_presented,
        )
        return (False, RefusalReason.SCOPE_MISSING, detail,
                scopes_presented, [required_scope])

    # Both checks passed
    write_audit(
        actor=actor,
        tool=tool_name,
        scopes_presented=scopes_presented,
        scopes_required=[required_scope],
        autonomy_level="supervised",
        outcome=AuditOutcome.ALLOWED,
        detail=f"Tool '{tool_name}' allowed for group '{group}'",
    )
    log.info("tool_allowed", actor=actor, tool=tool_name, group=group)
    return (True, RefusalReason.NONE, "", scopes_presented, [required_scope])


# ------------------------------------------------------------------ #
# MCP server
# ------------------------------------------------------------------ #

mcp = FastMCP(
    name="acp-mcp-server",
    instructions=(
        "AbhavTech Agentic Control Plane — governed MCP server. "
        "LAB PROTOTYPE. Every tool call is checked against "
        "control_hub.yaml and the caller's token scopes."
    ),
)


@mcp.tool()
def echo(message: str, token: str) -> dict:
    """
    Demo echo tool — proves governance before any real tool exists.
    Requires scope: knowledge:read
    Blocked for group: viewers
    """
    allowed, reason, detail, presented, required = _check_governance(
        token=token,
        tool_name="echo",
    )

    if not allowed:
        return {
            "allowed": False,
            "refusal_reason": reason.value,
            "detail": detail,
        }

    return {
        "allowed": True,
        "echo": message,
        "detail": "Tool call allowed — governance passed",
    }


@mcp.tool()
def search_wxcc_corpus(query: str, token: str, k: int = 5) -> dict:
    """
    Search the WxCC SLM corpus for relevant chunks.
    Requires scope: knowledge:read
    Blocked for group: viewers
    """
    return run_search(
        query=query, token=token, k=k,
        check_governance=_check_governance,
    )


# ------------------------------------------------------------------ #
# ASGI app for uvicorn (Option B)
# ------------------------------------------------------------------ #

async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "acp-mcp-server"})


app = Starlette(
    routes=[Route("/health", health)],
)

mcp_app = mcp.http_app(path="/mcp")
