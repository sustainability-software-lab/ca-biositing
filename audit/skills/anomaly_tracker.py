import gspread
from gspread.exceptions import WorksheetNotFound
from typing import List, Optional
import json
from audit.skills.grouped_outlier_detection import FlaggedObservation
from audit.skills.llm_synthesis import GroupedIssue

def write_anomaly_tracker(
    grouped_issues: List[GroupedIssue],
    target_name: str,
    audit_date: str,
    audit_run_id: str,
    sheet_key: str,
    credentials_path: str,
    evidently_report_url: str = "",
    raw_csv_path: str = "",
    worksheet_name: str = "Anomalies",
) -> str:
    """
    Writes grouped issues to a Google Sheet for collaborative triage.
    Deduplicates based on (audit_date, group_label, target_name).
    """
    if not grouped_issues:
        return ""

    gc = gspread.service_account(filename=credentials_path)
    sh = gc.open_by_key(sheet_key)

    try:
        worksheet = sh.worksheet(worksheet_name)
    except WorksheetNotFound:
        # Create worksheet with new schema
        headers = [
            "audit_date", "audit_run_id", "target_name",
            "priority", "group_label", "hypothesis",
            "affected_parameters", "affected_resources",
            "affected_record_ids", "evidently_finding",
            "recommended_action", "evidently_report_url",
            "raw_csv_path", "Status", "Analyst Notes"
        ]
        worksheet = sh.add_worksheet(title=worksheet_name, rows=1000, cols=len(headers))
        worksheet.append_row(headers)

    # Fetch existing data for deduplication
    existing_data = worksheet.get_all_values()
    existing_keys = set()
    if len(existing_data) > 1:
        # Key: (audit_date, group_label, target_name)
        # audit_date: col 0, group_label: col 4, target_name: col 2
        for row in existing_data[1:]:
            if len(row) > 4:
                existing_keys.add((row[0], row[4], row[2]))

    rows_to_append = []
    for issue in grouped_issues:
        key = (audit_date, issue.group_label, target_name)
        if key in existing_keys:
            continue

        row = [
            audit_date,
            audit_run_id,
            target_name,
            issue.priority,
            issue.group_label,
            issue.hypothesis,
            ", ".join(issue.affected_parameters),
            ", ".join(issue.affected_resources),
            ", ".join(issue.affected_record_ids),
            issue.evidently_finding or "",
            issue.recommended_action,
            evidently_report_url,
            raw_csv_path,
            "New",  # Status
            ""      # Analyst Notes
        ]
        rows_to_append.append(row)

    if rows_to_append:
        worksheet.append_rows(rows_to_append)

    return sh.url

def write_raw_anomaly_tracker(
    flagged: List[FlaggedObservation],
    target_name: str,
    audit_date: str,
    audit_run_id: str,
    sheet_key: str,
    credentials_path: str,
    worksheet_name: str = "Raw Anomalies",
) -> str:
    """
    Writes raw flagged anomalies to a separate worksheet for row-level access.
    Deduplicates based on (record_id, audit_date).
    """
    if not flagged:
        return ""

    gc = gspread.service_account(filename=credentials_path)
    sh = gc.open_by_key(sheet_key)

    try:
        worksheet = sh.worksheet(worksheet_name)
    except WorksheetNotFound:
        headers = [
            "audit_date", "audit_run_id", "target_name", "record_id",
            "resource_name", "parameter_name", "unit", "observed_value",
            "group_mean", "group_std", "group_n", "z_score", "severity",
            "analyst_email", "Status", "Analyst Notes"
        ]
        worksheet = sh.add_worksheet(title=worksheet_name, rows=2000, cols=len(headers))
        worksheet.append_row(headers)

    # Fetch existing data for deduplication
    existing_data = worksheet.get_all_values()
    existing_keys = set()
    if len(existing_data) > 1:
        # Assuming audit_date is col 0 and record_id is col 3
        for row in existing_data[1:]:
            if len(row) > 3:
                existing_keys.add((row[3], row[0]))

    rows_to_append = []
    for obs in flagged:
        key = (str(obs.record_id), audit_date)
        if key in existing_keys:
            continue

        row = [
            audit_date,
            audit_run_id,
            target_name,
            str(obs.record_id),
            obs.resource_name,
            obs.parameter_name,
            obs.unit,
            obs.observed_value,
            obs.group_mean,
            obs.group_std,
            obs.group_n,
            round(obs.z_score, 3),
            obs.severity,
            obs.analyst_email,
            "New",  # Status
            ""      # Analyst Notes
        ]
        rows_to_append.append(row)

    if rows_to_append:
        worksheet.append_rows(rows_to_append)

    return sh.url
