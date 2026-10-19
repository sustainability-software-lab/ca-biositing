"""Stage 2 Admin Google Sheets writeback service for `ca_biositing.webservice`.

Strictly isolated from `ca_biositing.pipeline` so the `webservice` container boots cleanly
without `pipeline` or top-level `gspread` dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any, Callable

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision
from ca_biositing.webservice.services.qc_ledger_service import (
    append_or_update_seed_csv,
    format_qc_audit_note,
    serialize_decision,
)

AIM1_GSHEET_NAME = "Aim 1-Feedstock Collection and Processing Data-BioCirV"
AIM2_BIOCHEM_GSHEET_NAME = "Aim 2-Biomass Biochem Conversion Data-BioCirV"
AIM2_THERMO_GSHEET_NAME = "Aim 2-Thermochem Conversion Data-BioCirV"

RECORD_WORKSHEET_MAP: dict[str, tuple[str, str]] = {
    "proximate_record": (AIM1_GSHEET_NAME, "03.1-Proximate"),
    "proximate": (AIM1_GSHEET_NAME, "03.1-Proximate"),
    "proximate_analysis": (AIM1_GSHEET_NAME, "03.1-Proximate"),
    "xrf_record": (AIM1_GSHEET_NAME, "03.2-XRF"),
    "xrf": (AIM1_GSHEET_NAME, "03.2-XRF"),
    "compositional_record": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "compositional": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "xrd_record": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "xrd": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "icp_record": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "icp": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "calorimetry_record": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "calorimetry": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "ultimate_record": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "ultimate": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "autoclave_record": (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave"),
    "autoclave": (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave"),
    "pretreatment_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "pretreatment": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "fermentation_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "fermentation": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "gasification_record": (AIM2_THERMO_GSHEET_NAME, "02-ThermoData"),
    "gasification": (AIM2_THERMO_GSHEET_NAME, "02-ThermoData"),
}

# In-memory worksheet row state used for dry-run / test verification and idempotent note tracking
_WORKSHEET_ROW_STATE: dict[tuple[str, str, str], dict[str, str]] = {}


def clear_worksheet_row_state() -> None:
    """Clear the in-memory Google Sheets row state cache (used in tests)."""
    _WORKSHEET_ROW_STATE.clear()


def get_worksheet_row_state(
    sheet_name: str,
    worksheet_name: str,
    record_id: str,
) -> dict[str, str] | None:
    """Inspect the current synced row state for `(sheet_name, worksheet_name, record_id)`."""
    return _WORKSHEET_ROW_STATE.get((sheet_name, worksheet_name, record_id))


def resolve_worksheet_target(
    record_table: str | None = None,
    analysis_type: str | None = None,
) -> tuple[str, str]:
    """Resolve `(gsheet_name, worksheet_name)` for a `record_table` or `analysis_type`."""
    for candidate in (record_table, analysis_type):
        if not candidate:
            continue
        norm = re.sub(r"[^a-z0-9]+", "_", str(candidate).strip().lower()).strip("_")
        if norm in RECORD_WORKSHEET_MAP:
            return RECORD_WORKSHEET_MAP[norm]
        if not norm.endswith("_record") and f"{norm}_record" in RECORD_WORKSHEET_MAP:
            return RECORD_WORKSHEET_MAP[f"{norm}_record"]
        first_token = norm.split("_")[0] if norm else ""
        if first_token and first_token in RECORD_WORKSHEET_MAP:
            return RECORD_WORKSHEET_MAP[first_token]
    return (AIM1_GSHEET_NAME, "03.1-Proximate")


def _col_to_letter(col_idx_1based: int) -> str:
    """Convert a 1-based column index to an A1 column letter (e.g. 1 -> A, 27 -> AA)."""
    result = ""
    n = col_idx_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _sync_via_googleapiclient(
    creds_path: Path,
    sheet_name: str,
    worksheet_name: str,
    record_id: str,
    qc_result: str,
    decision_id: int | str,
    resolved_by_email: str,
    review_note: str,
    resolved_at: datetime | None,
    rationale_chips: str | None,
) -> bool:
    """Perform live Google Sheets writeback using `google-api-python-client` (installed in `webservice`)."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=scopes
    )
    drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    escaped_name = sheet_name.replace("'", "\\'")
    q = (
        f"name = '{escaped_name}' and "
        "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    )
    files_resp = (
        drive_svc.files()
        .list(
            q=q,
            spaces="drive",
            fields="files(id, name)",
            pageSize=5,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = files_resp.get("files") or []
    if not files:
        return False
    spreadsheet_id = files[0]["id"]

    sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    range_name = f"'{worksheet_name}'"
    val_resp = (
        sheets_svc.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    all_values = val_resp.get("values") or []
    if not all_values:
        return False

    headers = [
        re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_")
        for h in all_values[0]
    ]
    rec_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"record_id", "id", "observation_id"}),
        None,
    )
    qc_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"qc_result", "qc_pass", "qc_status"}),
        None,
    )
    note_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"note", "notes", "lab_note"}),
        None,
    )
    if rec_col is None:
        return False

    data_updates: list[dict[str, Any]] = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        cell_val = row[rec_col - 1].strip() if (rec_col - 1) < len(row) else ""
        if cell_val == record_id:
            if qc_col is not None and qc_result:
                col_let = _col_to_letter(qc_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_let}{row_idx}",
                        "values": [[qc_result]],
                    }
                )
            if note_col is not None:
                existing_cell_note = (
                    row[note_col - 1].strip() if (note_col - 1) < len(row) else ""
                )
                merged_cell_note = format_qc_audit_note(
                    existing_note=existing_cell_note,
                    decision_id=decision_id,
                    new_qc_pass=qc_result,
                    resolved_by_email=resolved_by_email,
                    review_note=review_note,
                    resolved_at=resolved_at,
                    rationale_chips=rationale_chips,
                )
                col_let = _col_to_letter(note_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_let}{row_idx}",
                        "values": [[merged_cell_note]],
                    }
                )
    if data_updates:
        sheets_svc.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data_updates},
        ).execute()
        return True
    return False


