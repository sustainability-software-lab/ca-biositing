from __future__ import annotations

from datetime import date

import pandas as pd
from sqlmodel import Session, SQLModel, create_engine, select


def _build_engine():
    from ca_biositing.datamodels.models import (  # noqa: F401
        DataSource,
        Dataset,
        Method,
        MethodCategory,
        Observation,
        Parameter,
        Resource,
        ResourcePriceRecord,
        ResourceProductionRecord,
        Unit,
    )

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(
        engine,
        tables=[
            DataSource.__table__,
            Dataset.__table__,
            Method.__table__,
            MethodCategory.__table__,
            Observation.__table__,
            Parameter.__table__,
            Resource.__table__,
            ResourcePriceRecord.__table__,
            ResourceProductionRecord.__table__,
            Unit.__table__,
        ],
    )
    return engine


def test_load_county_ag_reports_upserts_and_spot_checks(monkeypatch):
    from ca_biositing.datamodels.models import Observation, Parameter, Resource, Unit
    from ca_biositing.pipeline.etl.load.analysis.almond_nsjv import load_county_ag_reports

    engine = _build_engine()
    monkeypatch.setattr("ca_biositing.pipeline.etl.load.analysis.almond_nsjv.get_engine", lambda: engine)

    with Session(engine) as session:
        unit = Unit(name="usd_per_ton")
        resource = Resource(name="almonds")
        parameter_price = Parameter(name="almond_price", description="old", standard_unit_id=None)
        parameter_production = Parameter(name="almond_production", description="old", standard_unit_id=None)
        session.add(unit)
        session.add(resource)
        session.add(parameter_price)
        session.add(parameter_production)
        session.commit()
        session.refresh(unit)
        session.refresh(resource)
        session.refresh(parameter_price)
        session.refresh(parameter_production)

    parameter_df = pd.DataFrame(
        [
            {
                "name": "almond price",
                "description": "county almond price",
                "calculated": False,
                "standard_unit_id": unit.id,
                "etl_run_id": 10,
                "lineage_group_id": 20,
            },
            {
                "name": "almond production",
                "description": "county almond production",
                "calculated": False,
                "standard_unit_id": unit.id,
                "etl_run_id": 10,
                "lineage_group_id": 20,
            },
            {
                "name": "price production weighted average",
                "description": "Price production weighted average",
                "calculated": True,
                "standard_unit_id": unit.id,
                "etl_run_id": 10,
                "lineage_group_id": 20,
            },
        ]
    )

    price_records = pd.DataFrame(
        [
            {
                "resource": "almonds",
                "geoid": "06047",
                "primary_ag_product_id": None,
                "report_start_date": date(2024, 1, 1),
                "report_end_date": date(2024, 12, 31),
                "note": "price row",
                "etl_run_id": 10,
                "lineage_group_id": 20,
            }
        ]
    )

    production_records = pd.DataFrame(
        [
            {
                "resource": "almonds",
                "geoid": "06047",
                "primary_ag_product_id": None,
                "report_date": date(2024, 1, 1),
                "note": "production row",
                "etl_run_id": 10,
                "lineage_group_id": 20,
            }
        ]
    )

    observations = pd.DataFrame(
        [
            {
                "resource": "almonds",
                "geoid": "06047",
                "record_type": "resource_price_record",
                "parameter_id": parameter_price.id,
                "unit_id": unit.id,
                "value": 100.25,
                "year": 2024,
                "etl_run_id": 10,
                "lineage_group_id": 20,
            },
            {
                "resource": "almonds",
                "geoid": "06047",
                "record_type": "resource_production_record",
                "parameter_id": parameter_production.id,
                "unit_id": unit.id,
                "value": 9.5,
                "year": 2024,
                "etl_run_id": 10,
                "lineage_group_id": 20,
            },
        ]
    )

    counts = load_county_ag_reports.fn(
        {
            "parameter": parameter_df,
            "records": {
                "resource_price_record": price_records,
                "resource_production_record": production_records,
            },
            "observation": observations,
        }
    )

    assert counts["parameter"] == 1
    assert counts["resource_price_record"] == 1
    assert counts["resource_production_record"] == 1
    assert counts["observation"] == 2

    with Session(engine) as session:
        updated_parameter = session.exec(select(Parameter).where(Parameter.name == "almond price")).first()
        assert updated_parameter is not None
        assert updated_parameter.description == "county almond price"

        weighted_average_parameter = session.exec(
            select(Parameter).where(Parameter.name == "price production weighted average")
        ).first()
        assert weighted_average_parameter is not None
        assert weighted_average_parameter.calculated is True

        loaded_observation = session.exec(select(Observation).where(Observation.parameter_id == parameter_price.id)).first()
        assert loaded_observation is not None
        assert loaded_observation.record_id == f"resource_price_record|06047|{resource.id}|2024"
        assert loaded_observation.value == 100.25