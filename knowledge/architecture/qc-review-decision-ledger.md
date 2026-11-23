---
type: Architecture
title: "QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)"
description: "The qc_review_decision table records analyst and admin QC decisions, their Stage 1 and Stage 2 state, and a CSV mirror used to survive DB resets."
tags: [qc, datamodels, alembic, webservice, pipeline]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:02Z" }
status: stable
code_refs: ["src/ca_biositing/datamodels/ca_biositing/datamodels/models/qc/qc_review_decision.py", "alembic/versions/0025_add_qc_review_decision_table.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_protected_records.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_ledger_seed.py", "src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py", "data/qc/qc_review_decisions_seed.csv"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/523", "https://github.com/sustainability-software-lab/ca-biositing/pull/524", "commit ca71a99", "commit 00a7146"]
governance: context
stale_after: "2026-12-31"
---

## Purpose
One row per QC decision on an analytical record. A Stage 1 decision changes `qc_pass` and appends a `[QC_AUDIT ...]` note on the record right away. A Stage 2 decision writes the same values back to the source Google Sheet. The ledger also tells ETL loads which records to leave alone (see `decisions/qc-decisions-protected-from-etl-overwrite`).

## Key files
| path:line | role |
|---|---|
| src/ca_biositing/datamodels/ca_biositing/datamodels/models/qc/qc_review_decision.py:13 | `QcReviewDecision(BaseEntity, table=True)`, table `qc_review_decision` |
| alembic/versions/0025_add_qc_review_decision_table.py:24 | creates the table; indexes at lines 75-122 (record_table, record_id, replicate_group_key, resource_name, flag_type, decision_status, assigned_to_email, synced_to_gsheet) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_protected_records.py:19-62 | `PROTECTED_QC_COLUMNS = {qc_pass, note}`; `get_unsynced_qc_protected_record_ids` (query at 49-53) |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_protected_records.py:65-116 | `build_qc_aware_update_dict`: per-row and bulk CASE modes |
| src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py:499 | `record_stage1_decision`: Last-Write-Wins upsert, resets `synced_to_gsheet` to False |
| src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py:263 | `apply_qc_decision_to_db`: writes `qc_pass` and note to the record table |
| src/ca_biositing/webservice/ca_biositing/webservice/services/qc_ledger_service.py:375 | `append_or_update_seed_csv`: CSV mirror written on every Stage 1 and Stage 2 action |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_ledger_seed.py:225 | `load_seed_csv_to_db`: CSV to DB, then optional record overrides |
| src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_ledger_seed.py:36-41 | default CSV path: `data/qc/qc_review_decisions_seed.csv` (env `BIOSITING_QC_SEED_CSV_PATH` overrides) |
| data/qc/qc_review_decisions_seed.csv | header-only at HEAD a2c8de8 (no seeded decisions) |

## How it works
- Columns: `record_table`, `record_id`, `replicate_group_key`, `resource_name`, `analysis_type`, `parameter_name`, `flag_type` (default `analyst_flagged`), `flag_trigger_value`, `old_qc_pass`, `new_qc_pass`, `decision_status` (default `open`), `decision_action`, `rationale_chips`, `review_note`, `submitted_by_email`, `assigned_to_email`, `resolved_by_email`, `resolved_at`, `synced_to_gsheet` (default False), `gsheet_synced_at`, `gsheet_writeback_target`.
- Stage 1 (`record_stage1_decision`): finds the existing row by `(record_table, record_id)` (or by `decision_id`), creates or updates it, sets `synced_to_gsheet = False`, applies the decision to every record in `record_ids`, then mirrors to the CSV.
- Re-editing a decision that is already synced sets it back to unsynced, so it re-enters the Stage 2 queue (`qc_ledger_service.py` around line 610).
- Stage 2 (`sync_single_decision_to_gsheet` in `gsheet_sync_service.py`): writes to the sheet, then sets `synced_to_gsheet = True`, `gsheet_synced_at`, and `gsheet_writeback_target`. Batch mode without ids selects `decision_status == "resolved"` and unsynced rows.
- Seed round trip: `qc_ledger_seed.py` (pipeline) matches incoming rows by `id`, falling back to `(record_table, record_id, flag_type)`. The webservice mirror keys on `(record_table, record_id)`. The two identities differ (see Gotchas).
- Status values seen in code: `open`, `in_review`, `needs_retest`, `resolved`. Assignment counts treat the first three as open.

## Gotchas
- ETL protection matches the exact `record_table` string (`proximate_record`, not `proximate`). `apply_qc_decision_to_db` accepts aliases, so an API caller that sends an alias writes the record but is not protected from ETL. The dashboard client always sends canonical `*_record` names (`analysis/metadata/resource_analysis_dashboard.py:2669-2682`).
- `_count_assigned_open` and the summary use `open`, `in_review`, `needs_retest`. Queue logic depends on these exact strings.
- The webservice writes the seed CSV on every action. Its default path is `parents[6]/data/qc/...`. In the production image only `src/` and `scripts/create_admin.py` are copied (`resources/docker/webservice.dockerfile`), so the write goes to a container-local file that does not persist (inferred from the Dockerfile; not run).
- `tests/webservice` and `tests/pipeline` redirect the CSV to a temp file under pytest (`get_seed_csv_path`).
- Two copies of the audit-note formatter exist (`qc_ledger_service.py:149` and `qc_ledger_seed.py:132`). Their signatures differ, and only the webservice copy adds rationale chips.

## History
- ca71a99 (2026-10-19, PR #523, Peter Smith): model, migration 0025, ETL guard, seed utilities, and their tests. Merged 2026-10-19 17:52 UTC.
- 00a7146 (2026-10-19, PR #524): webservice Stage 1 and Stage 2 API on top of the table.
- 587c1cb (PR #526) and 3eba913 (PR #527): dashboard overlay and docs. See `architecture/qc-review-api-v1-qc`.

## Open questions
- Whether the webservice seed CSV write should exist at all in Cloud Run (inferred: it is ephemeral there).

# Related Concepts
- [Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)](flow-analysis-records.md): ETL loads that read the protection set
- [/v1/qc API: routes, auth, request and response shapes](qc-review-api-v1-qc.md): the API that writes the ledger
- [Stage 2 Google Sheets writeback: webservice path and dormant pipeline copy](gsheet-qc-writeback.md): Stage 2 writeback that clears protection
- [Observation upserts depend on the (record_id, record_type, parameter_id, unit_id) unique key](../requirements/datamodels-observation-upsert-key.md): the other upsert contract; QC guard does not touch observation
