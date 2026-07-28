@echo off
:: AbhavTech Agentic Control Plane — start MCP server (Windows Option B)
echo [ACP] Starting MCP server on http://localhost:8100 ...
.venv\Scripts\uvicorn src.core.mcp.server.app:app --host 0.0.0.0 --port 8100 --reload