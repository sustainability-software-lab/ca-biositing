"""FastAPI application for CA Biositing project.

This module provides the main FastAPI application with REST API endpoints.
"""

from __future__ import annotations

import logging

from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text


from ca_biositing.datamodels.database import get_engine

from ca_biositing.webservice.config import config
from ca_biositing.webservice.services.dashboard_loader import (
    load_dashboard_asset,
    sanitize_dashboard_subpath,
)
from ca_biositing.webservice.services.portal_auth import get_optional_portal_user
from ca_biositing.webservice.v1 import router as v1_router
from ca_biositing.webservice.v1.public.router import public_rate_limit

logger = logging.getLogger(__name__)

# Warn if the JWT secret key is the insecure default
if config.jwt_secret_key == "changeme-only-for-local-dev-do-not-use-in-prod!!":
    logger.warning(
        "API_JWT_SECRET_KEY is set to the insecure default. "
        "Set a strong random secret in production via GCP Secret Manager."
    )

# Create FastAPI application with metadata
app = FastAPI(
    title=config.api_title,
    description=config.api_description,
    version=config.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=config.cors_allow_methods,
    allow_headers=config.cors_allow_headers,
)


@app.middleware("http")
async def public_api_cors_middleware(request: Request, call_next) -> Response:
    """Apply open read-only CORS headers (`*`) strictly to `/v1/public` endpoints.

    Authenticated routes (`/v1/auth`, `/v1/feedstocks`, `/v1/portal`) remain
    governed by the explicit `config.cors_origins` allowlist.
    """
    path = request.url.path
    if path == "/v1/public" or path.startswith("/v1/public/"):
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
        if request.method == "OPTIONS":
            try:
                public_rate_limit(request)
            except HTTPException as exc:
                err_headers = {**cors_headers, **(exc.headers or {})}
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers=err_headers,
                )
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                headers=cors_headers,
            )
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        if "access-control-allow-credentials" in response.headers:
            del response.headers["access-control-allow-credentials"]
        return response
    return await call_next(request)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with detailed messages.

    Args:
        request: The incoming request
        exc: The validation error

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse with error message
    """
    logger.exception("Unhandled exception on %s", request.url.path)
    path = request.url.path
    if path == "/v1/public" or path.startswith("/v1/public/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc),
        },
    )


# Root endpoint
@app.get("/", tags=["root"], include_in_schema=False)
def read_root() -> RedirectResponse:
    """Redirect root to Swagger UI."""
    return RedirectResponse(url="/docs")


# Legacy hello endpoint for backward compatibility
@app.get("/hello", tags=["root"])
def read_hello() -> dict[str, str]:
    """Hello endpoint for testing.

    Returns:
        Dictionary with hello message
    """
    return {"message": "Hello, world"}


@app.get("/health", tags=["health"])
def health_check() -> JSONResponse:
    """Health check verifying database connectivity.

    Used by Cloud Run readiness probe to gate traffic routing.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "healthy", "database": "connected"})
    except Exception as e:
        return JSONResponse(
            content={"status": "unhealthy", "database": str(e)},
            status_code=503,
        )


# Mount v1 router
app.include_router(v1_router.router)


def _serve_authenticated_dashboard(request: Request, subpath: str) -> Response:
    """Serve BioCirV dashboard assets with isolated portal OIDC auth and 2-role RBAC."""
    clean_subpath = sanitize_dashboard_subpath(subpath)
    if clean_subpath == "login":
        clean_subpath = "login.html"

    if clean_subpath != "login.html":
        user = get_optional_portal_user(request)
        if user is None:
            next_path = request.url.path
            if request.url.query:
                next_path = f"{next_path}?{request.url.query}"
            encoded_next = quote(next_path, safe="/?:=&")
            return RedirectResponse(
                url=f"/v1/dashboards/login.html?next={encoded_next}",
                status_code=status.HTTP_302_FOUND,
            )

        is_admin_only = clean_subpath.startswith("audit/") or (
            clean_subpath == "db_environment_drift_dashboard.html"
        )
        if is_admin_only and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portal administrator privileges required for schema and drift audit dashboards.",
            )

    content, media_type, source = load_dashboard_asset(clean_subpath)
    return Response(
        content=content,
        media_type=media_type,
        headers={"X-Dashboard-Source": source},
    )


@app.get("/v1/dashboards", tags=["dashboards"], include_in_schema=False)
def get_dashboards_root(request: Request) -> Response:
    """Serve the BioCirV dashboards gallery landing page (`index.html`)."""
    return _serve_authenticated_dashboard(request, "index.html")


@app.get("/v1/dashboards/{subpath:path}", tags=["dashboards"])
def get_dashboard_asset(subpath: str, request: Request) -> Response:
    """Serve an authenticated BioCirV dashboard asset from local disk or GCS."""
    return _serve_authenticated_dashboard(request, subpath)


@app.get("/dashboards", tags=["dashboards"], include_in_schema=False)
def redirect_legacy_dashboards_root(request: Request) -> RedirectResponse:
    """Redirect legacy `/dashboards` root to `/v1/dashboards/index.html` (`307`)."""
    target = "/v1/dashboards/index.html"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(
        url=target,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@app.get("/dashboards/{subpath:path}", tags=["dashboards"], include_in_schema=False)
def redirect_legacy_dashboards_subpath(
    subpath: str, request: Request
) -> RedirectResponse:
    """Redirect legacy `/dashboards/{subpath:path}` to `/v1/dashboards/{subpath:path}` (`307`)."""
    clean = subpath.lstrip("/") or "index.html"
    target = f"/v1/dashboards/{clean}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(
        url=target,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
