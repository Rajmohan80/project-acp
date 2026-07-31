r"""
AbhavTech Agentic Control Plane — Track N demo / validation.
LAB PROTOTYPE — not production ready.

Block 2 validation: describe_topology tool.

Proves a governed network tool call reaches real topology data, two ways:
  1. ALLOWED  — engineers token -> topology summary returned
  2. BLOCKED  — viewers token  -> TOOL_BLOCKED_IN_CONTROL_HUB, no data

Run:
    (.venv) D:\project-acp> python scripts\demo_network.py

All structured logs go to demo_network.log — stdout shows results only.
"""

from __future__ import annotations

import logging
import sys

# ------------------------------------------------------------------ #
# Redirect ALL logging to demo_network.log before any module imports.
# Keeps stdout clean for results only.
# ------------------------------------------------------------------ #
_LOG_FILE = "demo_network.log"
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
logging.root.handlers = []
logging.root.addHandler(_file_handler)
logging.root.setLevel(logging.DEBUG)
sys.stderr = open(_LOG_FILE, "a", encoding="utf-8")  # noqa: WPS515

from datetime import datetime, timedelta, timezone  # noqa: E402

from jose import jwt  # noqa: E402

from src.core.common.config import get_settings  # noqa: E402
from src.core.mcp.oauth.issuer import GROUP_SCOPES  # noqa: E402
from src.core.mcp.server.app import _check_governance  # noqa: E402
from src.domains.network.tool import (  # noqa: E402
    run_describe_topology,
    run_find_path,
    run_check_device_role,
)


def _mint(username: str, group: str) -> str:
    """Mint a JWT in-process — no HTTP call to the issuer needed."""
    settings = get_settings()
    payload = {
        "sub":    username,
        "group":  group,
        "scopes": GROUP_SCOPES[group],
        "exp":    datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.oauth_secret_key, algorithm="HS256")


def _print_topology(result: dict) -> None:
    """Pretty-print a describe_topology result."""
    print(f"  allowed        : {result.get('allowed')}")

    if not result.get("allowed"):
        print(f"  refusal_reason : {result.get('refusal_reason')}")
        print(f"  detail         : {result.get('detail')}")
        return

    if result.get("error"):
        print(f"  ERROR          : {result['error']}")
        return

    t = result.get("topology", {})
    print(f"  topology       : {t.get('name')}")
    print(f"  description    : {t.get('description')}")
    print(f"  platform       : {t.get('platform')}")
    print(f"  sites ({t.get('site_count', 0)})     : {', '.join(t.get('sites', []))}")
    print(f"  nodes          : {t.get('node_count')}")
    print(f"  links          : {t.get('link_count')}")

    print("\n  Role breakdown:")
    for role, count in sorted(t.get("role_counts", {}).items()):
        print(f"    {role:<28} {count}")

    print("\n  Link types:")
    for lt, count in sorted(t.get("link_types", {}).items()):
        print(f"    {lt:<28} {count}")

    print("\n  SD-WAN edges:")
    for edge in t.get("sd_wan_edges", []):
        transports = ", ".join(edge.get("transports", []))
        print(
            f"    {edge['label']:<24} "
            f"sd_wan_role={edge.get('sd_wan_role', 'n/a'):<8} "
            f"transports=[{transports}]  "
            f"site={edge.get('site')}"
        )

    print("\n  Nodes:")
    for n in t.get("nodes", []):
        print(
            f"    {n['label']:<24} "
            f"role={n.get('role', ''):<22} "
            f"site={n.get('site', '')}"
        )


def _print_path(result: dict) -> None:
    """Pretty-print a find_path result."""
    print(f"  allowed        : {result.get('allowed')}")

    if not result.get("allowed"):
        print(f"  refusal_reason : {result.get('refusal_reason')}")
        print(f"  detail         : {result.get('detail')}")
        return

    if result.get("error"):
        print(f"  ERROR          : {result['error']}")
        return

    pr = result.get("path_result", {})
    if not pr.get("found"):
        print(f"  found          : False")
        print(f"  reason         : {pr.get('reason')}")
        return

    print(f"  found          : True")
    print(f"  source         : {pr.get('source')}")
    print(f"  destination    : {pr.get('destination')}")
    print(f"  hops           : {pr.get('hop_count')}")
    print(f"  link types     : {' → '.join(pr.get('link_types_crossed', []))}")
    print()
    print("  Path:")
    for i, hop in enumerate(pr.get("path", [])):
        prefix = "  START" if i == 0 else f"  HOP {i}  "
        lt = hop.get("via_link_type")
        link_info = f"  ← via {lt}" if lt else ""
        print(f"  {prefix}  {hop['label']}{link_info}")


