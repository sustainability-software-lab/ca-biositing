"""Self-contained FastAPI service for Stage 1 QC decision persistence and seed CSV mirroring.

Maintains strict package boundary isolation (`ca_biositing.webservice` -> `ca_biositing.datamodels`
only, with zero imports from `ca_biositing.pipeline`).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence, Type

from sqlmodel import Session, SQLModel, select

from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision

logger = logging.getLogger(__name__)

FALLBACK_SEED_CSV_PATH = (
    Path(tempfile.gettempdir())
    / "ca_biositing_qc"
    / "qc_review_decisions_seed.csv"
)

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

VALID_QC_PASS_STATES: set[str] = {
    "pass",
    "fail",
    "provisional",
    "in_review",
    "retest",
}

GSHEET_SYNC_ELIGIBLE_STATUSES: set[str] = {
    "resolved",
    "needs_retest",
    "in_review",
}

ACTION_TO_QC_PASS: dict[str, str | None] = {
    "approve_pass": "pass",
    "approve": "pass",
    "keep_pass": "pass",
    "keep": "pass",
    "flip_to_pass": "pass",
    "pass": "pass",
    "trace_ignore": "pass",
    "accept_pass": "pass",
    "provisional": "provisional",
    "approve_provisional": "provisional",
    "mark_provisional": "provisional",
    "reject_fail": "fail",
    "mark_fail": "fail",
    "reject": "fail",
    "exclude_qc_fail": "fail",
    "flag_fail": "fail",
    "flip_to_fail": "fail",
    "fail": "fail",
    "needs_retest": "retest",
    "mark_retest": "retest",
    "retest": "retest",
    "re_assay": None,
    "accept_with_note": None,
    "keep_note": None,
    "in_review": "in_review",
    "mark_in_review": "in_review",
    "defer": "in_review",
    "flag_for_review": None,
    "open": None,
}

ACTION_TO_STATUS: dict[str, str] = {
    "approve_pass": "resolved",
    "approve": "resolved",
    "keep_pass": "resolved",
    "keep": "resolved",
    "flip_to_pass": "resolved",
    "pass": "resolved",
    "trace_ignore": "resolved",
    "accept_pass": "resolved",
    "provisional": "resolved",
    "approve_provisional": "resolved",
    "mark_provisional": "resolved",
    "reject_fail": "resolved",
    "mark_fail": "resolved",
    "reject": "resolved",
    "exclude_qc_fail": "resolved",
    "flag_fail": "resolved",
    "flip_to_fail": "resolved",
    "fail": "resolved",
    "needs_retest": "needs_retest",
    "mark_retest": "needs_retest",
    "retest": "needs_retest",
    "re_assay": "needs_retest",
    "defer": "in_review",
    "in_review": "in_review",
    "mark_in_review": "in_review",
    "accept_with_note": "in_review",
    "keep_note": "in_review",
    "flag_for_review": "open",
    "open": "open",
}

AIM1_GSHEET_NAME = "Aim 1-Feedstock Collection and Processing Data-BioCirV"
AIM2_BIOCHEM_GSHEET_NAME = "Aim 2-Biomass Biochem Conversion Data-BioCirV"
AIM2_THERMO_GSHEET_NAME = "Aim 2-Thermochem Conversion Data-BioCirV"

_ANALYSIS_DOMAIN_SPECS: list[
    tuple[str, str, tuple[str, str, str], tuple[str, ...]]
] = [
    (
        "proximate_record",
        "Proximate Analysis",
        (AIM1_GSHEET_NAME, "03.1-Proximate", "record_id"),
        (
            "proximate",
            "proximate_analysis",
            "proximate_record",
            "03_1_proximate",
        ),
    ),
    (
        "ultimate_record",
        "Ultimate Analysis",
        (AIM1_GSHEET_NAME, "03.7-Ultimate", "record_id"),
        (
            "ultimate",
            "ultimate_analysis",
            "ultimate_record",
            "03_7_ultimate",
        ),
    ),
    (
        "compositional_record",
        "Compositional Analysis",
        (AIM1_GSHEET_NAME, "03.3-CmpAna", "record_id"),
        (
            "compositional",
            "compositional_analysis",
            "compositional_record",
            "cmpana",
            "03_3_cmpana",
        ),
    ),
    (
        "calorimetry_record",
        "Calorimetry Analysis",
        (AIM1_GSHEET_NAME, "03.6-Caloric", "record_id"),
        (
            "calorimetry",
            "calorimetry_analysis",
            "calorimetry_record",
            "caloric",
            "03_6_caloric",
        ),
    ),
    (
        "icp_record",
        "ICP Analysis",
        (AIM1_GSHEET_NAME, "03.5-ICP", "record_id"),
        (
            "icp",
            "icp_analysis",
            "icp_elemental_analysis",
            "icp_elemental",
            "icp_record",
            "03_5_icp",
        ),
    ),
    (
        "xrf_record",
        "XRF Analysis",
        (AIM1_GSHEET_NAME, "03.2-XRF", "record_id"),
        (
            "xrf",
            "xrf_analysis",
            "xrf_elemental_analysis",
            "xrf_elemental",
            "xrf_record",
            "03_2_xrf",
        ),
    ),
    (
        "xrd_record",
        "XRD Analysis",
        (AIM1_GSHEET_NAME, "03.4-XRD", "record_id"),
        (
            "xrd",
            "xrd_analysis",
            "xrd_crystallinity",
            "xrd_record",
            "03_4_xrd",
        ),
    ),
    (
        "ftnir_record",
        "FT-NIR",
        (AIM1_GSHEET_NAME, "03.8-FT-NIR", "record_id"),
        (
            "ftnir",
            "ft_nir",
            "ft_ir",
            "ftir",
            "ft_nir_analysis",
            "ft_ir_analysis",
            "ftnir_analysis",
            "ftnir_record",
            "03_8_ft_nir",
        ),
    ),
    (
        "rgb_record",
        "Colorimetry / RGB",
        (AIM1_GSHEET_NAME, "03.9-RGB", "record_id"),
        (
            "rgb",
            "colorimetry",
            "colorimetry_rgb",
            "rgb_analysis",
            "rgb_record",
            "03_9_rgb",
        ),
    ),
    (
        "autoclave_record",
        "Autoclave",
        (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave", "record_id"),
        (
            "autoclave",
            "autoclave_analysis",
            "autoclave_pretreatment",
            "autoclave_record",
            "01_3_autoclave",
        ),
    ),
    (
        "pretreatment_record",
        "Pretreatment & Hydrolysis",
        (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData", "record_id"),
        (
            "pretreatment",
            "pretreatment_analysis",
            "pretreatment_hydrolysis",
            "pretreatment_and_hydrolysis",
            "pretreatment_record",
            "02_1_pretreatmentdata",
        ),
    ),
    (
        "fermentation_record",
        "Fermentation / Bioconversion",
        (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData", "record_id"),
        (
            "fermentation",
            "fermentation_analysis",
            "fermentation_bioconversion",
            "bioconversion",
            "fermentation_record",
            "02_2_bioconversiondata",
        ),
    ),
    (
        "gasification_record",
        "Gasification",
        (AIM2_THERMO_GSHEET_NAME, "02-ThermoData", "record_id"),
        (
            "gasification",
            "gasification_analysis",
            "thermochemical",
            "gasification_record",
            "02_thermodata",
        ),
    ),
]


def _normalize_domain_token(raw: str | None) -> str:
    if not raw:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(raw).strip().lower()).strip("_")


ANALYSIS_DOMAIN_REGISTRY: dict[
    str, tuple[str, str, tuple[str, str, str]]
] = {}
RECORD_TABLE_GSHEET_TARGET_MAP: dict[str, tuple[str, str, str]] = {}
for _canon_table, _canon_label, _gsheet_info, _aliases in _ANALYSIS_DOMAIN_SPECS:
    _entry = (_canon_table, _canon_label, _gsheet_info)
    RECORD_TABLE_GSHEET_TARGET_MAP[_canon_table] = _gsheet_info
    for _tok in (_canon_table, _canon_label, *_aliases):
        ANALYSIS_DOMAIN_REGISTRY[_normalize_domain_token(_tok)] = _entry
        ANALYSIS_DOMAIN_REGISTRY[str(_tok).strip().lower()] = _entry


def normalize_analysis_domain(
    record_table: str | None = None,
    analysis_type: str | None = None,
) -> tuple[str, str]:
    """Resolve `(canonical_record_table, canonical_analysis_label)` from any table or analysis_type alias."""
    candidates: list[str | None] = (
        [analysis_type, record_table]
        if (record_table or "").strip().lower() in {"", "proximate_record"}
        and (analysis_type or "").strip()
        else [record_table, analysis_type]
    )
    for candidate in candidates:
        if not candidate:
            continue
        norm = _normalize_domain_token(candidate)
        if norm in ANALYSIS_DOMAIN_REGISTRY:
            canon_table, canon_label, _ = ANALYSIS_DOMAIN_REGISTRY[norm]
            return canon_table, canon_label
        if not norm.endswith("_record") and f"{norm}_record" in ANALYSIS_DOMAIN_REGISTRY:
            canon_table, canon_label, _ = ANALYSIS_DOMAIN_REGISTRY[f"{norm}_record"]
            return canon_table, canon_label
        first_token = norm.split("_")[0] if norm else ""
        if first_token and first_token in ANALYSIS_DOMAIN_REGISTRY:
            canon_table, canon_label, _ = ANALYSIS_DOMAIN_REGISTRY[first_token]
            return canon_table, canon_label

    fallback_table = _normalize_domain_token(record_table) or "proximate_record"
    fallback_label = (analysis_type or record_table or "Proximate Analysis").strip()
    return fallback_table, fallback_label


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

    canonical_models: dict[str, Type[SQLModel]] = {
        "proximate_record": ProximateRecord,
        "ultimate_record": UltimateRecord,
        "compositional_record": CompositionalRecord,
        "calorimetry_record": CalorimetryRecord,
        "icp_record": IcpRecord,
        "xrf_record": XrfRecord,
        "xrd_record": XrdRecord,
        "pretreatment_record": PretreatmentRecord,
        "fermentation_record": FermentationRecord,
        "gasification_record": GasificationRecord,
        "autoclave_record": AutoclaveRecord,
        "ftnir_record": FtnirRecord,
        "rgb_record": RgbRecord,
    }
    model_map: dict[str, Type[SQLModel]] = dict(canonical_models)
    for token, (canon_table, _, _) in ANALYSIS_DOMAIN_REGISTRY.items():
        if canon_table in canonical_models:
            model_map[token] = canonical_models[canon_table]
    return model_map


def resolve_record_model(
    record_table: str | None,
    analysis_type: str | None = None,
) -> Type[SQLModel] | None:
    """Resolve the SQLModel record class from `record_table` or `analysis_type`."""
    model_map = get_record_model_map()
    for candidate in (record_table, analysis_type):
        if not candidate:
            continue
        norm = _normalize_domain_token(candidate)
        if norm in ANALYSIS_DOMAIN_REGISTRY:
            canon_table, _, _ = ANALYSIS_DOMAIN_REGISTRY[norm]
            if canon_table in model_map:
                return model_map[canon_table]
        if norm in model_map:
            return model_map[norm]
        if not norm.endswith("_record") and f"{norm}_record" in model_map:
            return model_map[f"{norm}_record"]
    return None


def apply_qc_decision_to_db(
    session: Session,
    decision: QcReviewDecision,
    target_record_ids: Sequence[str] | None = None,
    *,
    freeze_old_qc_pass: bool = False,
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
        if (
            not freeze_old_qc_pass
            and decision.old_qc_pass is None
            and current_qc is not None
        ):
            decision.old_qc_pass = str(current_qc)

        if (
            decision.new_qc_pass in VALID_QC_PASS_STATES
            and hasattr(rec, "qc_pass")
        ):
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
        if csv_path is None and FALLBACK_SEED_CSV_PATH.exists():
            target = FALLBACK_SEED_CSV_PATH
        else:
            return []
    try:
        with target.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [
                dict(row)
                for row in reader
                if row.get("record_id") or row.get("decision_key")
            ]
    except OSError as exc:
        logger.warning("Unable to read QC seed CSV at %s: %s", target, exc)
        return []


def append_or_update_seed_csv(
    decision: QcReviewDecision,
    csv_path: Path | str | None = None,
) -> Path:
    """Upsert a `QcReviewDecision` into the seed CSV keyed by `(record_table, record_id)`."""
    target = get_seed_csv_path(csv_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        if csv_path is None:
            logger.warning(
                "Primary QC seed CSV directory %s is not writable (%s); falling back to %s",
                target.parent,
                exc,
                FALLBACK_SEED_CSV_PATH,
            )
            target = FALLBACK_SEED_CSV_PATH
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except OSError as fallback_exc:
                logger.warning(
                    "Fallback QC seed CSV directory %s is also not writable: %s",
                    target.parent,
                    fallback_exc,
                )
                return target
        else:
            logger.warning("Explicit QC seed CSV directory %s not writable: %s", target.parent, exc)
            return target

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

    try:
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SEED_CSV_COLUMNS)
            writer.writeheader()
            for key in sorted_keys:
                writer.writerow(by_key[key])
    except OSError as exc:
        if csv_path is None and target != FALLBACK_SEED_CSV_PATH:
            logger.warning(
                "Primary QC seed CSV file %s is not writable (%s); falling back to %s",
                target,
                exc,
                FALLBACK_SEED_CSV_PATH,
            )
            target = FALLBACK_SEED_CSV_PATH
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=SEED_CSV_COLUMNS)
                    writer.writeheader()
                    for key in sorted_keys:
                        writer.writerow(by_key[key])
            except OSError as fallback_exc:
                logger.warning(
                    "Fallback QC seed CSV file %s is also not writable: %s",
                    target,
                    fallback_exc,
                )
        else:
            logger.warning("Unable to write QC seed CSV at %s: %s", target, exc)

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
    scope: str | None = None,
    csv_path: Path | str | None = None,
) -> tuple[QcReviewDecision, list[str]]:
    """Record or update a Stage 1 QC review decision (Last-Write-Wins).

    Persists to `qc_review_decision`, applies `new_qc_pass` and `[QC_AUDIT ...]` note
    to the analytical record table, resets `synced_to_gsheet = False`, and mirrors to seed CSV.
    When `scope == "group"` or `len(target_ids) > 1`, fans out the decision across all
    target replicate records and sibling `QcReviewDecision` rows in the replicate group.
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
        elif resolved_new_qc in {"pass", "fail", "provisional"}:
            resolved_status = "resolved"
        elif resolved_new_qc == "retest":
            resolved_status = "needs_retest"
        elif resolved_new_qc == "in_review":
            resolved_status = "in_review"
        else:
            resolved_status = "open"

    chips_norm = normalize_rationale_chips(rationale_chips)
    clean_resource = (resource_name or "unknown").strip().lower()
    clean_table = (record_table or "proximate_record").strip().lower()
    clean_record_id = (record_id or "").strip()

    target_ids: list[str] = []
    if clean_record_id:
        target_ids.append(clean_record_id)
    if record_ids:
        for rid in record_ids:
            clean_rid = str(rid or "").strip()
            if clean_rid and clean_rid not in target_ids:
                target_ids.append(clean_rid)
    if not clean_record_id and target_ids:
        clean_record_id = target_ids[0]

    primary_existing: QcReviewDecision | None = None
    if decision_id is not None:
        primary_existing = session.get(QcReviewDecision, decision_id)
    if primary_existing is None and clean_record_id:
        primary_existing = session.exec(
            select(QcReviewDecision).where(
                QcReviewDecision.record_table == clean_table,
                QcReviewDecision.record_id == clean_record_id,
            )
        ).first()

    effective_group_key = replicate_group_key
    if not effective_group_key and primary_existing is not None:
        effective_group_key = primary_existing.replicate_group_key

    clean_scope = str(scope or "").strip().lower()
    is_group_scope = clean_scope not in {"row", "single", "single_record"} and (
        clean_scope == "group" or len(target_ids) > 1
    )

    if is_group_scope and effective_group_key and effective_group_key.strip():
        sibling_rows = list(
            session.exec(
                select(QcReviewDecision).where(
                    QcReviewDecision.record_table == clean_table,
                    QcReviewDecision.replicate_group_key == effective_group_key,
                )
            ).all()
        )
        for sib in sibling_rows:
            sib_rid = (sib.record_id or "").strip()
            if sib_rid and sib_rid not in target_ids:
                target_ids.append(sib_rid)

    effective_target_ids = (
        target_ids
        if is_group_scope and target_ids
        else ([clean_record_id] if clean_record_id else target_ids[:1])
    )

    group_decisions: list[tuple[QcReviewDecision, bool]] = []
    for idx, rid in enumerate(effective_target_ids):
        existing: QcReviewDecision | None = None
        if idx == 0 and primary_existing is not None and (
            primary_existing.record_id == rid or len(effective_target_ids) == 1
        ):
            existing = primary_existing
        if existing is None:
            existing = session.exec(
                select(QcReviewDecision).where(
                    QcReviewDecision.record_table == clean_table,
                    QcReviewDecision.record_id == rid,
                )
            ).first()

        if existing is None:
            had_prior_qc_override = False
            sib_decision = QcReviewDecision(
                record_table=clean_table,
                record_id=rid,
                replicate_group_key=effective_group_key,
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
                    if resolved_status in GSHEET_SYNC_ELIGIBLE_STATUSES
                    else None
                ),
                resolved_at=(
                    now
                    if resolved_status in GSHEET_SYNC_ELIGIBLE_STATUSES
                    else None
                ),
                synced_to_gsheet=False,
                gsheet_synced_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(sib_decision)
        else:
            sib_decision = existing
            had_prior_qc_override = sib_decision.new_qc_pass is not None
            # Freeze old_qc_pass on first capture (Review B5): only populate when None and not yet overridden
            if (
                sib_decision.old_qc_pass is None
                and not had_prior_qc_override
                and old_qc_pass is not None
            ):
                sib_decision.old_qc_pass = old_qc_pass

            if effective_group_key is not None:
                sib_decision.replicate_group_key = effective_group_key
            if resource_name and resource_name != "unknown":
                sib_decision.resource_name = clean_resource
            if analysis_type is not None:
                sib_decision.analysis_type = analysis_type
            if parameter_name is not None:
                sib_decision.parameter_name = parameter_name
            if flag_type:
                sib_decision.flag_type = flag_type.strip()
            if flag_trigger_value is not None:
                sib_decision.flag_trigger_value = flag_trigger_value

            sib_decision.new_qc_pass = resolved_new_qc
            sib_decision.decision_status = resolved_status
            sib_decision.decision_action = clean_action
            if chips_norm is not None:
                sib_decision.rationale_chips = chips_norm
            sib_decision.review_note = review_note or ""
            if assigned_to_email is not None:
                sib_decision.assigned_to_email = (
                    assigned_to_email.strip().lower()
                    if assigned_to_email.strip()
                    else None
                )
            if resolved_status in GSHEET_SYNC_ELIGIBLE_STATUSES:
                sib_decision.resolved_by_email = actor_email
                sib_decision.resolved_at = now
            # Stage 1 modification resets synced_to_gsheet to False so it re-enters Admin GSheet queue
            sib_decision.synced_to_gsheet = False
            sib_decision.gsheet_synced_at = None
            sib_decision.updated_at = now
            session.add(sib_decision)

        group_decisions.append((sib_decision, had_prior_qc_override))

    session.flush()
    updated_record_ids: list[str] = []
    for sib_decision, had_prior_qc_override in group_decisions:
        mod_ids = apply_qc_decision_to_db(
            session=session,
            decision=sib_decision,
            target_record_ids=[sib_decision.record_id],
            freeze_old_qc_pass=had_prior_qc_override,
        )
        for mid in mod_ids:
            if mid not in updated_record_ids:
                updated_record_ids.append(mid)
        session.add(sib_decision)

    session.commit()
    for sib_decision, _ in group_decisions:
        session.refresh(sib_decision)
        append_or_update_seed_csv(sib_decision, csv_path=csv_path)

    primary_decision = group_decisions[0][0]
    return primary_decision, updated_record_ids


