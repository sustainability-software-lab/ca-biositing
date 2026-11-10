"""API v1 main router.

This module aggregates all v1 endpoints into a single router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ca_biositing.webservice.dependencies import get_current_user
from ca_biositing.webservice.v1.auth.router import router as auth_router
from ca_biositing.webservice.v1.endpoints import qc_review
from ca_biositing.webservice.v1.feedstocks import router as feedstocks_router
from ca_biositing.webservice.v1.public import router as public_router

# Create the main v1 router
router = APIRouter(prefix="/v1")


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status field set to "ok".
    """
    return {"status": "ok"}


# Auth endpoints are open (login must be accessible without a token)
router.include_router(auth_router)

# Open public dataset endpoints (/v1/public) — no auth required, IP rate-limited
router.include_router(public_router)

# Data endpoints require a valid JWT
router.include_router(feedstocks_router, dependencies=[Depends(get_current_user)])

# BioCirV Portal & QC Audit Workbench endpoints (isolated portal auth)
router.include_router(qc_review.router)
