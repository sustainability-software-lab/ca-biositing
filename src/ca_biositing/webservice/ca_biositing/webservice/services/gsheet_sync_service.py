"""Stage 2 Admin Google Sheets writeback service for `ca_biositing.webservice`.

Strictly isolated from `ca_biositing.pipeline` so the `webservice` container boots cleanly
without `pipeline` or top-level `gspread` dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
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
    "xrf_elemental": (AIM1_GSHEET_NAME, "03.2-XRF"),
    "compositional_record": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "compositional": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "compositional_analysis": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "xrd_record": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "xrd": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "xrd_crystallinity": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "icp_record": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "icp": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "icp_oes_icp_ms": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "calorimetry_record": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "calorimetry": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "calorimetry_analysis": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "ultimate_record": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "ultimate": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "ultimate_analysis": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "autoclave_record": (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave"),
    "autoclave": (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave"),
    "pretreatment_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "pretreatment": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "pretreatment_hydrolysis": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "fermentation_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "fermentation": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "fermentation_bioconversion": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "gasification_record": (AIM2_THERMO_GSHEET_NAME, "02-ThermoData"),
    "gasification": (AIM2_THERMO_GSHEET_NAME, "02-ThermoData"),
}

# In-memory worksheet row state used for dry-run / test verification and idempotent note tracking
_WORKSHEET_ROW_STATE: dict[tuple[str, str, str], dict[str, str]] = {}


def get_gsheet_custom_writer() -> Callable[[QcReviewDecision, str, str, str, str], None] | None:
    """FastAPI dependency returning an optional custom Google Sheets writer (used for test injection)."""
    return None


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
    updated_at_iso: str | None = None,
) -> tuple[bool, str | None]:
    """Perform live Google Sheets writeback using `google-api-python-client` (installed in `webservice`)."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        return (False, f"google-api-python-client not installed: {exc}")

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
        return (
            False,
            f"Spreadsheet {sheet_name!r} not found or not shared with service account.",
        )
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
        return (False, f"Worksheet '{sheet_name}/{worksheet_name}' is empty.")

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
    updated_col = next(
        (
            i + 1
            for i, h in enumerate(headers)
            if h in {"updated_at", "updatedat", "last_updated", "modified_at"}
        ),
        None,
    )
    if rec_col is None:
        return (
            False,
            f"Worksheet '{sheet_name}/{worksheet_name}' is missing a 'record_id' column (headers: {headers}).",
        )

    target_rec_id = str(record_id or "").strip().lower()
    ts_str = updated_at_iso or (resolved_at or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    data_updates: list[dict[str, Any]] = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        cell_val = row[rec_col - 1].strip() if (rec_col - 1) < len(row) else ""
        if target_rec_id and cell_val.lower() == target_rec_id:
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
            if updated_col is not None and ts_str:
                col_let = _col_to_letter(updated_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_let}{row_idx}",
                        "values": [[ts_str]],
                    }
                )
    if data_updates:
        sheets_svc.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data_updates},
        ).execute()
        return (True, None)
    return (
        False,
        f"No row with record_id={record_id!r} found in '{sheet_name}/{worksheet_name}' ({len(all_values) - 1} data rows scanned).",
    )


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
    updated_at_iso: str | None = None,
) -> tuple[bool, str | None]:
    """Perform live Google Sheets writeback if `BIOSITING_GSHEET_CREDENTIALS_PATH` is configured."""
    creds_path_str = os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
    if not creds_path_str:
        return (
            False,
            "BIOSITING_GSHEET_CREDENTIALS_PATH environment variable is not set.",
        )

    creds_path = Path(creds_path_str)
    if not creds_path.exists():
        return (
            False,
            f"Google Sheets service account credentials file not found at {creds_path}.",
        )

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
                updated_at_iso=updated_at_iso,
            )
        except Exception as exc:
            return (False, f"Google Sheets API writeback error: {exc}")

    try:
        gc = gspread.service_account(filename=str(creds_path))
        sh = gc.open(sheet_name)
        ws = sh.worksheet(worksheet_name)
        all_values = ws.get_all_values()
        if not all_values:
            return (False, f"Worksheet '{sheet_name}/{worksheet_name}' is empty.")

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
        updated_col = next(
            (
                i + 1
                for i, h in enumerate(headers)
                if h in {"updated_at", "updatedat", "last_updated", "modified_at"}
            ),
            None,
        )
        if rec_col is None:
            return (
                False,
                f"Worksheet '{sheet_name}/{worksheet_name}' is missing a 'record_id' column (headers: {headers}).",
            )

        target_rec_id = str(record_id or "").strip().lower()
        ts_str = updated_at_iso or (resolved_at or datetime.now(timezone.utc)).astimezone(
            timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        updates: list[dict[str, Any]] = []
        for row_idx, row in enumerate(all_values[1:], start=2):
            cell_val = row[rec_col - 1].strip() if (rec_col - 1) < len(row) else ""
            if target_rec_id and cell_val.lower() == target_rec_id:
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
                if updated_col is not None and ts_str:
                    updates.append(
                        {"range": rowcol_to_a1(row_idx, updated_col), "values": [[ts_str]]}
                    )
        if updates:
            ws.batch_update(updates, value_input_option="USER_ENTERED")
            return (True, None)
        return (
            False,
            f"No row with record_id={record_id!r} found in '{sheet_name}/{worksheet_name}' ({len(all_values) - 1} data rows scanned).",
        )
    except Exception as exc:
        return (False, f"gspread writeback error for '{sheet_name}/{worksheet_name}': {exc}")


def writeback_decision_to_gsheet_row(
    decision: QcReviewDecision,
    custom_writer: Callable[[QcReviewDecision, str, str, str, str], None] | None = None,
) -> dict[str, Any]:
    """Perform an idempotent upsert of `qc_result`, `[QC_AUDIT id=<id> ...]` note, and `updated_at` to Google Sheets.

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
    effective_resolved_at = decision.resolved_at or decision.updated_at or datetime.now(timezone.utc)
    updated_at_str = effective_resolved_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_note = format_qc_audit_note(
        existing_note=prior_row.get("note", ""),
        decision_id=decision.id or decision.record_id,
        new_qc_pass=qc_result,
        resolved_by_email=decision.resolved_by_email or decision.submitted_by_email,
        review_note=decision.review_note,
        resolved_at=effective_resolved_at,
        rationale_chips=decision.rationale_chips,
    )

    if not str(decision.record_id or "").strip():
        return {
            "sheet_name": sheet_name,
            "worksheet_name": worksheet_name,
            "target": f"{sheet_name}/{worksheet_name}",
            "record_id": decision.record_id,
            "qc_result": qc_result,
            "sheet_note": updated_note,
            "updated_at": updated_at_str,
            "live_synced": False,
            "sync_error": "Decision is missing record_id.",
        }

    if custom_writer is not None:
        try:
            custom_writer(decision, sheet_name, worksheet_name, qc_result, updated_note)
            live_synced = True
            sync_error: str | None = None
        except Exception as exc:
            live_synced = False
            sync_error = f"Google Sheets custom_writer error: {exc}"
    else:
        live_synced, sync_error = _sync_via_gspread_if_configured(
            sheet_name=sheet_name,
            worksheet_name=worksheet_name,
            record_id=decision.record_id,
            qc_result=qc_result,
            updated_note=updated_note,
            decision_id=decision.id or decision.record_id,
            resolved_by_email=decision.resolved_by_email or decision.submitted_by_email,
            review_note=decision.review_note,
            resolved_at=effective_resolved_at,
            rationale_chips=decision.rationale_chips,
            updated_at_iso=updated_at_str,
        )

    if live_synced:
        _WORKSHEET_ROW_STATE[key] = {
            "qc_result": qc_result,
            "note": updated_note,
            "updated_at": updated_at_str,
        }

    return {
        "sheet_name": sheet_name,
        "worksheet_name": worksheet_name,
        "target": f"{sheet_name}/{worksheet_name}",
        "record_id": decision.record_id,
        "qc_result": qc_result,
        "sheet_note": updated_note,
        "updated_at": updated_at_str,
        "live_synced": live_synced,
        "sync_error": sync_error,
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
    and returns `already_synced: True`. Only marks `synced_to_gsheet = True` when the
    live Google Sheets writeback (or injected `custom_writer`) actually succeeds.
    """
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QC decision {decision_id} not found.",
        )

    already_synced = bool(decision.synced_to_gsheet)
    now = datetime.now(timezone.utc)
    if not decision.resolved_by_email:
        decision.resolved_by_email = admin_email
    if not decision.resolved_at:
        decision.resolved_at = now
    decision.updated_at = now

    writeback_info = writeback_decision_to_gsheet_row(
        decision=decision,
        custom_writer=custom_writer,
    )
    live_synced = bool(writeback_info.get("live_synced"))
    sync_error = writeback_info.get("sync_error")

    decision.gsheet_writeback_target = writeback_info["target"]
    if live_synced:
        decision.synced_to_gsheet = True
        decision.gsheet_synced_at = now
    else:
        decision.synced_to_gsheet = False

    session.add(decision)
    session.commit()
    session.refresh(decision)

    append_or_update_seed_csv(decision, csv_path=csv_path)
    serialized = serialize_decision(decision)

    return {
        "status": "ok" if live_synced else "warning",
        "decision_id": decision.id,
        "already_synced": already_synced and live_synced,
        "synced_to_gsheet": bool(decision.synced_to_gsheet),
        "gsheet_synced_at": serialized["gsheet_synced_at"],
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "sheet_note": writeback_info["sheet_note"],
        "updated_at": writeback_info["updated_at"],
        "sync_error": sync_error,
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
        try:
            res = sync_single_decision_to_gsheet(
                session=session,
                decision_id=item.id,
                admin_email=admin_email,
                csv_path=csv_path,
                custom_writer=custom_writer,
            )
            synced_results.append(res)
        except Exception as exc:
            synced_results.append(
                {
                    "status": "warning",
                    "decision_id": item.id,
                    "already_synced": False,
                    "synced_to_gsheet": False,
                    "gsheet_synced_at": None,
                    "gsheet_writeback_target": item.gsheet_writeback_target,
                    "sheet_note": None,
                    "updated_at": None,
                    "sync_error": str(exc),
                    "decision": serialize_decision(item),
                }
            )

    actually_synced = [r for r in synced_results if r.get("synced_to_gsheet")]
    failed_results = [r for r in synced_results if not r.get("synced_to_gsheet")]
    sync_errors = [
        str(r.get("sync_error"))
        for r in failed_results
        if r.get("sync_error")
    ]

    return {
        "status": "ok" if not failed_results else "warning",
        "synced_count": len(actually_synced),
        "synced_decision_ids": [r["decision_id"] for r in actually_synced],
        "failed_count": len(failed_results),
        "failed_decision_ids": [r["decision_id"] for r in failed_results],
        "sync_errors": sync_errors,
        "results": synced_results,
    }


def diagnose_gsheet_writeback() -> dict[str, Any]:
    """Inspect Google Sheets writeback configuration, service account identity, and target sheets."""
    creds_path_str = os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
    report: dict[str, Any] = {
        "status": "ok",
        "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
        "credentials_path": creds_path_str or None,
        "credentials_file_exists": False,
        "service_account_email": None,
        "project_id": None,
        "spreadsheets": [],
        "error": None,
    }
    if not creds_path_str:
        report["status"] = "unconfigured"
        report["error"] = "BIOSITING_GSHEET_CREDENTIALS_PATH environment variable is not set."
        return report

    creds_path = Path(creds_path_str)
    if not creds_path.exists():
        report["status"] = "error"
        report["error"] = f"Credentials file not found at {creds_path}."
        return report

    report["credentials_file_exists"] = True
    try:
        raw_creds = json.loads(creds_path.read_text(encoding="utf-8"))
        report["service_account_email"] = raw_creds.get("client_email")
        report["project_id"] = raw_creds.get("project_id")
    except Exception as exc:
        report["status"] = "error"
        report["error"] = f"Failed to parse service account JSON: {exc}"
        return report

    unique_targets: dict[str, list[str]] = {}
    for sheet_name, ws_name in RECORD_WORKSHEET_MAP.values():
        unique_targets.setdefault(sheet_name, [])
        if ws_name not in unique_targets[sheet_name]:
            unique_targets[sheet_name].append(ws_name)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = service_account.Credentials.from_service_account_file(
            str(creds_path), scopes=scopes
        )
        drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)

        for sheet_name, expected_tabs in unique_targets.items():
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
                    fields="files(id, name, capabilities)",
                    pageSize=5,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            files = files_resp.get("files") or []
            if not files:
                report["spreadsheets"].append(
                    {
                        "sheet_name": sheet_name,
                        "accessible": False,
                        "spreadsheet_id": None,
                        "can_edit": False,
                        "worksheets": {},
                        "error": f"Spreadsheet not found or not shared with {report['service_account_email']}.",
                    }
                )
                report["status"] = "warning"
                continue

            f0 = files[0]
            spreadsheet_id = f0["id"]
            can_edit = bool((f0.get("capabilities") or {}).get("canEdit", True))
            ws_report: dict[str, Any] = {}
            for ws_name in expected_tabs:
                try:
                    header_resp = (
                        sheets_svc.spreadsheets()
                        .values()
                        .get(spreadsheetId=spreadsheet_id, range=f"'{ws_name}'!1:1")
                        .execute()
                    )
                    header_row = (header_resp.get("values") or [[]])[0]
                    norm_headers = [
                        re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_")
                        for h in header_row
                    ]
                    ws_report[ws_name] = {
                        "found": True,
                        "has_record_id": any(
                            h in {"record_id", "id", "observation_id"} for h in norm_headers
                        ),
                        "has_qc_col": any(
                            h in {"qc_result", "qc_pass", "qc_status"} for h in norm_headers
                        ),
                        "has_note_col": any(
                            h in {"note", "notes", "lab_note"} for h in norm_headers
                        ),
                        "has_updated_at_col": any(
                            h in {"updated_at", "updatedat", "last_updated", "modified_at"}
                            for h in norm_headers
                        ),
                        "headers": norm_headers,
                    }
                except Exception as ws_exc:
                    ws_report[ws_name] = {
                        "found": False,
                        "error": str(ws_exc),
                    }
                    report["status"] = "warning"

            report["spreadsheets"].append(
                {
                    "sheet_name": sheet_name,
                    "accessible": True,
                    "spreadsheet_id": spreadsheet_id,
                    "can_edit": can_edit,
                    "worksheets": ws_report,
                }
            )
    except Exception as exc:
        report["status"] = "warning"
        report["error"] = f"Live Google API probe could not complete: {exc}"

    return report
