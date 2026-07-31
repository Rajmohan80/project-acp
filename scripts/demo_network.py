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
from src.domains.network.tool import run_describe_topology  # noqa: E402


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

    print("\n" + "=" * 70)
    print(f"  Audit lines written to: audit.readable.log")
    print(f"  Expect: one ALLOWED and one REFUSED(TOOL_BLOCKED_IN_CONTROL_HUB)")
    print(f"          for tool=describe_topology")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
