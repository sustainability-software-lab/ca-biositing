"""ETL upsert protection helpers for unsynced Stage 1 QC review decisions.

Ensures that routine/scheduled ETL re-loads from Google Sheets do not overwrite
``qc_pass`` or ``note`` in PostgreSQL for analytical records that have an active,
unsynced Stage 1 QC decision (``synced_to_gsheet = False`` in ``qc_review_decision``).
Once an Admin runs Stage 2 Google Sheets sync (``synced_to_gsheet = True``), the
source sheet itself carries the updated ``qc_result`` and ``note`` values, so
subsequent ETL runs update all columns normally.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set

import sqlalchemy as sa
from sqlalchemy import select


PROTECTED_QC_COLUMNS: frozenset[str] = frozenset({"qc_pass", "note"})
EXCLUDED_IDENTITY_COLUMNS: frozenset[str] = frozenset({"id", "created_at", "record_id"})


def get_unsynced_qc_protected_record_ids(
    session: Any,
    record_table: Optional[str] = None,
    record_ids: Optional[Iterable[str]] = None,
    *,
    record_type: Optional[str] = None,
) -> Set[str]:
    """Return the subset of ``record_ids`` protected by an unsynced QC decision.

    Performs a single bulk query against ``qc_review_decision`` for the given
    ``record_table`` / ``record_type`` where ``synced_to_gsheet`` is ``False``.
    Gracefully returns an empty set if ``record_ids`` is empty, if the
    ``qc_review_decision`` table has not been created in an isolated test
    database, or if ``session`` is a mock.
    """
    resolved_table = record_table if record_table is not None else record_type
    normalized_table = str(resolved_table or "").strip()
    normalized_ids = sorted(
        {str(rid).strip() for rid in (record_ids or ()) if rid is not None and str(rid).strip()}
    )
    if not normalized_table or not normalized_ids or session is None:
        return set()

    try:
        from ca_biositing.datamodels.models import QcReviewDecision

        stmt = select(QcReviewDecision.record_id).where(
            QcReviewDecision.record_table == normalized_table,
            QcReviewDecision.record_id.in_(normalized_ids),
            QcReviewDecision.synced_to_gsheet.is_(False),
        )
        result = session.execute(stmt)
        rows = result.scalars().all()
        return {
            str(rid).strip()
            for rid in rows
            if isinstance(rid, str) and str(rid).strip() in normalized_ids
        }
    except Exception:
        return set()


def build_qc_aware_update_dict(
    model_cls: Any,
    stmt: Any,
    protected_record_ids: Iterable[str],
    record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the ``set_`` dictionary for ``stmt.on_conflict_do_update(...)``.

    - Excludes ``id``, ``created_at``, and ``record_id`` for all rows.
    - In per-row upsert mode (``record_id is not None``): omits ``qc_pass`` and
      ``note`` when ``str(record_id)`` is in ``protected_record_ids``.
    - In bulk upsert mode (``record_id is None``): when ``protected_record_ids``
      is non-empty, wraps ``qc_pass`` and ``note`` in a SQL ``CASE`` expression
      that preserves existing database values for protected ``record_id`` rows
      while updating unprotected rows from ``stmt.excluded``.
    """
    protected_set = {
        str(rid).strip()
        for rid in (protected_record_ids or ())
        if rid is not None and str(rid).strip()
    }
    table = model_cls.__table__

    if record_id is not None:
        is_protected = str(record_id).strip() in protected_set
        return {
            c.name: stmt.excluded[c.name]
            for c in table.columns
            if c.name not in EXCLUDED_IDENTITY_COLUMNS
            and not (is_protected and c.name in PROTECTED_QC_COLUMNS)
        }

    if not protected_set:
        return {
            c.name: stmt.excluded[c.name]
            for c in table.columns
            if c.name not in EXCLUDED_IDENTITY_COLUMNS
        }

    sorted_protected = sorted(protected_set)
    update_dict: Dict[str, Any] = {}
    for c in table.columns:
        if c.name in EXCLUDED_IDENTITY_COLUMNS:
            continue
        if c.name in PROTECTED_QC_COLUMNS and "record_id" in table.c:
            update_dict[c.name] = sa.case(
                (table.c.record_id.in_(sorted_protected), table.c[c.name]),
                else_=stmt.excluded[c.name],
            )
        else:
            update_dict[c.name] = stmt.excluded[c.name]
    return update_dict
