"""Authentication service for JWT-based user authentication and API key management.

Provides password hashing, JWT creation/decoding, user authentication logic,
and API key generation, validation, and rate limiting.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ca_biositing.datamodels.models import ApiKey, ApiUser

logger = logging.getLogger(__name__)

# Argon2 password hasher
password_hash = PasswordHash.recommended()

# Pre-computed dummy hash for constant-time comparison on missing users/keys
DUMMY_HASH = password_hash.hash("dummy-password-for-timing-safety")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2 hash."""
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)


def authenticate_user(session: Session, username: str, password: str) -> Optional[ApiUser]:
    """Look up a user by username and verify their password.

    Uses a constant-time dummy hash check for non-existent users to prevent
    timing-based username enumeration.

    Returns the ApiUser on success, or None on failure (wrong password,
    nonexistent user, or disabled account).
    """
    user = session.exec(select(ApiUser).where(ApiUser.username == username)).first()
    if not user:
        # Constant-time dummy check to prevent username enumeration
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if user.disabled:
        return None
    return user


def create_access_token(
    data: dict,
    secret_key: str,
    algorithm: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload data to encode (must include "sub" claim).
        secret_key: The HMAC signing secret.
        algorithm: JWT signing algorithm (e.g. "HS256").
        expires_delta: Token lifetime; defaults to 30 minutes.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str,
) -> Optional[str]:
    """Decode a JWT access token and return the username (sub claim).

    Returns None if the token is invalid, expired, or missing the sub claim.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: Optional[str] = payload.get("sub")
        return username
    except jwt.InvalidTokenError:
        return None


# --- API Key helpers ---

_API_KEY_PREFIX_LEN = 8
_API_KEY_MAX_LEN = 128


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        (raw_key, prefix, hashed_key) — raw_key is shown once to the caller
        and must never be stored. prefix is the first 8 URL-safe chars.
    """
    raw = secrets.token_urlsafe(32)
    prefix = raw[:_API_KEY_PREFIX_LEN]
    hashed = password_hash.hash(raw)
    return raw, prefix, hashed


def validate_api_key(session: Session, raw_key: str) -> Optional[ApiKey]:
    """Look up an active ApiKey by verifying raw_key against stored hashes.

    Uses key_prefix to narrow the candidate set (typically 1 row) before
    running the expensive Argon2 verification.

    Performs a constant-time dummy Argon2 verify when no prefix candidates
    exist to prevent prefix enumeration via timing side-channel (OWASP A07).

    Returns the ApiKey on success, or None if invalid or inactive.
    """
    if len(raw_key) < _API_KEY_PREFIX_LEN or len(raw_key) > _API_KEY_MAX_LEN:
        return None
    prefix = raw_key[:_API_KEY_PREFIX_LEN]
    candidates = session.exec(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active.is_(True))
    ).all()
    if not candidates:
        # Constant-time dummy verify to prevent prefix enumeration via timing.
        password_hash.verify(raw_key, DUMMY_HASH)
        logger.warning("API key auth failed: no active key with prefix %s", prefix)
        return None
    for key in candidates:
        if password_hash.verify(raw_key, key.key_hash):
            return key
    logger.warning("API key auth failed: hash mismatch for prefix %s", prefix)
    return None


def check_and_increment_rate_limit(session: Session, api_key: ApiKey) -> bool:
    """Check rate limit and increment counter atomically via SELECT FOR UPDATE.

    Implements a fixed-window rate limiter: the counter resets each time the
    60-second window expires. This means a burst of up to 2N requests in ~2s
    is possible at a window boundary — acceptable for a research API.

    Returns True if the request is allowed, False if the rate limit is exceeded.
    A rate_limit_per_minute of 0 means unlimited.
    """
    now = datetime.now(timezone.utc)
    # Re-read with a row lock, re-checking is_active in case of concurrent revocation.
    locked_key = session.exec(
        select(ApiKey)
        .where(ApiKey.id == api_key.id, ApiKey.is_active.is_(True))
        .with_for_update()
    ).first()
    if locked_key is None:
        # Key was revoked concurrently between validate_api_key and here.
        return False

    if locked_key.rate_limit_per_minute == 0:
        # Still update last_used_at for unlimited keys
        locked_key.last_used_at = now
        session.add(locked_key)
        session.commit()
        return True
    window_start = locked_key.rate_window_start
    # SQLite strips timezone info on round-trip; normalize to UTC if naive.
    if window_start is not None and window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=timezone.utc)
    window_expired = window_start is None or (now - window_start).total_seconds() >= 60

    if window_expired:
        locked_key.rate_window_start = now
        locked_key.rate_window_count = 1
    else:
        if locked_key.rate_window_count >= locked_key.rate_limit_per_minute:
            session.rollback()
            logger.warning(
                "Rate limit exceeded for api_key id=%s (limit=%s/min)",
                locked_key.id,
                locked_key.rate_limit_per_minute,
            )
            return False
        locked_key.rate_window_count += 1

    locked_key.last_used_at = now
    session.add(locked_key)
    session.commit()
    return True


# --- MCP service account provisioning ---

MCP_SERVICE_USERNAME = "mcp-service"


def ensure_mcp_service_key(session: Session, raw_key: str) -> None:
    """Idempotently provision the dedicated mcp-service ApiUser and its ApiKey.

    Called at startup when API_MCP_API_KEY is set. Safe to call on every boot
    and from multiple concurrent instances: duplicate inserts are caught via
    the unique constraints on ApiUser.username and ApiKey.key_hash.

    The mcp-service ApiUser exists only to satisfy ApiKey.api_user_id's NOT
    NULL foreign key; its password is a random value that is never surfaced
    or used for login.
    """
    user = session.exec(select(ApiUser).where(ApiUser.username == MCP_SERVICE_USERNAME)).first()
    if user is None:
        user = ApiUser(
            username=MCP_SERVICE_USERNAME,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            is_admin=False,
            disabled=False,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            # Lost a race with another instance provisioning the same user.
            logger.info("IntegrityError provisioning mcp-service user; re-querying to find winner")
            session.rollback()
        user = session.exec(select(ApiUser).where(ApiUser.username == MCP_SERVICE_USERNAME)).first()
        if user is None:
            raise RuntimeError("failed to provision or find mcp-service user after IntegrityError")

    prefix = raw_key[:_API_KEY_PREFIX_LEN]
    existing = session.exec(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active.is_(True))
    ).first()
    if existing is not None:
        return

    api_key = ApiKey(
        api_user_id=user.id,
        name="mcp-service-key",
        key_prefix=prefix,
        key_hash=password_hash.hash(raw_key),
        is_active=True,
        rate_limit_per_minute=60,
    )
    session.add(api_key)
    try:
        session.commit()
    except IntegrityError:
        # Lost a race with another instance provisioning the same key.
        logger.info("IntegrityError provisioning mcp-service key with prefix %s; another instance won the race", prefix)
        session.rollback()
