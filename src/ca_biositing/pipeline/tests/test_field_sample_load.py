from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from sqlmodel import select

from ca_biositing.datamodels.models import FieldSample, LocationAddress
from ca_biositing.pipeline.etl.load.field_sample import load_field_sample
from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import (
    transform_field_sample,
)
from ca_biositing.pipeline.utils.geo_utils import ensure_anonymous_county_addresses


@patch("ca_biositing.pipeline.etl.load.field_sample.get_engine")
def test_load_field_sample_insert(mock_get_engine, session, engine):
    mock_get_engine.return_value = engine

    df = pd.DataFrame(
        {
            "name": ["Sample 1", "Sample 2"],
            "note": ["Note 1", "Note 2"],
        }
    )

    # Call the task function directly
    load_field_sample.fn(df)

    # Verify records were inserted
    results = session.query(FieldSample).all()
    assert len(results) == 2
    assert results[0].name == "Sample 1"
    assert results[1].name == "Sample 2"


@patch("ca_biositing.pipeline.etl.load.field_sample.get_engine")
def test_load_field_sample_update(mock_get_engine, session, engine):
    mock_get_engine.return_value = engine

    # Pre-insert a record
    existing = FieldSample(name="Sample 1", note="Old Note")
    session.add(existing)
    session.commit()

    df = pd.DataFrame(
        {
            "name": ["Sample 1"],
            "note": ["New Note"],
        }
    )

    # Call the task function directly
    load_field_sample.fn(df)

    # Verify record was updated
    updated = session.query(FieldSample).filter(FieldSample.name == "Sample 1").one()
    assert updated.note == "New Note"

    # Ensure no duplicate was created
    assert session.query(FieldSample).count() == 1


@patch("ca_biositing.pipeline.etl.load.field_sample.get_engine")
def test_load_field_sample_preserves_all_three_location_fks(
    mock_get_engine, session, engine
):
    """Verify load_field_sample preserves sampling, field_storage, and producer location FKs."""
    mock_get_engine.return_value = engine

    addr_map = ensure_anonymous_county_addresses(
        session, ["06077", "06019", "06113"]
    )
    session.commit()

    id_06077 = addr_map["06077"]
    id_06019 = addr_map["06019"]
    id_06113 = addr_map["06113"]

    df = pd.DataFrame(
        {
            "name": ["Sample FK Preserve"],
            "note": ["Initial"],
            "sampling_location_id": [id_06077],
            "field_storage_location_id": [id_06019],
            "field_sample_storage_location_id": [id_06113],
        }
    )

    load_field_sample.fn(df)

    sample = session.exec(
        select(FieldSample).where(FieldSample.name == "Sample FK Preserve")
    ).one()
    assert sample.sampling_location_id == id_06077
    assert sample.field_storage_location_id == id_06019
    assert sample.field_sample_storage_location_id == id_06113

    # Update note while keeping the same FK IDs
    df_update = pd.DataFrame(
        {
            "name": ["Sample FK Preserve"],
            "note": ["Updated"],
            "sampling_location_id": [id_06077],
            "field_storage_location_id": [id_06019],
            "field_sample_storage_location_id": [id_06113],
        }
    )
    load_field_sample.fn(df_update)

    session.expire_all()
    updated = session.exec(
        select(FieldSample).where(FieldSample.name == "Sample FK Preserve")
    ).one()
    assert updated.note == "Updated"
    assert updated.sampling_location_id == id_06077
    assert updated.field_storage_location_id == id_06019
    assert updated.field_sample_storage_location_id == id_06113


@patch("ca_biositing.pipeline.etl.load.field_sample.get_engine")
def test_load_field_sample_legacy_raw_location_fallback(
    mock_get_engine, session, engine
):
    """Verify legacy raw location columns resolve to a county-only anonymous LocationAddress."""
    mock_get_engine.return_value = engine

    df = pd.DataFrame(
        {
            "name": ["Legacy Sample"],
            "sampling_location_id": [None],
            "sampling_city": ["Stockton"],
            "sampling_zip": ["95202"],
            "sampling_street": ["999 Secret St"],
        }
    )

    load_field_sample.fn(df)

    sample = session.exec(
        select(FieldSample).where(FieldSample.name == "Legacy Sample")
    ).one()
    assert sample.sampling_location_id is not None

    addr = session.get(LocationAddress, sample.sampling_location_id)
    assert addr is not None
    assert addr.geography_id == "06077"
    assert addr.is_anonymous is True
    assert addr.address_line1 is None
    assert addr.address_line2 is None
    assert addr.city is None
    assert addr.zip is None
    assert addr.lat is None
    assert addr.lon is None

    all_addrs = session.exec(select(LocationAddress)).all()
    for a in all_addrs:
        assert a.address_line1 != "999 Secret St"


