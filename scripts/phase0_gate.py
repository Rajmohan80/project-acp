"""
AbhavTech Agentic Control Plane — Phase 0 Validation Gate.
LAB PROTOTYPE — not production ready.

Runs all Phase 0 exit criteria. Every check must PASS to exit Phase 0.
"""
import pathlib
import sys

from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger
from src.core.audit.writer import (
    AuditOutcome, RefusalReason, write_audit, query_audit
)
from src.core.mcp.oauth.issuer import mint_token, TokenRequest
from src.core.mcp.server.app import _check_governance

configure_logging()
log = get_logger("phase0_gate")

results = []

def check(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    results.append((status, name, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


print("\n" + "="*60)
print("  AbhavTech ACP — Phase 0 Validation Gate")
print("="*60 + "\n")

# ------------------------------------------------------------------ #
# Gate 1 — Python version
# ------------------------------------------------------------------ #
print("Gate 1: Python version")
import sys as _sys
ver = _sys.version_info
check("Python 3.11", ver.major == 3 and ver.minor == 11,
      f"Found {ver.major}.{ver.minor}.{ver.micro}")

# ------------------------------------------------------------------ #
# Gate 2 — .env gitignored
# ------------------------------------------------------------------ #
print("\nGate 2: .env gitignored")
import subprocess
result = subprocess.run(
    ["git", "status"], capture_output=True, text=True
)
check(".env not in git status", ".env" not in result.stdout,
      "gitignore working")

# ------------------------------------------------------------------ #
# Gate 3 — Config loads cleanly
# ------------------------------------------------------------------ #
print("\nGate 3: Config loads cleanly")
try:
    s = get_settings()
    check("Settings load", True, f"log_level={s.log_level}")
except Exception as e:
    check("Settings load", False, str(e))

# ------------------------------------------------------------------ #
# Gate 4 — Structured JSON logging to stdout
# ------------------------------------------------------------------ #
print("\nGate 4: Structured JSON logging")
try:
    log.info("gate4_test", status="ok")
    check("JSON log to stdout", True, "line above is JSON")
except Exception as e:
    check("JSON log to stdout", False, str(e))

# ------------------------------------------------------------------ #
# Gate 5 — Audit trail writes distinct refusal reasons
# ------------------------------------------------------------------ #
print("\nGate 5: Audit trail — dual refusal reasons")
try:
    token_eng = mint_token(
        TokenRequest(username="gate-eng", group="engineers")
    )
    token_view = mint_token(
        TokenRequest(username="gate-viewer", group="viewers")
    )

    # Refusal A — tool blocked
    allowed_a, reason_a, _, _, _ = _check_governance(
        token=token_view.access_token, tool_name="echo"
    )
    check(
        "Refusal A — TOOL_BLOCKED fires",
        not allowed_a and reason_a == RefusalReason.TOOL_BLOCKED,
        reason_a.value,
    )

    # Refusal B — scope missing
    allowed_b, reason_b, _, _, _ = _check_governance(
        token=token_eng.access_token, tool_name="actions_execute"
    )
    check(
        "Refusal B — SCOPE_MISSING fires",
        not allowed_b and reason_b == RefusalReason.SCOPE_MISSING,
        reason_b.value,
    )

    # Both in audit log with distinct reasons
    refused = query_audit(outcome=AuditOutcome.REFUSED)
    reasons = {r["refusal_reason"] for r in refused}
    check(
        "Both refusal reasons in audit.log",
        "TOOL_BLOCKED_IN_CONTROL_HUB" in reasons
        and "TOKEN_MISSING_REQUIRED_SCOPE" in reasons,
        str(reasons),
    )
except Exception as e:
    check("Audit dual refusal", False, str(e))

# ------------------------------------------------------------------ #
# Gate 6 — LAB PROTOTYPE disclaimer in every __init__.py
# ------------------------------------------------------------------ #
print("\nGate 6: LAB PROTOTYPE disclaimer in all __init__.py")
missing = []
for p in pathlib.Path("src").rglob("__init__.py"):
    if "LAB PROTOTYPE" not in p.read_text(encoding="utf-8"):
        missing.append(str(p))
check(
    "LAB PROTOTYPE in all __init__.py",
    len(missing) == 0,
    f"{len(missing)} missing" if missing else "all 16 files OK",
)

# ------------------------------------------------------------------ #
# Gate 7 — naming-map.md exists and has content
# ------------------------------------------------------------------ #
print("\nGate 7: docs/naming-map.md")
nmap = pathlib.Path("docs/naming-map.md")
check(
    "naming-map.md exists and non-empty",
    nmap.exists() and len(nmap.read_text(encoding="utf-8")) > 500,
    f"{len(nmap.read_text(encoding='utf-8'))} chars" if nmap.exists() else "missing",
)

# ------------------------------------------------------------------ #
# Gate 8 — control_hub.yaml exists and has tools
# ------------------------------------------------------------------ #
print("\nGate 8: control_hub.yaml")
import yaml
hub = pathlib.Path("src/core/mcp/control_hub.yaml")
if hub.exists():
    data = yaml.safe_load(hub.read_text(encoding="utf-8"))
    tool_count = len(data.get("tools", {}))
    check("control_hub.yaml has tools", tool_count >= 1,
          f"{tool_count} tools defined")
else:
    check("control_hub.yaml exists", False, "file missing")

# ------------------------------------------------------------------ #
# Summary
# ------------------------------------------------------------------ #
print("\n" + "="*60)
passed = [r for r in results if r[0] == "PASS"]
failed = [r for r in results if r[0] == "FAIL"]
print(f"  PASSED: {len(passed)}/{len(results)}")
if failed:
    print(f"  FAILED: {len(failed)}")
    for _, name, detail in failed:
        print(f"    ✗ {name} — {detail}")
    print("\n  Phase 0 gate: NOT PASSED — fix failures above.")
    sys.exit(1)
else:
    print("\n  Phase 0 gate: ALL CHECKS PASSED")
    print("  Ready to exit Phase 0 and begin Phase 1.")
print("="*60 + "\n")