# ACP — Block 5a: MCP Transport Live Over HTTP

**Date:** 31 July 2026 · **Commit:** `e6399c7`
**Milestone:** ACP now serves the MCP protocol as a standing HTTP service.

---

## What this block achieved

Before this block, ACP's governed tools existed but were only ever called
**in-process** — the demo scripts imported `_check_governance` and called the
domain functions directly. The MCP transport (`mcp.http_app`) was declared in
`app.py` but never mounted, so nothing served it.

Block 5a closes that gap. ACP now runs as a real network service:

```
GET  http://localhost:8100/health  →  {"status":"ok","service":"acp-mcp-server"}
POST http://localhost:8100/mcp     →  MCP streamable-http transport (live)
```

This is the prerequisite for the A2A boundary (LD-13): a remote caller can now
connect to ACP over HTTP and invoke governed tools via the real MCP protocol,
rather than importing ACP's code.

---

## The change

Two edits, one new file.

**`src/core/mcp/server/app.py`** — mounted the MCP app into the Starlette app:

```python
from starlette.routing import Mount, Route

# mcp_app must be created BEFORE app so it can be mounted
mcp_app = mcp.http_app(path="/mcp")

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/mcp", app=mcp_app),
    ],
)
```

Previously `mcp_app` was created but never attached to `app`, so port 8100
served `/health` only and `/mcp` returned 404.

**`scripts/run_mcp_server.py`** — new launcher that starts ACP on port 8100
via uvicorn, serving both endpoints from one process.

**`.env`** — two corrections needed before the service ran cleanly:
- `OAUTH_SECRET_KEY` had a duplicated prefix (`OAUTH_SECRET_KEY=OAUTH_SECRET_KEY=...`)
- `GROQ_API_KEY` was commented out (needed for the Block 5b caller)

---

## How to run it

The server and the client must run in **two separate terminals**. The server
holds the terminal open; a second terminal is used to call it.

**Terminal 1 — start the server (leave running):**
```
cd D:\project-acp
.venv\Scripts\activate
python scripts\run_mcp_server.py
```
Wait for: `Uvicorn running on http://0.0.0.0:8100`

**Terminal 2 — verify (server still running in Terminal 1):**
```
curl http://127.0.0.1:8100/health
```
Returns: `{"status":"ok","service":"acp-mcp-server"}`

```
curl http://127.0.0.1:8100/mcp
```
Returns an empty/handshake-rejected response — NOT "connection refused".
A bare GET lacks the MCP handshake headers, so the endpoint rejects it;
the fact that it responds at all proves `/mcp` is mounted and serving.

---

## Lesson learned (recorded so it doesn't recur)

The server must stay running in its own terminal. Pressing Ctrl+C stops the
server — running `curl` after Ctrl+C hits a dead port and returns
"connection refused". This is not a code fault; it is the nature of a
standing service. Always use two terminals: one for the server, one for
the client.

On Windows, use `127.0.0.1` rather than `localhost` in curl to avoid
IPv4/IPv6 resolution ambiguity.

---

## Architecture position

```
┌─────────────────────────────────────────────────┐
│  Block 5b — network caller (NEXT)               │
│  Groq picks tool → connects to /mcp as client   │
└───────────────────────┬─────────────────────────┘
                        │ real MCP protocol over HTTP
                        ▼
┌─────────────────────────────────────────────────┐
│  ACP MCP server (port 8100)  ← Block 5a LIVE    │
│  /health  +  /mcp mounted                       │
│  5 governed tools, OAuth + policy + audit       │
└─────────────────────────────────────────────────┘
```

Block 5a is the wire. Block 5b is the caller that speaks over it.

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
