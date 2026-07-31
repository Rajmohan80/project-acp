"""
AbhavTech Agentic Control Plane — network topology store.
LAB PROTOTYPE — not production ready.

Loads topology descriptor JSON files from the topologies/ folder.
Returns plain dicts — JSON-serialisable, no dataclasses.

Topology files: src/domains/network/topologies/<name>.json
Each file describes nodes, links, and sites for one lab topology.

Fails loudly ([ACP] MISSING: ...) if a requested topology does not exist,
consistent with the config.py failure pattern.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.common.logging import get_logger

log = get_logger(__name__)

_TOPOLOGIES_DIR = Path(__file__).resolve().parent / "topologies"

# In-process cache — loaded once per topology name, per process lifetime.
_cache: dict[str, dict] = {}


def list_topologies() -> list[str]:
    """Return names of all available topology files (without .json extension)."""
    return [f.stem for f in _TOPOLOGIES_DIR.glob("*.json")]


def get_topology(name: str) -> dict:
    """
    Load and return a topology by name.
    Raises RuntimeError([ACP] MISSING) if not found.
    Result is cached after first load.
    """
    if name in _cache:
        return _cache[name]

    path = _TOPOLOGIES_DIR / f"{name}.json"
    if not path.exists():
        available = list_topologies()
        raise RuntimeError(
            f"\n\n  [ACP] MISSING: topology '{name}'\n"
            f"  Available topologies: {available}\n"
            f"  Add '{name}.json' to {_TOPOLOGIES_DIR}\n"
        )

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    _cache[name] = data
    log.info("topology_loaded", name=name, nodes=len(data.get("nodes", [])))
    return data


def summarise(topology: dict) -> dict:
    """
    Return a summary dict for describe_topology output.
    Extracts counts, site list, node roles, and link types.
    Plain dict — safe to return from any MCP tool.
    """
    nodes = topology.get("nodes", [])
    links = topology.get("links", [])
    sites = topology.get("sites", {})

    # Role breakdown
    role_counts: dict[str, int] = {}
    for n in nodes:
        role = n.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    # Link type breakdown
    link_types: dict[str, int] = {}
    for lk in links:
        lt = lk.get("type", "unknown")
        link_types[lt] = link_types.get(lt, 0) + 1

    # SD-WAN edges — hub vs spoke
    sd_wan_edges = [
        {
            "id":          n["id"],
            "label":       n.get("label", n["id"]),
            "sd_wan_role": n.get("sd_wan_role", ""),
            "transports":  n.get("wan_transports", []),
            "site":        n.get("site", ""),
        }
        for n in nodes
        if n.get("role") == "sd-wan-edge"
    ]

    # Node list for display
    node_list = [
        {
            "id":          n["id"],
            "label":       n.get("label", n["id"]),
            "site":        n.get("site", ""),
            "role":        n.get("role", ""),
            "device_type": n.get("device_type", ""),
            "platform":    n.get("platform", ""),
            "description": n.get("description", ""),
        }
        for n in nodes
    ]

    return {
        "name":        topology.get("name", ""),
        "description": topology.get("description", ""),
        "platform":    topology.get("platform", ""),
        "version":     topology.get("version", ""),
        "site_count":  len(sites),
        "sites":       list(sites.keys()),
        "node_count":  len(nodes),
        "link_count":  len(links),
        "role_counts": role_counts,
        "link_types":  link_types,
        "sd_wan_edges": sd_wan_edges,
        "nodes":       node_list,
    }
