"""Quick validation — Block 7 audit trail check."""
from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger
from src.core.audit.writer import (
    write_audit, query_audit, AuditOutcome, RefusalReason
)

get_settings()
configure_logging()
log = get_logger("test_audit")

# Write three audit records
write_audit(
    actor="test-user",
    tool="echo",
    scopes_presented=["knowledge:read"],
    scopes_required=["knowledge:read"],
    autonomy_level="supervised",
    outcome=AuditOutcome.ALLOWED,
    detail="Tool call allowed — all checks passed",
)
log.info("audit_write", record="ALLOWED")

write_audit(
    actor="test-user",
    tool="echo",
    scopes_presented=["knowledge:read"],
    scopes_required=["knowledge:read"],
    autonomy_level="supervised",
    outcome=AuditOutcome.REFUSED,
    refusal_reason=RefusalReason.TOOL_BLOCKED,
    detail="Tool is Blocked in control_hub.yaml for group: test-group",
)
log.info("audit_write", record="REFUSED_BLOCKED")

write_audit(
    actor="test-user",
    tool="echo",
    scopes_presented=["knowledge:read"],
    scopes_required=["actions:execute"],
    autonomy_level="supervised",
    outcome=AuditOutcome.REFUSED,
    refusal_reason=RefusalReason.SCOPE_MISSING,
    detail="Token missing required scope: actions:execute",
)
log.info("audit_write", record="REFUSED_SCOPE")

# Query and print
results = query_audit(outcome=AuditOutcome.REFUSED)
print(f"\nRefused calls in audit: {len(results)}")
for r in results:
    print(f"  [{r['refusal_reason']}] {r['detail']}")

print("\naudit.log written. Run: scripts\\audit.bat to view.")