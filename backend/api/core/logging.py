"""backend/api/core/logging.py — Structured logging configuration.

Sets up JSON-compatible logging with correlation IDs for production traceability.
Each log record includes: timestamp, level, logger, message, and request context.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

# Thread-local request context
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    _request_id_var.set(value)


def get_user_id() -> str:
    return _user_id_var.get()


def set_user_id(value: str) -> None:
    _user_id_var.set(value)


class ContextFilter(logging.Filter):
    """Inject request_id and user_id into every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.user_id = get_user_id() or "-"
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with structured format and context filter."""
    fmt = "%(asctime)s %(levelname)-8s [%(request_id)s] [user:%(user_id)s] %(name)s — %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%SZ"))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Remove existing handlers to avoid duplicates on reload
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy libraries
    for quiet in ("uvicorn.access", "sqlalchemy.engine", "stripe", "httpx"):
        logging.getLogger(quiet).setLevel(logging.WARNING)
