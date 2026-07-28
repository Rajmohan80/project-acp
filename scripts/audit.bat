@echo off
:: AbhavTech Agentic Control Plane — tail audit log (Windows Option B)
if exist audit.log (
    type audit.log
) else (
    echo [ACP] No audit.log yet — run the server first.
)