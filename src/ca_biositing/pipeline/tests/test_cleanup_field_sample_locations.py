"""Unit tests for the FK-scoped FieldSample LocationAddress cleanup utility."""

from __future__ import annotations

import logging

from sqlmodel import SQLModel, select

from ca_biositing.datamodels.models import (
    Equipment,
    Experiment,
    FacilityRecord,
    FieldSample,
    InfrastructureCombustionPlants,
    InfrastructureLandfills,
    LocationAddress,
    LocationSoilType,
    Place,
    UsdaMarketReport,
)
from ca_biositing.pipeline.utils.cleanup_field_sample_locations import (
    PROTECTED_LOCATION_FK_SPECS,
    cleanup_field_sample_locations,
    get_protected_location_address_ids,
)


def test_protected_fk_specs_cover_all_non_field_sample_location_fks():
    """Verify PROTECTED_LOCATION_FK_SPECS covers all 20 non-FieldSample FK columns."""
    metadata_fk_pairs: set[tuple[str, str]] = set()
    for table in SQLModel.metadata.tables.values():
        if table.name == "field_sample":
            continue
        for column in table.columns:
            for fk in column.foreign_keys:
                if fk.target_fullname == "location_address.id":
                    metadata_fk_pairs.add((table.name, column.name))

    spec_fk_pairs = {
        (model_cls.__tablename__, fk_col)
        for model_cls, fk_col in PROTECTED_LOCATION_FK_SPECS
    }

    assert len(PROTECTED_LOCATION_FK_SPECS) == 20
    assert spec_fk_pairs == metadata_fk_pairs


