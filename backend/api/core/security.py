"""
backend/api/core/security.py — JWT + password hashing
Password: Argon2id (PHC winner) with bcrypt fallback for existing hashes
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from api.config import settings

# Argon2id — OWASP recommended params (time=2, mem=64MB, parallel=2)
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# ── Password ──────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Hash with Argon2id — format: $argon2id$..."""
    return _ph.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify Argon2id hash. Falls back to bcrypt for migrated users."""
    if hashed.startswith("$argon2"):
        try:
            return _ph.verify(hashed, plain)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    else:
        # Legacy bcrypt hash — still valid, will re-hash on next login
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False

def needs_rehash(hashed: str) -> bool:
    """True if hash should be upgraded to latest Argon2id params."""
    if not hashed.startswith("$argon2"):
        return True  # bcrypt → upgrade to argon2id
    return _ph.check_needs_rehash(hashed)

# ── JWT ───────────────────────────────────────────────────────────────────────
def _make_token(subject: str, expires_delta: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_access_token(user_id: str, extra: dict | None = None) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
        extra={"type": "access", **(extra or {})},
    )

def create_refresh_token(user_id: str) -> str:
    return _make_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        extra={"type": "refresh"},
    )

def decode_token(token: str) -> dict[str, Any]:
    """Raises InvalidTokenError subclasses on invalid/expired tokens."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options={"require": ["exp", "iat", "sub"]},
    )
