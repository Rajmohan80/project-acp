"""
AbhavTech Agentic Control Plane — structured JSON logging.
LAB PROTOTYPE — not production ready.

Provides get_logger(name) for structured JSON logs to stdout.
Audit lines go to a SEPARATE audit.log via the audit module — not here.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.core.common.config import get_settings


def configure_logging() -> None:
    """
    Call once at application startup to wire structlog to stdlib to stdout.
    Subsequent calls are safe (idempotent).
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structured logger.
    Usage:
        log = get_logger(__name__)
        log.info("event", key="value")
    """
    return structlog.get_logger(name)