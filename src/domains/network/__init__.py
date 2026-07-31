"""
AbhavTech Agentic Control Plane — Track N: Network domain.
LAB PROTOTYPE — not production ready.

Track N provides governed MCP tools for network topology awareness.
Tools query static topology descriptors (JSON files in topologies/)
so they work without a live CML instance — right for a lab prototype.

Tools in this track:
  describe_topology  — Block 2 — returns nodes, links, sites for a topology
  find_path          — Block 3 — returns L3 hop path between two nodes
  check_device_role  — Block 4 — returns role and peers for a named node

Topology files live in:
  src/domains/network/topologies/<name>.json

Governance: every tool call goes through _check_governance() injected
from app.py — same pattern as Track C. No circular imports.

LD-12: Track N must be published publicly before Track C goes further.
LD-13: A2A boundary implemented at Stage 5 cross-domain delegation
       between Track N and Track C agents — not before.
"""
