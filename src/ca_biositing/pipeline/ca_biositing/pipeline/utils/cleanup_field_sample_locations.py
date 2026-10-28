"""FK-scoped cleanup utility for redacting sub-county FieldSample LocationAddress rows.

This module inspects ``FieldSample`` location foreign keys
(``sampling_location_id``, ``field_storage_location_id``, and
``field_sample_storage_location_id``), re-points any non-anonymous
``LocationAddress`` references to canonical county-level anonymous
``LocationAddress`` rows, and deletes non-anonymous ``LocationAddress`` rows
that are not referenced by any of the 20 protected non-``FieldSample`` tables.
"""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from sqlmodel import Session, SQLModel, select

import ca_biositing.datamodels.models as _models  # noqa: F401 - ensure all tables registered in SQLModel.metadata
from ca_biositing.datamodels.models import (
    Equipment,
    Experiment,
    FacilityRecord,
    FieldSample,
    InfrastructureBiodieselPlants,
    InfrastructureBiosolidsFacilities,
    InfrastructureCafoManureLocations,
    InfrastructureCombustionPlants,
    InfrastructureDistrictEnergySystems,
    InfrastructureEthanolBiorefineries,
    InfrastructureFoodManufacturersCARB,
    InfrastructureFoodManufacturersEPA,
    InfrastructureFoodProcessingFacilities,
    InfrastructureLandfills,
    InfrastructureLivestockAnaerobicDigesters,
    InfrastructureMswToEnergyAnaerobicDigesters,
    InfrastructureSafAndRenewableDieselPlants,
    InfrastructureTomatoProcessors,
    InfrastructureWastewaterTreatmentPlants,
    LocationAddress,
    LocationSoilType,
    UsdaMarketReport,
)
from ca_biositing.pipeline.utils.geo_utils import (
    ensure_anonymous_county_addresses,
)

logger = logging.getLogger(__name__)

FIELD_SAMPLE_LOCATION_FK_COLUMNS: tuple[str, str, str] = (
    "sampling_location_id",
    "field_storage_location_id",
    "field_sample_storage_location_id",
)

# Explicit list of all 20 non-FieldSample (Model, fk_column_name) pairs
# referencing location_address.id across the schema.
PROTECTED_LOCATION_FK_SPECS: list[tuple[type[SQLModel], str]] = [
    (LocationSoilType, "location_id"),
    (Equipment, "equipment_location_id"),
    (Experiment, "exper_location_id"),
    (UsdaMarketReport, "office_city_id"),
    (FacilityRecord, "location_id"),
    (InfrastructureLandfills, "address_id"),
    (InfrastructureSafAndRenewableDieselPlants, "address_id"),
    (InfrastructureBiodieselPlants, "address_id"),
    (InfrastructureDistrictEnergySystems, "address_id"),
    (InfrastructureCafoManureLocations, "address_id"),
    (InfrastructureFoodProcessingFacilities, "address_id"),
    (InfrastructureLivestockAnaerobicDigesters, "address_id"),
    (InfrastructureWastewaterTreatmentPlants, "address_id"),
    (InfrastructureBiosolidsFacilities, "address_id"),
    (InfrastructureEthanolBiorefineries, "address_id"),
    (InfrastructureMswToEnergyAnaerobicDigesters, "address_id"),
    (InfrastructureFoodManufacturersEPA, "address_id"),
    (InfrastructureTomatoProcessors, "address_id"),
    (InfrastructureFoodManufacturersCARB, "address_id"),
    (InfrastructureCombustionPlants, "address_id"),
]


def _is_canonical_anonymous_address(addr: LocationAddress | None) -> bool:
    """Return True iff ``addr`` is a canonical county-level anonymous row."""
    if addr is None:
        return False
    return (
        bool(addr.geography_id and str(addr.geography_id).strip())
        and addr.is_anonymous is True
        and addr.address_line1 is None
        and addr.address_line2 is None
        and addr.city is None
        and addr.zip is None
        and addr.lat is None
        and addr.lon is None
    )


def get_protected_location_address_ids(session: Session) -> set[int]:
    """Return all ``location_address.id`` values referenced by non-FieldSample tables."""
    protected_ids: set[int] = set()
    queried_table_cols: set[tuple[str, str]] = set()

    for model_cls, fk_col_name in PROTECTED_LOCATION_FK_SPECS:
        fk_col = getattr(model_cls, fk_col_name)
        table_name = getattr(model_cls, "__tablename__", "")
        queried_table_cols.add((table_name, fk_col_name))
        rows = session.exec(select(fk_col).where(fk_col.is_not(None))).all()
        for val in rows:
            if val is not None:
                protected_ids.add(int(val))

    # Dynamic safety net: inspect SQLModel.metadata for any additional non-FieldSample
    # foreign key columns targeting location_address.id.
    for table in SQLModel.metadata.tables.values():
        if table.name == "field_sample":
            continue
        for column in table.columns:
            if (table.name, column.name) in queried_table_cols:
                continue
            for fk in column.foreign_keys:
                if fk.target_fullname == "location_address.id":
                    rows = session.exec(
                        select(column).where(column.is_not(None))
                    ).all()
                    for val in rows:
                        if val is not None:
                            protected_ids.add(int(val))

    return protected_ids


