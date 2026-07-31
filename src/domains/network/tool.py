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


# ------------------------------------------------------------------ #
# Block 3 — find_path
# ------------------------------------------------------------------ #

TOOL_FIND_PATH = "find_path"


def run_find_path(
    source: str,
    destination: str,
    token: str,
    topology_name: str = "sample_sdwan_branch",
    *,
    check_governance,
) -> dict:
    """
    Governed path-finding tool.

    Finds the shortest L3 hop path between source and destination nodes
    using BFS over the topology graph. Returns the full hop list with
    link types crossed — useful for change impact analysis and design.

    Requires scope: diagnostics:run  (different from describe_topology)
    Blocked for group: viewers

    Args:
        source:          Source node ID (case-insensitive, e.g. "branch-sw-01")
        destination:     Destination node ID (e.g. "hq-core-sw-01")
        token:           JWT bearer token
        topology_name:   Topology to search (default: sample_sdwan_branch)
        check_governance: Injected from app.py

    Returns:
        Refused: {"allowed": False, "refusal_reason": ..., "detail": ...}
        Allowed: {"allowed": True, "path_result": <bfs result dict>}
    """
    allowed, reason, detail, presented, required = check_governance(
        token=token,
        tool_name=TOOL_FIND_PATH,
    )

    if not allowed:
        return {
            "allowed":        False,
            "refusal_reason": reason.value,
            "detail":         detail,
        }

    try:
        topo       = topology_store.get_topology(topology_name)
        graph_data = topology_store.build_graph(topo)
        result     = topology_store.bfs_path(graph_data, source, destination)
    except RuntimeError as exc:
        log.error("find_path_error", error=str(exc))
        return {
            "allowed": True,
            "error":   str(exc),
            "path_result": None,
        }

    log.info(
        "find_path_done",
        source=source,
        destination=destination,
        found=result.get("found"),
        hops=result.get("hop_count"),
    )

    return {
        "allowed":     True,
        "path_result": result,
        "detail":      "Tool call allowed — governance passed",
    }
