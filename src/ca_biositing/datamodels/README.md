# CA Biositing Data Models

SQLModel-based database models for the
[CA Biositing](https://github.com/sustainability-software-lab/ca-biositing)
project — a research platform for biomass feedstock siting in California.

This package provides 91 ORM models across 15 domain areas (resources, sampling,
analysis, infrastructure, external datasets), 7 materialized analytical views,
and Alembic-managed migrations backed by PostgreSQL with PostGIS.

## Installation

```bash
pip install ca-biositing-datamodels
```

## Quick Start

```python
from sqlmodel import Session, select
from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.models import Resource, FieldSample, Place

engine = get_engine()

with Session(engine) as session:
    resources = session.exec(select(Resource)).all()
```

## Development Workflow

This project uses a dual-track migration system:

1.  **Table Changes**: Modify SQLModel classes and run
    `pixi run migrate-autogenerate -m "message"`.
2.  **Materialized View Fixes**: Modify view expressions in `data_portal_views/`
    and run `pixi run compile-mv-fixes -m "message"`.

To iterate on a view fix migration without creating new revisions:

```bash
pixi run compile-mv-fixes --revision 0009 --force
```

## Data-Quality Filters

All data-quality filtering applied by the materialized views (resource and
provider blacklists, QC pass/fail gating, physically-impossible-value checks
like the ICP ppm cap, production-year cutoffs) is centralized in
[`data_portal_views/common.py`](ca_biositing/datamodels/data_portal_views/common.py).
The file is organized into labeled sections — one per filter dimension
(resource, primary product, experiment, replicate, provider, date, QC status,
physically-impossible-value checks) — so a reviewer can scan it top-to-bottom
and see everything that can exclude a record from a view, even where a dimension
currently has no active exclusions.

Some views (e.g. `usda_census_view`, `mv_usda_county_production`,
`mv_billion_ton_county_production`) deliberately apply none of these filters
because they surface raw external government data rather than BioCirV
lab-analysis records; this is documented in each view's module-level docstring,
not left as a silent omission.

### How to exclude a new resource, provider, etc.

1. Edit the relevant list or constant in `common.py` (e.g. add an entry to
   `EXCLUDED_RESOURCES` with a comment citing the issue/rationale).
2. Compile the change into a migration:
   `pixi run compile-mv-fixes -m "Exclude <thing> - see issue #NNN"`.
3. Review the generated migration diff in `alembic/versions/` - it's a full
   view-body snapshot, so confirm only the intended views/clauses changed.
4. Apply it: `pixi run migrate`.
5. Refresh the views so the new data is reflected: `pixi run refresh-views`.

See
[docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md](../../../docs/datamodels/ALEMBIC_VIEW_WORKFLOW.md)
for the full view/migration workflow.

## Two-Stage QC Audit Ledger (`QcReviewDecision`)

Model `QcReviewDecision`
(`src/ca_biositing/datamodels/ca_biositing/datamodels/models/qc/qc_review_decision.py`,
table `qc_review_decision`, introduced in Alembic migration
`0025_add_qc_review_decision_table`) stores the audit ledger for Stage 1 and
Stage 2 Quality Control (QC) review decisions across all 10 Aim 1 and Aim 2
analytical record tables.

| Column                                                                    | Type                            | Description                                                                                                                                            |
| :------------------------------------------------------------------------ | :------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                                                                      | `Integer` (PK)                  | Auto-incrementing decision identifier (`BaseEntity`).                                                                                                  |
| `record_table`                                                            | `String` (indexed)              | Target analytical record table (e.g., `proximate_record`, `compositional_record`, `icp_record`).                                                       |
| `record_id`                                                               | `String` (indexed)              | Primary `record_id` of the audited analytical observation.                                                                                             |
| `replicate_group_key`                                                     | `String` (nullable, indexed)    | Canonical 6-part replicate cohort key (`{resource}::{sample}::{domain_slug}::{param}::{context_label}::{experiment}`) when auditing a replicate group. |
| `selection_scope`                                                         | `String`                        | Selection granularity: `replicate_group` (default) or `single_record`.                                                                                 |
| `record_ids_json`                                                         | `Text` (nullable)               | JSON array of all target `record_id` strings covered by a replicate-group decision.                                                                    |
| `resource_name`                                                           | `String` (nullable, indexed)    | Lowercase canonical biomass resource name.                                                                                                             |
| `analysis_type`                                                           | `String` (nullable, indexed)    | Analytical domain (`proximate`, `ultimate`, `compositional`, `icp`, `xrf`, `xrd`, `calorimetry`, `fermentation`, `pretreatment`, `gasification`).      |
| `parameter_name`                                                          | `String` (nullable)             | Audited parameter name.                                                                                                                                |
| `flag_type`                                                               | `String`                        | Trigger category (`dixon_q`, `high_rsd`, `sum_exceeds_100`, `physically_impossible`, `analyst_flagged`, `manual_override`).                            |
| `flag_trigger_value`                                                      | `String` (nullable)             | Formatted statistical metric or threshold that triggered the flag.                                                                                     |
| `old_qc_pass` / `new_qc_pass`                                             | `String`                        | Previous and updated `qc_pass` status (`pass` or `fail`).                                                                                              |
| `decision_status`                                                         | `String` (indexed)              | Workflow state (`in_review`, `pending_review`, `approve_pass`, `reject_fail`, `revert`).                                                               |
| `rationale_tags_json`                                                     | `Text` (nullable)               | JSON array of structured rationale tags selected by the reviewer.                                                                                      |
| `review_note`                                                             | `Text`                          | Mandatory human-readable audit rationale note.                                                                                                         |
| `reviewer_email` / `assigned_to_email`                                    | `String` (indexed)              | Reviewer email and assignee email (auto-filled to the signed-in analyst when empty; supports bulk assignment via `/v1/qc/decisions/assign-batch`).     |
| `reviewed_at`                                                             | `DateTime`                      | UTC timestamp of the Stage 1 review action.                                                                                                            |
| `synced_to_gsheet`                                                        | `Boolean` (indexed)             | `False` during Stage 1 (protects `qc_pass` from ETL upsert overwrite); set to `True` after Stage 2 Google Sheets writeback completes.                  |
| `synced_at` / `gsheet_writeback_attempt_count` / `gsheet_writeback_error` | `DateTime` / `Integer` / `Text` | Stage 2 Google Sheets writeback telemetry and error tracking.                                                                                          |

## Portal Bug Reports in `QcReviewDecision` (`record_table="portal_bug_report"`)

Portal bug and data issue submissions dispatched from the unified
**`🐛 Submit Issue`** modal across all BioCirV dashboards
(`POST /v1/qc/github-issue` and `GET /v1/qc/bug-issues`) are persisted in
`qc_review_decision` with `record_table = "portal_bug_report"` and
`flag_type = "bug_report"`, ensuring zero lost reports even when external GitHub
Issues forwarding is unconfigured while remaining isolated from analytical QC
decision summaries and seed exports.

## Key Dependencies

- [SQLModel](https://sqlmodel.tiangolo.com/) — ORM + Pydantic validation
- [SQLAlchemy](https://www.sqlalchemy.org/) >= 2.0
- [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/) — PostGIS support
- [Alembic](https://alembic.sqlalchemy.org/) — database migrations

## Links

- [Repository](https://github.com/sustainability-software-lab/ca-biositing)
- [Issue Tracker](https://github.com/sustainability-software-lab/ca-biositing/issues)

## Contributors

[![Contributors](https://contrib.rocks/image?repo=sustainability-software-lab/ca-biositing)](https://github.com/sustainability-software-lab/ca-biositing/graphs/contributors)

## Acknowledgement

We acknowledge software engineering support from the University of Washington
[Scientific Software Engineering Center (SSEC)](https://escience.washington.edu/software-engineering/ssec/),
as part of the Schmidt Sciences
[Virtual Institute for Scientific Software (VISS)](https://www.schmidtsciences.org/).

## License

CA Biositing Data Models is licensed under the open source
[BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).
