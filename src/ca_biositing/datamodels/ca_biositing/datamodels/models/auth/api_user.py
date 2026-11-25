"""ApiUser model for JWT authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class ApiUser(SQLModel, table=True):
    """API user for JWT authentication.

    Users are managed by admins and authenticate via username/password
    to receive short-lived JWTs for accessing protected endpoints.

    Intentionally inherits SQLModel directly rather than BaseEntity: BaseEntity
    adds ETL-specific fields (etl_run_id, lineage_group_id) that are not
    meaningful for an auth model, and its timestamp fields lack the
    server_default / onupdate SA kwargs required here.
    """

    __tablename__ = "api_user"
    __table_args__ = {"schema": "auth"}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(nullable=False, unique=True, index=True)
    hashed_password: str = Field(nullable=False)
    email: Optional[str] = Field(default=None)
    full_name: Optional[str] = Field(default=None)
    is_admin: bool = Field(default=False, nullable=False)
    disabled: bool = Field(default=False, nullable=False)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": sa.text("CURRENT_TIMESTAMP")},
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": sa.text("CURRENT_TIMESTAMP"), "onupdate": lambda: datetime.now(timezone.utc)},
    )
