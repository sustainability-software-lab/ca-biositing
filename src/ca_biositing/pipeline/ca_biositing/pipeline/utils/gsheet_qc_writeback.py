"""Idempotent Stage 2 Google Sheets writeback utilities for QC Review Decisions.

Writes resolved `QcReviewDecision` rows back to the Aim 1 / Aim 2 Google Sheets
(`qc_result` and `note` columns), replacing `[QC_AUDIT id=<decision_id> ...]`
tags in-place via regex so repeated calls never produce duplicate audit entries.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import gspread
from gspread.utils import rowcol_to_a1
from sqlmodel import Session, select

from ca_biositing.datamodels.models import QcReviewDecision
from ca_biositing.pipeline.utils.qc_ledger_seed import format_qc_audit_note


AIM1_GSHEET_NAME = "Aim 1-Feedstock Collection and Processing Data-BioCirV"
AIM2_BIOCHEM_GSHEET_NAME = "Aim 2-Biomass Biochem Conversion Data-BioCirV"
AIM2_THERMO_GSHEET_NAME = "Aim 2-Thermochem Conversion Data-BioCirV"

RECORD_TABLE_TO_GSHEET_TARGET: Dict[str, Tuple[str, str]] = {
    "proximate_record": (AIM1_GSHEET_NAME, "03.1-Proximate"),
    "xrf_record": (AIM1_GSHEET_NAME, "03.2-XRF"),
    "compositional_record": (AIM1_GSHEET_NAME, "03.3-CmpAna"),
    "xrd_record": (AIM1_GSHEET_NAME, "03.4-XRD"),
    "icp_record": (AIM1_GSHEET_NAME, "03.5-ICP"),
    "calorimetry_record": (AIM1_GSHEET_NAME, "03.6-Caloric"),
    "ultimate_record": (AIM1_GSHEET_NAME, "03.7-Ultimate"),
    "autoclave_record": (AIM2_BIOCHEM_GSHEET_NAME, "01.3-Autoclave"),
    "pretreatment_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.1-PretreatmentData"),
    "fermentation_record": (AIM2_BIOCHEM_GSHEET_NAME, "02.2-BioConversionData"),
    "gasification_record": (AIM2_THERMO_GSHEET_NAME, "02-ThermoData"),
}

ANALYSIS_TYPE_TO_RECORD_TABLE: Dict[str, str] = {
    "proximate": "proximate_record",
    "proximate_analysis": "proximate_record",
    "ultimate": "ultimate_record",
    "ultimate_analysis": "ultimate_record",
    "compositional": "compositional_record",
    "compositional_analysis": "compositional_record",
    "icp": "icp_record",
    "icp_oes_icp_ms": "icp_record",
    "xrf": "xrf_record",
    "xrf_elemental": "xrf_record",
    "xrd": "xrd_record",
    "xrd_crystallinity": "xrd_record",
    "calorimetry": "calorimetry_record",
    "calorimetry_analysis": "calorimetry_record",
    "autoclave": "autoclave_record",
    "pretreatment": "pretreatment_record",
    "pretreatment_hydrolysis": "pretreatment_record",
    "fermentation": "fermentation_record",
    "fermentation_bioconversion": "fermentation_record",
    "gasification": "gasification_record",
}


def _normalize_header(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(raw or "").strip().lower()).strip("_")


def resolve_worksheet_target(
    record_table: Optional[str] = None,
    analysis_type: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Resolve `(spreadsheet_name, worksheet_tab_name)` for a record table or analysis type."""
    for candidate in (record_table, analysis_type):
        if not candidate:
            continue
        norm = re.sub(r"[^a-z0-9]+", "_", str(candidate).strip().lower()).strip("_")
        if norm in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[norm]
        mapped = ANALYSIS_TYPE_TO_RECORD_TABLE.get(norm)
        if mapped and mapped in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[mapped]
        if not norm.endswith("_record") and f"{norm}_record" in RECORD_TABLE_TO_GSHEET_TARGET:
            return RECORD_TABLE_TO_GSHEET_TARGET[f"{norm}_record"]
        first_token = norm.split("_")[0] if norm else ""
        if first_token in ANALYSIS_TYPE_TO_RECORD_TABLE:
            mapped_token = ANALYSIS_TYPE_TO_RECORD_TABLE[first_token]
            if mapped_token in RECORD_TABLE_TO_GSHEET_TARGET:
                return RECORD_TABLE_TO_GSHEET_TARGET[mapped_token]

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
    dry_run: bool = False,
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
    if not str(decision.record_id or "").strip():
        raise ValueError(f"QcReviewDecision with id={decision_id} is missing record_id")

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
        (i for i, h in enumerate(headers) if h in {"record_id", "recordid", "id", "observation_id"}),
        None,
    )
    qc_col = next(
        (i for i, h in enumerate(headers) if h in {"qc_result", "qc_pass", "qc_status"}),
        None,
    )
    note_col = next(
        (i for i, h in enumerate(headers) if h in {"note", "notes", "lab_note"}),
        None,
    )
    updated_col = next(
        (
            i
            for i, h in enumerate(headers)
            if h in {"updated_at", "updatedat", "last_updated", "modified_at"}
        ),
        None,
    )
    if record_id_col is None:
        raise ValueError(f"Worksheet '{tab_name}' is missing a 'record_id' column")

    now = datetime.now(timezone.utc)
    updated_at_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    resolved_iso = (
        decision.resolved_at.isoformat()
        if decision.resolved_at is not None
        else now.isoformat()
    )
    reviewer = decision.resolved_by_email or decision.submitted_by_email or "analyst"
    action = decision.decision_action or decision.decision_status or "review"

    updated_note: Optional[str] = None
    matched_row = False
    target_record_id = str(decision.record_id or "").strip().lower()

    for row_idx_1based, row in enumerate(all_values[1:], start=2):
        row_record_id = (
            str(row[record_id_col]).strip() if record_id_col < len(row) else ""
        )
        if not target_record_id or row_record_id.lower() != target_record_id:
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

        if updated_col is not None:
            col_updates.append((updated_col, updated_at_iso))

        if not dry_run:
            _apply_cell_updates(worksheet, row_idx_1based, col_updates)
        break

    if not matched_row:
        raise ValueError(
            f"record_id '{decision.record_id}' not found in worksheet '{tab_name}'"
        )

    if dry_run:
        return {
            "decision_id": decision.id,
            "record_table": decision.record_table,
            "record_id": decision.record_id,
            "already_synced": already_synced,
            "dry_run": True,
            "synced_to_gsheet": bool(decision.synced_to_gsheet),
            "gsheet_synced_at": (
                decision.gsheet_synced_at.isoformat()
                if decision.gsheet_synced_at is not None
                else None
            ),
            "gsheet_writeback_target": f"{gsheet_name}::{tab_name}",
            "updated_note": updated_note,
            "updated_at": updated_at_iso,
        }

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
        "dry_run": False,
        "synced_to_gsheet": True,
        "gsheet_synced_at": decision.gsheet_synced_at.isoformat(),
        "gsheet_writeback_target": decision.gsheet_writeback_target,
        "updated_note": updated_note,
        "updated_at": updated_at_iso,
    }