def _sync_via_gspread_if_configured(
    sheet_name: str,
    worksheet_name: str,
    record_id: str,
    qc_result: str,
    updated_note: str,
    decision_id: int | str,
    resolved_by_email: str,
    review_note: str,
    resolved_at: datetime | None,
    rationale_chips: str | None,
) -> bool:
    """Perform live Google Sheets writeback if `BIOSITING_GSHEET_CREDENTIALS_PATH` is configured."""
    creds_path_str = os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
    if not creds_path_str:
        return False

    creds_path = Path(creds_path_str)
    if not creds_path.exists():
        return False

    try:
        import gspread  # type: ignore[import-untyped]
        from gspread.utils import rowcol_to_a1  # type: ignore[import-untyped]
    except ImportError:
        try:
            return _sync_via_googleapiclient(
                creds_path=creds_path,
                sheet_name=sheet_name,
                worksheet_name=worksheet_name,
                record_id=record_id,
                qc_result=qc_result,
                decision_id=decision_id,
                resolved_by_email=resolved_by_email,
                review_note=review_note,
                resolved_at=resolved_at,
                rationale_chips=rationale_chips,
            )
        except Exception:
            return False

    gc = gspread.service_account(filename=str(creds_path))
    sh = gc.open(sheet_name)
    ws = sh.worksheet(worksheet_name)
    all_values = ws.get_all_values()
    if not all_values:
        return False

    headers = [re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_") for h in all_values[0]]
    rec_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"record_id", "id", "observation_id"}),
        None,
    )
    qc_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"qc_result", "qc_pass", "qc_status"}),
        None,
    )
    note_col = next(
        (i + 1 for i, h in enumerate(headers) if h in {"note", "notes", "lab_note"}),
        None,
    )
    if rec_col is None:
        return False

    updates: list[dict[str, Any]] = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        cell_val = row[rec_col - 1].strip() if (rec_col - 1) < len(row) else ""
        if cell_val == record_id:
            if qc_col is not None and qc_result:
                updates.append(
                    {"range": rowcol_to_a1(row_idx, qc_col), "values": [[qc_result]]}
                )
            if note_col is not None:
                existing_cell_note = (
                    row[note_col - 1].strip() if (note_col - 1) < len(row) else ""
                )
                merged_cell_note = format_qc_audit_note(
                    existing_note=existing_cell_note,
                    decision_id=decision_id,
                    new_qc_pass=qc_result,
                    resolved_by_email=resolved_by_email,
                    review_note=review_note,
                    resolved_at=resolved_at,
                    rationale_chips=rationale_chips,
                )
                updates.append(
                    {"range": rowcol_to_a1(row_idx, note_col), "values": [[merged_cell_note]]}
                )
    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        return True
    return False


