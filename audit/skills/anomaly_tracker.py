import gspread
from gspread.exceptions import WorksheetNotFound
from typing import List
from audit.skills.grouped_outlier_detection import FlaggedObservation

def write_anomaly_tracker(
    flagged: List[FlaggedObservation],
    target_name: str,
    audit_date: str,
    audit_run_id: str,
    sheet_key: str,
    credentials_path: str,
    worksheet_name: str,
) -> str:
    """
    Writes flagged anomalies to a Google Sheet for collaborative triage.
    Deduplicates based on (record_id, audit_date).
    """
    if not flagged:
        return ""

    gc = gspread.service_account(filename=credentials_path)
    sh = gc.open_by_key(sheet_key)

    try:
        worksheet = sh.worksheet(worksheet_name)
    except WorksheetNotFound:
        worksheet = sh.add_worksheet(title=worksheet_name, rows=1000, cols=16)
        headers = [
            "audit_date", "audit_run_id", "target_name", "record_id",
            "resource_name", "parameter_name", "unit", "observed_value",
            "group_mean", "group_std", "group_n", "z_score", "severity",
            "analyst_email", "Status", "Analyst Notes"
        ]
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