def test_transform_field_sample_resolves_county_fks_and_redacts_subcounty_columns(
    session, engine
):
    """Verify transform_field_sample resolves county FKs, falls back to producer county, and leaks zero raw addresses."""
    data_sources = {
        "sample_ids": pd.DataFrame(
            {
                "sample_name": ["SAMPLE_001", "SAMPLE_002"],
                "resource": ["Tomato pomace", "Olive pomace"],
                "provider_code": ["PROV1", "PROV2"],
                "fv_date_time": ["2024-01-01", "2024-01-02"],
            }
        ),
        "sample_desc": pd.DataFrame(
            {
                "sample_name": ["SAMPLE_001", "SAMPLE_002"],
                "sampling_city": ["Stockton", None],
                "sampling_zip": ["95202", None],
                "sampling_street": ["100 Private Farm Rd", None],
                "sampling_location": ["Private Farm A", None],
                "field_storage_location": ["Fresno", None],
                "particle_l_cm": [1.0, 2.0],
                "particle_w_cm": [1.0, 2.0],
                "particle_h_cm": [1.0, 2.0],
                "processing_method": ["Method A", "Method B"],
            }
        ),
        "qty_field_storage": pd.DataFrame(
            {
                "sample_name": ["SAMPLE_001", "SAMPLE_002"],
                "qty": [10, 20],
                "sample_container": ["Bucket", "Jar"],
                "field_storage_location": ["Fresno", "On-site Barn Cooler"],
                "storage_dur_value": [30, 60],
                "storage_dur_units": ["days", "days"],
            }
        ),
        "producers": pd.DataFrame(
            {
                "sample_name": ["SAMPLE_001", "SAMPLE_002"],
                "prod_location": ["555 Secret Producer Rd", "Modesto Producer Site"],
                "prod_street": ["555 Secret Producer Rd", "888 Modesto Ave"],
                "prod_city": ["Davis", "Modesto"],
                "prod_zip": ["95616", "95354"],
                "prod_date": ["2024-01-01", "2024-01-02"],
            }
        ),
    }

    with (
        patch("ca_biositing.pipeline.utils.engine.get_engine", return_value=engine),
        patch("ca_biositing.pipeline.utils.engine.engine", engine),
    ):
        result_df = transform_field_sample.fn(data_sources)

    assert result_df is not None
    assert len(result_df) == 2

    for fk_col in (
        "sampling_location_id",
        "field_storage_location_id",
        "field_sample_storage_location_id",
    ):
        assert fk_col in result_df.columns
        assert result_df[fk_col].notna().all()

    by_name = {row["name"]: row for _, row in result_df.iterrows()}
    row1 = by_name["sample_001"]
    row2 = by_name["sample_002"]

    addr_s1_sampling = session.get(LocationAddress, int(row1["sampling_location_id"]))
    addr_s1_storage = session.get(
        LocationAddress, int(row1["field_storage_location_id"])
    )
    addr_s1_prod = session.get(
        LocationAddress, int(row1["field_sample_storage_location_id"])
    )
    assert addr_s1_sampling is not None and addr_s1_sampling.geography_id == "06077"
    assert addr_s1_storage is not None and addr_s1_storage.geography_id == "06019"
    assert addr_s1_prod is not None and addr_s1_prod.geography_id == "06113"

    # SAMPLE_002 falls back to producer county 06099 (Stanislaus) for all three FKs
    addr_s2_sampling = session.get(LocationAddress, int(row2["sampling_location_id"]))
    addr_s2_storage = session.get(
        LocationAddress, int(row2["field_storage_location_id"])
    )
    addr_s2_prod = session.get(
        LocationAddress, int(row2["field_sample_storage_location_id"])
    )
    assert addr_s2_sampling is not None and addr_s2_sampling.geography_id == "06099"
    assert addr_s2_storage is not None and addr_s2_storage.geography_id == "06099"
    assert addr_s2_prod is not None and addr_s2_prod.geography_id == "06099"

    # Zero LocationAddress rows in DB have is_anonymous == False or non-null sub-county columns
    all_addrs = session.exec(select(LocationAddress)).all()
    assert len(all_addrs) > 0
    for addr in all_addrs:
        assert addr.is_anonymous is True
        assert addr.address_line1 is None
        assert addr.address_line2 is None
        assert addr.city is None
        assert addr.zip is None
        assert addr.lat is None
        assert addr.lon is None

    # Returned DataFrame contains zero raw sampling_*, prod_*, or fieldstorage_location columns
    forbidden_cols = {
        c
        for c in result_df.columns
        if (
            c.startswith("sampling_")
            and c != "sampling_location_id"
            or c.startswith("prod_")
            or c in {"fieldstorage_location", "field_storage_location"}
        )
    }
    assert forbidden_cols == set()