def writeback_decision_to_gsheet_row(
    decision: QcReviewDecision,
    custom_writer: Callable[[QcReviewDecision, str, str, str, str], None] | None = None,
) -> dict[str, Any]:
    """Perform an idempotent upsert of `qc_result` and `[QC_AUDIT id=<id> ...]` note to Google Sheets.

    Matching `\\[QC_AUDIT\\s+id=<decision_id>[^\\]]*\\]` is replaced in-place so repeated calls
    never append duplicate `[QC_AUDIT ...]` tags.
    """
    sheet_name, worksheet_name = resolve_worksheet_target(
        decision.record_table,
        decision.analysis_type,
    )
    key = (sheet_name, worksheet_name, decision.record_id)
    prior_row = _WORKSHEET_ROW_STATE.get(key, {"qc_result": decision.old_qc_pass or "pass", "note": ""})

    qc_result = (decision.new_qc_pass or prior_row.get("qc_result") or "pass").strip().lower()
    updated_note = format_qc_audit_note(
        existing_note=prior_row.get("note", ""),
        decision_id=decision.id or decision.record_id,
        new_qc_pass=qc_result,
        resolved_by_email=decision.resolved_by_email or decision.submitted_by_email,
        review_note=decision.review_note,
        resolved_at=decision.resolved_at or decision.updated_at,
        rationale_chips=decision.rationale_chips,
    )

    _WORKSHEET_ROW_STATE[key] = {
        "qc_result": qc_result,
        "note": updated_note,
    }

    if custom_writer is not None:
        custom_writer(decision, sheet_name, worksheet_name, qc_result, updated_note)
    else:
        _sync_via_gspread_if_configured(
            sheet_name=sheet_name,
            worksheet_name=worksheet_name,
            record_id=decision.record_id,
            qc_result=qc_result,
            updated_note=updated_note,
            decision_id=decision.id or decision.record_id,
            resolved_by_email=decision.resolved_by_email or decision.submitted_by_email,
            review_note=decision.review_note,
            resolved_at=decision.resolved_at or decision.updated_at,
            rationale_chips=decision.rationale_chips,
        )

    return {
        "sheet_name": sheet_name,
        "worksheet_name": worksheet_name,
        "target": f"{sheet_name}/{worksheet_name}",
        "record_id": decision.record_id,
        "qc_result": qc_result,
        "sheet_note": updated_note,
    }


def sync_single_decision_to_gsheet(
    session: Session,
    decision_id: int,
    admin_email: str,
    csv_path: Path | str | None = None,
    custom_writer: Callable[[QcReviewDecision, str, str, str, str], None] | None = None,
) -> dict[str, Any]:
    """Sync a single `QcReviewDecision` to Google Sheets (Admin-only Stage 2 action).

    Idempotent on repeated calls: if `synced_to_gsheet` is already `True`, performs an
    in-place upsert on the sheet row, updates `gsheet_synced_at` to current UTC time,
    and returns `already_synced: True`.
    """
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QC decision {decision_id} not found.",
        )

    already_synced = bool(decision.synced_to_gsheet)
    now = datetime.now(timezone.utc)

    writeback_info = writeback_decision_to_gsheet_row(
        decision=decision,
        custom_writer=custom_writer,
    )

    decision.synced_to_gsheet = True
    decision.gsheet_synced_at = now
    decision.gsheet_writeback_target = writeback_info["target"]
    decision.updated_at = now
    if not decision.resolved_by_email:
        decision.resolved_by_email = admin_email
    if not decision.resolved_at:
        decision.resolved_at = now

    session.add(decision)
    session.commit()
    session.refresh(decision)

    append_or_update_seed_csv(decision, csv_path=csv_path)
    serialized = serialize_decision(decision)

    return {
        "status": "ok",
        "decision_id": decision.id,
        "already_synced": already_synced,
        "synced_to_gsheet": True,
        "gsheet_synced_at": serialized["gsheet_synced_at"],
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "sheet_note": writeback_info["sheet_note"],
        "decision": serialized,
    }


def sync_pending_decisions_batch_to_gsheet(
    session: Session,
    admin_email: str,
    decision_ids: list[int] | None = None,
    csv_path: Path | str | None = None,
    custom_writer: Callable[[QcReviewDecision, str, str, str, str], None] | None = None,
) -> dict[str, Any]:
    """Batch-sync resolved `QcReviewDecision` rows where `synced_to_gsheet == False`."""
    stmt = select(QcReviewDecision)
    if decision_ids:
        stmt = stmt.where(QcReviewDecision.id.in_(decision_ids))
    else:
        stmt = stmt.where(
            QcReviewDecision.decision_status == "resolved",
            QcReviewDecision.synced_to_gsheet.is_(False),  # type: ignore[union-attr]
        )

    candidates = list(session.exec(stmt).all())
    synced_results: list[dict[str, Any]] = []
    for item in candidates:
        if item.id is None:
            continue
        res = sync_single_decision_to_gsheet(
            session=session,
            decision_id=item.id,
            admin_email=admin_email,
            csv_path=csv_path,
            custom_writer=custom_writer,
        )
        synced_results.append(res)

    return {
        "status": "ok",
        "synced_count": len(synced_results),
        "synced_decision_ids": [r["decision_id"] for r in synced_results],
        "results": synced_results,
    }
