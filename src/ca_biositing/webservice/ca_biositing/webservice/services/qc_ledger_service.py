"""Self-contained FastAPI service for Stage 1 QC decision persistence and seed CSV mirroring.

Maintains strict package boundary isolation (`ca_biositing.webservice` -> `ca_biositing.datamodels`
only, with zero imports from `ca_biositing.pipeline`).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence, Type

from sqlmodel import Session, SQLModel, select

from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision

DEFAULT_SEED_CSV_PATH = (
    Path(__file__).resolve().parents[6]
    / "data"
    / "qc"
    / "qc_review_decisions_seed.csv"
)

SEED_CSV_COLUMNS: list[str] = [
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

ACTION_TO_QC_PASS: dict[str, str | None] = {
    "approve_pass": "pass",
    "approve": "pass",
    "keep_pass": "pass",
    "keep": "pass",
    "flip_to_pass": "pass",
    "pass": "pass",
    "trace_ignore": "pass",
    "reject_fail": "fail",
    "reject": "fail",
    "exclude_qc_fail": "fail",
    "flag_fail": "fail",
    "flip_to_fail": "fail",
    "fail": "fail",
    "needs_retest": None,
    "retest": None,
    "re_assay": None,
    "defer": None,
    "in_review": None,
    "provisional": None,
    "accept_with_note": None,
    "keep_note": None,
    "flag_for_review": None,
}

ACTION_TO_STATUS: dict[str, str] = {
    "approve_pass": "resolved",
    "approve": "resolved",
    "keep_pass": "resolved",
    "keep": "resolved",
    "flip_to_pass": "resolved",
    "pass": "resolved",
    "trace_ignore": "resolved",
    "reject_fail": "resolved",
    "reject": "resolved",
    "exclude_qc_fail": "resolved",
    "flag_fail": "resolved",
    "flip_to_fail": "resolved",
    "fail": "resolved",
    "needs_retest": "needs_retest",
    "retest": "needs_retest",
    "re_assay": "needs_retest",
    "defer": "in_review",
    "in_review": "in_review",
    "provisional": "in_review",
    "accept_with_note": "in_review",
    "keep_note": "in_review",
    "flag_for_review": "open",
    "open": "open",
}


def get_seed_csv_path(csv_path: Path | str | None = None) -> Path:
    """Resolve the active seed CSV path, using a temp file under pytest unless overridden."""
    if csv_path is not None:
        return Path(csv_path)
    env_override = os.environ.get("BIOSITING_QC_SEED_CSV_PATH", "").strip()
    if env_override:
        return Path(env_override)
    if "PYTEST_CURRENT_TEST" in os.environ:
        return (
            Path(tempfile.gettempdir())
            / "biocirv_pytest_qc_review_decisions_seed.csv"
        )
    return DEFAULT_SEED_CSV_PATH


def _format_dt(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    return str(value).strip()


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def normalize_rationale_chips(chips: Sequence[str] | str | None) -> str | None:
    """Normalize rationale chips into a comma-separated string."""
    if chips is None:
        return None
    if isinstance(chips, str):
        parts = [part.strip() for part in chips.split(",") if part.strip()]
    else:
        parts = [str(part).strip() for part in chips if str(part).strip()]
    return ", ".join(parts) if parts else None


def format_qc_audit_note(
    existing_note: str | None,
    decision_id: int | str,
    new_qc_pass: str | None,
    resolved_by_email: str,
    review_note: str,
    resolved_at: datetime | str | None = None,
    rationale_chips: Sequence[str] | str | None = None,
) -> str:
    """Format and idempotently upsert a `[QC_AUDIT id=<decision_id> ...]` tag in `existing_note`.

    If a `[QC_AUDIT id=<decision_id> ...]` block already exists in `existing_note`, it is
    replaced in-place rather than appended as a duplicate.
    """
    ts_str = _format_dt(resolved_at or datetime.now(timezone.utc))
    qc_label = (new_qc_pass or "review").strip().lower()
    chips_norm = normalize_rationale_chips(rationale_chips)
    chips_part = f" chips={chips_norm.replace(']', ')')}" if chips_norm else ""
    clean_comment = (
        str(review_note or "").strip().replace("]", ")").replace("\n", " ")
    )
    comment_part = f": {clean_comment}" if clean_comment else ""
    audit_tag = (
        f"[QC_AUDIT id={decision_id} qc={qc_label} by={resolved_by_email} "
        f"at={ts_str}{chips_part}{comment_part}]"
    )

    base = str(existing_note or "").strip()
    if not base or base.lower() in {"none", "nan", "null", "-"}:
        return audit_tag

    pattern = re.compile(
        r"\[QC_AUDIT\s+id=" + re.escape(str(decision_id)) + r"\b[^\]]*\]"
    )
    if pattern.search(base):
        return pattern.sub(lambda _: audit_tag, base)

    return f"{base} | {audit_tag}"


def get_record_model_map() -> dict[str, Type[SQLModel]]:
    """Map `record_table` and `analysis_type` identifiers to SQLModel record classes."""
    from ca_biositing.datamodels.models import (
        AutoclaveRecord,
        CalorimetryRecord,
        CompositionalRecord,
        FermentationRecord,
        FtnirRecord,
        GasificationRecord,
        IcpRecord,
        PretreatmentRecord,
        ProximateRecord,
        RgbRecord,
        UltimateRecord,
        XrdRecord,
        XrfRecord,
    )

    return {
        "proximate_record": ProximateRecord,
        "proximate": ProximateRecord,
        "proximate_analysis": ProximateRecord,
        "ultimate_record": UltimateRecord,
        "ultimate": UltimateRecord,
        "ultimate_analysis": UltimateRecord,
        "compositional_record": CompositionalRecord,
        "compositional": CompositionalRecord,
        "compositional_analysis": CompositionalRecord,
        "calorimetry_record": CalorimetryRecord,
        "calorimetry": CalorimetryRecord,
        "calorimetry_analysis": CalorimetryRecord,
        "icp_record": IcpRecord,
        "icp": IcpRecord,
        "icp_elemental_analysis": IcpRecord,
        "xrf_record": XrfRecord,
        "xrf": XrfRecord,
        "xrf_elemental_analysis": XrfRecord,
        "xrd_record": XrdRecord,
        "xrd": XrdRecord,
        "xrd_crystallinity": XrdRecord,
        "pretreatment_record": PretreatmentRecord,
        "pretreatment": PretreatmentRecord,
        "pretreatment_hydrolysis": PretreatmentRecord,
        "fermentation_record": FermentationRecord,
        "fermentation": FermentationRecord,
        "fermentation_bioconversion": FermentationRecord,
        "gasification_record": GasificationRecord,
        "gasification": GasificationRecord,
        "autoclave_record": AutoclaveRecord,
        "autoclave": AutoclaveRecord,
        "ftnir_record": FtnirRecord,
        "ftnir": FtnirRecord,
        "rgb_record": RgbRecord,
        "rgb": RgbRecord,
    }


def resolve_record_model(
    record_table: str | None,
    analysis_type: str | None = None,
) -> Type[SQLModel] | None:
    """Resolve the SQLModel record class from `record_table` or `analysis_type`."""
    model_map = get_record_model_map()
    for candidate in (record_table, analysis_type):
        if not candidate:
            continue
        norm = re.sub(r"[^a-z0-9]+", "_", str(candidate).strip().lower()).strip("_")
        if norm in model_map:
            return model_map[norm]
        if not norm.endswith("_record") and f"{norm}_record" in model_map:
            return model_map[f"{norm}_record"]
    return None


def apply_qc_decision_to_db(
    session: Session,
    decision: QcReviewDecision,
    target_record_ids: Sequence[str] | None = None,
) -> list[str]:
    """Apply a Stage 1 `QcReviewDecision` to the target analytical record row(s) in PostgreSQL.

    Returns the list of `record_id` values modified in the analytical table.
    """
    model_cls = resolve_record_model(decision.record_table, decision.analysis_type)
    if model_cls is None:
        return []

    record_id_col = getattr(model_cls, "record_id", None)
    if record_id_col is None:
        return []

    ids_to_update: list[str] = []
    if decision.record_id:
        ids_to_update.append(str(decision.record_id).strip())
    if target_record_ids:
        for rid in target_record_ids:
            clean_rid = str(rid or "").strip()
            if clean_rid and clean_rid not in ids_to_update:
                ids_to_update.append(clean_rid)

    if not ids_to_update:
        return []

    stmt = select(model_cls).where(record_id_col.in_(ids_to_update))
    records = list(session.exec(stmt).all())
    updated_ids: list[str] = []

    for rec in records:
        current_qc = getattr(rec, "qc_pass", None)
        if decision.old_qc_pass is None and current_qc is not None:
            decision.old_qc_pass = str(current_qc)

        if decision.new_qc_pass in {"pass", "fail"} and hasattr(rec, "qc_pass"):
            setattr(rec, "qc_pass", decision.new_qc_pass)

        if hasattr(rec, "note"):
            existing_note = getattr(rec, "note", None)
            new_note = format_qc_audit_note(
                existing_note=existing_note,
                decision_id=decision.id or decision.record_id,
                new_qc_pass=decision.new_qc_pass,
                resolved_by_email=decision.resolved_by_email
                or decision.submitted_by_email,
                review_note=decision.review_note,
                resolved_at=decision.resolved_at or decision.updated_at,
                rationale_chips=decision.rationale_chips,
            )
            setattr(rec, "note", new_note)

        if hasattr(rec, "updated_at"):
            setattr(rec, "updated_at", datetime.now(timezone.utc))

        session.add(rec)
        updated_ids.append(str(getattr(rec, "record_id", "")))

    return updated_ids


def serialize_decision(decision: QcReviewDecision) -> dict[str, Any]:
    """Serialize a `QcReviewDecision` SQLModel row into a JSON-compatible dictionary."""
    chips_raw = decision.rationale_chips or ""
    chips_list = [c.strip() for c in chips_raw.split(",") if c.strip()]
    return {
        "id": decision.id,
        "record_table": decision.record_table,
        "record_id": decision.record_id,
        "replicate_group_key": decision.replicate_group_key,
        "resource_name": decision.resource_name,
        "analysis_type": decision.analysis_type,
        "parameter_name": decision.parameter_name,
        "flag_type": decision.flag_type,
        "flag_trigger_value": decision.flag_trigger_value,
        "old_qc_pass": decision.old_qc_pass,
        "new_qc_pass": decision.new_qc_pass,
        "decision_status": decision.decision_status,
        "status": decision.decision_status,
        "decision_action": decision.decision_action,
        "rationale_chips": decision.rationale_chips,
        "rationale_chips_list": chips_list,
        "review_note": decision.review_note,
        "submitted_by_email": decision.submitted_by_email,
        "assigned_to_email": decision.assigned_to_email,
        "resolved_by_email": decision.resolved_by_email,
        "resolved_at": _format_dt(decision.resolved_at) or None,
        "synced_to_gsheet": bool(decision.synced_to_gsheet),
        "gsheet_synced_at": _format_dt(decision.gsheet_synced_at) or None,
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "created_at": _format_dt(decision.created_at) or None,
        "updated_at": _format_dt(decision.updated_at) or None,
    }


def read_seed_csv(csv_path: Path | str | None = None) -> list[dict[str, str]]:
    """Read all rows from the QC review decisions seed CSV."""
    target = get_seed_csv_path(csv_path)
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            dict(row)
            for row in reader
            if row.get("record_id") or row.get("decision_key")
        ]


def append_or_update_seed_csv(
    decision: QcReviewDecision,
    csv_path: Path | str | None = None,
) -> Path:
    """Upsert a `QcReviewDecision` into the seed CSV keyed by `(record_table, record_id)`."""
    target = get_seed_csv_path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_rows = read_seed_csv(target)

    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in existing_rows:
        rec_table = str(row.get("record_table") or "").strip()
        rec_id = str(
            row.get("record_id") or row.get("target_id") or row.get("decision_key") or ""
        ).strip()
        if rec_id:
            normalized = {col: str(row.get(col) or "") for col in SEED_CSV_COLUMNS}
            by_key[(rec_table, rec_id)] = normalized

    serialized = serialize_decision(decision)
    new_row: dict[str, str] = {}
    for col in SEED_CSV_COLUMNS:
        val = serialized.get(col)
        if col == "synced_to_gsheet":
            new_row[col] = "true" if bool(val) else "false"
        elif val is None:
            new_row[col] = ""
        else:
            new_row[col] = str(val)

    by_key[(decision.record_table, decision.record_id)] = new_row
    sorted_keys = sorted(by_key.keys())

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_CSV_COLUMNS)
        writer.writeheader()
        for key in sorted_keys:
            writer.writerow(by_key[key])

    return target


def sync_seed_csv_to_db(
    session: Session,
    csv_path: Path | str | None = None,
) -> dict[str, int]:
    """Seed `qc_review_decision` rows from `qc_review_decisions_seed.csv` and apply overrides."""
    rows = read_seed_csv(csv_path)
    seeded_count = 0
    records_updated = 0

    for row in rows:
        record_table = str(row.get("record_table") or "proximate_record").strip()
        record_id = str(row.get("record_id") or row.get("target_id") or "").strip()
        if not record_id:
            continue

        existing = session.exec(
            select(QcReviewDecision).where(
                QcReviewDecision.record_table == record_table,
                QcReviewDecision.record_id == record_id,
            )
        ).first()

        now = datetime.now(timezone.utc)
        if existing is None:
            existing = QcReviewDecision(
                record_table=record_table,
                record_id=record_id,
                replicate_group_key=row.get("replicate_group_key") or None,
                resource_name=str(row.get("resource_name") or "unknown").strip().lower(),
                analysis_type=row.get("analysis_type") or None,
                parameter_name=row.get("parameter_name") or None,
                flag_type=str(
                    row.get("flag_type") or row.get("flag_types") or "analyst_flagged"
                ).strip(),
                flag_trigger_value=row.get("flag_trigger_value") or None,
                old_qc_pass=row.get("old_qc_pass") or row.get("previous_qc_pass") or None,
                new_qc_pass=row.get("new_qc_pass") or None,
                decision_status=str(
                    row.get("decision_status") or row.get("status") or "open"
                ).strip(),
                decision_action=row.get("decision_action") or None,
                rationale_chips=row.get("rationale_chips") or None,
                review_note=str(row.get("review_note") or ""),
                submitted_by_email=str(
                    row.get("submitted_by_email") or "seed@lbl.gov"
                ).strip(),
                assigned_to_email=row.get("assigned_to_email") or None,
                resolved_by_email=row.get("resolved_by_email") or None,
                resolved_at=_parse_dt(row.get("resolved_at")),
                synced_to_gsheet=_parse_bool(row.get("synced_to_gsheet")),
                gsheet_synced_at=_parse_dt(row.get("gsheet_synced_at")),
                gsheet_writeback_target=row.get("gsheet_writeback_target") or None,
                created_at=_parse_dt(row.get("created_at")) or now,
                updated_at=_parse_dt(row.get("updated_at")) or now,
            )
            session.add(existing)
        else:
            existing.new_qc_pass = row.get("new_qc_pass") or existing.new_qc_pass
            existing.decision_status = str(
                row.get("decision_status")
                or row.get("status")
                or existing.decision_status
            ).strip()
            existing.decision_action = (
                row.get("decision_action") or existing.decision_action
            )
            existing.review_note = str(row.get("review_note") or existing.review_note)
            existing.updated_at = now
            session.add(existing)

        session.flush()
        seeded_count += 1
        updated = apply_qc_decision_to_db(session, existing)
        records_updated += len(updated)

    session.commit()
    return {
        "decisions_seeded": seeded_count,
        "records_updated": records_updated,
    }


def record_stage1_decision(
    session: Session,
    *,
    actor_email: str,
    record_table: str,
    record_id: str,
    record_ids: Sequence[str] | None = None,
    decision_id: int | None = None,
    replicate_group_key: str | None = None,
    resource_name: str = "unknown",
    analysis_type: str | None = None,
    parameter_name: str | None = None,
    flag_type: str = "analyst_flagged",
    flag_trigger_value: str | None = None,
    old_qc_pass: str | None = None,
    new_qc_pass: str | None = None,
    decision_action: str | None = None,
    decision_status: str | None = None,
    rationale_chips: Sequence[str] | str | None = None,
    review_note: str = "",
    assigned_to_email: str | None = None,
    csv_path: Path | str | None = None,
) -> tuple[QcReviewDecision, list[str]]:
    """Record or update a Stage 1 QC review decision (Last-Write-Wins).

    Persists to `qc_review_decision`, applies `new_qc_pass` and `[QC_AUDIT ...]` note
    to the analytical record table, resets `synced_to_gsheet = False`, and mirrors to seed CSV.
    """
    now = datetime.now(timezone.utc)
    clean_action = (decision_action or "").strip().lower() or None

    resolved_new_qc = (new_qc_pass or "").strip().lower() or None
    if resolved_new_qc is None and clean_action in ACTION_TO_QC_PASS:
        resolved_new_qc = ACTION_TO_QC_PASS[clean_action]

    resolved_status = (decision_status or "").strip().lower() or None
    if resolved_status is None:
        if clean_action and clean_action in ACTION_TO_STATUS:
            resolved_status = ACTION_TO_STATUS[clean_action]
        elif resolved_new_qc in {"pass", "fail"}:
            resolved_status = "resolved"
        else:
            resolved_status = "open"

    chips_norm = normalize_rationale_chips(rationale_chips)
    clean_resource = (resource_name or "unknown").strip().lower()
    clean_table = (record_table or "proximate_record").strip().lower()
    clean_record_id = (record_id or "").strip()

    existing: QcReviewDecision | None = None
    if decision_id is not None:
        existing = session.get(QcReviewDecision, decision_id)
    if existing is None and clean_record_id:
        existing = session.exec(
            select(QcReviewDecision).where(
                QcReviewDecision.record_table == clean_table,
                QcReviewDecision.record_id == clean_record_id,
            )
        ).first()

    if existing is None:
        decision = QcReviewDecision(
            record_table=clean_table,
            record_id=clean_record_id,
            replicate_group_key=replicate_group_key,
            resource_name=clean_resource,
            analysis_type=analysis_type,
            parameter_name=parameter_name,
            flag_type=(flag_type or "analyst_flagged").strip(),
            flag_trigger_value=flag_trigger_value,
            old_qc_pass=old_qc_pass,
            new_qc_pass=resolved_new_qc,
            decision_status=resolved_status,
            decision_action=clean_action,
            rationale_chips=chips_norm,
            review_note=review_note or "",
            submitted_by_email=actor_email,
            assigned_to_email=(
                assigned_to_email.strip().lower()
                if assigned_to_email and assigned_to_email.strip()
                else None
            ),
            resolved_by_email=(
                actor_email
                if resolved_status in {"resolved", "needs_retest"}
                else None
            ),
            resolved_at=(
                now if resolved_status in {"resolved", "needs_retest"} else None
            ),
            synced_to_gsheet=False,
            gsheet_synced_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(decision)
    else:
        decision = existing
        if old_qc_pass is not None:
            decision.old_qc_pass = old_qc_pass
        elif decision.new_qc_pass is not None and resolved_new_qc != decision.new_qc_pass:
            decision.old_qc_pass = decision.new_qc_pass

        if replicate_group_key is not None:
            decision.replicate_group_key = replicate_group_key
        if resource_name and resource_name != "unknown":
            decision.resource_name = clean_resource
        if analysis_type is not None:
            decision.analysis_type = analysis_type
        if parameter_name is not None:
            decision.parameter_name = parameter_name
        if flag_type:
            decision.flag_type = flag_type.strip()
        if flag_trigger_value is not None:
            decision.flag_trigger_value = flag_trigger_value

        decision.new_qc_pass = resolved_new_qc
        decision.decision_status = resolved_status
        decision.decision_action = clean_action
        if chips_norm is not None:
            decision.rationale_chips = chips_norm
        decision.review_note = review_note or ""
        if assigned_to_email is not None:
            decision.assigned_to_email = (
                assigned_to_email.strip().lower() if assigned_to_email.strip() else None
            )
        if resolved_status in {"resolved", "needs_retest"}:
            decision.resolved_by_email = actor_email
            decision.resolved_at = now
        # Stage 1 modification resets synced_to_gsheet to False so it re-enters Admin GSheet queue
        decision.synced_to_gsheet = False
        decision.gsheet_synced_at = None
        decision.updated_at = now
        session.add(decision)

    session.flush()
    updated_record_ids = apply_qc_decision_to_db(
        session=session,
        decision=decision,
        target_record_ids=record_ids,
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)

    append_or_update_seed_csv(decision, csv_path=csv_path)
    return decision, updated_record_ids


def export_decisions_to_csv_string(decisions: Sequence[QcReviewDecision]) -> str:
    """Serialize a sequence of `QcReviewDecision` rows into a CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SEED_CSV_COLUMNS)
    writer.writeheader()
    for d in decisions:
        serialized = serialize_decision(d)
        row: dict[str, str] = {}
        for col in SEED_CSV_COLUMNS:
            val = serialized.get(col)
            if col == "synced_to_gsheet":
                row[col] = "true" if bool(val) else "false"
            elif val is None:
                row[col] = ""
            else:
                row[col] = str(val)
        writer.writerow(row)
    return buf.getvalue()
