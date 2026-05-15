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
