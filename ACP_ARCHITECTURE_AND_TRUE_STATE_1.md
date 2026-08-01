# AbhavTech — Architecture & True State
**Rajmohan Mangattu | CCIE Collaboration #55207 | AbhavTech Consulting**
**Date: 28 July 2026 | Prepared after Session 1 of ACP build**

---

## 1. Two Projects — Do Not Confuse Them

| Item | WxCC SLM | Agentic Control Plane (ACP) |
|---|---|---|
| Path | `D:\project-slm-webex\` | `D:\project-acp\` |
| Purpose | Domain AI — Cisco WxCC consulting answers | Governed control plane for agentic automation |
| Status | Phase 4 active (LangGraph + agent built) | Phase 0 skeleton only (started today) |
| MCP server | Item 5 — planned, zero code written | Phase 0 scope — zero code written |
| FastAPI | `api_server.py` EXISTS and runs on port 8000 | Will be used for OAuth issuer (not yet written) |
| FastMCP | Dependency listed, not yet used | Installed in venv, not yet used |
| LLM | Groq Llama-3.3-70B (live) | None yet (Phase 0 has no LLM) |

---

## 2. WxCC SLM — What Is Actually Built

### Truly built and confirmed running

```
D:\project-slm-webex\
  slm_pipeline.py        — classifier + retriever + generator pipeline
  slm_graph.py           — LangGraph StateGraph (4 nodes)
  slm_state.py           — WxCCState TypedDict
  slm_agent.py           — LangChain ReAct agent (2 tools)
  tools.py               — search_vector_db + run_capacity_calculator
  prompt_builder.py      — classification + generation prompts
  llm_client.py          — model-agnostic LLM abstraction
  api_server.py          — FastAPI REST on port 8000 (BUILT, RUNS)
  streamlit_app.py       — Streamlit UI on port 8501 (BUILT, RUNS)
  run_graph.py           — CLI runner for LangGraph
```

### Corpus (Qdrant Cloud)
- Collection: `wxcc_slm_corpus`
- Chunks: 2,633
- Embeddings: BGE-M3 (dim=1024), cached at `D:\hf_cache\`
- Workbooks A–D: NOT yet indexed (corpus gap — known)

### What "in progress" actually means for WxCC SLM

| Item | Real State |
|---|---|
| Item 5 — MCP server (11 tools) | Architecture decided. Zero Python files written. FastMCP not yet used. |
| Item 6 — n8n automation | Designed. Not built. |
| Item 7 — Integration + 49 golden tests | Designed. Not run end-to-end. |
| Anthropic billing | Pending. All LLM calls go via Groq today. |
| PostgresSaver | Not migrated yet. MemorySaver in use. |

### Known technical debt (WxCC SLM)

1. `_generate_groq()` hardcodes model string instead of `GROQ_FAST_MODEL` constant
2. `BACKEND = "gemini"` docstring is stale — runtime is all-Groq
3. Legacy `run()` conversation_history list not fully replaced by LangGraph state
4. Workbooks A–D not indexed in Qdrant
5. Four corpus folders contain only README placeholders

---

## 3. Agentic Control Plane (ACP) — What Is Actually Built

### What exists on disk as of 28 July 2026 (end of Session 1)

```
D:\project-acp\
  .gitignore             DONE — secrets, venv, audit.log excluded
  .env.example           DONE — placeholders only
  .env                   DONE — local dev values (gitignored)
  pyproject.toml         DONE — Python 3.11, all deps declared
  Makefile               DONE — stub, cross-platform documented path
  docker-compose.yml     DONE — documented optional path (Option B active)
  README.md              STUB — empty
  ARCHITECTURE.md        STUB — empty
  docs/naming-map.md     STUB — empty
  scripts/
    install.bat          DONE
    run_oauth.bat        DONE
    run_mcp.bat          DONE
    audit.bat            DONE
    demo.bat             DONE
  src/
    __init__.py          DONE
    core/
      __init__.py        DONE
      mcp/
        __init__.py      DONE
        control_hub.yaml STUB — empty
        server/          STUB — __init__.py only
        lifecycle/       STUB — __init__.py only
        oauth/           STUB — __init__.py only
        registry/        STUB — __init__.py only
      autonomy/          STUB — __init__.py only
      audit/             STUB — __init__.py only
      common/            STUB — __init__.py only
    domains/
      network/           STUB — __init__.py only (Phase 1+)
      contact_center/    STUB — __init__.py only (Phase 1+)
    surfaces/
      canvas/            STUB — __init__.py only (Phase 1+)
      api/               STUB — __init__.py only (Phase 1+)
  tests/                 STUB — .gitkeep only