record_qc_decision = record_stage1_decision


def revert_qc_decision(
    session: Session,
    *,
    decision_id: int,
    actor_email: str,
    reason: str = "Reverted to open review queue",
    sync_to_gsheet: bool = False,
    is_admin: bool = False,
    csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """Revert a resolved/synced `QcReviewDecision` (and any replicate-group siblings) back to `open`.

    Restores `rec.qc_pass` on each analytical record in PostgreSQL to `sib.old_qc_pass`
    (preserving `None` when the original pre-audit `qc_pass` was `NULL` per Review B6),
    resets `decision_status = "open"`, and optionally writes the revert back to Google Sheets.
    """
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise KeyError(f"QC decision {decision_id} not found.")

    group_decisions: list[QcReviewDecision] = [decision]
    if decision.replicate_group_key and decision.replicate_group_key.strip():
        siblings = list(
            session.exec(
                select(QcReviewDecision).where(
                    QcReviewDecision.record_table == decision.record_table,
                    QcReviewDecision.replicate_group_key
                    == decision.replicate_group_key,
                )
            ).all()
        )
        for sib in siblings:
            if all(sib.id != d.id for d in group_decisions):
                group_decisions.append(sib)

    was_synced = any(bool(d.synced_to_gsheet) for d in group_decisions)
    now = datetime.now(timezone.utc)
    now_iso = _format_dt(now)
    clean_reason = (reason or "Reverted to open review queue").strip()
    revert_tag = f"[Reverted by {actor_email} at {now_iso}: {clean_reason}]"

    model_cls = resolve_record_model(decision.record_table, decision.analysis_type)
    record_id_col = (
        getattr(model_cls, "record_id", None) if model_cls is not None else None
    )
    reverted_record_ids: list[str] = []

    for sib in group_decisions:
        restored_qc: str | None = (
            sib.old_qc_pass.strip().lower()
            if sib.old_qc_pass is not None and sib.old_qc_pass.strip()
            else None
        )

        if model_cls is not None and record_id_col is not None and sib.record_id:
            rec = session.exec(
                select(model_cls).where(record_id_col == sib.record_id)
            ).first()
            if rec is not None:
                if hasattr(rec, "qc_pass"):
                    setattr(rec, "qc_pass", restored_qc)
                if hasattr(rec, "note"):
                    existing_note = getattr(rec, "note", None)
                    new_note = format_qc_audit_note(
                        existing_note=existing_note,
                        decision_id=sib.id or sib.record_id,
                        new_qc_pass=(restored_qc or "reverted"),
                        resolved_by_email=actor_email,
                        review_note=f"Reverted: {clean_reason}",
                        resolved_at=now,
                        rationale_chips=sib.rationale_chips,
                    )
                    setattr(rec, "note", new_note)
                if hasattr(rec, "updated_at"):
                    setattr(rec, "updated_at", now)
                session.add(rec)
                reverted_record_ids.append(str(sib.record_id))

        sib.decision_status = "open"
        sib.decision_action = "open"
        sib.new_qc_pass = restored_qc
        sib.resolved_by_email = None
        sib.resolved_at = None
        sib.synced_to_gsheet = False
        sib.gsheet_synced_at = None
        sib.updated_at = now
        prior_note = (sib.review_note or "").strip()
        sib.review_note = (
            f"{prior_note} {revert_tag}".strip() if prior_note else revert_tag
        )
        session.add(sib)

    session.commit()
    for sib in group_decisions:
        session.refresh(sib)
        append_or_update_seed_csv(sib, csv_path=csv_path)

    gsheet_writeback_info: dict[str, Any] | None = None
    if was_synced and sync_to_gsheet and is_admin:
        from ca_biositing.webservice.services.gsheet_sync_service import (
            writeback_decision_to_gsheet_row,
        )

        gsheet_writeback_info = writeback_decision_to_gsheet_row(
            decision=decision,
            target_record_ids=[d.record_id for d in group_decisions if d.record_id],
        )

    serialized = serialize_decision(decision)
    return {
        "status": "ok",
        "decision_id": decision.id,
        "decision": serialized,
        "decisions": [serialize_decision(d) for d in group_decisions],
        "reverted_decision_ids": [
            d.id for d in group_decisions if d.id is not None
        ],
        "reverted_record_ids": reverted_record_ids,
        "restored_qc_pass": decision.new_qc_pass,
        "gsheet_reverted": bool(
            gsheet_writeback_info
            and gsheet_writeback_info.get("writeback_status") == "synced"
        ),
    }


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
