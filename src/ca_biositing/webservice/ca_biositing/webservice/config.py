"""Configuration for CA Biositing Web Service.

This module provides API-specific configuration using Pydantic Settings.
"""

from __future__ import annotations

from typing import List

from ca_biositing.webservice._version import __version__ as _pkg_version

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebServiceConfig(BaseSettings):
    """Configuration for the web service.

    Attributes:
        api_title: Title for the API
        api_description: Description for the API
        api_version: Version of the API
        cors_origins: List of allowed CORS origins
        cors_allow_credentials: Whether to allow credentials in CORS
        cors_allow_methods: Allowed HTTP methods for CORS
        cors_allow_headers: Allowed headers for CORS
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="API_",
    )

    api_title: str = "CA Biositing API"
    api_description: str = "REST API for CA Biositing bioeconomy data"
    api_version: str = _pkg_version

    # CORS configuration
    cors_origins: List[str] = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://localhost:8000",  # Local FastAPI & dashboard host
        "http://127.0.0.1:8000",  # Local FastAPI loopback
        "http://localhost:8080",  # Alternative frontend port
        "null",  # Standalone file:// dashboard origin
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # JWT authentication configuration
    # Override API_JWT_SECRET_KEY in production via GCP Secret Manager.
    # The default is a clearly-labeled dev-only value that satisfies the min_length
    # constraint; a runtime warning is emitted in main.py when it is still in use.
    jwt_secret_key: str = Field(
        default="changeme-only-for-local-dev-do-not-use-in-prod!!",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    # Defaults to False for local HTTP dev. Cloud Run must set API_JWT_COOKIE_SECURE=true.
    jwt_cookie_secure: bool = False

    # Isolated BioCirV Portal Auth, 2-Role RBAC & GCS Dashboard configuration
    google_client_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "google_client_id", "API_GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID"
        ),
    )
    dashboard_allowed_domains: list[str] = Field(
        default=["lbl.gov", "ucdavis.edu", "beamcircular.org"],
        validation_alias=AliasChoices(
            "dashboard_allowed_domains",
            "API_DASHBOARD_ALLOWED_DOMAINS",
            "DASHBOARD_ALLOWED_DOMAINS",
        ),
    )
    dashboard_allowed_emails: list[str] = Field(
        default=[],
        validation_alias=AliasChoices(
            "dashboard_allowed_emails",
            "API_DASHBOARD_ALLOWED_EMAILS",
            "DASHBOARD_ALLOWED_EMAILS",
        ),
    )
    dashboard_admin_emails: list[str] = Field(
        default=["petersmith@lbl.gov"],
        validation_alias=AliasChoices(
            "dashboard_admin_emails",
            "API_DASHBOARD_ADMIN_EMAILS",
            "DASHBOARD_ADMIN_EMAILS",
        ),
    )
    require_dashboard_auth: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "require_dashboard_auth",
            "API_REQUIRE_DASHBOARD_AUTH",
            "REQUIRE_DASHBOARD_AUTH",
        ),
    )
    dashboards_bucket_name: str = Field(
        default="",
        validation_alias=AliasChoices(
            "dashboards_bucket_name",
            "API_DASHBOARDS_BUCKET_NAME",
            "DASHBOARDS_BUCKET_NAME",
        ),
    )
    dashboards_gcs_prefix: str = Field(
        default="dashboards/staging/latest",
        validation_alias=AliasChoices(
            "dashboards_gcs_prefix",
            "API_DASHBOARDS_GCS_PREFIX",
            "DASHBOARDS_GCS_PREFIX",
        ),
    )


# Global configuration instance
config = WebServiceConfig()
settings = config
