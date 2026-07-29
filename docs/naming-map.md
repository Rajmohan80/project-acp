# AbhavTech Agentic Control Plane — Naming Map
**LAB PROTOTYPE — not production ready.**
Rajmohan Mangattu | CCIE Collaboration #55207 | AbhavTech Consulting

This table maps every ACP component to its Cisco AgenticOps equivalent.
It exists so any Cisco-fluent engineer can read the ACP architecture
and immediately understand what each piece corresponds to in Cisco's model.

---

## Core mapping table

| ACP Component | Cisco AgenticOps Concept | Notes |
|---|---|---|
| `mcp/server/app.py` (FastMCP) | Webex AI Agent Studio — MCP server | AI Agent Studio hosts and governs MCP tool servers for Webex agents |
| `mcp/control_hub.yaml` | Cisco Webex Control Hub — Agentic Apps provisioning | Control Hub allows/blocks agentic app access per user group. control_hub.yaml mirrors this exactly |
| `mcp/oauth/issuer.py` | Control Hub identity + scoped access tokens | Control Hub issues scoped credentials to agentic apps. The OAuth issuer is the lab equivalent |
| `mcp/lifecycle/` | MCP protocol lifecycle in AI Agent Studio | initialize, capability negotiation, shutdown mirror the MCP session lifecycle Cisco implements |
| `mcp/registry/` | AI Agent Studio tool registry | Cisco maintains a registry of available tools per agent. The ACP registry is the lab equivalent |
| `autonomy/` (stub) | Cisco Autonomy Dial | Cisco's autonomy dial controls how much an agent acts vs asks. The ACP autonomy module encodes this as a confidence + risk score |
| `audit/writer.py` | Webex Control Hub audit log | Control Hub logs all agentic app activity. The ACP audit trail is the lab equivalent — same fields, same governance purpose |
| `common/config.py` | Cisco cloud config + secrets management | Cisco uses Vault/Secret Manager. The ACP config loader is the lab equivalent — environment-driven, no hardcoded secrets |
| `domains/network/` (Track N) | Cisco Deep Network Model (DNM) | The DNM is Cisco's AI model for network operations. Track N is the ACP domain module that would consume it |
| `domains/contact_center/` (Track C) | Webex Contact Center AI + WxCC SLM | Track C connects the ACP control plane to the WxCC SLM domain module |
| `surfaces/canvas/` | Cisco AI Canvas | The AI Canvas is Cisco's agentic workflow UI. The ACP canvas surface is the lab equivalent |
| `surfaces/api/` | Cisco AI Canvas API layer | REST API surface consumed by the canvas and external clients |
| Internal multi-agent coordination | Cisco multi-agent orchestration | Internal coordination within ACP. NOT called A2A — that term is reserved for the external boundary below |
| A2A boundary (Phase 1+) | Cisco Agent-to-Agent (A2A) protocol | A2A is used at exactly ONE boundary: GCP Dialogflow CX → ACP. Uses Agent Cards, Tasks, JSON-RPC over HTTP/SSE |
| `docker-compose.yml` (optional) | Cisco containerised deployment | Documented path for containerisation. Active runtime is Option B (uvicorn direct) for lab |

---

## Domain registry (control_hub.yaml routing)

| Domain Module | Qdrant Collection | Classifier | Status |
|---|---|---|---|
| WxCC SLM (`domains/contact_center/`) | `wxcc_slm_corpus` | WxCC intent patterns | EXISTS — `D:\project-slm-webex\` |
| GCP CCAI SLM (future) | `ccai_corpus` | CCAI intent patterns | Phase 1+ — separate repo |
| Network NOC (future) | `network_corpus` | Network intent patterns | Phase 1+ — Track N |

---

## A2A boundary — where it sits