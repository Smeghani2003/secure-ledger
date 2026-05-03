"""Authentication and crypto primitives.

- Password hashing: bcrypt with manual SHA-256 prehash.
  Why prehash: bcrypt has a hard 72-byte password limit and (in 4.x) raises
  rather than silently truncating. SHA-256 prehashing produces a fixed
  32-byte digest, base64-encoded to 44 printable bytes — well under bcrypt's
  limit, with no entropy loss. Same approach used by Django and Supabase.
  We use bcrypt directly (not passlib) because passlib 1.7.4 is unmaintained
  and has known incompatibilities with bcrypt 4.x.
- JWT access + refresh tokens via python-jose
- Helpers used by the auth router
"""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def _prehash(plain: str) -> bytes:
    """SHA-256 prehash, base64-encoded to printable bytes safe for bcrypt."""
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_prehash(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB — treat as failed verify.
        return False


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on any problem."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError(f"expected token type {expected_type}, got {payload.get('type')}")
    return payload
