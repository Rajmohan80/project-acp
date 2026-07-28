@echo off
:: AbhavTech Agentic Control Plane — start OAuth issuer (Windows Option B)
echo [ACP] Starting OAuth issuer on http://localhost:9000 ...
.venv\Scripts\uvicorn src.core.mcp.oauth.issuer:app --host 0.0.0.0 --port 9000 --reload