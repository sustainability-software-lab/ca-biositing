"""Idempotent Stage 2 Google Sheets writeback utilities for QC Review Decisions.

Writes resolved `QcReviewDecision` rows back to the Aim 1 / Aim 2 Google Sheets
(`qc_result` and `note` columns), replacing `[QC_AUDIT id=<decision_id> ...]`
tags in-place via regex so repeated calls never produce duplicate audit entries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gspread
from gspread.utils import rowcol_to_a1
from sqlmodel import Session, select

from ca_biositing.datamodels.models import QcReviewDecision
from ca_biositing.pipeline.utils.qc_ledger_seed import format_qc_audit_note


AIM1_GSHEET_NAME = "Aim 1 - Feedstock CharacterizationData"
AIM2_BIOCHEM_GSHEET_NAME = "Aim 2 - BioChem Conversion Data"
AIM2_THERMO_GSHEET_NAME = "Aim 2 - ThermoChem Conversion Data"

RECORD_TABLE_TO_GSHEET_TARGET: Dict[str, Tuple[str, str]] = {
    "proximate_record": (AIM1_GSHEET_NAME, "03.1-Proximate"),
    "ultimate_record": (AIM1_GSHEET_NAME, "03.2-Ultimate"),
    "compositional_record": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "icp_record": (AIM1_GSHEET_NAME, "03.4-ICP"),
    "xrf_record": (AIM1_GSHEET_NAME, "03.5-XRF"),
    "xrd_record": (AIM1_GSHEET_NAME, "03.6-XRD"),
    "calorimetry_record": (AIM1_GSHEET_NAME, "03.7-Calorimetry"),
    "pretreatment_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-Pretreatment"),
    "fermentation_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "gasification_record": (AIM2_THERMO_GSHEET_NAME, "02.3-Gasification"),
}

ANALYSIS_TYPE_TO_RECORD_TABLE: Dict[str, str] = {
    "proximate": "proximate_record",
    "ultimate": "ultimate_record",
    "compositional": "compositional_record",
    "icp": "icp_record",
    "xrf": "xrf_record",
    "xrd": "xrd_record",
    "calorimetry": "calorimetry_record",
    "pretreatment": "pretreatment_record",
    "fermentation": "fermentation_record",
    "gasification": "gasification_record",
}


def _normalize_header(raw: str) -> str:
    return str(raw or "").strip().lower().replace(" ", "_")


def resolve_worksheet_target(
    record_table: Optional[str] = None,
    analysis_type: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Resolve `(spreadsheet_name, worksheet_tab_name)` for a record table or analysis type."""
    if record_table:
        norm_table = str(record_table).strip().lower()
        if norm_table in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[norm_table]
        mapped = ANALYSIS_TYPE_TO_RECORD_TABLE.get(norm_table)
        if mapped and mapped in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[mapped]

    if analysis_type:
        norm_type = str(analysis_type).strip().lower()
        mapped = ANALYSIS_TYPE_TO_RECORD_TABLE.get(norm_type)
        if mapped and mapped in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[mapped]
        if norm_type in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[norm_type]

    return None


def _resolve_worksheet(
    worksheet_client: Any,
    gsheet_name: str,
    tab_name: str,
    credentials_path: str = "credentials.json",
) -> Any:
    """Resolve a target worksheet object from a gspread client, spreadsheet, or worksheet."""
    if worksheet_client is None:
        cred_file = Path(credentials_path)
        if not cred_file.exists():
            raise FileNotFoundError(
                f"Google Sheets credentials not found at '{credentials_path}'"
            )
        worksheet_client = gspread.service_account(filename=str(cred_file))

    if hasattr(worksheet_client, "get_all_values"):
        return worksheet_client
    if hasattr(worksheet_client, "worksheet"):
        return worksheet_client.worksheet(tab_name)
    if hasattr(worksheet_client, "open"):
        spreadsheet = worksheet_client.open(gsheet_name)
        return spreadsheet.worksheet(tab_name)
    raise TypeError(f"Unsupported worksheet_client type: {type(worksheet_client)!r}")


def _apply_cell_updates(
    worksheet: Any,
    row_idx_1based: int,
    col_updates: List[Tuple[int, str]],
) -> None:
    """Apply cell updates to `worksheet`, supporting both `batch_update` and `update_cell`."""
    if not col_updates:
        return

    batch_payload = [
        {
            "range": rowcol_to_a1(row_idx_1based, col_idx_0based + 1),
            "values": [[val]],
        }
        for col_idx_0based, val in col_updates
    ]
    if hasattr(worksheet, "batch_update"):
        worksheet.batch_update(batch_payload, value_input_option="USER_ENTERED")
    elif hasattr(worksheet, "update_cell"):
        for col_idx_0based, val in col_updates:
            worksheet.update_cell(row_idx_1based, col_idx_0based + 1, val)
    elif hasattr(worksheet, "update"):
        for item in batch_payload:
            worksheet.update(item["range"], item["values"])


