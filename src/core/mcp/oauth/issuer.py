"""
AbhavTech Agentic Control Plane — local OAuth issuer.
LAB PROTOTYPE — not production ready.

FastAPI app that mints scoped JWT tokens for the MCP server.
Scopes: knowledge:read, knowledge:write, diagnostics:run, actions:execute.
Runs on port 9000 (Option B — uvicorn direct, not docker-compose).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from jose import jwt
from pydantic import BaseModel

from src.core.common.config import get_settings
from src.core.common.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

app = FastAPI(
    title="ACP OAuth Issuer",
    description="Local token minter for AbhavTech Agentic Control Plane",
    version="0.1.0",
)

# Valid groups and their allowed scopes
GROUP_SCOPES: dict[str, list[str]] = {
    "admins": [
        "knowledge:read",
        "knowledge:write",
        "diagnostics:run",
        "actions:execute",
    ],
    "engineers": [
        "knowledge:read",
        "knowledge:write",
        "diagnostics:run",
    ],
    "viewers": [
        "knowledge:read",
    ],
}


class TokenRequest(BaseModel):
    username: str
    group: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scopes: list[str]
    expires_in: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "acp-oauth-issuer"}


@app.post("/token", response_model=TokenResponse)
def mint_token(req: TokenRequest) -> TokenResponse:
    """
    Mint a scoped JWT token for the given username and group.
    Returns 400 if the group is unknown.
    """
    settings = get_settings()

    if req.group not in GROUP_SCOPES:
        log.warning("token_rejected", username=req.username, group=req.group)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown group '{req.group}'. "
                   f"Valid groups: {list(GROUP_SCOPES.keys())}",
        )

    scopes = GROUP_SCOPES[req.group]
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.oauth_access_token_expire_minutes
    )

    payload = {
        "sub": req.username,
        "group": req.group,
        "scopes": scopes,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.oauth_secret_key,
        algorithm="HS256",
    )

    log.info(
        "token_minted",
        username=req.username,
        group=req.group,
        scopes=scopes,
    )

    return TokenResponse(
        access_token=token,
        scopes=scopes,
        expires_in=settings.oauth_access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises jose.JWTError if invalid or expired.
    Called by the MCP server to validate every incoming request.
    """
    settings = get_settings()
    return jwt.decode(token, settings.oauth_secret_key, algorithms=["HS256"])