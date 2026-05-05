"""Diagnostic script: print sample observations and record ids for debugging."""
from ca_biositing.pipeline.utils.engine import get_engine
from sqlmodel import Session, select

from ca_biositing.datamodels.models import Observation, ResourcePriceRecord, ResourceProductionRecord


def main():
    engine = get_engine()
    with engine.connect() as conn:
        with Session(bind=conn) as session:
            print("Sample ResourcePriceRecord ids:")
            for r in session.exec(select(ResourcePriceRecord).limit(10)).all():
                print(getattr(r, "id", None), getattr(r, "geoid", None), getattr(r, "resource_id", None))

            print("\nSample ResourceProductionRecord ids:")
            for r in session.exec(select(ResourceProductionRecord).limit(10)).all():
                print(getattr(r, "id", None), getattr(r, "geoid", None), getattr(r, "resource_id", None))

            print("\nSample Observations (all):")
            obs = session.exec(select(Observation).limit(50)).all()
            for o in obs:
                print(getattr(o, "id", None), getattr(o, "record_id", None), getattr(o, "record_type", None), getattr(o, "parameter_id", None), getattr(o, "unit_id", None))

            print("\nSample Observations (almond record types):")
            stmt = select(Observation).where(Observation.record_type.in_(["resource_price_record", "resource_production_record"]))
            almond_obs = session.exec(stmt).all()
            for o in almond_obs[:100]:
                print(
                    getattr(o, "id", None),
                    getattr(o, "record_id", None),
                    getattr(o, "record_type", None),
                    getattr(o, "parameter_id", None),
                    getattr(o, "unit_id", None),
                    getattr(o, "etl_run_id", None),
                    getattr(o, "lineage_group_id", None),
                )

            # Quick statistics on the almond slice
            colon_count = sum(1 for o in almond_obs if isinstance(getattr(o, "record_id", None), str) and ":" in getattr(o, "record_id", ""))
            numeric_string_count = sum(1 for o in almond_obs if isinstance(getattr(o, "record_id", None), str) and getattr(o, "record_id").isdigit())
            print(f"\nSample almond slice colon_count={colon_count}, numeric_string_count={numeric_string_count}")


if __name__ == "__main__":
    main()
