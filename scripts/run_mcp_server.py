"""
AbhavTech Agentic Control Plane — MCP server launcher.
LAB PROTOTYPE — not production ready.

Starts the ACP governed MCP server as a standing HTTP service on port 8100.
Both /health and /mcp are served from the same port.

Run from D:\\project-acp\\ with venv active:
    python scripts\\run_mcp_server.py

Endpoints:
    GET  http://localhost:8100/health  — liveness check
    POST http://localhost:8100/mcp     — MCP streamable-http transport

Keep this terminal open while running network_caller.py in a second terminal.
"""

import os
import sys

# Ensure project root is on path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

if __name__ == "__main__":
    print("\nAbhavTech ACP — MCP server starting")
    print("  Health : http://localhost:8100/health")
    print("  MCP    : http://localhost:8100/mcp")
    print("  Press Ctrl+C to stop\n")

    uvicorn.run(
        "src.core.mcp.server.app:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
        log_level="warning",   # suppress uvicorn access logs — ACP audit handles it
    )
