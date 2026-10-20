"""Seed CSV and database synchronization helpers for QC Review Decisions.

Provides deterministic CSV round-trip (`load_seed_csv_to_db`,
`export_db_decisions_to_seed_csv`), idempotent `[QC_AUDIT id=<id> ...]` note
formatting (`format_qc_audit_note`), and Stage 1 database application
(`apply_qc_decision_to_db`) for `QcReviewDecision` rows.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Type

from sqlmodel import Session, select

from ca_biositing.datamodels.models import (
    CalorimetryRecord,
    CompositionalRecord,
    FermentationRecord,
    GasificationRecord,
    IcpRecord,
    PretreatmentRecord,
    ProximateRecord,
    QcReviewDecision,
    UltimateRecord,
    XrdRecord,
    XrfRecord,
)


DEFAULT_SEED_CSV_PATH = (
    Path(__file__).resolve().parents[6]
    / "data"
    / "qc"
    / "qc_review_decisions_seed.csv"
)

SEED_CSV_COLUMNS: List[str] = [
    "id",
    "record_table",
    "record_id",
    "replicate_group_key",
    "resource_name",
    "analysis_type",
    "parameter_name",
    "flag_type",
    "flag_trigger_value",
    "old_qc_pass",
    "new_qc_pass",
    "decision_status",
    "decision_action",
    "rationale_chips",
    "review_note",
    "submitted_by_email",
    "assigned_to_email",
    "resolved_by_email",
    "resolved_at",
    "synced_to_gsheet",
    "gsheet_synced_at",
    "gsheet_writeback_target",
    "created_at",
    "updated_at",
]

RECORD_TABLE_TO_MODEL: Dict[str, Type[Any]] = {
    "calorimetry_record": CalorimetryRecord,
    "compositional_record": CompositionalRecord,
    "fermentation_record": FermentationRecord,
    "gasification_record": GasificationRecord,
    "icp_record": IcpRecord,
    "pretreatment_record": PretreatmentRecord,
    "proximate_record": ProximateRecord,
    "ultimate_record": UltimateRecord,
    "xrd_record": XrdRecord,
    "xrf_record": XrfRecord,
}


def resolve_seed_csv_path(csv_path: Optional[Path | str] = None) -> Path:
    """Resolve the active seed CSV path, honoring optional argument or env override."""
    if csv_path is not None:
        return Path(csv_path)
    env_override = os.environ.get("BIOSITING_QC_SEED_CSV_PATH")
    if env_override:
        return Path(env_override)
    return DEFAULT_SEED_CSV_PATH


def _parse_iso_dt(val: Optional[str | datetime]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string into a timezone-aware UTC datetime."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val
    text = str(val).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _format_iso_dt(val: Optional[datetime | str]) -> str:
    """Format a datetime or ISO string for deterministic CSV serialization."""
    if val is None or val == "":
        return ""
    if isinstance(val, str):
        return val.strip()
    if val.tzinfo is None:
        val = val.replace(tzinfo=timezone.utc)
    return val.isoformat()


def _parse_bool(val: Any) -> bool:
    """Parse a boolean value from CSV or Python representation."""
    if isinstance(val, bool):
        return val
    return str(val or "").strip().lower() in {"true", "1", "yes", "y"}


def format_qc_audit_note(
    existing_note: Optional[str],
    decision_id: int | str,
    action: str,
    new_qc_pass: Optional[str],
    reviewer_email: str,
    review_note: str,
    resolved_at_iso: str,
) -> str:
    """Format or idempotently replace a `[QC_AUDIT id=<decision_id> ...]` stamp in `existing_note`.

    If a `[QC_AUDIT id=<decision_id> ...]` block already exists in `existing_note`,
    it is replaced in-place via regex so repeated Stage 1 or Stage 2 calls never
    produce duplicate audit tags. Otherwise, the block is appended cleanly.
    """
    clean_note = str(review_note or "").replace('"', "'").replace("\n", " ").strip()
    qc_val = str(new_qc_pass or "unchanged").strip()
    act_val = str(action or "review").strip()
    rev_val = str(reviewer_email or "analyst").strip()
    ts_val = str(resolved_at_iso or "").strip()

    stamp = (
        f'[QC_AUDIT id={decision_id} action={act_val} qc_pass={qc_val} '
        f'by={rev_val} at={ts_val} note="{clean_note}"]'
    )
    pattern = re.compile(r"\[QC_AUDIT\s+id=" + re.escape(str(decision_id)) + r"\b[^\]]*\]")

    base = str(existing_note or "").strip()
    if not base:
        return stamp
    if pattern.search(base):
        return pattern.sub(lambda _: stamp, base)
    return f"{base} | {stamp}"


def apply_qc_decision_to_db(session: Session, decision: QcReviewDecision) -> bool:
    """Apply a `QcReviewDecision` to its target analytical record in PostgreSQL/SQLite.

    Updates `qc_pass` (when `decision.new_qc_pass` is `"pass"` or `"fail"`) and
    idempotently stamps `note` with `[QC_AUDIT id=<decision_id> ...]`.
    """
    model_cls = RECORD_TABLE_TO_MODEL.get(str(decision.record_table or "").strip())
    if model_cls is None:
        return False

    record = session.exec(
        select(model_cls).where(model_cls.record_id == decision.record_id)
    ).first()
    if record is None:
        return False

    normalized_qc = str(decision.new_qc_pass or "").strip().lower()
    if normalized_qc in {"pass", "fail"}:
        record.qc_pass = normalized_qc

    decision_identifier: int | str = (
        decision.id
        if decision.id is not None
        else f"{decision.record_table}:{decision.record_id}"
    )
    resolved_iso = _format_iso_dt(
        decision.resolved_at or decision.updated_at or datetime.now(timezone.utc)
    )
    reviewer = decision.resolved_by_email or decision.submitted_by_email or "analyst"
    action = decision.decision_action or decision.decision_status or "review"

    record.note = format_qc_audit_note(
        existing_note=getattr(record, "note", None),
        decision_id=decision_identifier,
        action=action,
        new_qc_pass=decision.new_qc_pass,
        reviewer_email=reviewer,
        review_note=decision.review_note,
        resolved_at_iso=resolved_iso,
    )
    if hasattr(record, "updated_at"):
        record.updated_at = datetime.now(timezone.utc)

    session.add(record)
    session.flush()
    return True


def read_seed_csv(csv_path: Optional[Path | str] = None) -> List[Dict[str, str]]:
    """Read all rows from the QC review decisions seed CSV."""
    path = resolve_seed_csv_path(csv_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if row.get("record_table") and row.get("record_id")]


def load_seed_csv_to_db(
    session: Session,
    csv_path: Optional[Path | str] = None,
    apply_record_overrides: bool = True,
) -> List[QcReviewDecision]:
    """Load `qc_review_decisions_seed.csv` into `qc_review_decision` and apply record overrides."""
    rows = read_seed_csv(csv_path)
    loaded: List[QcReviewDecision] = []
    now = datetime.now(timezone.utc)

    for row in rows:
        rec_table = str(row.get("record_table") or "").strip()
        rec_id = str(row.get("record_id") or "").strip()
        flag_type = str(row.get("flag_type") or "analyst_flagged").strip() or "analyst_flagged"
        if not rec_table or not rec_id:
            continue

        existing: Optional[QcReviewDecision] = None
        raw_id = str(row.get("id") or "").strip()
        if raw_id.isdigit():
            existing = session.get(QcReviewDecision, int(raw_id))

        if existing is None:
            existing = session.exec(
                select(QcReviewDecision).where(
                    QcReviewDecision.record_table == rec_table,
                    QcReviewDecision.record_id == rec_id,
                    QcReviewDecision.flag_type == flag_type,
                )
            ).first()

        resolved_at = _parse_iso_dt(row.get("resolved_at"))
        gsheet_synced_at = _parse_iso_dt(row.get("gsheet_synced_at"))
        created_at = _parse_iso_dt(row.get("created_at")) or now
        updated_at = _parse_iso_dt(row.get("updated_at")) or now
        synced_bool = _parse_bool(row.get("synced_to_gsheet"))

        if existing is None:
            existing = QcReviewDecision(
                record_table=rec_table,
                record_id=rec_id,
                replicate_group_key=row.get("replicate_group_key") or None,
                resource_name=str(row.get("resource_name") or ""),
                analysis_type=row.get("analysis_type") or None,
                parameter_name=row.get("parameter_name") or None,
                flag_type=flag_type,
                flag_trigger_value=row.get("flag_trigger_value") or None,
                old_qc_pass=row.get("old_qc_pass") or None,
                new_qc_pass=row.get("new_qc_pass") or None,
                decision_status=str(row.get("decision_status") or "open"),
                decision_action=row.get("decision_action") or None,
                rationale_chips=row.get("rationale_chips") or None,
                review_note=str(row.get("review_note") or ""),
                submitted_by_email=str(row.get("submitted_by_email") or ""),
                assigned_to_email=row.get("assigned_to_email") or None,
                resolved_by_email=row.get("resolved_by_email") or None,
                resolved_at=resolved_at,
                synced_to_gsheet=synced_bool,
                gsheet_synced_at=gsheet_synced_at,
                gsheet_writeback_target=row.get("gsheet_writeback_target") or None,
                created_at=created_at,
                updated_at=updated_at,
            )
            if raw_id.isdigit():
                existing.id = int(raw_id)
        else:
            existing.replicate_group_key = (
                row.get("replicate_group_key") or existing.replicate_group_key
            )
            existing.resource_name = str(row.get("resource_name") or existing.resource_name)
            existing.analysis_type = row.get("analysis_type") or existing.analysis_type
            existing.parameter_name = row.get("parameter_name") or existing.parameter_name
            existing.flag_trigger_value = (
                row.get("flag_trigger_value") or existing.flag_trigger_value
            )
            existing.old_qc_pass = row.get("old_qc_pass") or existing.old_qc_pass
            existing.new_qc_pass = row.get("new_qc_pass") or existing.new_qc_pass
            existing.decision_status = str(
                row.get("decision_status") or existing.decision_status
            )
            existing.decision_action = row.get("decision_action") or existing.decision_action
            existing.rationale_chips = row.get("rationale_chips") or existing.rationale_chips
            existing.review_note = str(row.get("review_note") or existing.review_note)
            existing.submitted_by_email = str(
                row.get("submitted_by_email") or existing.submitted_by_email
            )
            existing.assigned_to_email = (
                row.get("assigned_to_email") or existing.assigned_to_email
            )
            existing.resolved_by_email = (
                row.get("resolved_by_email") or existing.resolved_by_email
            )
            existing.resolved_at = resolved_at or existing.resolved_at
            existing.synced_to_gsheet = synced_bool
            existing.gsheet_synced_at = gsheet_synced_at or existing.gsheet_synced_at
            existing.gsheet_writeback_target = (
                row.get("gsheet_writeback_target") or existing.gsheet_writeback_target
            )
            existing.updated_at = updated_at

        session.add(existing)
        session.flush()

        if apply_record_overrides and existing.new_qc_pass:
            apply_qc_decision_to_db(session, existing)

        loaded.append(existing)

    session.commit()
    return loaded


def export_db_decisions_to_seed_csv(
    session: Session,
    csv_path: Optional[Path | str] = None,
) -> int:
    """Export all `QcReviewDecision` rows from `session` into `qc_review_decisions_seed.csv`."""
    path = resolve_seed_csv_path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    decisions = list(
        session.exec(
            select(QcReviewDecision).order_by(
                QcReviewDecision.record_table,
                QcReviewDecision.record_id,
                QcReviewDecision.id,
            )
        ).all()
    )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_CSV_COLUMNS)
        writer.writeheader()
        for item in decisions:
            writer.writerow(
                {
                    "id": str(item.id or ""),
                    "record_table": item.record_table or "",
                    "record_id": item.record_id or "",
                    "replicate_group_key": item.replicate_group_key or "",
                    "resource_name": item.resource_name or "",
                    "analysis_type": item.analysis_type or "",
                    "parameter_name": item.parameter_name or "",
                    "flag_type": item.flag_type or "analyst_flagged",
                    "flag_trigger_value": item.flag_trigger_value or "",
                    "old_qc_pass": item.old_qc_pass or "",
                    "new_qc_pass": item.new_qc_pass or "",
                    "decision_status": item.decision_status or "open",
                    "decision_action": item.decision_action or "",
                    "rationale_chips": item.rationale_chips or "",
                    "review_note": item.review_note or "",
                    "submitted_by_email": item.submitted_by_email or "",
                    "assigned_to_email": item.assigned_to_email or "",
                    "resolved_by_email": item.resolved_by_email or "",
                    "resolved_at": _format_iso_dt(item.resolved_at),
                    "synced_to_gsheet": "true" if item.synced_to_gsheet else "false",
                    "gsheet_synced_at": _format_iso_dt(item.gsheet_synced_at),
                    "gsheet_writeback_target": item.gsheet_writeback_target or "",
                    "created_at": _format_iso_dt(item.created_at),
                    "updated_at": _format_iso_dt(item.updated_at),
                }
            )

    return len(decisions)


def main() -> int:
    """CLI entrypoint for seeding or exporting `qc_review_decisions_seed.csv`."""
    parser = argparse.ArgumentParser(
        description="Seed or export QC review decisions between PostgreSQL and data/qc/qc_review_decisions_seed.csv."
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export database qc_review_decision rows to data/qc/qc_review_decisions_seed.csv.",
    )
    parser.add_argument(
        "--csv-path",
        default=None,
        help="Optional override path for qc_review_decisions_seed.csv.",
    )
    parser.add_argument(
        "--no-record-overrides",
        action="store_true",
        help="Skip applying resolved qc_pass/note overrides to analytical record tables.",
    )
    args = parser.parse_args()

    from ca_biositing.pipeline.utils.engine import get_engine

    engine = get_engine()
    with Session(engine) as session:
        if args.export:
            count = export_db_decisions_to_seed_csv(session, csv_path=args.csv_path)
            print(f"Exported {count} QC review decisions to seed CSV.")
        else:
            decisions = load_seed_csv_to_db(
                session,
                csv_path=args.csv_path,
                apply_record_overrides=not args.no_record_overrides,
            )
            print(f"Seeded {len(decisions)} QC review decisions from seed CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