```

### Git state
- Root commit: `d83aff2` — "Phase 0: repo skeleton, pyproject, venv, batch scripts"
- All 32 files committed
- `.env` confirmed gitignored

### Dependencies installed (venv confirmed clean)
```
fastmcp 3.4.5      — MCP server library (installed, not yet used)
fastapi 0.140.8    — REST API framework (installed, not yet used)
uvicorn 0.51.0     — ASGI server (installed, not yet used)
structlog 24.x     — structured logging (installed, not yet used)
python-dotenv      — secrets loader (installed, not yet used)
pydantic-settings  — config validation (installed, not yet used)
python-jose        — JWT tokens (installed, not yet used)
tinydb             — audit trail storage (installed, not yet used)
pytest             — test runner (installed)
ruff               — linter (installed)
```

---

## 4. ACP — What Needs To Be Built (Blocks 6–9)

These are the remaining Phase 0 items. Nothing below exists yet.

### Block 6 — Foundation code
| File | What it does |
|---|---|
| `src/core/common/config.py` | Loads all settings from `.env`. Fails loudly with `[ACP] MISSING: X` if required var absent. Singleton via `lru_cache`. |
| `src/core/common/logging.py` | Configures structlog → JSON → stdout. Call `get_logger(__name__)` in every module. |

### Block 7 — Audit trail
| File | What it does |
|---|---|
| `src/core/audit/writer.py` | Writes every tool call, refusal, and governance decision to `audit.log` as structured JSON. Separate from stdout logs. Queryable via TinyDB. |

### Block 8 — OAuth issuer + MCP server
| File | What it does |
|---|---|
| `src/core/mcp/oauth/issuer.py` | FastAPI app. Mints JWT tokens with scopes: `knowledge:read`, `knowledge:write`, `diagnostics:run`, `actions:execute`. Runs on port 9000. |
| `src/core/mcp/control_hub.yaml` | Policy file. Lists each tool + each user group + Allowed/Blocked. MCP server reads this at startup. |
| `src/core/mcp/server/app.py` | FastMCP server. Hosts one demo tool (`echo`). Enforces two refusal types: (a) tool Blocked in control_hub.yaml, (b) token missing required scope. Both refusals write distinct audit lines. Runs on port 8100. |
| `src/core/mcp/lifecycle/manager.py` | initialize, capability negotiation, shutdown. `authorize_automatic_server_data_updates` flag. |
| `scripts/demo_echo.py` | Fires the echo tool, triggers both refusal types, prints audit output. |

### Block 9 — Documentation + validation gate
| File | What it does |
|---|---|
| `docs/naming-map.md` | Full table: ACP component → Cisco AgenticOps concept. MCP server = AI Agent Studio. Autonomy dial = confidence threshold. control_hub.yaml = Control Hub Agentic Apps provisioning. |
| All `__init__.py` files | Add LAB PROTOTYPE docstring. `grep` must find it in every module. |
| Phase 0 validation gate | Run all 7 gate checks. Pass all to exit Phase 0. |

---

## 5. Phase 0 Validation Gate (not yet passed)

These are the exit criteria. None have been run yet.

- [ ] Python 3.11 confirmed ✅ | Git confirmed ✅ | Docker Option B documented ✅
- [ ] `scripts\install.bat` completes clean ✅ (done via manual pip)
- [ ] `.env` gitignored ✅ | `.env.example` has placeholders only ✅
- [ ] Missing required var → clean `[ACP] MISSING: X` message, not stack trace — **NOT YET TESTED**
- [ ] Structured JSON logs → stdout — **NOT YET WRITTEN**
- [ ] Audit lines → separate `audit.log` — **NOT YET WRITTEN**
- [ ] THE MONEY SHOT: tool refused two ways (Blocked + wrong scope), both in audit.log with distinct reasons — **NOT YET WRITTEN**
- [ ] `authorize_automatic_server_data_updates=false` → metadata change forces re-auth — **NOT YET WRITTEN**
- [ ] Every module docstring carries LAB PROTOTYPE disclaimer — **NOT YET WRITTEN**
- [ ] `docs/naming-map.md` contains full Cisco concept table — **NOT YET WRITTEN**

---

## 6. Overall Architecture — What ACP Will Be

```
┌─────────────────────────────────────────────────────────────────┐
│                  AbhavTech Agentic Control Plane                 │
│                      LAB PROTOTYPE                               │
├───────────────────────┬─────────────────────────────────────────┤
│   Track N             │   Track C                               │
│   domains/network/    │   domains/contact_center/               │
│   (Phase 1+)          │   (Phase 1+ — feeds WxCC SLM)           │
├───────────────────────┴─────────────────────────────────────────┤
│                    src/core/  (Phase 0)                          │
│                                                                   │
│   mcp/server/app.py        ← FastMCP — governed tool server     │
│   mcp/oauth/issuer.py      ← FastAPI — local token minter       │
│   mcp/control_hub.yaml     ← allow/block policy per group       │
│   mcp/lifecycle/           ← init, capability neg., shutdown     │
│   mcp/registry/            ← tool metadata + versioning          │
│                                                                   │
│   audit/writer.py          ← every decision → audit.log         │
│   common/config.py         ← all secrets from .env              │
│   common/logging.py        ← structured JSON → stdout           │
│   autonomy/                ← dial, confidence, risk (stubs)     │
├───────────────────────────────────────────────────────────────────┤
│   OAuth issuer (port 9000) │ MCP server (port 8100)             │
│   JWT scopes:              │ Tools: echo (demo)                  │
│   knowledge:read           │ Refusal type A: Blocked in yaml     │
│   knowledge:write          │ Refusal type B: missing scope       │
│   diagnostics:run          │ Both → distinct audit.log lines     │
│   actions:execute          │                                      │
└───────────────────────────────────────────────────────────────────┘
```

### Technology decisions

| Technology | Role | Why |
|---|---|---|
| FastMCP | MCP server | Implements Model Context Protocol — standard for AI agent tool calls |
| FastAPI | OAuth issuer | Lightweight Python REST framework — runs with uvicorn |
| structlog | Stdout logging | JSON-structured, machine-readable, production pattern |
| python-dotenv + pydantic-settings | Config + secrets | Loads `.env`, validates types, fails loudly if missing |
| python-jose | JWT tokens | Industry-standard signed tokens with embedded scopes |
| TinyDB | Audit trail | JSON file store — queryable, no server, right for lab prototype |
| Python 3.11 | Runtime | Ecosystem floor — all binary wheels exist, LangChain/FastMCP tested |

### What FastAPI vs FastMCP each do

**FastAPI** is a general Python web framework. In ACP it plays one specific role: the OAuth issuer. It receives a username+group, validates credentials, and returns a signed JWT token. That's all it does in Phase 0.

**FastMCP** is a Model Context Protocol server library. It hosts tools that AI agents call in a structured way. The MCP protocol defines how an agent discovers what tools exist, what scopes they require, and how to call them. FastMCP handles all the protocol mechanics. You write the tool functions; FastMCP wraps them.

They run on different ports (9000 and 8100) and are independent services.

---

## 7. Naming Discipline

| What we call it | What it is NOT |
|---|---|
| Multi-agent orchestration (internal coordination) | NOT "A2A" |
| A2A boundary | Only at the Webex AI Agent Studio integration point — Phase 1+, not Phase 0 |
| Track N / Track C | Two domains sharing one control plane |
| control_hub.yaml | The ACP equivalent of Cisco Control Hub Agentic Apps provisioning |

---

## 8. Session Continuity

**At the start of every ACP build session:**
1. Navigate to `D:\project-acp\`
2. Run `.venv\Scripts\activate`
3. Verify prompt shows `(.venv) D:\project-acp>`
4. Continue from the last confirmed block

**Current last confirmed block: Block 5**
**Next block to build: Block 6** — `common/config.py` and `common/logging.py`

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
*Document generated: 28 July 2026 | ACP Session 1 debrief*
