"""QC Review Decision model for tracking statistical and ad hoc QC findings and analyst resolutions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field

from ..base import BaseEntity


class QcReviewDecision(BaseEntity, table=True):
    """Persistent ledger of QC review findings and two-stage analyst/admin decisions.

    Stage 1 (Analyst/Admin): Immediately persists the QC decision in PostgreSQL
    and updates the analytical record's ``qc_pass`` and ``note`` fields while
    ``synced_to_gsheet`` remains ``False``.
    Stage 2 (Admin): Idempotently writes the resolved decision back to the
    source-of-truth Aim 1 / Aim 2 Google Sheets and sets ``synced_to_gsheet = True``.
    """

    __tablename__ = "qc_review_decision"

    record_table: str = Field(nullable=False, index=True)
    record_id: str = Field(nullable=False, index=True)
    replicate_group_key: Optional[str] = Field(default=None, index=True)
    resource_name: str = Field(nullable=False, index=True)
    analysis_type: Optional[str] = Field(default=None)
    parameter_name: Optional[str] = Field(default=None)
    flag_type: str = Field(default="analyst_flagged", nullable=False, index=True)
    flag_trigger_value: Optional[str] = Field(default=None)
    old_qc_pass: Optional[str] = Field(default=None)
    new_qc_pass: Optional[str] = Field(default=None)
    decision_status: str = Field(default="open", nullable=False, index=True)
    decision_action: Optional[str] = Field(default=None)
    rationale_chips: Optional[str] = Field(default=None)
    review_note: str = Field(default="", nullable=False)
    submitted_by_email: str = Field(nullable=False)
    assigned_to_email: Optional[str] = Field(default=None, index=True)
    resolved_by_email: Optional[str] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)
    synced_to_gsheet: bool = Field(default=False, nullable=False, index=True)
    gsheet_synced_at: Optional[datetime] = Field(default=None)
    gsheet_writeback_target: Optional[str] = Field(default=None)
