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
from ca_biositing.webservice.v1 import router as v1_router

logger = logging.getLogger(__name__)

# Warn if the JWT secret key is the insecure default
if config.jwt_secret_key == "changeme-only-for-local-dev-do-not-use-in-prod!!":
    logger.warning(
        "API_JWT_SECRET_KEY is set to the insecure default. "
        "Set a strong random secret in production via GCP Secret Manager."
    )

# Initialize MCP server
session_factory = sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)
mcp, _tools = build_mcp_server(session_factory, config)
mcp_app = mcp.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for the FastAPI application.

    Drives the MCP session manager.
    """
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

# Mount MCP server
app.mount("/mcp", mcp_app)
