"""Migrate Observation.record_id composite keys to numeric PK strings.

Usage:
  python scripts/migrate_observation_record_ids.py --dry-run
  python scripts/migrate_observation_record_ids.py --apply

Dry-run will print candidate updates without modifying the DB.
Apply will perform updates in a transaction.
"""
import argparse
from typing import Tuple
from sqlmodel import Session, select
from ca_biositing.pipeline.utils.engine import get_engine

from ca_biositing.datamodels.models import Observation, ResourcePriceRecord, ResourceProductionRecord


def parse_composite_record_id(record_id: str) -> Tuple[str, str, int, int] | None:
    try:
        parts = record_id.split("|")
        if len(parts) != 4:
            return None
        record_type, geoid, resource_id_s, year_s = parts
        return record_type, geoid, int(resource_id_s), int(year_s)
    except Exception:
        return None


def find_matching_record(session: Session, record_type: str, geoid: str, resource_id: int, year: int):
    if record_type == "resource_price_record":
        # match by report_start_date year
        rows = session.exec(select(ResourcePriceRecord).where(ResourcePriceRecord.geoid == geoid, ResourcePriceRecord.resource_id == resource_id)).all()
        matches = [r for r in rows if getattr(r, "report_start_date") is not None and getattr(r, "report_start_date").year == year]
        if len(matches) == 1:
            return matches[0]
        # fallback: try report_end_date year or any close match
        matches = [r for r in rows if getattr(r, "report_end_date") is not None and getattr(r, "report_end_date").year == year]
        if len(matches) == 1:
            return matches[0]
        return None
    elif record_type == "resource_production_record":
        rows = session.exec(select(ResourceProductionRecord).where(ResourceProductionRecord.geoid == geoid, ResourceProductionRecord.resource_id == resource_id)).all()
        matches = [r for r in rows if getattr(r, "report_date") is not None and getattr(r, "report_date").year == year]
        if len(matches) == 1:
            return matches[0]
        return None
    return None


def migrate(dry_run: bool = True):
    engine = get_engine()
    with Session(engine) as session:
        obs_rows = session.exec(select(Observation).where(Observation.record_type.in_(["resource_price_record", "resource_production_record"]))).all()
        candidates = []
        for o in obs_rows:
            rid = getattr(o, "record_id", None)
            if not isinstance(rid, str):
                continue
            if "|" not in rid:
                continue
            parsed = parse_composite_record_id(rid)
            if parsed is None:
                continue
            record_type, geoid, resource_id, year = parsed
            match = find_matching_record(session, record_type, geoid, resource_id, year)
            if match is None:
                candidates.append((o.id, rid, None))
            else:
                candidates.append((o.id, rid, getattr(match, "id")))

        print(f"Found {len(candidates)} candidate observation rows for migration (including unresolved).")
        resolved = [c for c in candidates if c[2] is not None]
        unresolved = [c for c in candidates if c[2] is None]
        print(f"Resolved candidates: {len(resolved)}; Unresolved: {len(unresolved)}")

        if dry_run:
            print("\nSample resolved updates (obs_id, old_record_id, new_record_id):")
            for c in resolved[:50]:
                print(c)
            if unresolved:
                print("\nSample unresolved (obs_id, old_record_id, None):")
                for c in unresolved[:20]:
                    print(c)
            return 0

        # apply changes
        applied = 0
        for obs_id, old, new in resolved:
            session.exec(select(Observation).where(Observation.id == obs_id)).one()
            session.execute(
                Observation.__table__.update().where(Observation.id == obs_id).values(record_id=str(new))
            )
            applied += 1
        session.commit()
        print(f"Applied {applied} updates.")
        if unresolved:
            print(f"{len(unresolved)} observations could not be resolved; see sample below:")
            for c in unresolved[:20]:
                print(c)
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply updates. If not set, runs dry-run.")
    args = parser.parse_args()
    return migrate(dry_run=not args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
