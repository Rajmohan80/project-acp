# ACP — Block 5: The A2A Boundary (Complete)

**Date:** 1 August 2026 · **Commits:** `e6399c7` (5a), `ffbd644` (5b/5c)
**Milestone:** Natural-language question → LLM tool selection → governed MCP call → prose answer, end to end, over the wire.

---

## What Block 5 achieved

This is the A2A (agent-to-agent) boundary — LD-13. It is the single point in
the architecture where an autonomous caller talks to ACP over the real MCP
protocol, and it is the portfolio centrepiece.

Before Block 5, every tool call was **in-process**: a Python script imported
`_check_governance` and called the domain functions directly, choosing the
parameters by hand. Block 5 replaces that with a genuine agentic flow across a
network boundary:

```
Natural-language question
   ↓
LLM (Groq Llama-3.3-70B) picks a tool + parameters from a GROUNDED inventory
   ↓
Validation guard checks the chosen node ids against the real topology
   ↓
Caller invokes the tool over a REAL MCP client (streamable-http, port 8100)
   ↓
ACP checks token + policy, runs the tool, returns a governed result
   ↓
LLM writes a prose answer from the governed result
```

---

## Block 5a — MCP transport live over HTTP (`e6399c7`)

The MCP transport was declared in `app.py` but never mounted or served.
Block 5a made ACP a standing HTTP service.

Two things were required and easy to miss:

1. **Mount alignment.** `mcp.http_app(path="/")` serves the MCP app at its own
   root; mounting it at `Mount("/mcp", ...)` makes the full endpoint exactly
   `/mcp/`. Setting `path="/mcp"` AND mounting at `/mcp` stacks the paths and
   yields a 404.
2. **Lifespan.** The Starlette app MUST pass `lifespan=mcp_app.lifespan`.
   Without it, the MCP session manager never starts and every client call
   fails with "Session terminated". FastMCP's own error message documents this.

```python
mcp_app = mcp.http_app(path="/")

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/mcp", app=mcp_app),
    ],
    lifespan=mcp_app.lifespan,   # ← without this: "Session terminated"
)
```

---

## Block 5b/5c — the network caller (`ffbd644`)

`scripts/network_caller.py` is the A2A caller. It does five things:

**1. Grounds the LLM with real inventory.**
Before the LLM picks anything, the caller invokes `describe_topology` over MCP
and feeds the actual node list to the model. The LLM never guesses ids from
thin air — it selects from what exists.

**2. LLM selects a tool + parameters.**
Groq maps the natural-language question to one tool call, returning strict JSON:
`{"tool": "check_device_role", "args": {"node": "branch-cedge-01"}}`.

**3. Validates the selection against reality.**
Every node id the LLM proposed is checked against the real topology before any
governed call. A hallucinated id is rejected with the list of valid options —
this is the disambiguation / correction guard. **The LLM proposes; the code
verifies.**

**4. Calls the governed tool over real MCP.**
Using `fastmcp.Client` against `http://127.0.0.1:8100/mcp/`, a genuine MCP
session is negotiated and the tool is called with a signed JWT token. This is
not in-process — it crosses the network boundary. ACP checks the token and the
`control_hub.yaml` policy before running the tool.

**5. LLM writes the answer.**
Groq turns the governed structured result into a concise prose answer, using
only the returned facts.

---

## Validated run (engineers token)

**Question:** "What is the device in Mumbai branch?"

```
[1] Fetching node inventory from ACP (describe_topology over MCP)...
    POST http://127.0.0.1:8100/mcp/  200 OK
    Received session ID: b0672d19e0c0435ca1846624e7384e20
    Negotiated protocol version: 2025-11-25
    9 nodes grounded.
[2] Groq selecting tool + parameters (grounded)...
    Groq picked: check_device_role({"node": "branch-cedge-01"})
[3] Validating proposed parameters against real topology...
    OK — all node ids exist.
[4] Calling check_device_role over MCP (governed)...
    POST http://127.0.0.1:8100/mcp/  200 OK
    ALLOWED — governed result returned.
[5] Groq composing answer...

ANSWER:
The device in the Mumbai branch is a Cisco ISR1100 IOS-XE SD-WAN device,
specifically a cEdge, with the role of "sd-wan-edge" acting as a spoke.
It has 5 peers (vManage, vBond, vSmart, HQ-cEdge-01, Branch-SW-01) across
management, control, OMP tunnel, and LAN links. Dual-transport (MPLS +
internet), located at the branch-mumbai site, node id branch-cedge-01.
```

Every fact traces to the topology. No hallucination. The governed call is
recorded in `audit.readable.log`.

---

## Design principle — why validation matters (the CCIE lens)

A naive LLM tool-caller would let the model guess parameters and call the tool
blind. In a real network there is never just "the Mumbai branch" — there are
site hierarchies, naming conventions, redundant device pairs, multiple devices
per site. An agent that guesses is dangerous.

This caller encodes the production-correct pattern:

- **Grounding:** the LLM chooses from the real inventory, not from memory.
- **Validation:** the chosen id is verified to exist before any governed call.
- **Disambiguation:** an id that does not exist is rejected with valid options,
  rather than passed through as a guess.

The scarce skill is not calling an LLM — it is refusing to trust the LLM's
parameter until it has been checked against reality.

---

## Identity comes from the signed token, not the caller's claim

In the demo, `--group` selects the caller's group for convenience. In
production the group is never chosen by the caller: the OAuth issuer
authenticates the identity, looks up its group, and encodes that group inside a
cryptographically signed JWT. ACP reads the group from the signed token and
cannot be lied to. The demo's `_mint()` shortcuts issuance but ACP's
group-enforcement mechanism is already production-correct — it decodes the
signed token and reads `payload["group"]`.

---

## How to run (TWO TERMINALS)

**Terminal 1 — server (leave running):**
```
cd D:\project-acp
.venv\Scripts\activate
python scripts\run_mcp_server.py
```

**Terminal 2 — caller (server still running in Terminal 1):**
```
cd D:\project-acp
.venv\Scripts\activate
python scripts\network_caller.py --question "What is the device in Mumbai branch?"
```

Try `--group viewers` to see governance block the flow, and vary the question
("path from branch to HQ", "describe the topology") to exercise all three
Track N tools through the LLM router.

Requires `GROQ_API_KEY` and `OAUTH_SECRET_KEY` in `D:\project-acp\.env`.

---

## Architecture position — what is now complete

```
┌──────────────────────────────────────────────────────────┐
│  network_caller.py — A2A caller (Block 5b/5c) ✅         │
│  Groq tool router + validation guard + prose writer      │
└───────────────────────────┬──────────────────────────────┘
                            │ real MCP protocol over HTTP
                            ▼
┌──────────────────────────────────────────────────────────┐
│  ACP MCP server, port 8100 (Block 5a) ✅                 │
│  /health + /mcp mounted, lifespan running                │
│  ┌────────────────┬─────────────────────────────────┐    │
│  │ Track C        │ Track N                          │    │
│  │ search_wxcc_   │ describe_topology / find_path /  │    │
│  │ corpus         │ check_device_role                │    │
│  └────────────────┴─────────────────────────────────┘    │
│  OAuth 2.1 scopes + control_hub.yaml policy + audit      │
└──────────────────────────────────────────────────────────┘
```

Natural language in → governed answer out, over the wire. This is the
demonstrable end-to-end system.

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
*Document written from working lab — not ahead of it.*