def _print_device(result: dict) -> None:
    """Pretty-print a check_device_role result."""
    print(f"  allowed        : {result.get('allowed')}")

    if not result.get("allowed"):
        print(f"  refusal_reason : {result.get('refusal_reason')}")
        print(f"  detail         : {result.get('detail')}")
        return

    if result.get("error"):
        print(f"  ERROR          : {result['error']}")
        return

    d = result.get("device", {})
    if not d.get("found"):
        print(f"  found          : False")
        print(f"  reason         : {d.get('reason')}")
        print(f"  available      : {d.get('available_nodes')}")
        return

    print(f"  node           : {d.get('label')}")
    print(f"  role           : {d.get('role')}")
    if d.get("sd_wan_role"):
        print(f"  sd_wan_role    : {d.get('sd_wan_role')}")
    if d.get("wan_transports"):
        print(f"  wan_transports : {d.get('wan_transports')}")
    print(f"  site           : {d.get('site')}")
    print(f"  device_type    : {d.get('device_type')}")
    print(f"  platform       : {d.get('platform')}")
    print(f"  description    : {d.get('description')}")
    print(f"\n  Peers ({d.get('peer_count', 0)}):")
    for p in d.get("peers", []):
        print(f"    {p['label']:<28} via {p['link_type']}")


def main() -> None:
    print("\nACP Block 2 — Track N: describe_topology demo")
    print(f"Topology       : sample_sdwan_branch")
    print(f"Logs           : {_LOG_FILE}  (all structured logs redirected here)")

    # RUN 1 — engineers (ALLOWED)
    eng_token = _mint("demo.engineer", "engineers")
    result_allowed = run_describe_topology(
        name="sample_sdwan_branch",
        token=eng_token,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 1 — engineers token (expect ALLOWED + topology summary)")
    print("=" * 70)
    _print_topology(result_allowed)

    # RUN 2 — viewers (BLOCKED)
    view_token = _mint("demo.viewer", "viewers")
    result_blocked = run_describe_topology(
        name="sample_sdwan_branch",
        token=view_token,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 2 — viewers token (expect BLOCKED, no topology data)")
    print("=" * 70)
    _print_topology(result_blocked)

    # RUN 3 — find_path engineers (ALLOWED)
    eng_token2 = _mint("demo.engineer", "engineers")
    result_path = run_find_path(
        source="branch-sw-01",
        destination="hq-core-sw-01",
        token=eng_token2,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 3 — find_path: branch-sw-01 → hq-core-sw-01 (ALLOWED)")
    print("=" * 70)
    _print_path(result_path)

    # RUN 4 — find_path viewers (BLOCKED)
    view_token2 = _mint("demo.viewer", "viewers")
    result_path_blocked = run_find_path(
        source="branch-sw-01",
        destination="hq-core-sw-01",
        token=view_token2,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 4 — find_path: viewers token (expect BLOCKED)")
    print("=" * 70)
    _print_path(result_path_blocked)

    # RUN 5 — check_device_role engineers (ALLOWED)
    eng_token3 = _mint("demo.engineer", "engineers")
    result_role = run_check_device_role(
        node="hq-cedge-01",
        token=eng_token3,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 5 — check_device_role: hq-cedge-01 (ALLOWED)")
    print("=" * 70)
    _print_device(result_role)

    # RUN 6 — check_device_role viewers (BLOCKED)
    view_token3 = _mint("demo.viewer", "viewers")
    result_role_blocked = run_check_device_role(
        node="hq-cedge-01",
        token=view_token3,
        check_governance=_check_governance,
    )
    print("\n" + "=" * 70)
    print("  RUN 6 — check_device_role: viewers token (expect BLOCKED)")
    print("=" * 70)
    _print_device(result_role_blocked)

    print("\n" + "=" * 70)
    print(f"  Audit lines written to: audit.readable.log")
    print(f"  Expect: ALLOWED + REFUSED for describe_topology")
    print(f"          ALLOWED + REFUSED for find_path")
    print(f"          ALLOWED + REFUSED for check_device_role")
    print(f"  Three tools, two scopes (knowledge:read + diagnostics:run)")
    print(f"  Six governance decisions, all audited.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