def test_cleanup_preserves_protected_addresses_and_repoints_field_sample_fks(session):
    """Verify protected addresses are untouched while FieldSample & orphan addresses are cleaned."""
    # Seed Place rows (with 06077 missing county_name to test backfill)
    session.add(Place(geoid="06077", state_name="CALIFORNIA", state_fips="06", county_name=None))
    session.add(Place(geoid="06113", state_name="CALIFORNIA", state_fips="06", county_name="Yolo"))
    session.flush()

    # 1. Seed 7 non-anonymous LocationAddress rows referenced by protected tables
    protected_specs = [
        ("100 Landfill Way", "Stockton", "95201", 37.91, -121.25),
        ("200 Biomass Power Rd", "Woodland", "95695", 38.67, -121.77),
        ("300 Soil Pit Ln", "Lodi", "95240", 38.13, -121.27),
        ("400 Lab Equipment Dr", "Davis", "95616", 38.54, -121.76),
        ("500 Experiment Hall", "Davis", "95616", 38.53, -121.75),
        ("600 Market Office Blvd", "Sacramento", "95814", 38.58, -121.49),
        ("700 Facility Ave", "Tracy", "95376", 37.73, -121.42),
    ]
    protected_addrs: list[LocationAddress] = []
    for street, city, zip_code, lat, lon in protected_specs:
        addr = LocationAddress(
            geography_id="06077",
            address_line1=street,
            address_line2="Suite A",
            city=city,
            zip=zip_code,
            lat=lat,
            lon=lon,
            is_anonymous=False,
        )
        session.add(addr)
        protected_addrs.append(addr)
    session.flush()

    session.add(InfrastructureLandfills(project_id="LF-TEST-1", address_id=protected_addrs[0].id))
    session.add(InfrastructureCombustionPlants(combustion_fid=901, address_id=protected_addrs[1].id))
    session.add(LocationSoilType(location_id=protected_addrs[2].id))
    session.add(Equipment(name="Bomb Calorimeter", equipment_location_id=protected_addrs[3].id))
    session.add(Experiment(name="EXP-TEST-1", exper_location_id=protected_addrs[4].id))
    session.add(UsdaMarketReport(slug_name="MKT-TEST-1", office_city_id=protected_addrs[5].id))
    session.add(FacilityRecord(facility_name="Test Biorefinery", location_id=protected_addrs[6].id))
    session.flush()

    # 2. Seed 3 non-anonymous LocationAddress rows referenced exclusively by FieldSample
    sample_sampling_addr = LocationAddress(
        geography_id="06077",
        address_line1="123 Private Grower Rd",
        city="Stockton",
        zip="95202",
        lat=37.9577,
        lon=-121.2908,
        is_anonymous=False,
    )
    sample_field_storage_addr = LocationAddress(
        geography_id="06077",
        address_line1="Corner of West Barn",
        is_anonymous=None,
    )
    sample_producer_addr = LocationAddress(
        geography_id="06113",
        address_line1="456 Producer Way",
        city="Woodland",
        zip="95695",
        lat=38.6785,
        lon=-121.7733,
        is_anonymous=False,
    )
    # 3. Seed 1 unreferenced orphan non-anonymous LocationAddress (from normalize_dataframes)
    orphan_addr = LocationAddress(
        geography_id=None,
        address_line1="789 Leaked Orphan Producer St",
        city="Modesto",
        zip="95354",
        is_anonymous=False,
    )
    session.add_all([
        sample_sampling_addr,
        sample_field_storage_addr,
        sample_producer_addr,
        orphan_addr,
    ])
    session.flush()

    unprotected_ids = {
        sample_sampling_addr.id,
        sample_field_storage_addr.id,
        sample_producer_addr.id,
        orphan_addr.id,
    }

    sample_1 = FieldSample(
        name="SAMPLE-001",
        sampling_location_id=sample_sampling_addr.id,
        field_storage_location_id=sample_field_storage_addr.id,
        field_sample_storage_location_id=sample_producer_addr.id,
    )
    # Second sample whose sampling_location_id shares a protected FacilityRecord address
    sample_2 = FieldSample(
        name="SAMPLE-002",
        sampling_location_id=protected_addrs[6].id,
    )
    session.add_all([sample_1, sample_2])
    session.commit()

    # Verify get_protected_location_address_ids
    protected_id_set = get_protected_location_address_ids(session)
    assert protected_id_set == {a.id for a in protected_addrs}

    # Step A: Run dry_run=True and verify counts without DB mutation
    dry_summary = cleanup_field_sample_locations(session, dry_run=True)
    assert dry_summary["protected_address_count"] == 7
    assert dry_summary["field_samples_updated"] == 2
    assert dry_summary["field_sample_fks_repointed"] == 4
    assert dry_summary["non_anonymous_addresses_deleted"] == 4

    session.refresh(sample_1)
    assert sample_1.sampling_location_id == sample_sampling_addr.id
    for leaked_id in unprotected_ids:
        assert session.get(LocationAddress, leaked_id) is not None

    # Step B: Run dry_run=False and verify DB state
    apply_summary = cleanup_field_sample_locations(session, dry_run=False)
    assert apply_summary == dry_summary

    # All 7 protected LocationAddress rows must remain byte-for-byte untouched
    for idx, (street, city, zip_code, lat, lon) in enumerate(protected_specs):
        preserved = session.get(LocationAddress, protected_addrs[idx].id)
        assert preserved is not None
        assert preserved.address_line1 == street
        assert preserved.address_line2 == "Suite A"
        assert preserved.city == city
        assert preserved.zip == zip_code
        assert preserved.lat == lat
        assert preserved.lon == lon
        assert preserved.is_anonymous is False

    # All 4 unprotected non-anonymous LocationAddress rows must be deleted
    for leaked_id in unprotected_ids:
        assert session.get(LocationAddress, leaked_id) is None

    # FieldSample FKs must now reference canonical county-level anonymous rows
    session.refresh(sample_1)
    session.refresh(sample_2)

    for fk_id, expected_geoid in [
        (sample_1.sampling_location_id, "06077"),
        (sample_1.field_storage_location_id, "06077"),
        (sample_1.field_sample_storage_location_id, "06113"),
        (sample_2.sampling_location_id, "06077"),
    ]:
        assert fk_id is not None
        assert fk_id not in protected_id_set
        anon_row = session.get(LocationAddress, fk_id)
        assert anon_row is not None
        assert anon_row.geography_id == expected_geoid
        assert anon_row.is_anonymous is True
        assert anon_row.address_line1 is None
        assert anon_row.address_line2 is None
        assert anon_row.city is None
        assert anon_row.zip is None
        assert anon_row.lat is None
        assert anon_row.lon is None

    # Both 06077 FKs on sample_1 and sample_2 must share the single canonical 06077 row
    assert sample_1.sampling_location_id == sample_1.field_storage_location_id
    assert sample_1.sampling_location_id == sample_2.sampling_location_id

    # Verify Place.county_name was backfilled for 06077
    place_06077 = session.get(Place, "06077")
    assert place_06077 is not None
    assert place_06077.county_name == "San Joaquin"

    # Step C: Running apply a second time is idempotent
    second_summary = cleanup_field_sample_locations(session, dry_run=False)
    assert second_summary["field_samples_updated"] == 0
    assert second_summary["field_sample_fks_repointed"] == 0
    assert second_summary["non_anonymous_addresses_deleted"] == 0


def test_cleanup_never_logs_or_prints_raw_subcounty_addresses(session, caplog, capsys):
    """Ensure no raw street, city, ZIP, or coordinate values appear in logs or stdout."""
    secret_street = "999 Confidential Orchard Lane"
    secret_city = "SecretGroverVille"
    secret_zip = "95299"

    leaked_addr = LocationAddress(
        geography_id="06077",
        address_line1=secret_street,
        city=secret_city,
        zip=secret_zip,
        lat=37.987654,
        lon=-121.123456,
        is_anonymous=False,
    )
    session.add(leaked_addr)
    session.flush()
    session.add(FieldSample(name="SAMPLE-PRIVACY", sampling_location_id=leaked_addr.id))
    session.commit()

    with caplog.at_level(logging.DEBUG):
        cleanup_field_sample_locations(session, dry_run=True)
        cleanup_field_sample_locations(session, dry_run=False)

    captured = capsys.readouterr()
    combined_output = "\n".join([caplog.text, captured.out, captured.err])

    assert secret_street not in combined_output
    assert secret_city not in combined_output
    assert secret_zip not in combined_output
    assert "37.987654" not in combined_output
    assert "-121.123456" not in combined_output

    # Verify only the canonical anonymous row remains in the DB
    remaining = session.exec(select(LocationAddress)).all()
    assert len(remaining) == 1
    assert remaining[0].is_anonymous is True
    assert remaining[0].address_line1 is None