def writeback_qc_decision_to_gsheet(
    session: Session,
    decision_id: int,
    worksheet_client: Optional[Any] = None,
    credentials_path: str = "credentials.json",
) -> Dict[str, Any]:
    """Write a resolved `QcReviewDecision` to Google Sheets idempotently.

    - Finds the row matching `decision.record_id` in the target worksheet.
    - Sets `qc_result` (or `qc_pass`) to `decision.new_qc_pass`.
    - Updates `note` in-place via `format_qc_audit_note`, replacing any existing
      `[QC_AUDIT id=<decision_id> ...]` tag rather than duplicating it.
    - Marks `decision.synced_to_gsheet = True` and updates `decision.gsheet_synced_at`.
    """
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise ValueError(f"QcReviewDecision with id={decision_id} not found")

    already_synced = bool(decision.synced_to_gsheet)
    target = resolve_worksheet_target(
        record_table=decision.record_table,
        analysis_type=decision.analysis_type,
    )
    gsheet_name = target[0] if target else AIM1_GSHEET_NAME
    tab_name = target[1] if target else (decision.record_table or "03.1-Proximate")

    worksheet = _resolve_worksheet(
        worksheet_client=worksheet_client,
        gsheet_name=gsheet_name,
        tab_name=tab_name,
        credentials_path=credentials_path,
    )

    all_values = worksheet.get_all_values()
    if not all_values:
        raise ValueError(f"Worksheet '{tab_name}' is empty")

    headers = [_normalize_header(h) for h in all_values[0]]
    record_id_col = next(
        (i for i, h in enumerate(headers) if h in {"record_id", "recordid"}),
        None,
    )
    qc_col = next(
        (i for i, h in enumerate(headers) if h in {"qc_result", "qc_pass", "qc_status"}),
        None,
    )
    note_col = next(
        (i for i, h in enumerate(headers) if h in {"note", "notes"}),
        None,
    )
    if record_id_col is None:
        raise ValueError(f"Worksheet '{tab_name}' is missing a 'record_id' column")

    now = datetime.now(timezone.utc)
    resolved_iso = (
        decision.resolved_at.isoformat()
        if decision.resolved_at is not None
        else now.isoformat()
    )
    reviewer = decision.resolved_by_email or decision.submitted_by_email or "analyst"
    action = decision.decision_action or decision.decision_status or "review"

    updated_note: Optional[str] = None
    matched_row = False

    for row_idx_1based, row in enumerate(all_values[1:], start=2):
        row_record_id = (
            str(row[record_id_col]).strip() if record_id_col < len(row) else ""
        )
        if row_record_id != str(decision.record_id).strip():
            continue

        matched_row = True
        col_updates: List[Tuple[int, str]] = []
        if qc_col is not None and decision.new_qc_pass:
            col_updates.append((qc_col, str(decision.new_qc_pass)))

        if note_col is not None:
            existing_note = row[note_col] if note_col < len(row) else ""
            updated_note = format_qc_audit_note(
                existing_note=existing_note,
                decision_id=decision.id if decision.id is not None else decision_id,
                action=action,
                new_qc_pass=decision.new_qc_pass,
                reviewer_email=reviewer,
                review_note=decision.review_note,
                resolved_at_iso=resolved_iso,
            )
            col_updates.append((note_col, updated_note))

        _apply_cell_updates(worksheet, row_idx_1based, col_updates)
        break

    if not matched_row:
        raise ValueError(
            f"record_id '{decision.record_id}' not found in worksheet '{tab_name}'"
        )

    decision.synced_to_gsheet = True
    decision.gsheet_synced_at = now
    decision.gsheet_writeback_target = f"{gsheet_name}::{tab_name}"
    decision.updated_at = now
    session.add(decision)
    session.commit()
    session.refresh(decision)

    return {
        "decision_id": decision.id,
        "record_table": decision.record_table,
        "record_id": decision.record_id,
        "already_synced": already_synced,
        "synced_to_gsheet": True,
        "gsheet_synced_at": decision.gsheet_synced_at.isoformat(),
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "updated_note": updated_note,
    }


def writeback_batch_to_gsheet(
    session: Session,
    decision_ids: Optional[List[int]] = None,
    worksheet_client: Optional[Any] = None,
    credentials_path: str = "credentials.json",
) -> Dict[str, Any]:
    """Batch-sync resolved QC decisions to Google Sheets idempotently."""
    if decision_ids is not None:
        target_ids = list(decision_ids)
    else:
        pending = session.exec(
            select(QcReviewDecision)
            .where(
                QcReviewDecision.decision_status == "resolved",
                QcReviewDecision.synced_to_gsheet.is_(False),
            )
            .order_by(QcReviewDecision.id)
        ).all()
        target_ids = [int(d.id) for d in pending if d.id is not None]

    results: List[Dict[str, Any]] = []
    for did in target_ids:
        res = writeback_qc_decision_to_gsheet(
            session=session,
            decision_id=did,
            worksheet_client=worksheet_client,
            credentials_path=credentials_path,
        )
        results.append(res)

    return {
        "synced_count": len(results),
        "results": results,
    }
