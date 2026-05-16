"""backend/api/middleware/pii.py — PII log anonymization filter."""
from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence

# Email: user@example.com → u***@e***.com
_EMAIL_RE = re.compile(
    r"\b([A-Za-z0-9])[A-Za-z0-9._%+\-]*@([A-Za-z0-9])[A-Za-z0-9.\-]*\.([A-Za-z]{2,})\b"
)
# IPv4: 192.168.1.100 → 192.168.1.***
_IP_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}\b")
# JWT Bearer token: Bearer eyJxxx.yyy.zzz → Bearer eyJxxx.yyy.[REDACTED]
_JWT_RE = re.compile(
    r"(Bearer\s+eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)\.[A-Za-z0-9_\-]+"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization|cookie|set-cookie)\b([=:]\s*)([^,\s;]+)"
)
_SENSITIVE_FIELD_MARKERS = (
    "authorization",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "cookie",
    "set-cookie",
)


def _mask(text: str) -> str:
    """Apply all PII masks to *text*."""
    text = _EMAIL_RE.sub(lambda m: f"{m.group(1)}***@{m.group(2)}***.{m.group(3)}", text)
    text = _IP_RE.sub(lambda m: f"{m.group(1)}.***", text)
    text = _JWT_RE.sub(r"\1.[REDACTED]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    return text


def _is_sensitive_key(key: str | None) -> bool:
    if not key:
        return False
    lowered = key.lower().replace("-", "_")
    return any(marker in lowered for marker in _SENSITIVE_FIELD_MARKERS)


def sanitize_log_value(value, *, key: str | None = None):
    """Recursively sanitize log payloads without changing their overall shape."""
    if _is_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, str):
        return _mask(value)

    if isinstance(value, Mapping):
        return {
            str(item_key): sanitize_log_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [sanitize_log_value(item) for item in value]

    return value


class PIIFilter(logging.Filter):
    """logging.Filter that redacts emails, IPs, and JWTs from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, (str, dict, list, tuple)):
            record.msg = sanitize_log_value(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_log_value(a) for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: sanitize_log_value(v, key=str(k))
                    for k, v in record.args.items()
                }
        return True
