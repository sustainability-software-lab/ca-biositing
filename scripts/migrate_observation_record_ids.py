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


def _find_candidate_records(session: Session, record_type: str, geoid: str, resource_id: int, year: int):
    if record_type == "resource_price_record":
        rows = session.exec(select(ResourcePriceRecord).where(ResourcePriceRecord.geoid == geoid, ResourcePriceRecord.resource_id == resource_id)).all()
        matches = [r for r in rows if getattr(r, "report_start_date") is not None and getattr(r, "report_start_date").year == year]
        if matches:
            return sorted(matches, key=lambda r: getattr(r, "id", 0))
        matches = [r for r in rows if getattr(r, "report_end_date") is not None and getattr(r, "report_end_date").year == year]
        return sorted(matches, key=lambda r: getattr(r, "id", 0)) if matches else []
    elif record_type == "resource_production_record":
        rows = session.exec(select(ResourceProductionRecord).where(ResourceProductionRecord.geoid == geoid, ResourceProductionRecord.resource_id == resource_id)).all()
        matches = [r for r in rows if getattr(r, "report_date") is not None and getattr(r, "report_date").year == year]
        return sorted(matches, key=lambda r: getattr(r, "id", 0)) if matches else []
    return []


def _pick_preferred_record(matches):
    return sorted(
        matches,
        key=lambda r: (
            getattr(r, "created_at", None) is None,
            getattr(r, "created_at", None) or 0,
            getattr(r, "id", 0),
        ),
    )[0] if matches else None


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
            matches = _find_candidate_records(session, record_type, geoid, resource_id, year)
            candidates.append((o, rid, matches))

        print(f"Found {len(candidates)} candidate observation rows for migration (including unresolved).")

        resolved: list[tuple[int, str, int]] = []
        unresolved: list[tuple[int, str, list[Any]]] = []

        for obs, old, matches in candidates:
            preferred = _pick_preferred_record(matches)
            if preferred is None:
                unresolved.append((getattr(obs, "id", None), old, matches))
                continue
            resolved.append((getattr(obs, "id", None), old, getattr(preferred, "id", None)))

        print(f"Resolved candidates: {len(resolved)}; Unresolved: {len(unresolved)}")

        if unresolved:
            print("\nUnresolved key diagnostics (first 20):")
            for obs_id, old, matches in unresolved[:20]:
                parsed = parse_composite_record_id(old)
                if parsed is None:
                    print((obs_id, old, "unparseable"))
                    continue
                record_type, geoid, resource_id, year = parsed
                print((obs_id, old, len(matches), [
                    (
                        getattr(r, "id", None),
                        getattr(r, "report_start_date", None),
                        getattr(r, "report_end_date", None),
                        getattr(r, "report_date", None),
                        getattr(r, "primary_ag_product_id", None),
                        getattr(r, "freight_terms", None),
                    )
                    for r in matches[:5]
                ]))

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
        deleted = 0
        skipped = 0
        for obs_id, old, new in resolved:
            legacy_row = session.exec(select(Observation).where(Observation.id == obs_id)).one()
            replacement = session.exec(
                select(Observation).where(
                    Observation.record_id == str(new),
                    Observation.record_type == getattr(legacy_row, "record_type", None),
                    Observation.parameter_id == getattr(legacy_row, "parameter_id", None),
                    Observation.unit_id == getattr(legacy_row, "unit_id", None),
                )
            ).first()

            if replacement is not None:
                same_payload = all(
                    getattr(replacement, field, None) == getattr(legacy_row, field, None)
                    for field in ("dataset_id", "value", "note")
                )
                if same_payload:
                    session.delete(legacy_row)
                    deleted += 1
                    continue
                skipped += 1
                print(
                    f"Skipping conflicting legacy row obs_id={obs_id} old_record_id={old} new_record_id={new}; replacement id={getattr(replacement, 'id', None)} has different payload"
                )
                continue

            session.execute(
                Observation.__table__.update().where(Observation.id == obs_id).values(record_id=str(new))
            )
            applied += 1
        session.commit()
        print(f"Applied {applied} updates, deleted {deleted} duplicate legacy rows, skipped {skipped} conflicts.")
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
