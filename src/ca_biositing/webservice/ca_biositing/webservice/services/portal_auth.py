"""Isolated BioCirV Portal authentication and 2-role RBAC service.

Provides Google OIDC ID token verification, domain/email allowlist checks,
2-role resolution (`analyst` vs. `admin`), and HTTP-only JWT cookie handling
using the `biocirv_portal_token` cookie.

100% isolated from CalBioScape's `access_token` cookie and `dependencies.py`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

from fastapi import Depends, HTTPException, Request, Response, status
import jwt
from pydantic import BaseModel

from ca_biositing.webservice.config import WebServiceConfig, config

try:
    from google.auth.transport import requests as google_auth_requests
    from google.oauth2 import id_token as google_id_token
    from google.oauth2.id_token import verify_oauth2_token
except ImportError:  # pragma: no cover
    google_auth_requests = None  # type: ignore[assignment]
    google_id_token = None  # type: ignore[assignment]

    def verify_oauth2_token(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ValueError("google-auth is not installed")


_ORIG_VERIFY_OAUTH2_TOKEN = verify_oauth2_token

PORTAL_COOKIE_NAME = "biocirv_portal_token"


class PortalUser(BaseModel):
    """Authenticated BioCirV portal user identity and resolved role."""

    sub: str = ""
    email: str
    name: str = ""
    role: str = "analyst"
    auth_mode: str = "cookie"

    def model_post_init(self, __context: Any) -> None:
        if not self.sub:
            self.sub = self.email
        if not self.name and self.email:
            self.name = self.email.split("@", 1)[0]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def is_email_allowed(
    email: str,
    current_config: Optional[WebServiceConfig] = None,
) -> bool:
    """Return True if `email` matches the configured domain or email allowlists."""
    cfg = current_config or config
    norm_email = _normalize_email(email)
    if not norm_email or "@" not in norm_email:
        return False

    domain = norm_email.split("@", 1)[1].strip().lower()
    allowed_domains = {
        d.strip().lower().lstrip("@")
        for d in cfg.dashboard_allowed_domains
        if d and d.strip()
    }
    allowed_emails = {
        _normalize_email(e) for e in cfg.dashboard_allowed_emails if e and e.strip()
    }
    admin_emails = {
        _normalize_email(e) for e in cfg.dashboard_admin_emails if e and e.strip()
    }

    return (
        norm_email in admin_emails
        or norm_email in allowed_emails
        or domain in allowed_domains
    )


def resolve_portal_role(
    email: str,
    current_config: Optional[WebServiceConfig] = None,
) -> str:
    """Resolve the 2-tier portal role (`admin` or `analyst`) for an allowed email."""
    cfg = current_config or config
    norm_email = _normalize_email(email)
    admin_emails = {
        _normalize_email(e) for e in cfg.dashboard_admin_emails if e and e.strip()
    }
    if norm_email in admin_emails:
        return "admin"
    return "analyst"


def authorize_portal_email(
    email: str,
    name: Optional[str] = None,
    current_config: Optional[WebServiceConfig] = None,
    auth_mode: str = "google_oidc",
) -> PortalUser:
    """Validate `email` against the allowlist and return a `PortalUser`.

    Raises:
        HTTPException(403): If the email is not in `dashboard_allowed_domains`,
            `dashboard_allowed_emails`, or `dashboard_admin_emails`.
    """
    cfg = current_config or config
    norm_email = _normalize_email(email)
    if not is_email_allowed(norm_email, current_config=cfg):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email '{norm_email or email}' is not authorized to access BioCirV dashboards.",
        )

    role = resolve_portal_role(norm_email, current_config=cfg)
    display_name = (name or "").strip() or norm_email.split("@", 1)[0]
    return PortalUser(
        sub=norm_email,
        email=norm_email,
        name=display_name,
        role=role,
        auth_mode=auth_mode,
    )


def verify_google_id_token(
    credential: str,
    current_config: Optional[WebServiceConfig] = None,
) -> dict[str, Any]:
    """Verify a Google OIDC ID token and return its claims dictionary.

    Raises:
        HTTPException(401): If the token cannot be verified or lacks a verified email.
    """
    cfg = current_config or config
    if not credential or not credential.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Google ID token",
        )

    verifier = (
        verify_oauth2_token
        if verify_oauth2_token is not _ORIG_VERIFY_OAUTH2_TOKEN
        else (
            google_id_token.verify_oauth2_token
            if google_id_token is not None
            else verify_oauth2_token
        )
    )
    req_adapter = (
        google_auth_requests.Request() if google_auth_requests is not None else None
    )
    audience = cfg.google_client_id or None

    try:
        id_info = verifier(credential, req_adapter, audience)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {exc}",
        ) from exc

    if not isinstance(id_info, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token payload",
        )

    if id_info.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified",
        )

    email = _normalize_email(id_info.get("email"))
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token missing email claim",
        )

    return id_info


def create_portal_token(
    user: PortalUser,
    expires_delta: Optional[timedelta] = None,
    current_config: Optional[WebServiceConfig] = None,
) -> str:
    """Create a signed HTTP-only JWT for the BioCirV portal session."""
    cfg = current_config or config
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=cfg.jwt_expire_minutes)
    )
    payload = {
        "sub": user.email,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "token_use": "biocirv_portal",
        "exp": expire,
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def decode_portal_token(
    token: str,
    current_config: Optional[WebServiceConfig] = None,
) -> Optional[PortalUser]:
    """Decode and validate a `biocirv_portal_token` JWT.

    Returns None if the token is invalid, expired, or not a BioCirV portal token
    (e.g., a CalBioScape `access_token` lacking portal email/role claims).
    """
    cfg = current_config or config
    try:
        payload = jwt.decode(
            token,
            cfg.jwt_secret_key,
            algorithms=[cfg.jwt_algorithm],
        )
    except jwt.InvalidTokenError:
        return None

    email = _normalize_email(payload.get("email") or payload.get("sub"))
    role = payload.get("role")
    # Reject tokens that do not carry portal email + valid role (prevents collision with CalBioScape access_token)
    if not email or "@" not in email or role not in {"analyst", "admin"}:
        return None

    if not is_email_allowed(email, current_config=cfg):
        return None

    resolved_role = resolve_portal_role(email, current_config=cfg)
    name = (payload.get("name") or "").strip() or email.split("@", 1)[0]
    return PortalUser(
        sub=email,
        email=email,
        name=name,
        role=resolved_role,
    )


def set_portal_auth_cookie(
    response: Response,
    token: str,
    current_config: Optional[WebServiceConfig] = None,
) -> None:
    """Set the isolated `biocirv_portal_token` HTTP-only cookie on `response`."""
    cfg = current_config or config
    response.set_cookie(
        key=PORTAL_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=cfg.jwt_cookie_secure,
        max_age=cfg.jwt_expire_minutes * 60,
        path="/",
    )


def clear_portal_auth_cookie(
    response: Response,
    current_config: Optional[WebServiceConfig] = None,
) -> None:
    """Clear the `biocirv_portal_token` cookie on `response`."""
    cfg = current_config or config
    response.delete_cookie(
        key=PORTAL_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=cfg.jwt_cookie_secure,
        path="/",
    )


def get_optional_portal_user(request: Request) -> Optional[PortalUser]:
    """Resolve the current BioCirV portal user if authenticated, or None.

    Resolution order:
    1. `biocirv_portal_token` HTTP-only cookie
    2. Trusted `X-Auth-Request-Email` header (when behind `oauth2-proxy`)
    3. `Authorization: Bearer <portal_jwt>` if valid portal JWT

    Note: Never reads CalBioScape's `access_token` cookie.
    """
    # 1. Check isolated portal cookie
    cookie_token = request.cookies.get(PORTAL_COOKIE_NAME)
    if cookie_token:
        user = decode_portal_token(cookie_token)
        if user is not None:
            return user

    # 2. Check trusted oauth2-proxy header
    proxy_email = request.headers.get("X-Auth-Request-Email")
    if proxy_email and proxy_email.strip():
        proxy_name = request.headers.get("X-Auth-Request-User")
        return authorize_portal_email(
            proxy_email, name=proxy_name, auth_mode="oauth2_proxy"
        )

    # 3. Check Authorization Bearer header if a portal JWT was sent directly
    auth_header = request.headers.get("Authorization") or ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()
        if bearer_token:
            user = decode_portal_token(bearer_token)
            if user is not None:
                user.auth_mode = "bearer"
                return user

    # 4. If dashboard auth is explicitly disabled in config, return a local dev analyst
    if not config.require_dashboard_auth:
        return PortalUser(
            sub="dev@lbl.gov",
            email="dev@lbl.gov",
            name="dev",
            role="analyst",
            auth_mode="disabled",
        )

    return None


def require_portal_analyst(request: Request) -> PortalUser:
    """FastAPI dependency requiring `analyst` or `admin` portal authentication.

    Raises:
        HTTPException(401): If unauthenticated.
        HTTPException(403): If authenticated email is not allowlisted.
    """
    user = get_optional_portal_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="BioCirV portal authentication required",
        )
    if user.role not in {"analyst", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or Admin role required",
        )
    return user


def require_portal_admin(request: Request) -> PortalUser:
    """FastAPI dependency requiring `admin` portal authentication.

    Raises:
        HTTPException(401): If unauthenticated.
        HTTPException(403): If authenticated user has `analyst` role instead of `admin`.
    """
    user = require_portal_analyst(request)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation",
        )
    return user


OptionalPortalUserDep = Annotated[
    Optional[PortalUser], Depends(get_optional_portal_user)
]
PortalAnalystDep = Annotated[PortalUser, Depends(require_portal_analyst)]
PortalAdminDep = Annotated[PortalUser, Depends(require_portal_admin)]
