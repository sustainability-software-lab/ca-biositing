"""Self-contained FastAPI service for Stage 2 Admin-only Google Sheets writeback.

Supports live Google Sheets writeback when `BIOSITING_GSHEET_CREDENTIALS_PATH` is
configured, an injectable custom writer hook for testing, and idempotent `[QC_AUDIT ...]`
note updates on worksheet rows. Only marks `synced_to_gsheet = True` when every targeted
record in the decision / replicate group succeeds (`writeback_status == "synced"`).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Callable, Sequence

from fastapi import HTTPException, status
from sqlmodel import Session, select

from ca_biositing.datamodels.models.qc.qc_review_decision import QcReviewDecision
from ca_biositing.webservice.services.qc_ledger_service import (
    AIM1_GSHEET_NAME,
    AIM2_BIOCHEM_GSHEET_NAME,
    AIM2_THERMO_GSHEET_NAME,
    ANALYSIS_DOMAIN_REGISTRY,
    GSHEET_SYNC_ELIGIBLE_STATUSES,
    RECORD_TABLE_GSHEET_TARGET_MAP,
    append_or_update_seed_csv,
    format_qc_audit_note,
    normalize_analysis_domain,
    serialize_decision,
)

logger = logging.getLogger(__name__)

# Type alias for optional injectable worksheet writer used in tests or custom hooks
GsheetRowWriter = Callable[..., Any]


def get_gsheet_custom_writer() -> GsheetRowWriter | None:
    """FastAPI dependency returning an optional custom Google Sheets row writer."""
    return None


# In-memory worksheet row state mirror used to verify idempotent `[QC_AUDIT ...]` updates
# in environments without live Google Sheets API credentials.
_WORKSHEET_ROW_STATE: dict[tuple[str, str, str], dict[str, Any]] = {}


def reset_worksheet_row_state() -> None:
    """Clear the in-memory worksheet row state cache (used by unit tests)."""
    _WORKSHEET_ROW_STATE.clear()


clear_worksheet_row_state = reset_worksheet_row_state


def get_worksheet_row_state(
    sheet_name: str,
    worksheet_name: str,
    record_id: str,
) -> dict[str, Any] | None:
    """Return the latest in-memory worksheet row state for `(sheet_name, worksheet_name, record_id)`."""
    return _WORKSHEET_ROW_STATE.get((sheet_name, worksheet_name, record_id))


def _format_utc_iso(value: Any) -> str:
    """Format a datetime or timestamp value as a UTC ISO-8601 string ending in 'Z'."""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    text = str(value or "").strip()
    if text:
        if text.endswith("+00:00"):
            return text[:-6] + "Z"
        return text
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_gsheet_target(
    record_table: str | None,
    analysis_type: str | None = None,
    record_id: str | None = None,
) -> tuple[str, str, str]:
    """Return `(sheet_name, worksheet_name, key_column)` for a given `record_table` or `analysis_type`."""
    rid_upper = (record_id or "").strip().upper()
    if rid_upper:
        prefix_table_map = (
            ("THERMO-GAS-", "gasification_record"),
            ("GAS-", "gasification_record"),
            ("FERM-", "fermentation_record"),
            ("BIOCONV-", "fermentation_record"),
            ("PRET-", "pretreatment_record"),
            ("PROX-", "proximate_record"),
            ("ULT-", "ultimate_record"),
            ("CMP-", "compositional_record"),
            ("COMP-", "compositional_record"),
            ("CAL-", "calorimetry_record"),
            ("ICP-", "icp_record"),
            ("XRF-", "xrf_record"),
            ("XRD-", "xrd_record"),
            ("AUTO-", "autoclave_record"),
            ("FTNIR-", "ftnir_record"),
            ("RGB-", "rgb_record"),
        )
        raw_tbl = (record_table or "").strip().lower()
        if raw_tbl in {"", "proximate_record"} and not (analysis_type or "").strip():
            for prefix, mapped_table in prefix_table_map:
                if rid_upper.startswith(prefix):
                    record_table = mapped_table
                    break

    canon_table, _ = normalize_analysis_domain(
        record_table=record_table,
        analysis_type=analysis_type,
    )
    if canon_table in ANALYSIS_DOMAIN_REGISTRY:
        _, _, target = ANALYSIS_DOMAIN_REGISTRY[canon_table]
        return target
    if canon_table in RECORD_TABLE_GSHEET_TARGET_MAP:
        return RECORD_TABLE_GSHEET_TARGET_MAP[canon_table]
    return (AIM1_GSHEET_NAME, "03.1-Proximate", "record_id")


def _col_index_to_letter(col_idx_zero_based: int) -> str:
    """Convert a 0-based column index to A1 column letters (0 -> 'A', 25 -> 'Z', 26 -> 'AA')."""
    result = ""
    n = col_idx_zero_based + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _coerce_writeback_result(
    raw_result: Any,
    target_record_ids: Sequence[str],
) -> dict[str, Any]:
    """Normalize a writer return value into a canonical writeback status dict.

    Supports:
    - `dict` with `writeback_status` (`"synced" | "partial_sync" | "skipped" | "failed"`),
      `updated_record_ids`, `missing_record_ids`, `reason`
    - `(bool, str | None)` tuple
    - `bool` or `None` (where `None` from a 5-arg custom writer signifies success)
    """
    all_ids = [str(r).strip() for r in target_record_ids if str(r or "").strip()]
    if raw_result is None:
        return {
            "writeback_status": "synced",
            "updated_record_ids": list(all_ids),
            "missing_record_ids": [],
            "reason": None,
        }
    if isinstance(raw_result, dict):
        raw_status = (
            str(raw_result.get("writeback_status") or "").strip().lower()
        )
        updated_ids = [
            str(r).strip()
            for r in (raw_result.get("updated_record_ids") or [])
            if str(r or "").strip()
        ]
        missing_ids = [
            str(r).strip()
            for r in (raw_result.get("missing_record_ids") or [])
            if str(r or "").strip()
        ]
        reason = raw_result.get("reason") or raw_result.get("error")
        if raw_status == "partial":
            raw_status = "partial_sync"
        if not raw_status:
            if updated_ids and len(updated_ids) == len(all_ids):
                raw_status = "synced"
            elif updated_ids:
                raw_status = "partial_sync"
            else:
                raw_status = "skipped"
        elif (
            raw_status == "synced"
            and updated_ids
            and len(updated_ids) < len(all_ids)
        ):
            raw_status = "partial_sync"
        if raw_status == "synced" and not updated_ids and all_ids:
            updated_ids = list(all_ids)
        if not missing_ids and all_ids:
            updated_lower = {u.lower() for u in updated_ids}
            missing_ids = [r for r in all_ids if r.lower() not in updated_lower]
        if missing_ids and not reason and updated_ids:
            reason = f"Updated {len(updated_ids)}/{len(all_ids)} row(s); missing record_id(s) {missing_ids}."
        return {
            "writeback_status": raw_status,
            "updated_record_ids": updated_ids,
            "missing_record_ids": missing_ids,
            "reason": str(reason) if reason else None,
        }

    if isinstance(raw_result, tuple) and len(raw_result) >= 2:
        ok, err = bool(raw_result[0]), raw_result[1]
        return {
            "writeback_status": "synced" if ok else "skipped",
            "updated_record_ids": list(all_ids) if ok else [],
            "missing_record_ids": [] if ok else list(all_ids),
            "reason": str(err) if err else None,
        }

    ok_bool = bool(raw_result)
    return {
        "writeback_status": "synced" if ok_bool else "skipped",
        "updated_record_ids": list(all_ids) if ok_bool else [],
        "missing_record_ids": [] if ok_bool else list(all_ids),
        "reason": None if ok_bool else "Custom Google Sheets writer returned False.",
    }


def _sync_via_googleapiclient(
    *,
    creds_path: str,
    sheet_name: str,
    worksheet_name: str,
    record_id: str = "",
    target_record_ids: Sequence[str] | None = None,
    key_column: str = "record_id",
    qc_result: str = "pass",
    decision_id: int | str = "",
    resolved_by_email: str = "",
    review_note: str = "",
    resolved_at: datetime | str | None = None,
    rationale_chips: Sequence[str] | str | None = None,
    updated_at_iso: str | None = None,
) -> tuple[bool, str | None] | dict[str, Any]:
    """Fallback Google Sheets writeback using `googleapiclient` + `google.oauth2` when `gspread` is not installed.

    Matches `record_id` values case-insensitively and returns `(True, None)` when all
    targets succeed, `(False, error_msg)` when none succeed, or a partial-status `dict`
    when a subset of `target_record_ids` succeeds.
    """
    target_ids: list[str] = []
    if target_record_ids:
        for rid in target_record_ids:
            clean_rid = str(rid or "").strip()
            if clean_rid and clean_rid not in target_ids:
                target_ids.append(clean_rid)
    if record_id and record_id.strip() and record_id.strip() not in target_ids:
        target_ids.insert(0, record_id.strip())

    try:
        from google.oauth2.service_account import Credentials  # type: ignore[import-untyped]
        from googleapiclient.discovery import build  # type: ignore[import-untyped]
    except ImportError as exc:
        return False, f"Neither gspread nor googleapiclient is available: {exc}"

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        drive_service = build(
            "drive", "v3", credentials=creds, cache_discovery=False
        )
        escaped_name = sheet_name.replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and "
            "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        )
        drive_resp = (
            drive_service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=5,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = drive_resp.get("files", [])
        if not files:
            return (
                False,
                f"Spreadsheet '{sheet_name}' not found via Drive API.",
            )
        spreadsheet_id = files[0]["id"]

        sheets_service = build(
            "sheets", "v4", credentials=creds, cache_discovery=False
        )
        read_Resp = (
            sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"'{worksheet_name}'",
            )
            .execute()
        )
        all_values: list[list[str]] = read_Resp.get("values", [])
        if not all_values:
            return (
                False,
                f"Worksheet '{worksheet_name}' in '{sheet_name}' is empty.",
            )

        headers = [str(h).strip().lower() for h in all_values[0]]
        key_col_lower = (key_column or "record_id").strip().lower()
        key_candidates = [key_col_lower, "record_id", "id", "sample_id"]
        rec_col: int | None = None
        for cand in key_candidates:
            if cand in headers:
                rec_col = headers.index(cand)
                break
        if rec_col is None:
            return (
                False,
                f"Worksheet '{worksheet_name}' is missing '{key_column}' column.",
            )

        qc_col = headers.index("qc_pass") if "qc_pass" in headers else None
        if qc_col is None and "qc_result" in headers:
            qc_col = headers.index("qc_result")
        note_col = headers.index("note") if "note" in headers else None
        if note_col is None and "notes" in headers:
            note_col = headers.index("notes")
        updated_col = (
            headers.index("updated_at") if "updated_at" in headers else None
        )

        # Case-insensitive lookup map: lowercase -> canonical target record_id
        target_lower_map: dict[str, str] = {
            tid.strip().lower(): tid.strip()
            for tid in target_ids
            if tid and tid.strip()
        }

        matched_canonical_ids: list[str] = []
        data_updates: list[dict[str, Any]] = []

        for row_idx, row in enumerate(all_values[1:], start=2):
            cell_val = (
                str(row[rec_col]).strip() if rec_col < len(row) else ""
            )
            if not cell_val:
                continue
            canonical_tid = target_lower_map.get(cell_val.lower())
            if canonical_tid is None:
                continue

            if canonical_tid not in matched_canonical_ids:
                matched_canonical_ids.append(canonical_tid)

            existing_note = (
                str(row[note_col])
                if (note_col is not None and note_col < len(row))
                else ""
            )
            merged_note = format_qc_audit_note(
                existing_note=existing_note,
                decision_id=decision_id,
                new_qc_pass=qc_result,
                resolved_by_email=resolved_by_email,
                review_note=review_note,
                resolved_at=resolved_at,
                rationale_chips=rationale_chips,
            )

            if qc_col is not None:
                col_letter = _col_index_to_letter(qc_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_letter}{row_idx}",
                        "values": [[qc_result]],
                    }
                )
            if note_col is not None:
                col_letter = _col_index_to_letter(note_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_letter}{row_idx}",
                        "values": [[merged_note]],
                    }
                )
            if updated_col is not None and updated_at_iso:
                col_letter = _col_index_to_letter(updated_col)
                data_updates.append(
                    {
                        "range": f"'{worksheet_name}'!{col_letter}{row_idx}",
                        "values": [[updated_at_iso]],
                    }
                )

        if not matched_canonical_ids:
            return (
                False,
                f"record_id(s) {target_ids} not found in '{sheet_name}' -> '{worksheet_name}'.",
            )

        if data_updates:
            sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "valueInputOption": "RAW",
                    "data": data_updates,
                },
            ).execute()

        matched_lower = {m.lower() for m in matched_canonical_ids}
        missing_ids = [
            tid for tid in target_ids if tid.strip().lower() not in matched_lower
        ]
        if missing_ids:
            return {
                "writeback_status": "partial",
                "updated_record_ids": matched_canonical_ids,
                "missing_record_ids": missing_ids,
                "reason": (
                    f"Updated {len(matched_canonical_ids)}/{len(target_ids)} row(s); "
                    f"missing record_id(s) {missing_ids} in '{sheet_name}' -> '{worksheet_name}'."
                ),
            }
        return True, None
    except Exception as exc:
        logger.warning(
            "Google Sheets writeback via googleapiclient failed for %s: %s",
            target_ids,
            exc,
        )
        return False, str(exc)


def _sync_via_gspread_if_configured(
    *,
    sheet_name: str,
    worksheet_name: str,
    record_id: str,
    target_record_ids: Sequence[str] | None = None,
    key_column: str = "record_id",
    qc_result: str,
    decision_id: int | str,
    resolved_by_email: str,
    review_note: str,
    resolved_at: datetime | str | None,
    rationale_chips: Sequence[str] | str | None,
    updated_at_iso: str | None = None,
) -> dict[str, Any]:
    """Attempt live Google Sheets writeback via `gspread` (or `googleapiclient` fallback).

    Performs case-insensitive `record_id` matching across all `target_record_ids` and
    updates all matching rows in a single batch.
    """
    target_ids = [
        str(r).strip()
        for r in (target_record_ids or [record_id])
        if str(r or "").strip()
    ]
    if not target_ids and record_id:
        target_ids = [str(record_id).strip()]

    creds_path = os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
    if not creds_path:
        return {
            "writeback_status": "skipped",
            "updated_record_ids": [],
            "missing_record_ids": list(target_ids),
            "reason": "BIOSITING_GSHEET_CREDENTIALS_PATH environment variable is not set.",
        }
    if not Path(creds_path).exists():
        return {
            "writeback_status": "skipped",
            "updated_record_ids": [],
            "missing_record_ids": list(target_ids),
            "reason": f"Credentials file not found at {creds_path}",
        }

    try:
        import gspread  # type: ignore[import-untyped]
    except ImportError:
        raw_fb = _sync_via_googleapiclient(
            creds_path=creds_path,
            sheet_name=sheet_name,
            worksheet_name=worksheet_name,
            record_id=record_id,
            target_record_ids=target_ids,
            key_column=key_column,
            qc_result=qc_result,
            decision_id=decision_id,
            resolved_by_email=resolved_by_email,
            review_note=review_note,
            resolved_at=resolved_at,
            rationale_chips=rationale_chips,
            updated_at_iso=updated_at_iso,
        )
        return _coerce_writeback_result(raw_fb, target_ids)

    try:
        client = gspread.service_account(filename=creds_path)
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        all_values = worksheet.get_all_values()
        if not all_values:
            return {
                "writeback_status": "skipped",
                "updated_record_ids": [],
                "missing_record_ids": list(target_ids),
                "reason": f"Worksheet '{worksheet_name}' in '{sheet_name}' is empty.",
            }

        headers = [str(h).strip().lower() for h in all_values[0]]
        key_col_lower = (key_column or "record_id").strip().lower()
        key_candidates = [key_col_lower, "record_id", "id", "sample_id"]
        rec_col: int | None = None
        for cand in key_candidates:
            if cand in headers:
                rec_col = headers.index(cand)
                break
        if rec_col is None:
            return {
                "writeback_status": "skipped",
                "updated_record_ids": [],
                "missing_record_ids": list(target_ids),
                "reason": f"Worksheet '{worksheet_name}' is missing '{key_column}' column.",
            }

        qc_col = headers.index("qc_pass") if "qc_pass" in headers else None
        if qc_col is None and "qc_result" in headers:
            qc_col = headers.index("qc_result")
        note_col = headers.index("note") if "note" in headers else None
        if note_col is None and "notes" in headers:
            note_col = headers.index("notes")
        updated_col = (
            headers.index("updated_at") if "updated_at" in headers else None
        )

        target_lower_map: dict[str, str] = {
            tid.strip().lower(): tid.strip()
            for tid in target_ids
            if tid and tid.strip()
        }

        matched_canonical_ids: list[str] = []
        for row_idx, row in enumerate(all_values[1:], start=2):
            cell_val = (
                str(row[rec_col]).strip() if rec_col < len(row) else ""
            )
            if not cell_val:
                continue
            canonical_tid = target_lower_map.get(cell_val.lower())
            if canonical_tid is None:
                continue

            if canonical_tid not in matched_canonical_ids:
                matched_canonical_ids.append(canonical_tid)

            existing_note = (
                str(row[note_col])
                if (note_col is not None and note_col < len(row))
                else ""
            )
            merged_note = format_qc_audit_note(
                existing_note=existing_note,
                decision_id=decision_id,
                new_qc_pass=qc_result,
                resolved_by_email=resolved_by_email,
                review_note=review_note,
                resolved_at=resolved_at,
                rationale_chips=rationale_chips,
            )

            if qc_col is not None:
                worksheet.update_cell(row_idx, qc_col + 1, qc_result)
            if note_col is not None:
                worksheet.update_cell(row_idx, note_col + 1, merged_note)
            if updated_col is not None and updated_at_iso:
                worksheet.update_cell(row_idx, updated_col + 1, updated_at_iso)

        if not matched_canonical_ids:
            return {
                "writeback_status": "skipped",
                "updated_record_ids": [],
                "missing_record_ids": list(target_ids),
                "reason": (
                    f"record_id(s) {target_ids} not found in '{sheet_name}' -> '{worksheet_name}'."
                ),
            }

        matched_lower = {m.lower() for m in matched_canonical_ids}
        missing_ids = [
            tid for tid in target_ids if tid.strip().lower() not in matched_lower
        ]
        if missing_ids:
            return {
                "writeback_status": "partial",
                "updated_record_ids": matched_canonical_ids,
                "missing_record_ids": missing_ids,
                "reason": (
                    f"Updated {len(matched_canonical_ids)}/{len(target_ids)} row(s); "
                    f"missing record_id(s) {missing_ids} in '{sheet_name}' -> '{worksheet_name}'."
                ),
            }

        return {
            "writeback_status": "synced",
            "updated_record_ids": matched_canonical_ids,
            "missing_record_ids": [],
            "reason": None,
        }
    except Exception as exc:
        logger.warning(
            "Google Sheets writeback failed for %s: %s", target_ids, exc
        )
        return {
            "writeback_status": "failed",
            "updated_record_ids": [],
            "missing_record_ids": list(target_ids),
            "reason": str(exc),
        }


def writeback_decision_to_gsheet_row(
    decision: QcReviewDecision,
    target_record_ids: Sequence[str] | None = None,
    custom_writer: GsheetRowWriter | None = None,
) -> dict[str, Any]:
    """Write a Stage 2 QC decision (`qc_pass`/`qc_result` and idempotent `[QC_AUDIT ...]` note) to Google Sheets.

    Returns a dictionary containing `writeback_status` (`"synced" | "partial" | "skipped" | "failed"`),
    `live_synced` (`True` iff `writeback_status == "synced"`), `updated_record_ids`,
    `missing_record_ids`, `reason`, `sync_error`, and `updated_at`.
    """
    sheet_name, worksheet_name, key_column = resolve_gsheet_target(
        decision.record_table,
        decision.analysis_type,
        record_id=decision.record_id,
    )
    qc_result = (decision.new_qc_pass or "review").strip().lower()
    resolver_email = decision.resolved_by_email or decision.submitted_by_email
    resolved_ts = decision.resolved_at or decision.updated_at
    updated_at_str = _format_utc_iso(
        decision.updated_at or datetime.now(timezone.utc)
    )

    all_target_ids: list[str] = []
    if target_record_ids:
        for rid in target_record_ids:
            clean_rid = str(rid or "").strip()
            if clean_rid and clean_rid not in all_target_ids:
                all_target_ids.append(clean_rid)
    if decision.record_id and decision.record_id.strip() not in all_target_ids:
        all_target_ids.insert(0, decision.record_id.strip())

    # Compute merged note per target record without mutating _WORKSHEET_ROW_STATE until writeback succeeds
    merged_notes_by_rid: dict[str, str] = {}
    for rid in all_target_ids:
        key = (sheet_name, worksheet_name, rid)
        prev_state = _WORKSHEET_ROW_STATE.get(key)
        existing_note = prev_state.get("note") if prev_state else None
        merged_note = format_qc_audit_note(
            existing_note=existing_note,
            decision_id=decision.id or rid,
            new_qc_pass=qc_result,
            resolved_by_email=resolver_email,
            review_note=decision.review_note,
            resolved_at=resolved_ts,
            rationale_chips=decision.rationale_chips,
        )
        merged_notes_by_rid[rid] = merged_note

    primary_rid = (
        all_target_ids[0] if all_target_ids else (decision.record_id or "")
    )
    primary_merged_note = merged_notes_by_rid.get(primary_rid, "")

    row_payload: dict[str, Any] = {
        "sheet_name": sheet_name,
        "worksheet_name": worksheet_name,
        "key_column": key_column,
        "record_id": primary_rid,
        "target_record_ids": all_target_ids,
        "qc_pass": qc_result,
        "qc_result": qc_result,
        "note": primary_merged_note,
        "updated_at": updated_at_str,
        "decision_id": decision.id,
        "resolved_by_email": resolver_email,
    }

    dry_run = (
        os.environ.get("BIOSITING_GSHEET_DRY_RUN", "").strip().lower()
        in {"1", "true", "yes"}
    )

    if custom_writer is not None:
        try:
            import inspect

            sig = inspect.signature(custom_writer)
            if len(sig.parameters) >= 5:
                raw_res = custom_writer(
                    decision,
                    sheet_name,
                    worksheet_name,
                    qc_result,
                    primary_merged_note,
                )
            else:
                raw_res = custom_writer(dict(row_payload))
            wb_res = _coerce_writeback_result(raw_res, all_target_ids)
        except Exception as exc:
            logger.warning(
                "Custom Google Sheets writer failed for %s: %s",
                all_target_ids,
                exc,
            )
            wb_res = {
                "writeback_status": "failed",
                "updated_record_ids": [],
                "missing_record_ids": list(all_target_ids),
                "reason": f"Custom Google Sheets writer exception: {exc}",
            }
    elif dry_run:
        wb_res = {
            "writeback_status": "synced",
            "updated_record_ids": list(all_target_ids),
            "missing_record_ids": [],
            "reason": None,
        }
    else:
        raw_res = _sync_via_gspread_if_configured(
            sheet_name=sheet_name,
            worksheet_name=worksheet_name,
            record_id=primary_rid,
            target_record_ids=all_target_ids,
            key_column=key_column,
            qc_result=qc_result,
            decision_id=decision.id or primary_rid,
            resolved_by_email=resolver_email,
            review_note=decision.review_note,
            resolved_at=resolved_ts,
            rationale_chips=decision.rationale_chips,
            updated_at_iso=updated_at_str,
        )
        wb_res = _coerce_writeback_result(raw_res, all_target_ids)

    writeback_status = wb_res["writeback_status"]
    updated_record_ids = wb_res["updated_record_ids"]
    missing_record_ids = wb_res["missing_record_ids"]
    reason = wb_res["reason"]

    # Update in-memory worksheet state only for record_ids that succeeded
    updated_lower = {u.lower() for u in updated_record_ids}
    for rid in all_target_ids:
        if rid.lower() in updated_lower:
            key = (sheet_name, worksheet_name, rid)
            _WORKSHEET_ROW_STATE[key] = {
                "sheet_name": sheet_name,
                "worksheet_name": worksheet_name,
                "key_column": key_column,
                "record_id": rid,
                "qc_pass": qc_result,
                "qc_result": qc_result,
                "note": merged_notes_by_rid.get(rid, primary_merged_note),
                "updated_at": updated_at_str,
                "decision_id": decision.id,
                "resolved_by_email": resolver_email,
            }

    live_synced = (
        writeback_status == "synced"
        and len(updated_record_ids) == len(all_target_ids)
        and len(all_target_ids) > 0
    )

    return {
        **row_payload,
        "sheet_note": primary_merged_note,
        "target": f"{sheet_name}/{worksheet_name}",
        "writeback_target": f"{sheet_name}/{worksheet_name}",
        "writeback_status": writeback_status,
        "live_synced": live_synced,
        "partially_synced": writeback_status in {"partial", "partial_sync"},
        "updated_record_ids": updated_record_ids,
        "missing_record_ids": missing_record_ids,
        "reason": reason,
        "sync_error": reason,
        "updated_at": updated_at_str,
    }


def sync_single_decision_to_gsheet(
    session: Session,
    decision_id: int,
    admin_email: str = "",
    *,
    actor_email: str = "",
    custom_writer: GsheetRowWriter | None = None,
    csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """Execute Stage 2 Admin Google Sheets sync for a single `QcReviewDecision` (and any replicate-group siblings)."""
    from fastapi import HTTPException, status

    effective_actor = (admin_email or actor_email or "admin@lbl.gov").strip()
    decision = session.get(QcReviewDecision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"QC decision {decision_id} not found.",
        )

    already_synced = bool(decision.synced_to_gsheet)

    if decision.decision_status not in GSHEET_SYNC_ELIGIBLE_STATUSES:
        reason_msg = (
            f"Decision {decision_id} has status '{decision.decision_status}' which is ineligible "
            f"for Google Sheets writeback (must be one of {sorted(GSHEET_SYNC_ELIGIBLE_STATUSES)})."
        )
        serialized = serialize_decision(decision)
        return {
            "status": "warning",
            "decision_id": decision.id,
            "record_id": decision.record_id,
            "already_synced": already_synced,
            "synced_to_gsheet": False,
            "partially_synced": False,
            "writeback_status": "skipped",
            "gsheet_synced_at": serialized["gsheet_synced_at"],
            "gsheet_writeback_target": decision.gsheet_writeback_target,
            "updated_at": _format_utc_iso(decision.updated_at),
            "sheet_note": decision.review_note or "",
            "worksheet_note": decision.review_note or "",
            "updated_record_ids": [],
            "missing_record_ids": (
                [decision.record_id] if decision.record_id else []
            ),
            "reason": reason_msg,
            "sync_error": reason_msg,
            "decision": serialized,
            "decisions": [serialized],
        }

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
            if (
                sib.decision_status in GSHEET_SYNC_ELIGIBLE_STATUSES
                and all(sib.id != d.id for d in group_decisions)
            ):
                group_decisions.append(sib)

    target_record_ids = [
        d.record_id.strip()
        for d in group_decisions
        if d.record_id and d.record_id.strip()
    ]

    now = datetime.now(timezone.utc)
    if not decision.resolved_by_email:
        decision.resolved_by_email = effective_actor
    if not decision.resolved_at:
        decision.resolved_at = now
    decision.updated_at = now

    writeback_info = writeback_decision_to_gsheet_row(
        decision=decision,
        target_record_ids=target_record_ids,
        custom_writer=custom_writer,
    )
    writeback_status = str(
        writeback_info.get("writeback_status") or "skipped"
    )
    updated_record_ids = list(writeback_info.get("updated_record_ids") or [])
    missing_record_ids = list(writeback_info.get("missing_record_ids") or [])
    reason = writeback_info.get("reason")
    updated_lower = {u.lower() for u in updated_record_ids}

    synced_decision_ids: list[int] = []
    unsynced_decision_ids: list[int] = []

    for sib in group_decisions:
        if not sib.resolved_by_email:
            sib.resolved_by_email = effective_actor
        if not sib.resolved_at:
            sib.resolved_at = now
        sib.gsheet_writeback_target = writeback_info["writeback_target"]
        sib.updated_at = now

        sib_rid_lower = (sib.record_id or "").strip().lower()
        row_succeeded = bool(sib_rid_lower and sib_rid_lower in updated_lower)
        if writeback_status in {"synced", "partial_sync", "partial"} and row_succeeded:
            sib.synced_to_gsheet = True
            sib.gsheet_synced_at = now
            if sib.id is not None:
                synced_decision_ids.append(sib.id)
        else:
            sib.synced_to_gsheet = False
            sib.gsheet_synced_at = None
            if sib.id is not None:
                unsynced_decision_ids.append(sib.id)

        session.add(sib)

    session.commit()
    for sib in group_decisions:
        session.refresh(sib)
        append_or_update_seed_csv(sib, csv_path=csv_path)

    serialized = serialize_decision(decision)
    all_synced = bool(
        writeback_status == "synced"
        and len(unsynced_decision_ids) == 0
        and len(synced_decision_ids) == len(group_decisions)
    )
    return {
        "status": "ok" if all_synced else "warning",
        "decision_id": decision.id,
        "record_id": decision.record_id,
        "already_synced": already_synced and all_synced,
        "synced_to_gsheet": all_synced,
        "partially_synced": writeback_status in {"partial", "partial_sync"},
        "writeback_status": writeback_status,
        "gsheet_synced_at": serialized["gsheet_synced_at"],
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "updated_at": writeback_info["updated_at"],
        "sheet_note": writeback_info["note"],
        "worksheet_note": writeback_info["note"],
        "updated_record_ids": updated_record_ids,
        "missing_record_ids": missing_record_ids,
        "synced_decision_ids": synced_decision_ids,
        "unsynced_decision_ids": unsynced_decision_ids,
        "group_decision_ids": [
            d.id for d in group_decisions if d.id is not None
        ],
        "reason": reason,
        "sync_error": reason,
        "decision": serialized,
        "decisions": [serialize_decision(d) for d in group_decisions],
    }


def sync_pending_decisions_batch_to_gsheet(
    session: Session,
    admin_email: str = "",
    *,
    actor_email: str = "",
    decision_ids: Sequence[int] | None = None,
    custom_writer: GsheetRowWriter | None = None,
    csv_path: Path | str | None = None,
) -> dict[str, Any]:
    """Batch-sync resolved/unsynced `QcReviewDecision` rows to Google Sheets (Admin-only)."""
    effective_actor = (admin_email or actor_email or "admin@lbl.gov").strip()
    stmt = select(QcReviewDecision).where(
        QcReviewDecision.synced_to_gsheet.is_(False),  # type: ignore[union-attr]
        QcReviewDecision.decision_status.in_(
            list(GSHEET_SYNC_ELIGIBLE_STATUSES)
        ),  # type: ignore[union-attr]
    )
    if decision_ids:
        stmt = stmt.where(QcReviewDecision.id.in_(list(decision_ids)))  # type: ignore[union-attr]

    pending = list(session.exec(stmt).all())
    results: list[dict[str, Any]] = []
    processed_ids: set[int] = set()

    for d in pending:
        if d.id is None or d.id in processed_ids:
            continue
        res = sync_single_decision_to_gsheet(
            session=session,
            decision_id=d.id,
            actor_email=effective_actor,
            custom_writer=custom_writer,
            csv_path=csv_path,
        )
        results.append(res)
        for gid in res.get("group_decision_ids") or [d.id]:
            if isinstance(gid, int):
                processed_ids.add(gid)

    synced_ids: list[int] = []
    skipped_ids: list[int] = []
    failed_ids: list[int] = []
    sync_errors: list[dict[str, Any]] = []

    for r in results:
        wb_status = r.get("writeback_status")
        if r.get("synced_to_gsheet"):
            for sid in r.get("synced_decision_ids") or [r["decision_id"]]:
                if sid not in synced_ids:
                    synced_ids.append(sid)
        else:
            for uid in r.get("unsynced_decision_ids") or [r["decision_id"]]:
                if uid not in failed_ids:
                    failed_ids.append(uid)
                if wb_status in {"skipped", "not_found"} and uid not in skipped_ids:
                    skipped_ids.append(uid)
            sync_errors.append(
                {
                    "decision_id": r["decision_id"],
                    "record_id": r["record_id"],
                    "error": r.get("reason") or r.get("sync_error"),
                }
            )

    return {
        "status": "ok" if not failed_ids else "warning",
        "synced_count": len(synced_ids),
        "skipped_count": len(skipped_ids),
        "failed_count": len(failed_ids),
        "synced_decision_ids": synced_ids,
        "skipped_decision_ids": skipped_ids,
        "failed_decision_ids": failed_ids,
        "sync_errors": sync_errors,
        "results": results,
    }


def diagnose_gsheet_writeback() -> dict[str, Any]:
    """Verify Google Sheets API credentials and spreadsheet read access without mutating cells."""
    creds_path = os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
    configured = bool(creds_path)
    file_exists = bool(creds_path and Path(creds_path).exists())

    target_sheets = sorted(
        {
            AIM1_GSHEET_NAME,
            AIM2_BIOCHEM_GSHEET_NAME,
            AIM2_THERMO_GSHEET_NAME,
        }
    )

    if not configured:
        return {
            "status": "unconfigured",
            "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
            "credentials_configured": False,
            "credentials_file_exists": False,
            "driver": None,
            "target_sheets": target_sheets,
            "accessible_sheets": [],
            "missing_sheets": target_sheets,
            "message": (
                "BIOSITING_GSHEET_CREDENTIALS_PATH is not set. Stage 1 DB + seed CSV "
                "persistence is active, but Stage 2 live Google Sheets writeback is disabled."
            ),
        }

    if not file_exists:
        return {
            "status": "error",
            "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
            "credentials_configured": True,
            "credentials_file_exists": False,
            "credentials_path": creds_path,
            "driver": None,
            "target_sheets": target_sheets,
            "accessible_sheets": [],
            "missing_sheets": target_sheets,
            "message": f"Credentials file does not exist at {creds_path}.",
        }

    accessible_sheets: list[str] = []
    missing_sheets: list[str] = []
    driver_used: str | None = None
    service_account_email: str | None = None

    try:
        import json

        with Path(creds_path).open("r", encoding="utf-8") as fh:
            creds_json = json.load(fh)
            service_account_email = creds_json.get("client_email")
    except Exception:
        service_account_email = None

    try:
        import gspread  # type: ignore[import-untyped]

        driver_used = "gspread"
        client = gspread.service_account(filename=creds_path)
        for s_name in target_sheets:
            try:
                client.open(s_name)
                accessible_sheets.append(s_name)
            except Exception:
                missing_sheets.append(s_name)
    except ImportError:
        try:
            from google.oauth2.service_account import Credentials  # type: ignore[import-untyped]
            from googleapiclient.discovery import build  # type: ignore[import-untyped]

            driver_used = "googleapiclient"
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            drive_service = build(
                "drive", "v3", credentials=creds, cache_discovery=False
            )
            for s_name in target_sheets:
                escaped = s_name.replace("'", "\\'")
                q = (
                    f"name = '{escaped}' and "
                    "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
                )
                resp = (
                    drive_service.files()
                    .list(
                        q=q,
                        spaces="drive",
                        fields="files(id, name)",
                        pageSize=1,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                if resp.get("files"):
                    accessible_sheets.append(s_name)
                else:
                    missing_sheets.append(s_name)
        except Exception as exc:
            return {
                "status": "error",
                "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
                "credentials_configured": True,
                "credentials_file_exists": True,
                "credentials_path": creds_path,
                "service_account_email": service_account_email,
                "driver": driver_used,
                "target_sheets": target_sheets,
                "accessible_sheets": accessible_sheets,
                "missing_sheets": target_sheets,
                "message": f"Google API client initialization failed: {exc}",
            }
    except Exception as exc:
        return {
            "status": "error",
            "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
            "credentials_configured": True,
            "credentials_file_exists": True,
            "credentials_path": creds_path,
            "service_account_email": service_account_email,
            "driver": driver_used,
            "target_sheets": target_sheets,
            "accessible_sheets": accessible_sheets,
            "missing_sheets": target_sheets,
            "message": f"gspread authentication failed: {exc}",
        }

    overall_status = (
        "ok"
        if len(accessible_sheets) == len(target_sheets)
        else ("partial" if accessible_sheets else "error")
    )
    return {
        "status": overall_status,
        "credentials_env_var": "BIOSITING_GSHEET_CREDENTIALS_PATH",
        "credentials_configured": True,
        "credentials_file_exists": True,
        "credentials_path": creds_path,
        "service_account_email": service_account_email,
        "driver": driver_used,
        "target_sheets": target_sheets,
        "accessible_sheets": accessible_sheets,
        "missing_sheets": missing_sheets,
        "message": (
            f"Connected via {driver_used}; {len(accessible_sheets)}/{len(target_sheets)} target spreadsheets accessible."
        ),
    }
