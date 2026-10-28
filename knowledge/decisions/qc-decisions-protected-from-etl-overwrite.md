---
type: Decision
title: QC decisions are protected from ETL overwrite until they reach the Google Sheet
description: "Routine ETL reloads skip qc_pass and note for records with an unsynced QC decision, so analyst overrides survive until Stage 2 writes them to the source sheet."
tags: [qc, etl, decision, upsert]
generated: { by: "claude-code:claude-haiku-5-5", at: "2026-10-22T21:27:03Z" }
status: stable
code_refs: ["src/ca_biositing/pipeline/ca_biositing/pipeline/utils/qc_protected_records.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/proximate_record.py", "src/ca_biositing/pipeline/ca_biositing/pipeline/etl/load/analysis/calorimetry_record.py", "tests/pipeline/test_qc_writeback_and_seed.py", "docs/pipeline/ETL_WORKFLOW.md"]
sources: ["https://github.com/sustainability-software-lab/ca-biositing/pull/523", "commit ca71a99", "docs/pipeline/ETL_WORKFLOW.md (commit 3eba913)"]
governance: context
stale_after: "2027-04-22"
---

## Context
Analysts record Stage 1 QC decisions in the Audit Workbench. These change `qc_pass` and `note` in PostgreSQL right away. The source of truth is still the Google Sheet, and the ETL re-reads that sheet on each run. Without a guard, the next ETL run would overwrite the analyst’s `qc_pass` and `note` before Stage 2 has written them back. The PR body for #523 and `docs/pipeline/ETL_WORKFLOW.md` (section "Two-Stage QC Protection") state this rationale.

## Decision
- Protect only the two columns that Stage 1 changes: `qc_pass` and `note`. Other columns keep updating from the sheet (`qc_protected_records.py:19`).
- Protect only while `qc_review_decision.synced_to_gsheet = False` for that `(record_table, record_id)`.
- Once Stage 2 marks the row synced, the sheet is treated as the source of truth and ETL updates all columns again.
- Two code paths implement it: per-row upserts pass the record_id through, and bulk upserts wrap the two columns in a SQL CASE (`build_qc_aware_update_dict`, lines 65-116).

## Consequences
- Re-running ETL after a Stage 1 decision leaves the analyst’s value in place. Tests cover this for the per-row path (`load_proximate_record`) and the bulk path (`load_calorimetry_record`) in `tests/pipeline/test_qc_writeback_and_seed.py`.
- The protection is only as good as Stage 2. If Stage 2 marks a row synced without the sheet being updated, the next ETL run reverts the decision. See `bugs/qc-stage2-marks-synced-without-sheet-write`.
- Alternatives considered: none recorded in the PR or code (inferred). Not stated whether the sheet is ever edited by hand between Stage 1 and Stage 2.

## Scope
Applies to the ten `*_record` loads listed in `architecture/qc-review-decision-ledger`. Does not apply to `observation`.

# Related Concepts
- [QC review decision ledger (qc_review_decision table, lifecycle, seed CSV)](../architecture/qc-review-decision-ledger.md): the table whose synced flag drives the guard
- [Analysis Records ETL flow (proximate, ultimate, compositional, ICP, XRF, calorimetry, XRD)](../architecture/flow-analysis-records.md): main ETL that applies the guard
- [Stage 2 sync marks a QC decision synced even when no sheet cell was written](../bugs/qc-stage2-marks-synced-without-sheet-write.md): failure mode that undoes the protection
