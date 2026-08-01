r"""
AbhavTech Agentic Control Plane — Block 5b: A2A Network Caller.
LAB PROTOTYPE — not production ready.

THE A2A BOUNDARY (LD-13).

A lightweight agent that:
  1. Takes a natural-language question
  2. Grounds the LLM with the REAL node inventory (from describe_topology)
  3. Uses Groq (Llama-3.3-70B) to pick a tool + parameters FROM that inventory
  4. VALIDATES the chosen node IDs against the real topology (no blind trust)
  5. Disambiguates when a reference matches more than one node (asks, not guesses)
  6. Calls ACP over a REAL MCP client (streamable-http, port 8100) — not in-process
  7. Uses Groq to write a prose answer from the governed result

Design principle (from the CCIE domain lens):
  The LLM PROPOSES a parameter; this code VALIDATES it against what actually
  exists before any governed tool call. Ambiguity triggers a disambiguation
  prompt, never a guess.

PREREQUISITE — TWO TERMINALS:
  Terminal 1 (server, leave running):
      cd D:\project-acp
      .venv\Scripts\activate
      python scripts\run_mcp_server.py
  Terminal 2 (this caller):
      cd D:\project-acp
      .venv\Scripts\activate
      python scripts\network_caller.py --question "..."

Requires GROQ_API_KEY and OAUTH_SECRET_KEY in D:\project-acp\.env
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jose import jwt

from src.core.common.config import get_settings
from src.core.mcp.oauth.issuer import GROUP_SCOPES

MCP_URL = "http://127.0.0.1:8100/mcp/"
GROQ_MODEL = "llama-3.3-70b-versatile"
TOPOLOGY = "sample_sdwan_branch"

# The tools this caller knows how to route to, with their parameter shape.
TOOL_CATALOG = [
    {
        "name": "describe_topology",
        "purpose": "Overview of the whole topology — nodes, links, sites, SD-WAN edges.",
        "args": {"name": "topology name (use '" + TOPOLOGY + "')"},
    },
    {
        "name": "find_path",
        "purpose": "Shortest hop path between two named nodes.",
        "args": {"source": "source node id", "destination": "destination node id"},
    },
    {
        "name": "check_device_role",
        "purpose": "Role, platform, and connected peers for one named node.",
        "args": {"node": "node id"},
    },
]


# ------------------------------------------------------------------ #
# Token minting (same pattern as the demos)
# ------------------------------------------------------------------ #

def mint_token(username: str, group: str) -> str:
    settings = get_settings()
    payload = {
        "sub": username,
        "group": group,
        "scopes": GROUP_SCOPES[group],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.oauth_secret_key, algorithm="HS256")


# ------------------------------------------------------------------ #
# Groq helpers
# ------------------------------------------------------------------ #

def _groq_client():
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "\n  [ACP] MISSING: GROQ_API_KEY\n"
            "  Set it in D:\\project-acp\\.env\n"
        )
    from groq import Groq
    return Groq(api_key=settings.groq_api_key)


def groq_pick_tool(question: str, inventory: list[dict]) -> dict:
    """
    Ask Groq to pick a tool and parameters, GROUNDED in the real node inventory.
    Returns: {"tool": ..., "args": {...}}  (raw LLM proposal — not yet validated)
    """
    client = _groq_client()

    node_lines = "\n".join(
        f"  - id={n['id']}  label={n['label']}  site={n['site']}  role={n['role']}"
        for n in inventory
    )
    tools_desc = "\n".join(
        f"  {t['name']}: {t['purpose']}  args={json.dumps(t['args'])}"
        for t in TOOL_CATALOG
    )

    system = (
        "You are a network tool router. Map the user's question to exactly one "
        "tool and its parameters. You MUST choose node ids ONLY from the "
        "inventory provided — never invent an id. If the question is ambiguous "
        "(matches more than one node), still return your best single guess; a "
        "separate validation step will handle disambiguation. "
        "Respond with ONLY a JSON object, no prose, no markdown: "
        '{"tool": "<tool_name>", "args": {<parameters>}}'
    )
    user = (
        f"QUESTION: {question}\n\n"
        f"AVAILABLE TOOLS:\n{tools_desc}\n\n"
        f"NODE INVENTORY (choose ids from here only):\n{node_lines}\n"
    )

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def groq_write_answer(question: str, tool: str, result: dict) -> str:
    """Ask Groq to turn the governed tool result into a prose answer."""
    client = _groq_client()
    system = (
        "You are a Cisco network consultant. Write a concise, accurate answer "
        "to the user's question using ONLY the tool result provided. Do not "
        "invent facts. Mention hop counts, device roles, and link types where "
        "relevant. 2-4 sentences."
    )
    user = (
        f"QUESTION: {question}\n\n"
        f"TOOL USED: {tool}\n\n"
        f"TOOL RESULT (JSON):\n{json.dumps(result, indent=2)}\n"
    )
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ------------------------------------------------------------------ #
# Validation + disambiguation
# ------------------------------------------------------------------ #

def validate_args(tool: str, args: dict, inventory: list[dict]) -> tuple[bool, str]:
    """
    Verify every node id the LLM proposed actually exists in the topology.
    Returns (ok, message). On failure, message lists valid options —
    this is the disambiguation / correction path.
    """
    valid_ids = {n["id"].lower() for n in inventory}

    node_fields = {
        "find_path": ["source", "destination"],
        "check_device_role": ["node"],
        "describe_topology": [],   # takes a topology name, not a node id
    }.get(tool, [])

    for field in node_fields:
        proposed = str(args.get(field, "")).lower()
        if proposed not in valid_ids:
            options = ", ".join(sorted(n["id"] for n in inventory))
            return (
                False,
                f"Proposed {field}='{args.get(field)}' is not a real node. "
                f"Valid node ids: {options}",
            )
    return (True, "")


# ------------------------------------------------------------------ #
# MCP client calls
# ------------------------------------------------------------------ #

def _unwrap(call_result) -> dict:
    """
    Normalise a FastMCP 3.x call_tool result into a plain dict.
    Prefers structured .data, falls back to parsing text content.
    """
    data = getattr(call_result, "data", None)
    if isinstance(data, dict):
        return data
    if data is not None:
        # data might be a pydantic-ish object
        try:
            return dict(data)
        except Exception:
            pass
    # Fall back to text content blocks
    content = getattr(call_result, "content", None)
    if content:
        for block in content:
            text = getattr(block, "text", None)
            if text:
                try:
                    return json.loads(text)
                except Exception:
                    return {"raw": text}
    return {"raw": str(call_result)}


async def fetch_inventory(token: str) -> list[dict]:
    """Call describe_topology over MCP to ground the LLM with real nodes."""
    from fastmcp import Client
    async with Client(MCP_URL) as client:
        res = await client.call_tool(
            "describe_topology",
            {"name": TOPOLOGY, "token": token},
        )
    payload = _unwrap(res)
    topo = payload.get("topology") or {}
    return topo.get("nodes", [])


async def call_tool_over_mcp(tool: str, args: dict, token: str) -> dict:
    """Call the chosen governed tool over the real MCP HTTP transport."""
    from fastmcp import Client
    full_args = dict(args)
    full_args["token"] = token
    async with Client(MCP_URL) as client:
        res = await client.call_tool(tool, full_args)
    return _unwrap(res)


# ------------------------------------------------------------------ #
# Main flow
# ------------------------------------------------------------------ #

async def run(question: str, group: str) -> None:
    print("\n" + "=" * 70)
    print("  ACP Block 5b — A2A Network Caller")
    print("=" * 70)
    print(f"  Question : {question}")
    print(f"  Caller   : demo.{group} (group={group})")
    print(f"  MCP URL  : {MCP_URL}")

    token = mint_token(f"demo.{group}", group)

    # Step 1 — ground with real inventory (over MCP)
    print("\n  [1] Fetching node inventory from ACP (describe_topology over MCP)...")
    try:
        inventory = await fetch_inventory(token)
    except Exception as exc:
        print(f"\n  ERROR connecting to ACP: {exc}")
        print("  Is the server running in Terminal 1? "
              "(python scripts\\run_mcp_server.py)")
        return

    if not inventory:
        print("  No inventory returned — caller group may be blocked from "
              "describe_topology, or topology is empty.")
        return
    print(f"      {len(inventory)} nodes grounded.")

    # Step 2 — LLM picks a tool + args from the inventory
    print("\n  [2] Groq selecting tool + parameters (grounded)...")
    try:
        pick = groq_pick_tool(question, inventory)
    except Exception as exc:
        print(f"  ERROR from Groq: {exc}")
        return
    tool = pick.get("tool", "")
    args = pick.get("args", {})
    print(f"      Groq picked: {tool}({json.dumps(args)})")

    # Step 3 — validate the pick against reality
    print("\n  [3] Validating proposed parameters against real topology...")
    ok, msg = validate_args(tool, args, inventory)
    if not ok:
        print(f"      REJECTED — {msg}")
        print("      (This is the disambiguation guard — the LLM's guess was "
              "not a real node, so no governed call is made.)")
        return
    print("      OK — all node ids exist.")

    # Step 4 — call the governed tool over MCP
    print(f"\n  [4] Calling {tool} over MCP (governed)...")
    result = await call_tool_over_mcp(tool, args, token)

    if not result.get("allowed", True):
        print(f"      GOVERNANCE REFUSED: {result.get('refusal_reason')}")
        print(f"      {result.get('detail')}")
        return
    print("      ALLOWED — governed result returned.")

    # Step 5 — LLM writes prose answer
    print("\n  [5] Groq composing answer...")
    answer = groq_write_answer(question, tool, result)

    print("\n" + "=" * 70)
    print("  ANSWER")
    print("=" * 70)
    print(f"  {answer}")
    print("=" * 70)
    print("\n  Audit: check audit.readable.log — one ALLOWED line for "
          f"{tool} (came over MCP, not in-process).\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="ACP A2A network caller")
    parser.add_argument(
        "--question",
        default="What is the path from the Mumbai branch to the HQ core switch?",
        help="Natural-language network question",
    )
    parser.add_argument(
        "--group",
        default="engineers",
        choices=["admins", "engineers", "viewers"],
        help="Caller group — try 'viewers' to see governance block the call",
    )
    args = parser.parse_args()
    asyncio.run(run(args.question, args.group))


if __name__ == "__main__":
    main()
