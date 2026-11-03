---
type: Architecture
title: "Stage 2 Google Sheets writeback: webservice path and dormant pipeline copy"
description: "How an admin’s Stage 2 sync writes qc_result and a [QC_AUDIT] note into the Aim 1 and Aim 2 sheets, and why the pipeline copy in utils is not the live path."
tags: [qc, gsheet, gspread, webservice, pipeline]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:06Z" }
status: stable
code_refs: ["src/ca_biositing/webservice/ca_biositing/webservice/services/gsheet_sync_service.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/gsheet_qc_writeback.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_ledger_seed.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/extract/", "tests/pipeline/test_qc_writeback_and_seed.py", "tests/webservice/test_qc_review.py"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/523", "https://github.com/sustainability-software-lab/ca-biositing/pull/524", "commit ca71a99", "commit 00a7146"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
Stage 2 pushes resolved QC decisions back to the Google Sheets that the ETL reads. Those sheets are the source of truth.

## Key files
| path:line | role |
|---|---|
| webservice services/gsheet_sync_service.py:37-60 | `RECORD_WORKSHEET_MAP`: record table to (sheet, tab), using the sheet names the extractors use |
| webservice services/gsheet_sync_service.py:58 | `_WORKSHEET_ROW_STATE`: in-memory row state, per process |
| webservice services/gsheet_sync_service.py:73-90 | `resolve_worksheet_target`: normalises record_table or analysis_type |
| webservice services/gsheet_sync_service.py:223-314 | `_sync_via_gspread_if_configured`: live write via gspread when `BIOSITING_GSHEET_CREDENTIALS_PATH` is set |
| webservice services/gsheet_sync_service.py:317-372 | `writeback_decision_to_gsheet_row` (builds note, calls writer) |
| webservice services/gsheet_sync_service.py:375-428 | `sync_single_decision_to_gsheet` (sets synced flag) |
| webservice services/gsheet_sync_service.py:431-460 | batch sync |
| pipeline utils/gsheet_qc_writeback.py:26-50 | pipeline copy of the mapping (wrong targets, see bugs) |
| pipeline utils/gsheet_qc_writeback.py:132-247 | pipeline `writeback_qc_decision_to_gsheet`: raises `ValueError` when the record is missing |

## How it works
- Live path (webservice): the admin route calls `sync_single_decision_to_gsheet`, which calls `writeback_decision_to_gsheet_row`, which builds the audit note and calls `_sync_via_gspread_if_configured`. The file gets `qc_result` and `note` cells updated for the row whose `record_id` matches.
- Note format: `[QC_AUDIT id=<decision_id> qc=<pass|fail> by=<email> at=<iso>[ chips=...][: comment]]`. Repeated writes replace the same tag (regex), so there are no duplicates.
- Sheet and tab names are the same as the ETL extractors (for example `Aim 1-Feedstock Collection and Processing Data-BioCirV` and `03.7-Ultimate`), so a write lands where the next ETL run reads.
- Pipeline copy: `utils/gsheet_qc_writeback.py` is imported only by tests and docs. No flow or endpoint calls it.

## Gotchas
- `_sync_via_gspread_if_configured` returns False without writing when the creds file is missing, when the worksheet is empty, or when no row matches the record_id. Its caller ignores the return value, and the decision is still marked synced. See `bugs/qc-stage2-marks-synced-without-sheet-write`.
- Batch mode with explicit `decision_ids` does not filter on `decision_status`. Open or in-review decisions can be pushed to the sheet (`gsheet_sync_service.py:431-438`). Only the no-ids batch selects resolved rows.
- The per-process row state (`_WORKSHEET_ROW_STATE`) is not shared across Cloud Run instances. Idempotency for the note relies on reading the sheet, not on this dict.
- Two divergent mappings exist (see the bugs concept for the pipeline copy). Treat the webservice mapping as authoritative because it matches `pipeline/etl/extract/*.py`.

## History
- 00a7146 (2026-10-19, PR #524): webservice writeback.
- ca71a99 (2026-10-19, PR #523): pipeline writeback utility and its tests.

## Open questions
- Whether `QC_AUDIT_GSHEET_NAME` (documented in `src/ca_biositing/webservice/README.md`) is read anywhere (not found in the config I read; the sheet name is hardcoded).

# Related Concepts
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](qc-review-decision-ledger.md): the table this writes status back to
- [Google Sheets extraction: factory, gsheet_to_df, and retries](pipeline-gsheet-extraction.md): the extractors whose sheet and tab names must match
- [Google Sheets extracts need a service-account credentials.json](../requirements/pipeline-gsheet-credentials-file.md): credentials path convention
- [Stage 2 sync marks a QC decision synced even when no sheet cell was written](../bugs/qc-stage2-marks-synced-without-sheet-write.md): silent success path
- [Pipeline QC writeback utility maps records to the wrong sheet names and tabs](../bugs/pipeline-gsheet-qc-writeback-wrong-targets.md): pipeline copy mismatch
