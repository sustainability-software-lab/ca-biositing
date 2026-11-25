"""ApiKey model for per-client API key authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class ApiKey(SQLModel, table=True):
    """Per-client API key for authenticating external callers.

    Raw keys are shown exactly once at creation and never stored. Only the
    Argon2 hash is persisted. The key_prefix (first 8 chars of the raw key)
    is stored in plaintext to allow efficient lookup before hash verification.

    Rate limiting uses a DB-based fixed-window counter with SELECT FOR UPDATE
    to handle multiple Cloud Run instances without requiring Redis. The window
    resets each time 60 seconds have elapsed since rate_window_start, meaning
    a burst of up to 2N requests in ~2s is possible at a window boundary —
    acceptable for a research API.
    """

    __tablename__ = "api_key"
    __table_args__ = {"schema": "auth"}

    id: Optional[int] = Field(default=None, primary_key=True)
    api_user_id: int = Field(foreign_key="auth.api_user.id", nullable=False, index=True)
    name: str = Field(nullable=False)
    key_prefix: str = Field(nullable=False, index=True)
    key_hash: str = Field(nullable=False, unique=True)
    is_active: bool = Field(default=True, nullable=False)
    rate_limit_per_minute: int = Field(default=60, nullable=False)
    # Fixed-window rate limit state. Stored with explicit timezone=True so that
    # SQLAlchemy maps these to TIMESTAMPTZ on Postgres, matching the migration.
    rate_window_start: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )
    rate_window_count: int = Field(default=0, nullable=False)
    last_used_at: Optional[datetime] = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": sa.text("CURRENT_TIMESTAMP")},
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={
            "server_default": sa.text("CURRENT_TIMESTAMP"),
            "onupdate": lambda: datetime.now(timezone.utc),
        },
    )
