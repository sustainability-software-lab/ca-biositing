"""Authentication endpoints: login, register, refresh, logout."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ca_biositing.datamodels.models import ApiKey, ApiUser
from ca_biositing.webservice.config import config
from ca_biositing.webservice.dependencies import AdminUserDep, JWTCurrentUserDep, SessionDep
from ca_biositing.webservice.services.auth_service import (
    authenticate_user,
    create_access_token,
    generate_api_key,
    get_password_hash,
)
from ca_biositing.webservice.v1.auth.schemas import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
    Token,
    UserCreate,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def _set_access_cookie(response: Response, token: str, secure: bool) -> None:
    """Set the HTTP-only access_token cookie on the response."""
    max_age = config.jwt_expire_minutes * 60
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: SessionDep = ...,
    response: Response = ...,
) -> Token:
    """Authenticate with username/password and receive a JWT access token.

    Also sets an HTTP-only `access_token` cookie for browser SPA clients.
    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise _CREDENTIALS_ERROR

    expires = timedelta(minutes=config.jwt_expire_minutes)
    token = create_access_token(
        {"sub": user.username},
        config.jwt_secret_key,
        config.jwt_algorithm,
        expires,
    )
    _set_access_cookie(response, token, config.jwt_cookie_secure)
    return Token(access_token=token, token_type="bearer")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_create: UserCreate,
    session: SessionDep,
    _admin: AdminUserDep,
) -> UserResponse:
    """Create a new API user. Requires admin privileges."""
    existing = session.exec(
        select(ApiUser).where(ApiUser.username == user_create.username)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_create.username}' already exists",
        )

    new_user = ApiUser(
        username=user_create.username,
        hashed_password=get_password_hash(user_create.password),
        email=user_create.email,
        full_name=user_create.full_name,
        is_admin=user_create.is_admin,
        disabled=False,
    )
    session.add(new_user)
    try:
        session.commit()
        session.refresh(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_create.username}' already exists",
        )

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_admin=new_user.is_admin,
        disabled=new_user.disabled,
    )


@router.post("/refresh", response_model=Token)
def refresh(
    current_user: JWTCurrentUserDep,
    response: Response,
) -> Token:
    """Issue a new access token for the currently authenticated user.

    Requires a valid (non-expired) token via Bearer header or cookie.
    X-API-Key is not accepted, so an API key can never be exchanged for a JWT.
    Also updates the HTTP-only cookie with the new token.
    """
    expires = timedelta(minutes=config.jwt_expire_minutes)
    token = create_access_token(
        {"sub": current_user.username},
        config.jwt_secret_key,
        config.jwt_algorithm,
        expires,
    )
    _set_access_cookie(response, token, config.jwt_cookie_secure)
    return Token(access_token=token, token_type="bearer")


@router.post("/logout")
def logout(response: Response) -> dict:
    """Clear the access_token cookie, effectively logging out browser clients.

    Note: the JWT itself remains valid until expiry. Bearer-token clients should
    discard the token client-side. Only the HTTP-only cookie is cleared here.
    """
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logged out"}


# --- API Key management (admin-only, JWT auth required) ---


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    key_create: ApiKeyCreate,
    session: SessionDep,
    _admin: AdminUserDep,
) -> ApiKeyCreateResponse:
    """Create a new per-client API key. Requires admin JWT authentication.

    The raw key is returned exactly once in this response and is never stored.
    Store it securely (e.g. GCP Secret Manager) immediately.
    """
    owner = session.exec(select(ApiUser).where(ApiUser.id == key_create.api_user_id)).first()
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ApiUser {key_create.api_user_id} not found",
        )

    raw_key, prefix, hashed = generate_api_key()
    new_key = ApiKey(
        api_user_id=key_create.api_user_id,
        name=key_create.name,
        key_prefix=prefix,
        key_hash=hashed,
        rate_limit_per_minute=key_create.rate_limit_per_minute,
    )
    session.add(new_key)
    session.commit()
    session.refresh(new_key)

    logger.info(
        "API key created: id=%s name=%r api_user_id=%s",
        new_key.id,
        new_key.name,
        new_key.api_user_id,
    )

    return ApiKeyCreateResponse(
        id=new_key.id,
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        raw_key=raw_key,
        rate_limit_per_minute=new_key.rate_limit_per_minute,
        created_at=new_key.created_at,
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    session: SessionDep,
    _admin: AdminUserDep,
    api_user_id: Optional[int] = Query(default=None, description="Filter by owner user ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum keys to return"),
    offset: int = Query(default=0, ge=0, description="Number of keys to skip"),
) -> List[ApiKeyResponse]:
    """List API keys. Requires admin JWT authentication.

    Returns prefix and metadata only — never the hash or raw key.
    Supports optional filtering by api_user_id and pagination via limit/offset.
    """
    stmt = select(ApiKey)
    if api_user_id is not None:
        stmt = stmt.where(ApiKey.api_user_id == api_user_id)
    keys = session.exec(stmt.offset(offset).limit(limit)).all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            api_user_id=k.api_user_id,
            is_active=k.is_active,
            rate_limit_per_minute=k.rate_limit_per_minute,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    session: SessionDep,
    _admin: AdminUserDep,
) -> dict:
    """Soft-deactivate an API key (sets is_active=False). Requires admin JWT.

    The key row is retained for audit purposes but rejected on all subsequent
    authentication attempts. Deactivation is permanent via this API — to restore
    access, issue a new key.
    """
    key = session.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    key.is_active = False
    session.add(key)
    session.commit()
    logger.info("API key revoked: id=%s name=%r", key.id, key.name)
    return {"message": "API key revoked"}


@router.patch("/api-keys/{key_id}", response_model=ApiKeyResponse)
def update_api_key(
    key_id: int,
    update: ApiKeyUpdate,
    session: SessionDep,
    _admin: AdminUserDep,
) -> ApiKeyResponse:
    """Update a key's name or rate limit. Requires admin JWT authentication.

    Only ``name`` and ``rate_limit_per_minute`` are accepted; any other field
    (e.g. ``is_active``) returns 422. To deactivate a key, use DELETE.
    """
    key = session.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if update.name is not None:
        key.name = update.name
    if update.rate_limit_per_minute is not None:
        key.rate_limit_per_minute = update.rate_limit_per_minute
    session.add(key)
    session.commit()
    session.refresh(key)
    return ApiKeyResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        api_user_id=key.api_user_id,
        is_active=key.is_active,
        rate_limit_per_minute=key.rate_limit_per_minute,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )
