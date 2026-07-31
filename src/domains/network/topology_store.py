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


# ------------------------------------------------------------------ #
# Block 3 — graph builder + BFS path finder
# ------------------------------------------------------------------ #

def build_graph(topology: dict) -> dict:
    """
    Build a bidirectional adjacency map from topology links.

    Returns:
        {
          "node_id": [
            {"neighbour": "other_id", "link_type": "lan", "link_id": "link-08"},
            ...
          ],
          ...
        }

    Links are bidirectional — if A→B exists, B→A is also added.
    Node IDs are normalised to lowercase for case-insensitive lookup.
    """
    # Build id→label map for readable output
    id_to_label: dict[str, str] = {}
    for n in topology.get("nodes", []):
        id_to_label[n["id"].lower()] = n.get("label", n["id"])

    graph: dict[str, list[dict]] = {nid: [] for nid in id_to_label}

    for lk in topology.get("links", []):
        a = lk["from"].lower()
        b = lk["to"].lower()
        lt = lk.get("type", "unknown")
        lid = lk.get("id", "")

        if a in graph:
            graph[a].append({"neighbour": b, "link_type": lt, "link_id": lid})
        if b in graph:
            graph[b].append({"neighbour": a, "link_type": lt, "link_id": lid})

    return {"adjacency": graph, "id_to_label": id_to_label}


def bfs_path(
    graph_data: dict,
    source: str,
    destination: str,
) -> dict:
    """
    BFS shortest-hop path between source and destination node IDs.
    Node IDs are matched case-insensitively.

    Returns a plain dict:
        Found:
          {
            "found": True,
            "source": "branch-sw-01",
            "destination": "hq-core-sw-01",
            "hop_count": 4,
            "path": [
              {"node_id": ..., "label": ..., "via_link_type": ..., "via_link_id": ...},
              ...
            ]
          }
        Not found:
          {"found": False, "source": ..., "destination": ..., "reason": ...}
    """
    adjacency   = graph_data["adjacency"]
    id_to_label = graph_data["id_to_label"]

    src  = source.lower()
    dest = destination.lower()

    if src not in adjacency:
        return {
            "found":       False,
            "source":      source,
            "destination": destination,
            "reason":      f"Source node '{source}' not found in topology.",
        }
    if dest not in adjacency:
        return {
            "found":       False,
            "source":      source,
            "destination": destination,
            "reason":      f"Destination node '{destination}' not found in topology.",
        }
    if src == dest:
        return {
            "found":       True,
            "source":      source,
            "destination": destination,
            "hop_count":   0,
            "path": [{"node_id": src, "label": id_to_label[src],
                      "via_link_type": None, "via_link_id": None}],
        }

    # BFS — track (node, link_type, link_id) so we can report link types crossed
    from collections import deque
    visited: set[str] = {src}
    # queue items: (current_node, path_so_far)
    # path entry: (node_id, arrived_via_link_type, arrived_via_link_id)
    queue: deque = deque()
    queue.append((src, [(src, None, None)]))

    while queue:
        current, path = queue.popleft()
        for edge in adjacency.get(current, []):
            nb  = edge["neighbour"]
            lt  = edge["link_type"]
            lid = edge["link_id"]
            if nb in visited:
                continue
            new_path = path + [(nb, lt, lid)]
            if nb == dest:
                # Build readable path list
                path_list = []
                for node_id, via_lt, via_lid in new_path:
                    path_list.append({
                        "node_id":       node_id,
                        "label":         id_to_label.get(node_id, node_id),
                        "via_link_type": via_lt,
                        "via_link_id":   via_lid,
                    })
                link_types_crossed = list(dict.fromkeys(
                    e["via_link_type"] for e in path_list
                    if e["via_link_type"] is not None
                ))
                return {
                    "found":               True,
                    "source":              source,
                    "destination":         destination,
                    "hop_count":           len(path_list) - 1,
                    "path":                path_list,
                    "link_types_crossed":  link_types_crossed,
                }
            visited.add(nb)
            queue.append((nb, new_path))

    return {
        "found":       False,
        "source":      source,
        "destination": destination,
        "reason":      f"No path found between '{source}' and '{destination}'.",
    }


# ------------------------------------------------------------------ #
# Block 4 — node role lookup
# ------------------------------------------------------------------ #

def get_node(topology: dict, node_id: str) -> dict:
    """
    Look up a node by ID (case-insensitive) and return its full
    profile plus all directly connected peers.

    Returns a plain dict:
        Found:
          {
            "found": True,
            "node_id": "hq-cedge-01",
            "label": "HQ-cEdge-01",
            "role": "sd-wan-edge",
            "sd_wan_role": "hub",          # only for sd-wan-edge nodes
            "site": "hq",
            "device_type": "cEdge",
            "platform": "Cisco ISR4451...",
            "wan_transports": ["mpls","internet"],  # only for sd-wan-edge
            "description": "...",
            "peer_count": 5,
            "peers": [
              {"node_id": ..., "label": ..., "link_type": ..., "link_id": ...},
              ...
            ]
          }
        Not found:
          {"found": False, "node_id": ..., "reason": ...,
           "available_nodes": [...]}
    """
    nid = node_id.lower()

    # Build id→node map
    id_to_node: dict[str, dict] = {
        n["id"].lower(): n for n in topology.get("nodes", [])
    }
    id_to_label: dict[str, str] = {
        k: v.get("label", v["id"]) for k, v in id_to_node.items()
    }

    if nid not in id_to_node:
        return {
            "found":           False,
            "node_id":         node_id,
            "reason":          f"Node '{node_id}' not found in topology.",
            "available_nodes": sorted(id_to_label.values()),
        }

    node = id_to_node[nid]

    # Collect peers from links
    peers: list[dict] = []
    for lk in topology.get("links", []):
        a = lk["from"].lower()
        b = lk["to"].lower()
        lt  = lk.get("type", "unknown")
        lid = lk.get("id", "")

        if a == nid and b in id_to_label:
            peers.append({
                "node_id":   b,
                "label":     id_to_label[b],
                "link_type": lt,
                "link_id":   lid,
            })
        elif b == nid and a in id_to_label:
            peers.append({
                "node_id":   a,
                "label":     id_to_label[a],
                "link_type": lt,
                "link_id":   lid,
            })

    result: dict = {
        "found":       True,
        "node_id":     nid,
        "label":       node.get("label", node["id"]),
        "role":        node.get("role", "unknown"),
        "site":        node.get("site", ""),
        "device_type": node.get("device_type", ""),
        "platform":    node.get("platform", ""),
        "description": node.get("description", ""),
        "peer_count":  len(peers),
        "peers":       peers,
    }

    # SD-WAN-specific fields — only present for edge nodes
    if node.get("sd_wan_role"):
        result["sd_wan_role"]    = node["sd_wan_role"]
    if node.get("wan_transports"):
        result["wan_transports"] = node["wan_transports"]

    return result
