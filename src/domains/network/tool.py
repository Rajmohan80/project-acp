"""
AbhavTech Agentic Control Plane — Track N governed network tools.
LAB PROTOTYPE — not production ready.

Block 2: describe_topology
  Returns nodes, links, sites, and SD-WAN edge summary for a named topology.
  Requires scope: knowledge:read
  Blocked for group: viewers

Block 3 (find_path) and Block 4 (check_device_role) added here later.

Governance is injected from app.py (_check_governance) to avoid
circular imports — identical pattern to Track C tool.py.
"""

from __future__ import annotations

from src.core.common.logging import get_logger
from src.domains.network import topology_store

log = get_logger(__name__)

# ------------------------------------------------------------------ #
# Block 2 — describe_topology
# ------------------------------------------------------------------ #

TOOL_DESCRIBE = "describe_topology"


def run_describe_topology(
    name: str,
    token: str,
    *,
    check_governance,
) -> dict:
    """
    Governed topology description tool.

    Args:
        name:             Topology name (matches a .json file in topologies/)
        token:            JWT bearer token from the OAuth issuer
        check_governance: Injected from app.py — _check_governance function

    Returns:
        Refused: {"allowed": False, "refusal_reason": ..., "detail": ...}
        Allowed: {"allowed": True, "topology": <summary dict>}
    """
    allowed, reason, detail, presented, required = check_governance(
        token=token,
        tool_name=TOOL_DESCRIBE,
    )

    if not allowed:
        return {
            "allowed":        False,
            "refusal_reason": reason.value,
            "detail":         detail,
        }

    try:
        topo = topology_store.get_topology(name)
        summary = topology_store.summarise(topo)
    except RuntimeError as exc:
        log.error("describe_topology_error", error=str(exc))
        return {
            "allowed": True,
            "error":   str(exc),
            "topology": None,
        }

    log.info(
        "describe_topology_done",
        name=name,
        nodes=summary["node_count"],
        links=summary["link_count"],
    )

    return {
        "allowed":  True,
        "topology": summary,
        "detail":   "Tool call allowed — governance passed",
    }
