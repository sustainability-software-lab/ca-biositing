"""FastAPI application for CA Biositing project.

This module provides the main FastAPI application with REST API endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from ca_biositing.datamodels.database import get_engine

from ca_biositing.webservice.config import config
from ca_biositing.webservice.mcp_server import build_mcp_server
from ca_biositing.webservice.middleware import MCPAuthMiddleware
from ca_biositing.webservice.services.auth_service import ensure_mcp_service_key
from ca_biositing.webservice.v1 import router as v1_router

logger = logging.getLogger(__name__)

# Fail fast if the JWT secret is still the insecure default outside local
# dev. Mirrors the API_MCP_API_KEY check below: a missing/forgotten secret
# must stop the app from starting, not silently sign tokens with a
# publicly-known key.
if config.jwt_secret_key == "changeme-only-for-local-dev-do-not-use-in-prod!!":
    if not config.dev_mode:
        raise RuntimeError(
            "API_JWT_SECRET_KEY is required when API_DEV_MODE is not set to "
            "true (the default value is insecure outside local development)."
        )
    logger.warning(
        "API_JWT_SECRET_KEY is set to the insecure default. "
        "Set a strong random secret in production via GCP Secret Manager."
    )

# Fail fast if auth is required but no MCP key was provisioned. Prevents a
# deploy that accidentally omits API_DEV_MODE=false from silently leaving
# /mcp unauthenticated, and prevents one that omits the secret from starting
# with no credential anyone could ever present.
if not config.dev_mode and not config.mcp_api_key:
    raise RuntimeError(
        "API_MCP_API_KEY is required when API_DEV_MODE is not set to true "
        "(auth is enabled by default outside local development)."
    )

# Initialize MCP server
session_factory = sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)
mcp = build_mcp_server(session_factory, config)




@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for the FastAPI application.

    Drives the MCP session manager and provisions the mcp-service API key.
    """
    if config.mcp_api_key:
        with session_factory() as session:
            ensure_mcp_service_key(session, config.mcp_api_key)

    # StreamableHTTPSessionManager.run() is required for streamable HTTP to work.
    # We ensure it's initialized by calling streamable_http_app()
    _ = mcp.streamable_http_app()
    async with mcp.session_manager.run():
        yield

# Create FastAPI application with metadata
app = FastAPI(
    title=config.api_title,
    description=config.api_description,
    version=config.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=config.cors_allow_methods,
    allow_headers=config.cors_allow_headers,
)


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
    """Health check verifying database connectivity and MCP readiness.

    Returns the server status, database connectivity, and whether the MCP server
    is ready to handle requests. Used by Cloud Run readiness probe to gate traffic
    routing.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(
            content={
                "status": "healthy",
                "db": "connected",
                "ready_for_mcp": True,
            }
        )
    except Exception as e:
        logger.warning(f"Health check: database connectivity failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "db": "disconnected",
                "ready_for_mcp": False,
            },
            status_code=503,
        )


# Mount v1 router
app.include_router(v1_router.router)

# Mount MCP server, gated by MCPAuthMiddleware (bypassed when config.dev_mode)
app.mount("/mcp", MCPAuthMiddleware(mcp.streamable_http_app(), session_factory, config))
