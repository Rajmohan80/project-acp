# A2A Boundary — How the Flow Works

**Commit:** `ffbd644` · **Component:** `scripts/network_caller.py` → ACP port 8100

This document explains the end-to-end flow of the A2A (agent-to-agent) boundary —
the single point where an autonomous caller speaks to ACP over the real MCP protocol.

---

## The two sides

| Side | Component | Role |
|---|---|---|
| **MCP client** | `scripts/network_caller.py` | Takes a natural-language question, routes it to the right tool, writes a prose answer |
| **MCP server** | ACP on port 8100 | Governs every tool call — checks token, checks policy, runs the domain tool, writes audit line |

The client never calls domain functions directly. Every call crosses an HTTP boundary
and goes through governance. That is what makes this A2A, not in-process.

---

## Flow diagram

```
LEFT COLUMN — network_caller.py          RIGHT COLUMN — ACP port 8100
─────────────────────────────────        ──────────────────────────────

Natural-language question
"What is the device in Mumbai branch?"

         │
         ▼
Step 1 — fetch inventory   ──MCP POST /mcp/──▶   describe_topology
call describe_topology                            governed ✓ → 9 nodes
over MCP                   ◀── 9 nodes ─────────
         │
         ▼
Step 2 — Groq tool router  ──HTTPS──▶  Groq (Llama-3.3-70B)
reads question +           ◀── JSON ──  api.groq.com
node inventory
→ picks check_device_role(branch-cedge-01)
         │
         ▼
Step 3 — validation guard
is branch-cedge-01 in real topology? ✓
         │
         ▼
Step 4 — MCP client call   ──MCP POST /mcp/──▶   _check_governance()
fastmcp.Client                                    decode JWT → engineers
JWT token + args                                  control_hub.yaml → ALLOWED
                                                  audit line written ✓
                                                         │
                                                         ▼
                           ◀── structured result ──  check_device_role
                                                     topology_store.get_node()
         │
         ▼
Step 5 — Groq answer writer
structured result → prose answer

         │
         ▼
"Cisco ISR1100, sd-wan-edge spoke,
 5 peers, dual-transport MPLS + internet"
```

---

## Step-by-step explanation

### Step 1 — Grounding (the most important step)

Before Groq picks any tool or parameters, the caller fetches the **real node
inventory** from ACP via `describe_topology`. This grounds the LLM — Groq is
told to choose node IDs only from this list, never to invent one.

Without grounding, Groq would guess `mumbai-branch-router-01` (a node that
doesn't exist). With grounding, it matches *"Mumbai branch"* against the real
`branch-mumbai` site entry and picks `branch-cedge-01` — a real ID.

This grounding call is itself governed: `describe_topology` requires
`knowledge:read` scope. A blocked caller cannot even get the inventory — the
whole flow stops at Step 1.

### Step 2 — LLM tool selection

Groq receives the question plus the full node inventory. It returns strict JSON:

```json
{"tool": "check_device_role", "args": {"node": "branch-cedge-01"}}
```

Temperature is set to 0 for deterministic output. The LLM proposes; it does
not decide.

### Step 3 — Validation guard

Every node ID the LLM proposed is checked against the real topology before any
governed call. A hallucinated ID is rejected with the list of valid options.
This is the disambiguation and correction path — the LLM never gets to pass a
fake node ID to a governed tool.

### Step 4 — Governed MCP call (the A2A boundary itself)

`fastmcp.Client` connects to `http://127.0.0.1:8100/mcp/` and calls the tool
with a signed JWT token. This crosses a real HTTP boundary — ACP is a separate
running process on port 8100, not an imported library.

Inside ACP, `_check_governance()` runs:
1. Decodes the JWT — reads `group=engineers`
2. Checks `control_hub.yaml` — `check_device_role: engineers: Allowed`
3. Writes an ALLOWED audit line to `audit.readable.log`
4. Calls `check_device_role` → `topology_store.get_node()` → returns the result

### Step 5 — Prose answer

Groq receives the structured tool result and writes a concise, factual answer
using only the returned data. No hallucination is possible at this stage —
the answer is grounded in what ACP returned.

---

## Why the validation guard matters

In a real network there is never just *"the Mumbai branch"*. There are site
hierarchies, naming conventions, redundant device pairs, multiple devices per
site. A naive LLM tool-caller guesses — and in a production network, a wrong
guess causes a wrong answer or a failed call.

This caller encodes the production-correct pattern:

- **Ground** the LLM with the real inventory before it picks anything
- **Validate** the chosen ID exists before any governed call
- **Disambiguate** when a reference matches nothing — return valid options,
  not a guess

The governance layer (OAuth scopes + `control_hub.yaml`) is what makes this
safe. The validation guard is what makes it correct.

---

## Identity comes from the signed token

In the demo, `--group` selects the caller's group for convenience. In production
the group is never chosen by the caller — the OAuth issuer authenticates the
identity, looks up its group, and encodes that group in a cryptographically
signed JWT. ACP reads the group from the signed token. The caller cannot lie
about their group.

---

## How to run (two terminals required)

**Terminal 1 — ACP server (leave running):**
```
cd D:\project-acp
.venv\Scripts\activate
python scripts\run_mcp_server.py
```

**Terminal 2 — A2A caller:**
```
cd D:\project-acp
.venv\Scripts\activate
python scripts\network_caller.py --question "What is the device in Mumbai branch?"
```

Try `--group viewers` to see governance block the flow at Step 1.

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
*Document written from working lab — not ahead of it.*
