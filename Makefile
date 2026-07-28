# ============================================================
# AbhavTech Agentic Control Plane — Makefile
# LAB PROTOTYPE — not production ready.
#
# Windows Option B: use the .bat scripts in scripts\ instead.
#   scripts\install.bat
#   scripts\run_oauth.bat
#   scripts\run_mcp.bat
#   scripts\audit.bat
#   scripts\demo.bat
#
# Cross-platform targets (Linux/macOS/CI):
# ============================================================

PYTHON  := python
VENV    := .venv

.PHONY: install test run-mcp run-oauth audit demo clean

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(VENV)/bin/pytest tests/ -v

run-oauth:
	$(VENV)/bin/uvicorn src.core.mcp.oauth.issuer:app --host 0.0.0.0 --port 9000 --reload

run-mcp:
	$(VENV)/bin/uvicorn src.core.mcp.server.app:app --host 0.0.0.0 --port 8100 --reload

audit:
	@cat audit.log 2>/dev/null || echo "No audit.log yet."

demo:
	$(VENV)/bin/python scripts/demo_echo.py

clean:
	rm -rf $(VENV) $$(find . -type d -name __pycache__)