"""
Quick validation — Block 8 money shot.
Tests both refusal types without running the full server.
Calls governance logic directly.
"""
import httpx
from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger
from src.core.mcp.oauth.issuer import mint_token, TokenRequest
from src.core.mcp.server.app import _check_governance
from src.core.audit.writer import AuditOutcome, RefusalReason, query_audit

get_settings()
configure_logging()
log = get_logger("test_governance")

print("\n=== ACP Governance Test ===\n")

# --- Mint two tokens ---
# Token A: engineers group (echo is Allowed, has knowledge:read)
token_a = mint_token(TokenRequest(username="eng-user", group="engineers"))
print(f"Token A minted — group: engineers, scopes: {token_a.scopes}")

# Token B: viewers group (echo is Blocked for viewers)
token_b = mint_token(TokenRequest(username="viewer-user", group="viewers"))
print(f"Token B minted — group: viewers,   scopes: {token_b.scopes}")

# --- Test 1: ALLOWED — engineers calling echo ---
print("\n--- Test 1: engineers calling echo (should ALLOW) ---")
allowed, reason, detail, presented, required = _check_governance(
    token=token_a.access_token,
    tool_name="echo",
)
print(f"  Result  : {'ALLOWED' if allowed else 'REFUSED'}")
print(f"  Reason  : {reason.value}")
print(f"  Detail  : {detail}")
assert allowed, "Test 1 FAILED — should have been allowed"
print("  PASS")

# --- Test 2: REFUSED type A — viewers calling echo (Blocked in hub) ---
print("\n--- Test 2: viewers calling echo (should REFUSE — TOOL_BLOCKED) ---")
allowed, reason, detail, presented, required = _check_governance(
    token=token_b.access_token,
    tool_name="echo",
)
print(f"  Result  : {'ALLOWED' if allowed else 'REFUSED'}")
print(f"  Reason  : {reason.value}")
print(f"  Detail  : {detail}")
assert not allowed, "Test 2 FAILED — should have been refused"
assert reason == RefusalReason.TOOL_BLOCKED, "Test 2 FAILED — wrong reason"
print("  PASS")

# --- Test 3: REFUSED type B — engineers calling actions_execute (scope missing) ---
print("\n--- Test 3: engineers calling actions_execute (should REFUSE — SCOPE_MISSING) ---")
allowed, reason, detail, presented, required = _check_governance(
    token=token_a.access_token,
    tool_name="actions_execute",
)
print(f"  Result  : {'ALLOWED' if allowed else 'REFUSED'}")
print(f"  Reason  : {reason.value}")
print(f"  Detail  : {detail}")
assert not allowed, "Test 3 FAILED — should have been refused"
assert reason == RefusalReason.SCOPE_MISSING, "Test 3 FAILED — wrong reason"
print("  PASS")

# --- Audit query ---
print("\n--- Audit trail — refused calls ---")
refused = query_audit(outcome=AuditOutcome.REFUSED)
for r in refused:
    print(f"  [{r['refusal_reason']}] actor={r['actor']} tool={r['tool']}")

print("\n=== All governance tests PASSED ===")
print("Both refusal types confirmed with distinct audit reasons.")
print("Run: scripts\\audit.bat to see full audit.log")