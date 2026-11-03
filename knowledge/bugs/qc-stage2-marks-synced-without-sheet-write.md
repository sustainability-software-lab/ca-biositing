---
type: Bug
title: Stage 2 sync marks a QC decision synced even when no sheet cell was written
description: "The webservice sync ignores whether the gspread write happened, so a missing creds file or unmatched record_id marks the decision synced and lets the next ETL revert it."
tags: [qc, gsheet, data-integrity, bug]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:08Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/gsheet_sync_service.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_protected_records.py", "tests/webservice/test_qc_review.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_qc_writeback.py"]
sources: ["commit ca71a99", "commit 00a7146"]
governance: context
stale_after: "2026-12-31"
---

## Symptom
An admin runs Stage 2 for a decision. The API returns `synced_to_gsheet: true`, but the Google Sheet is unchanged. Because the decision is now synced, `qc_protected_records` stops protecting it, and the next ETL run overwrites `qc_pass` and `note` in PostgreSQL with the stale sheet values.

## Location
- `services/gsheet_sync_service.py:352-357`: `_sync_via_gspread_if_configured(...)` is called and its return value is discarded.
- `services/gsheet_sync_service.py:223-314`: returns False with no write when `BIOSITING_GSHEET_CREDENTIALS_PATH` is empty (238), the file is missing (242), the sheet is empty (262 area), or no row matches `record_id` (end of function, returns False when there are no updates).
- `services/gsheet_sync_service.py:403`: `decision.synced_to_gsheet = True` runs unconditionally.
- Consumer: `pipeline/ca_biositing/pipeline/utils/qc_protected_records.py:52` filters on `synced_to_gsheet IS FALSE`.

## Contrast
The pipeline copy `utils/gsheet_qc_writeback.py` raises `ValueError` when the record is not found (around line 225) and only then sets the flag.

## Test coverage
`tests/webservice/test_qc_review.py:261-407` runs Stage 2 without `BIOSITING_GSHEET_CREDENTIALS_PATH` and asserts `synced_to_gsheet is True`. So the silent path is what the test expects. No test checks that the sheet was modified.

## Evidence and status
Code reading. Not reproduced against a sheet. The chain depends on the ETL loaders at `pipeline/.../etl/load/analysis/*_record.py` reading the sheet after the flag flips.

## Suggested fix (not applied)
Return the boolean from `_sync_via_gspread_if_configured`. Raise (or return an error) when it is False, and set the synced flag only after a confirmed write. Add a test that asserts the sheet cell changed.

## Status
Open at HEAD a2c8de8.

# Related Concepts
- [Stage 2 Google Sheets writeback: webservice path and dormant pipeline copy](../architecture/gsheet-qc-writeback.md): code path with the discarded return
- [QC decisions are protected from ETL overwrite until they reach the Google Sheet](../decisions/qc-decisions-protected-from-etl-overwrite.md): the protection that is lifted too early
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](../architecture/qc-review-decision-ledger.md): synced flag semantics
