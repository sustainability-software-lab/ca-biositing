import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from prefect import task, get_run_logger
from sqlalchemy.orm import Session
from ca_biositing.pipeline.utils.engine import get_engine

# California FIPS codes used by the static resource info pipeline.
# GEOID format: 2-digit state FIPS + 3-digit county FIPS ("000" = state-level).
_KNOWN_PLACES = {
    "06000": {
        "geoid": "06000",
        "state_name": "california",
        "state_fips": "06",
        "county_name": None,
        "county_fips": "000",
        "region_name": None,
        "agg_level_desc": "STATE",
    },
}


def _get_place_metadata(geoid: str) -> dict:
    """Return Place attributes for a GEOID.

    Known places (e.g. 06000 California state, target counties) are seeded
    via Alembic migration.  This fallback parses the GEOID into state/county
    FIPS components so that any new Place record has at minimum its FIPS
    fields populated.
    """
    return {
        "geoid": geoid,
        "state_fips": geoid[:2] if len(geoid) >= 2 else None,
        "county_fips": geoid[2:] if len(geoid) >= 5 else None,
    }


@task
def load_landiq_resource_mapping(df: pd.DataFrame):
    """
    Upserts LandiqResourceMapping records.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No LandIQ resource mapping data to load.")
        return

    logger.info(f"Upserting {len(df)} LandIQ resource mapping records...")

    try:
        from ca_biositing.datamodels.models import LandiqResourceMapping

        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in LandiqResourceMapping.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} mapping records...")

                    clean_record = {k: v for k, v in record.items() if k in table_columns}
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    # Check for existing mapping (unique by landiq_crop_name and resource_id)
                    existing = session.query(LandiqResourceMapping).filter(
                        LandiqResourceMapping.landiq_crop_name == clean_record['landiq_crop_name']
                    ).filter(
                        LandiqResourceMapping.resource_id == clean_record['resource_id']
                    ).first()

                    if existing:
                        for key, value in clean_record.items():
                            if key not in ['id', 'created_at']:
                                setattr(existing, key, value)
                    else:
                        session.add(LandiqResourceMapping(**clean_record))

                session.commit()
        logger.info("Successfully upserted LandIQ resource mapping records.")
    except Exception as e:
        logger.error(f"Failed to load LandIQ resource mapping: {e}")
        raise

@task
def load_resource_availability(df: pd.DataFrame):
    """
    Upserts ResourceAvailability records.
    """
    try:
        logger = get_run_logger()
    except Exception:
        import logging
        logger = logging.getLogger(__name__)

    if df is None or df.empty:
        logger.info("No resource availability data to load.")
        return

    logger.info(f"Upserting {len(df)} resource availability records...")

    try:
        from ca_biositing.datamodels.models import Place, ResourceAvailability

        now = datetime.now(timezone.utc)
        table_columns = {c.name for c in ResourceAvailability.__table__.columns}
        records = df.replace({np.nan: None}).to_dict(orient='records')

        engine = get_engine()
        with engine.connect() as conn:
            with Session(bind=conn) as session:
                # Ensure referenced Place records exist before inserting availability.
                # Place is a reference table with no dedicated ETL; records are
                # upserted here so the FK constraint is satisfied.
                geoids = {r['geoid'] for r in records if r.get('geoid')}
                for geoid in geoids:
                    existing_place = session.query(Place).filter(Place.geoid == geoid).first()
                    if not existing_place:
                        place_data = _get_place_metadata(geoid)
                        session.add(Place(**place_data))
                        logger.info(f"Created Place record for geoid={geoid}")
                session.flush()

                for i, record in enumerate(records):
                    if i > 0 and i % 500 == 0:
                        logger.info(f"Processed {i} availability records...")

                    clean_record = {k: v for k, v in record.items() if k in table_columns}
                    clean_record['updated_at'] = now
                    if clean_record.get('created_at') is None:
                        clean_record['created_at'] = now

                    # Check for existing availability (unique by resource_id and geoid if applicable,
                    # but for static data we might just use resource_id for now if geoid is null)
                    query = session.query(ResourceAvailability).filter(
                        ResourceAvailability.resource_id == clean_record['resource_id']
                    )

                    if clean_record.get('geoid'):
                        query = query.filter(ResourceAvailability.geoid == clean_record['geoid'])
                    else:
                        query = query.filter(ResourceAvailability.geoid.is_(None))

                    existing = query.first()

                    if existing:
                        for key, value in clean_record.items():
                            if key not in ['id', 'created_at']:
                                setattr(existing, key, value)
                    else:
                        session.add(ResourceAvailability(**clean_record))

                session.commit()
        logger.info("Successfully upserted resource availability records.")
    except Exception as e:
        logger.error(f"Failed to load resource availability: {e}")
        raise
