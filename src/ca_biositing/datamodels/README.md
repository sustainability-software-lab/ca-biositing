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
