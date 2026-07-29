"""
AbhavTech Agentic Control Plane — common configuration loader.
LAB PROTOTYPE — not production ready.

Loads all secrets and settings from environment variables via python-dotenv.
Nothing secret is ever hardcoded.
Fails loudly with a clear [ACP] MISSING: X message if a required var is absent.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH)


class Settings(BaseSettings):
    """Central settings object. All values come from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OAuth issuer
    oauth_issuer_url: str = "http://localhost:9000"
    oauth_secret_key: str                           # REQUIRED — no default
    oauth_access_token_expire_minutes: int = 60

    # MCP server
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8100
    mcp_authorize_automatic_server_data_updates: bool = False

    # Audit trail
    audit_log_path: str = "audit.log"

    # Logging
    log_level: str = "INFO"

    # Domain secrets — optional in Phase 0, populated in later phases
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    groq_api_key: str | None = None
    anthropic_api_key: str | None = None

    @field_validator("oauth_secret_key", mode="before")
    @classmethod
    def _require_oauth_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "\n\n  [ACP] MISSING REQUIRED ENV VAR: OAUTH_SECRET_KEY\n"
                "  Copy .env.example to .env and set a real value.\n"
            )
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(
                f"[ACP] LOG_LEVEL must be one of {allowed}, got '{v}'"
            )
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.
    Import and call this everywhere:
        from src.core.common.config import get_settings
    """
    try:
        return Settings()
    except Exception as exc:
        raise SystemExit(
            f"\n[ACP] Configuration error — cannot start:\n{exc}\n"
        ) from exc