def _ensure_canonical_anonymous_county_address(
    session: Session,
    geoid: str | None,
) -> LocationAddress:
    """Ensure a ``Place`` and canonical anonymous ``LocationAddress`` exist for ``geoid``."""
    normalized_geoid = (str(geoid).strip() if geoid is not None else "") or "06000"
    geoid_to_id = ensure_anonymous_county_addresses(session, [normalized_geoid])
    addr_id = geoid_to_id[normalized_geoid]
    anon_addr = session.get(LocationAddress, addr_id)
    assert anon_addr is not None
    return anon_addr


def cleanup_field_sample_locations(
    session: Session,
    dry_run: bool = True,
) -> dict[str, int]:
    """Re-point FieldSample location FKs to anonymous county rows and purge leaked addresses.

    Args:
        session: Active SQLModel database session.
        dry_run: When True (default), computes and logs summary counts without
            modifying or committing any database records.

    Returns:
        Dictionary of summary counts (never containing raw address values).
    """
    protected_ids = get_protected_location_address_ids(session)

    initial_addresses = session.exec(select(LocationAddress)).all()
    addr_by_id: dict[int, LocationAddress] = {
        addr.id: addr for addr in initial_addresses if addr.id is not None
    }

    samples = session.exec(select(FieldSample)).all()
    repointed_fk_count = 0
    updated_sample_count = 0

    for sample in samples:
        sample_modified = False
        for fk_col in FIELD_SAMPLE_LOCATION_FK_COLUMNS:
            loc_id = getattr(sample, fk_col)
            if loc_id is None:
                continue
            existing_addr = addr_by_id.get(loc_id)
            if (
                existing_addr is None
                or not _is_canonical_anonymous_address(existing_addr)
                or loc_id in protected_ids
            ):
                repointed_fk_count += 1
                sample_modified = True
                if not dry_run:
                    target_geoid = (
                        existing_addr.geography_id
                        if existing_addr is not None and existing_addr.geography_id
                        else "06000"
                    )
                    canon_addr = _ensure_canonical_anonymous_county_address(
                        session, target_geoid
                    )
                    setattr(sample, fk_col, canon_addr.id)

        if sample_modified:
            updated_sample_count += 1
            if not dry_run:
                session.add(sample)

    if not dry_run and updated_sample_count > 0:
        session.flush()

    deletable_addresses = [
        addr
        for addr in initial_addresses
        if addr.id is not None
        and addr.id not in protected_ids
        and not _is_canonical_anonymous_address(addr)
    ]
    deleted_addr_count = len(deletable_addresses)

    if not dry_run:
        for addr in deletable_addresses:
            session.delete(addr)
        session.commit()

    mode_label = "DRY-RUN" if dry_run else "APPLIED"
    logger.info(
        "[%s] FieldSample LocationAddress cleanup summary: "
        "protected_addresses=%d, field_samples_updated=%d, "
        "field_sample_fks_repointed=%d, non_anonymous_addresses_deleted=%d",
        mode_label,
        len(protected_ids),
        updated_sample_count,
        repointed_fk_count,
        deleted_addr_count,
    )

    return {
        "protected_address_count": len(protected_ids),
        "protected_untouched_count": len(protected_ids),
        "field_sample_fks_repointed": repointed_fk_count,
        "field_samples_updated": updated_sample_count,
        "field_samples_repointed_count": updated_sample_count,
        "non_anonymous_addresses_deleted": deleted_addr_count,
        "redacted_or_deleted_address_count": deleted_addr_count,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for FK-scoped FieldSample LocationAddress cleanup."""
    parser = argparse.ArgumentParser(
        description=(
            "Re-point FieldSample location FKs to canonical county-level anonymous "
            "LocationAddress rows and delete non-anonymous unprotected LocationAddress rows."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report counts without mutating the database (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute database updates and deletions.",
    )
    args = parser.parse_args(argv)
    dry_run = not args.apply

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from ca_biositing.datamodels.database import get_engine

    with Session(get_engine()) as session:
        summary = cleanup_field_sample_locations(session, dry_run=dry_run)

    logger.info("Summary counts: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