def writeback_batch_to_gsheet(
    session: Session,
    decision_ids: Optional[List[int]] = None,
    worksheet_client: Optional[Any] = None,
    credentials_path: str = "credentials.json",
    dry_run: bool = False,
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
    synced_count = 0
    failed_count = 0
    for did in target_ids:
        try:
            res = writeback_qc_decision_to_gsheet(
                session=session,
                decision_id=did,
                worksheet_client=worksheet_client,
                credentials_path=credentials_path,
                dry_run=dry_run,
            )
            results.append(res)
            if not dry_run and res.get("synced_to_gsheet") is True:
                synced_count += 1
            elif not dry_run:
                failed_count += 1
        except Exception as exc:
            failed_count += 1
            results.append(
                {
                    "decision_id": did,
                    "synced_to_gsheet": False,
                    "error": str(exc),
                }
            )

    return {
        "synced_count": 0 if dry_run else synced_count,
        "failed_count": failed_count,
        "dry_run": dry_run,
        "results": results,
    }


def diagnose_gsheet_writeback(
    credentials_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect Google Sheets service account credentials, Drive visibility, and target worksheet headers."""
    cred_str = (
        credentials_path
        or os.environ.get("BIOSITING_GSHEET_CREDENTIALS_PATH", "").strip()
        or "credentials.json"
    )
    cred_path = Path(cred_str)
    report: Dict[str, Any] = {
        "status": "ok",
        "credentials_path": str(cred_path),
        "credentials_file_exists": cred_path.exists(),
        "service_account_email": None,
        "project_id": None,
        "spreadsheets": [],
        "error": None,
    }
    if not cred_path.exists():
        report["status"] = "unconfigured"
        report["error"] = (
            f"Credentials file not found at '{cred_path}'. "
            "Set BIOSITING_GSHEET_CREDENTIALS_PATH or pass --credentials."
        )
        return report

    try:
        raw_creds = json.loads(cred_path.read_text(encoding="utf-8"))
        report["service_account_email"] = raw_creds.get("client_email")
        report["project_id"] = raw_creds.get("project_id")
    except Exception as exc:
        report["status"] = "error"
        report["error"] = f"Failed to parse service account JSON: {exc}"
        return report

    unique_targets: Dict[str, List[str]] = {}
    for gsheet_name, tab_name in RECORD_TABLE_TO_GSHEET_TARGET.values():
        unique_targets.setdefault(gsheet_name, [])
        if tab_name not in unique_targets[gsheet_name]:
            unique_targets[gsheet_name].append(tab_name)

    try:
        gc = gspread.service_account(filename=str(cred_path))
        for gsheet_name, expected_tabs in unique_targets.items():
            try:
                sh = gc.open(gsheet_name)
                tabs_report: Dict[str, Any] = {}
                for tab_name in expected_tabs:
                    try:
                        ws = sh.worksheet(tab_name)
                        all_vals = ws.get_all_values()
                        header_row = all_vals[0] if all_vals else []
                        norm_headers = [_normalize_header(h) for h in header_row]
                        tabs_report[tab_name] = {
                            "found": True,
                            "row_count": max(0, len(all_vals) - 1),
                            "has_record_id": any(
                                h in {"record_id", "recordid", "id", "observation_id"}
                                for h in norm_headers
                            ),
                            "has_qc_col": any(
                                h in {"qc_result", "qc_pass", "qc_status"}
                                for h in norm_headers
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
                    except Exception as tab_exc:
                        tabs_report[tab_name] = {
                            "found": False,
                            "error": str(tab_exc),
                        }
                        report["status"] = "warning"
                report["spreadsheets"].append(
                    {
                        "sheet_name": gsheet_name,
                        "accessible": True,
                        "spreadsheet_id": getattr(sh, "id", None),
                        "worksheets": tabs_report,
                    }
                )
            except Exception as sh_exc:
                report["spreadsheets"].append(
                    {
                        "sheet_name": gsheet_name,
                        "accessible": False,
                        "error": (
                            f"Cannot open spreadsheet '{gsheet_name}' as "
                            f"{report['service_account_email']}: {sh_exc}"
                        ),
                    }
                )
                report["status"] = "warning"
    except Exception as exc:
        report["status"] = "warning"
        report["error"] = f"gspread diagnostic probe error: {exc}"

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BioCIRV Stage 2 Google Sheets QC Write-Back & Diagnostic CLI"
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Inspect Google Sheets service account credentials, permissions, and target worksheets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview pending QC decisions and target worksheets without mutating Google Sheets.",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default=None,
        help="Path to service account JSON (defaults to BIOSITING_GSHEET_CREDENTIALS_PATH or credentials.json).",
    )
    args = parser.parse_args()

    if args.diagnose:
        report = diagnose_gsheet_writeback(credentials_path=args.credentials)
        print(json.dumps(report, indent=2))
        return

    if args.dry_run:
        report = diagnose_gsheet_writeback(credentials_path=args.credentials)
        report["dry_run"] = True
        print(json.dumps(report, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
