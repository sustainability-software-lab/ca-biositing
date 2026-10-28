from __future__ import annotations

import logging
import sys
import traceback

import numpy as np
import pandas as pd
from prefect import get_run_logger, task
from sqlmodel import Session, select

from ca_biositing.pipeline.utils.engine import get_engine
from ca_biositing.pipeline.utils.geo_utils import (
    ensure_anonymous_county_addresses,
    resolve_county_geoid,
)


def _first_non_empty(record: dict, keys: tuple[str, ...]) -> object:
    """Return the first non-missing value for ``keys`` in ``record``."""
    for key in keys:
        if key not in record:
            continue
        val = record[key]
        if val is None:
            continue
        try:
            if pd.isna(val):
                continue
        except Exception:
            pass
        if isinstance(val, str) and not val.strip():
            continue
        return val
    return None


@task
def load_location_address(df: pd.DataFrame) -> None:
    """Upsert canonical county-level anonymous ``LocationAddress`` records.

    This loader is exclusively the ``FieldSample`` county-level ``LocationAddress``
    loader. It unconditionally ignores/discards any incoming ``address_line1``,
    ``address_line2``, ``city``, ``zip``, ``lat``, ``lon``, or ``is_anonymous=False``
    values and delegates DB persistence to ``ensure_anonymous_county_addresses``.
    """
    try:
        logger = get_run_logger()
    except Exception:
        logger = logging.getLogger("prefect.task_runs")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    if df is None or df.empty:
        logger.info("No LocationAddress record data to load.")
        return

    logger.info(f"Upserting {len(df)} county-level LocationAddress records...")

    try:
        from ca_biositing.datamodels.models import Place

        records = df.replace({np.nan: None}).to_dict(orient="records")

        etl_run_id = None
        lineage_group_id = None
        for rec in records:
            if etl_run_id is None and rec.get("etl_run_id") is not None:
                etl_run_id = rec.get("etl_run_id")
            if lineage_group_id is None and rec.get("lineage_group_id") is not None:
                lineage_group_id = rec.get("lineage_group_id")

        with Session(get_engine()) as session:
            places = session.exec(select(Place.geoid, Place.county_name)).all()
            county_to_geoid = {
                str(p.county_name).strip().lower(): str(p.geoid).strip()
                for p in places
                if p.county_name and p.geoid
            }

            geoids_to_use: list[str] = []
            for record in records:
                raw_geoid = _first_non_empty(record, ("geography_id",))
                explicit_county = (
                    raw_geoid
                    if raw_geoid not in (None, "", "06000")
                    else _first_non_empty(
                        record,
                        (
                            "sampling_county",
                            "Sampling_County",
                            "prod_county",
                            "Prod_County",
                            "county",
                            "sampling_location",
                            "location_name",
                        ),
                    )
                )
                geoid = resolve_county_geoid(
                    county=explicit_county,
                    latlong=_first_non_empty(
                        record,
                        (
                            "sampling_latlong",
                            "Sampling_LatLong",
                            "prod_latlong",
                            "Prod_LatLong",
                            "latlong",
                        ),
                    ),
                    lat=_first_non_empty(record, ("lat", "latitude")),
                    lon=_first_non_empty(record, ("lon", "long", "longitude")),
                    zip_code=_first_non_empty(
                        record,
                        (
                            "zip",
                            "zip_code",
                            "sampling_zip",
                            "Sampling_Zip",
                            "prod_zip",
                            "Prod_Zip",
                        ),
                    ),
                    city=_first_non_empty(
                        record,
                        (
                            "city",
                            "sampling_city",
                            "Sampling_City",
                            "prod_city",
                            "Prod_City",
                        ),
                    ),
                    street=_first_non_empty(
                        record,
                        (
                            "address_line1",
                            "street",
                            "sampling_street",
                            "Sampling_Street",
                            "prod_street",
                            "Prod_Street",
                        ),
                    ),
                    location_desc=_first_non_empty(
                        record,
                        (
                            "sampling_location",
                            "location_name",
                            "prod_location",
                            "fieldstorage_location",
                            "field_storage_location",
                        ),
                    ),
                    county_to_geoid=county_to_geoid,
                )
                geoids_to_use.append(geoid)

            ensure_anonymous_county_addresses(
                session,
                geoids_to_use,
                etl_run_id=etl_run_id,
                lineage_group_id=lineage_group_id,
            )
            session.commit()

        logger.info("Successfully upserted anonymous county LocationAddress records.")
    except Exception as e:
        logger.error(f"Failed to load LocationAddress records: {type(e).__name__}")
        logger.error("".join(traceback.format_tb(e.__traceback__)))
        raise
