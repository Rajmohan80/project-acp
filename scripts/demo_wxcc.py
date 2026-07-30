r"""
AbhavTech Agentic Control Plane — Block 1 demo / validation.
LAB PROTOTYPE — not production ready.

Proves a governed tool call reaches REAL corpus data, two ways:

  1. ALLOWED  — engineers token (has knowledge:read, not Blocked)
                -> governance passes -> chunks come back from Qdrant
  2. BLOCKED  — viewers token (search_wxcc_corpus is Blocked for viewers)
                -> refusal type A (TOOL_BLOCKED_IN_CONTROL_HUB), zero chunks

Both write distinct lines to the audit log. Run:

    (.venv) D:\project-acp> python scripts\demo_wxcc.py --query "..."

Requires the OAuth secret + Qdrant creds in D:\project-acp\.env.
Does NOT require the MCP server or issuer to be running — it mints
tokens and invokes governance in-process, which is enough to prove
the governance -> corpus path end to end.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------------ #
# Redirect ALL logging to demo.log BEFORE any module imports that
# trigger structlog / stdlib logging. Keeps stdout clean for results.
# ------------------------------------------------------------------ #
_LOG_FILE = "demo.log"
_file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
logging.root.handlers = []
logging.root.addHandler(_file_handler)
logging.root.setLevel(logging.DEBUG)

# Suppress tqdm progress bars (BGE-M3 load) to stderr — redirect to log too
import io
sys.stderr = open(_LOG_FILE, "a", encoding="utf-8")  # noqa: WPS515

from jose import jwt  # noqa: E402

from src.core.common.config import get_settings  # noqa: E402
from src.core.mcp.oauth.issuer import GROUP_SCOPES  # noqa: E402
from src.core.mcp.server.app import _check_governance  # noqa: E402
from src.domains.contact_center.tool import run_search  # noqa: E402


def _mint(username: str, group: str) -> str:
    """Mint a JWT the same way the issuer does, without an HTTP call."""
    settings = get_settings()
    scopes = GROUP_SCOPES[group]
    payload = {
        "sub": username,
        "group": group,
        "scopes": scopes,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.oauth_secret_key, algorithm="HS256")


def _print_result(label: str, result: dict) -> None:
    print("\n" + "=" * 70)
    print(f"  {label}")
    print("=" * 70)
    print(f"  allowed        : {result.get('allowed')}")
    if not result.get("allowed"):
        print(f"  refusal_reason : {result.get('refusal_reason')}")
        print(f"  detail         : {result.get('detail')}")
        print(f"  chunks         : 0 (refused before retrieval)")
        return
    if result.get("error"):
        print(f"  ERROR          : {result['error']}")
        return
    print(f"  query          : {result.get('query')}")
    print(f"  chunks returned: {result.get('count')}")
    for i, c in enumerate(result.get("chunks", []), 1):
        snippet = (c.get("text", "") or "")[:600].replace("\n", " ")
        print(f"\n  [{i}] {c.get('filename')} "
              f"(Tier {c.get('provenance_tier')}, score={c.get('score'):.3f})")
        print(f"      {snippet}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Block 1 WxCC corpus demo")
    parser.add_argument(
        "--query",
        default="What are the WxCC data residency requirements for UAE?",
        help="Query to run against the WxCC corpus",
    )
    parser.add_argument("--k", type=int, default=5, help="chunks to return")
    args = parser.parse_args()

    settings = get_settings()

    print("\nACP Block 1 — governed WxCC corpus tool demo")
    print(f"Collection : {settings.qdrant_collection}")
    print(f"Query      : {args.query}")
    print(f"Logs       : {_LOG_FILE}  (all structured logs redirected here)")
    print("\n  Loading BGE-M3 from cache and connecting to Qdrant...")
    print("  (first run ~10s — model loads from D:\\hf_cache)\n")

    # 1) ALLOWED — engineers
    eng_token = _mint("demo.engineer", "engineers")
    allowed_result = run_search(
        query=args.query, token=eng_token, k=args.k,
        check_governance=_check_governance,
    )
    _print_result("RUN 1 — engineers token (expect ALLOWED + chunks)",
                  allowed_result)

    # 2) BLOCKED — viewers (search_wxcc_corpus Blocked for viewers)
    view_token = _mint("demo.viewer", "viewers")
    blocked_result = run_search(
        query=args.query, token=view_token, k=args.k,
        check_governance=_check_governance,
    )
    _print_result("RUN 2 — viewers token (expect BLOCKED, zero chunks)",
                  blocked_result)

    # Point the user at the audit record.
    readable = str(settings.audit_log_path)
    if readable.endswith(".log"):
        readable = readable[:-4] + ".readable.log"
    else:
        readable = readable + ".readable.log"
    print("\n" + "=" * 70)
    print(f"  Audit lines written to: {readable}")
    print(f"  Expect: one ALLOWED and one "
          f"REFUSED(TOOL_BLOCKED_IN_CONTROL_HUB) for {settings.qdrant_collection}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
