"""
Comprehensive integration test for Field Sample ETL pipeline.

Tests the complete workflow:
1. Extract all four worksheets
2. Transform LocationAddress records
3. Transform FieldSample records with multi-way join
4. Verify data quality, county resolution, and privacy redaction
"""

from __future__ import annotations

import hashlib
import struct
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine, select


def _sqlite_safe_after_create(table, bind, **kw):
    """Restore columns saved by GeoAlchemy2's before_create without calling SpatiaLite functions."""
    from geoalchemy2 import Geometry
    from geoalchemy2.admin.dialects.sqlite import _check_spatial_type

    table.columns = table.info.pop("_saved_columns")
    for col in table.columns:
        if _check_spatial_type(col.type, Geometry, bind.dialect):
            col.type = col._actual_type
            del col._actual_type

    for idx in table.info.pop("_after_create_indexes"):
        table.indexes.add(idx)
        idx.create(bind=bind)


def _wkt_to_ewkb_hex(wkt_str, srid=-1):
    """Convert a WKT string to EWKB hex for GeoAlchemy2 compatibility."""
    from shapely import wkt

    geom = wkt.loads(wkt_str)
    wkb_bytes = geom.wkb
    byte_order = wkb_bytes[0]
    fmt = "<I" if byte_order == 1 else ">I"
    sfmt = "<i" if byte_order == 1 else ">i"
    wkb_type = struct.unpack(fmt, wkb_bytes[1:5])[0]
    ewkb_type = wkb_type | 0x20000000
    ewkb = (
        bytes([byte_order])
        + struct.pack(fmt, ewkb_type)
        + struct.pack(sfmt, srid)
        + wkb_bytes[5:]
    )
    return ewkb.hex()


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        def sqlite_md5(value):
            if value is None:
                return None
            return hashlib.md5(str(value).encode()).hexdigest()

        dbapi_connection.create_function("md5", 1, sqlite_md5, deterministic=True)

        def _geom_from_ewkt(value):
            if value is None:
                return None
            if isinstance(value, str) and ";" in value:
                return value.split(";", 1)[1]
            return str(value)

        def _as_ewkb(value):
            if value is None:
                return None
            try:
                return _wkt_to_ewkb_hex(value)
            except Exception:
                return value

        dbapi_connection.create_function("GeomFromEWKT", 1, _geom_from_ewkt)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, _geom_from_ewkt)
        dbapi_connection.create_function("AsEWKB", 1, _as_ewkb)
        dbapi_connection.create_function("ST_AsEWKB", 1, _as_ewkb)

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def strip_pg_casts(conn, cursor, statement, parameters, context, executemany):
        if "::text" in statement:
            statement = statement.replace("::text", "")
        return statement, parameters

    import geoalchemy2.admin.dialects.sqlite as ga2_sqlite

    with patch.object(ga2_sqlite, "after_create", _sqlite_safe_after_create):
        from ca_biositing.datamodels.models import LandiqRecord

        LandiqRecord.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)

    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_ids_data():
    """01_Sample_IDs (137 rows - base dataset)."""
    return pd.DataFrame(
        {
            "sample_name": [f"SAMPLE_{i:04d}" for i in range(137)],
            "resource": ["Tomato pomace"] * 50
            + ["Olive pomace"] * 50
            + ["Grape pomace"] * 37,
            "provider_code": ["BIOCIR"] * 80 + ["PROV2"] * 57,
            "fv_date_time": pd.date_range("2024-01-01", periods=137),
            "index": range(1, 138),
            "fv_folder": [f"https://drive.google.com/{i}" for i in range(137)],
            "dataset": ["biocirv"] * 137,
        }
    )


@pytest.fixture
def sample_desc_data():
    """02_Sample_Desc (104 rows - unique matches on sample_name)."""
    cities = ["Kern", "Tulare", "Kings"]
    zips = ["93301", "93274", "93230"]
    methods = ["Method_A", "Method_B", "Method_C"]
    return pd.DataFrame(
        {
            "sample_name": [f"SAMPLE_{i:04d}" for i in range(104)],
            "sampling_location": [f"Location_{i % 15}" for i in range(104)],
            "sampling_street": [f"{i} Main St" for i in range(104)],
            "sampling_city": [cities[i % 3] for i in range(104)],
            "sampling_zip": [zips[i % 3] for i in range(104)],
            "particle_l_cm": [1.5 + (i * 0.01) for i in range(104)],
            "particle_w_cm": [2.0 + (i * 0.01) for i in range(104)],
            "particle_h_cm": [2.5 + (i * 0.01) for i in range(104)],
            "processing_method": [methods[i % 3] for i in range(104)],
            "field_storage_location": [
                f"Storage_Collection_{i % 20}" for i in range(104)
            ],
            "dataset": ["biocirv"] * 104,
        }
    )


@pytest.fixture
def qty_field_storage_data():
    """03_Qty_FieldStorage (unique records per sample, 130 rows to test partial matching)."""
    sample_names = [f"SAMPLE_{i:04d}" for i in range(130)]

    containers = ["Bucket (5 gal.)", "Core", "Bale", "Jar"]
    storage_conds = ["Cool", "Frozen", "Ambient"]
    storage_durs = [30, 60, 90]

    return pd.DataFrame(
        {
            "sample_name": sample_names,
            "qty": list(range(1, 131)),
            "sample_container": [containers[i % 4] for i in range(130)],
            "field_storage_location": [f"Storage_Field_{i % 25}" for i in range(130)],
            "storage_conditions": [storage_conds[i % 3] for i in range(130)],
            "storage_dur_value": [storage_durs[i % 3] for i in range(130)],
            "storage_dur_units": ["days"] * 130,
            "dataset": ["biocirv"] * 130,
        }
    )


@pytest.fixture
def producers_data():
    """04_Producers (64 rows - partial match on sample_name, non-overlapping range)."""
    cities = ["Los Angeles", "San Francisco", "Sacramento"]
    zips = ["90012", "94102", "95814"]
    return pd.DataFrame(
        {
            "sample_name": [f"SAMPLE_{i:04d}" for i in range(50, 114)],
            "prod_location": [f"Producer_{i}" for i in range(64)],
            "prod_street": [f"{2000 + i} Factory Ave" for i in range(64)],
            "prod_city": [cities[i % 3] for i in range(64)],
            "prod_zip": [zips[i % 3] for i in range(64)],
            "producer_code": [f"PROD_{i:03d}" for i in range(64)],
            "prod_date": pd.date_range("2024-01-01", periods=64),
            "dataset": ["biocirv"] * 64,
        }
    )


@pytest.fixture
def all_data_sources(
    sample_ids_data, sample_desc_data, qty_field_storage_data, producers_data
):
    """All four worksheet data sources."""
    return {
        "sample_ids": sample_ids_data,
        "sample_desc": sample_desc_data,
        "qty_field_storage": qty_field_storage_data,
        "producers": producers_data,
    }


class TestFieldSamplePipeline:
    """Integration tests for complete Field Sample ETL pipeline."""

    @patch("ca_biositing.pipeline.etl.extract.factory.get_run_logger")
    @patch("ca_biositing.pipeline.utils.gsheet_to_pandas.gsheet_to_df")
    def test_end_to_end_extract_all_worksheets(
        self, mock_gsheet, _mock_logger, all_data_sources
    ):
        """Verify all four extractors can be called and return correct row counts."""

        def worksheet_mapper(gsheet_name, worksheet_name, credentials_path):
            sheet_map = {
                "01_Sample_IDs": all_data_sources["sample_ids"],
                "02_Sample_Desc": all_data_sources["sample_desc"],
                "03_Qty_FieldStorage": all_data_sources["qty_field_storage"],
                "04_Producers": all_data_sources["producers"],
            }
            return sheet_map.get(worksheet_name, pd.DataFrame())

        mock_gsheet.side_effect = worksheet_mapper

        from ca_biositing.pipeline.etl.extract.producers import extract as extract_prod
        from ca_biositing.pipeline.etl.extract.qty_field_storage import (
            extract as extract_qty,
        )
        from ca_biositing.pipeline.etl.extract.sample_desc import (
            extract as extract_desc,
        )
        from ca_biositing.pipeline.etl.extract.sample_ids import extract as extract_ids

        result_ids = extract_ids.fn()
        result_desc = extract_desc.fn()
        result_qty = extract_qty.fn()
        result_prod = extract_prod.fn()

        assert len(result_ids) == 137, (
            f"Expected 137 sample_ids, got {len(result_ids)}"
        )
        assert len(result_desc) == 104, (
            f"Expected 104 sample_desc, got {len(result_desc)}"
        )
        assert len(result_qty) == 130, (
            f"Expected 130 qty_field_storage, got {len(result_qty)}"
        )
        assert len(result_prod) == 64, f"Expected 64 producers, got {len(result_prod)}"

    def test_location_address_transform(self, all_data_sources):
        """Test LocationAddress transformation outputs county-only anonymous rows."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        result = transform_location_address.fn(all_data_sources)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

        if "location_type" in result.columns:
            assert set(result["location_type"].unique()).issubset(
                {"collection_site", "facility_storage"}
            )

        assert (result["is_anonymous"] == True).all()  # noqa: E712
        for subcounty_col in (
            "address_line1",
            "address_line2",
            "city",
            "zip",
            "lat",
            "lon",
        ):
            assert subcounty_col in result.columns
            assert result[subcounty_col].isna().all()

        for geoid in result["geography_id"]:
            assert isinstance(geoid, str)
            assert len(geoid) == 5
            assert geoid.startswith("06")
            assert geoid.isdigit()

        forbidden_cols = {
            c
            for c in result.columns
            if c.startswith("sampling_")
            or c.startswith("prod_")
            or c in {"fieldstorage_location", "field_storage_location", "location_name"}
        }
        assert forbidden_cols == set()

    def test_extract_sources_list_completeness(self):
        """Verify EXTRACT_SOURCES list is complete in transform module."""
        from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import (
            EXTRACT_SOURCES,
        )

        expected_sources = {
            "sample_ids",
            "sample_desc",
            "qty_field_storage",
            "producers",
        }
        assert set(EXTRACT_SOURCES) == expected_sources

    def test_location_address_handles_empty_data(self):
        """Verify LocationAddress transform handles empty data sources."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        empty_sources = {
            "sample_desc": pd.DataFrame(),
            "producers": pd.DataFrame(),
        }

        result = transform_location_address.fn(empty_sources)

        assert isinstance(result, pd.DataFrame)
        assert result.empty or len(result) == 0

    def test_location_address_deduplication(self, all_data_sources):
        """Verify LocationAddress deduplicates by geography_id."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        result = transform_location_address.fn(all_data_sources)

        assert result is not None and not result.empty
        assert result["geography_id"].is_unique

    def test_location_address_location_type_tagging(self, all_data_sources):
        """Verify locations are tagged with type (collection_site or facility_storage)."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        result = transform_location_address.fn(all_data_sources)

        if result is not None and "location_type" in result.columns:
            valid_types = {"collection_site", "facility_storage"}
            actual_types = set(result["location_type"].dropna().unique())
            assert actual_types.issubset(valid_types)

    def test_location_address_is_anonymous_logic(self, all_data_sources):
        """Verify every transformed LocationAddress row is unconditionally anonymous with null sub-county fields."""
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        result = transform_location_address.fn(all_data_sources)

        assert result is not None and not result.empty
        assert "is_anonymous" in result.columns
        assert (result["is_anonymous"] == True).all()  # noqa: E712

        for subcounty_col in (
            "address_line1",
            "address_line2",
            "city",
            "zip",
            "lat",
            "lon",
        ):
            assert result[subcounty_col].isna().all()

        for geoid in result["geography_id"]:
            assert isinstance(geoid, str) and len(geoid) == 5 and geoid.startswith("06")

        forbidden_cols = {
            c
            for c in result.columns
            if c.startswith("sampling_")
            or c.startswith("prod_")
            or c in {"fieldstorage_location", "field_storage_location", "location_name"}
        }
        assert forbidden_cols == set()

    def test_end_to_end_transform_and_load_privacy_and_county_fks(
        self, all_data_sources, session, engine
    ):
        """Run transform + load for LocationAddress and FieldSample and verify county FKs and 100% redaction."""
        from ca_biositing.datamodels.models import FieldSample, LocationAddress
        from ca_biositing.pipeline.etl.load.field_sample import load_field_sample
        from ca_biositing.pipeline.etl.load.location_address import (
            load_location_address,
        )
        from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import (
            transform_field_sample,
        )
        from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
            transform_location_address,
        )

        with (
            patch(
                "ca_biositing.pipeline.etl.load.location_address.get_engine",
                return_value=engine,
            ),
            patch(
                "ca_biositing.pipeline.etl.load.field_sample.get_engine",
                return_value=engine,
            ),
            patch(
                "ca_biositing.pipeline.utils.engine.get_engine",
                return_value=engine,
            ),
            patch("ca_biositing.pipeline.utils.engine.engine", engine),
        ):
            loc_df = transform_location_address.fn(all_data_sources)
            assert loc_df is not None and not loc_df.empty
            load_location_address.fn(loc_df)

            fs_df = transform_field_sample.fn(all_data_sources)
            assert fs_df is not None and len(fs_df) == 137
            load_field_sample.fn(fs_df)

        persisted_samples = session.exec(select(FieldSample)).all()
        assert len(persisted_samples) == 137
        for s in persisted_samples:
            assert s.sampling_location_id is not None

        persisted_addrs = session.exec(select(LocationAddress)).all()
        assert len(persisted_addrs) > 0
        for addr in persisted_addrs:
            assert addr.is_anonymous is True
            assert addr.address_line1 is None
            assert addr.address_line2 is None
            assert addr.city is None
            assert addr.zip is None
            assert addr.lat is None
            assert addr.lon is None

        expected_geoids = {
            "06029",  # Kern
            "06107",  # Tulare
            "06031",  # Kings
            "06037",  # Los Angeles
            "06075",  # San Francisco
            "06067",  # Sacramento
        }
        actual_geoids = {addr.geography_id for addr in persisted_addrs}
        assert expected_geoids.issubset(actual_geoids)

    def test_multi_way_join_strategy_preserves_base_records(self, all_data_sources):
        """Test the multi-way join strategy preserves all base records."""
        sample_ids = all_data_sources["sample_ids"].copy()
        sample_desc = all_data_sources["sample_desc"].copy()
        qty_field_storage = all_data_sources["qty_field_storage"].copy()
        producers = all_data_sources["producers"].copy()

        base_count = len(sample_ids)

        joined = sample_ids.merge(
            sample_desc, on="sample_name", how="left", suffixes=("", "_desc")
        )
        assert len(joined) == base_count, (
            "Left-join with sample_desc should preserve base records"
        )

        qty_field_storage_dedup = qty_field_storage.drop_duplicates(
            subset=["sample_name"], keep="first"
        )
        joined = joined.merge(
            qty_field_storage_dedup, on="sample_name", how="left", suffixes=("", "_qty")
        )
        assert len(joined) == base_count, (
            "Left-join with qty_field_storage should preserve base records"
        )

        producers_dedup = producers.drop_duplicates(
            subset=["sample_name"], keep="first"
        )
        joined = joined.merge(
            producers_dedup, on="sample_name", how="left", suffixes=("", "_prod")
        )
        assert len(joined) == base_count, (
            "Left-join with producers should preserve base records"
        )

    def test_sample_desc_particle_dimensions_present(self, all_data_sources):
        """Verify particle dimensions are present in sample_desc data."""
        sample_desc = all_data_sources["sample_desc"]

        assert "particle_l_cm" in sample_desc.columns
        assert "particle_w_cm" in sample_desc.columns
        assert "particle_h_cm" in sample_desc.columns

        assert sample_desc["particle_l_cm"].dtype in ["float64", "int64"]
        assert sample_desc["particle_w_cm"].dtype in ["float64", "int64"]
        assert sample_desc["particle_h_cm"].dtype in ["float64", "int64"]

    def test_sample_container_field_variations(self, all_data_sources):
        """Verify sample_container field has expected container types."""
        qty_field_storage = all_data_sources["qty_field_storage"]

        assert "sample_container" in qty_field_storage.columns
        containers = set(qty_field_storage["sample_container"].unique())
        expected_containers = {"Bucket (5 gal.)", "Core", "Bale", "Jar"}
        assert expected_containers.issubset(containers)

    def test_producer_location_fields_present(self, all_data_sources):
        """Verify producer location fields are available."""
        producers = all_data_sources["producers"]

        location_fields = {"prod_location", "prod_street", "prod_city", "prod_zip"}
        assert location_fields.issubset(set(producers.columns))

    def test_sampling_location_fields_present(self, all_data_sources):
        """Verify sampling location fields are available in sample_desc."""
        sample_desc = all_data_sources["sample_desc"]

        location_fields = {
            "sampling_location",
            "sampling_street",
            "sampling_city",
            "sampling_zip",
        }
        assert location_fields.issubset(set(sample_desc.columns))

    def test_extract_source_validation(self, all_data_sources):
        """Verify all required extract sources have expected columns."""
        assert "sample_name" in all_data_sources["sample_ids"].columns
        assert "resource" in all_data_sources["sample_ids"].columns
        assert "provider_code" in all_data_sources["sample_ids"].columns

        assert "sample_name" in all_data_sources["sample_desc"].columns

        assert "sample_name" in all_data_sources["qty_field_storage"].columns
        assert "sample_container" in all_data_sources["qty_field_storage"].columns

        assert "sample_name" in all_data_sources["producers"].columns

    def test_sample_names_are_join_keys(self, all_data_sources):
        """Verify sample_name is the common join key across all worksheets."""
        for source_name, data in all_data_sources.items():
            if not data.empty:
                assert "sample_name" in data.columns, (
                    f"{source_name} missing sample_name join key"
                )
                assert data["sample_name"].notna().sum() > 0, (
                    f"{source_name} has nulls in sample_name"
                )

    def test_base_dataset_has_all_sample_ids(self, sample_ids_data):
        """Verify base dataset (sample_ids) has expected record count."""
        assert len(sample_ids_data) == 137
        assert sample_ids_data["sample_name"].notna().all()

    def test_partial_matching_on_joins(self, all_data_sources):
        """Verify datasets have partial overlap in sample_names (realistic scenario)."""
        ids_names = set(all_data_sources["sample_ids"]["sample_name"])
        desc_names = set(all_data_sources["sample_desc"]["sample_name"].dropna())
        qty_names = set(all_data_sources["qty_field_storage"]["sample_name"].dropna())
        prod_names = set(all_data_sources["producers"]["sample_name"].dropna())

        assert len(desc_names & ids_names) < len(ids_names)
        assert len(desc_names & ids_names) > 0

        assert len(qty_names & ids_names) < len(ids_names)
        assert len(qty_names & ids_names) > 0

        assert len(prod_names & ids_names) < len(ids_names)
        assert len(prod_names & ids_names) > 0

    def test_field_storage_location_from_sample_desc(self, all_data_sources):
        """Verify field_storage_location comes from sample_desc."""
        sample_desc = all_data_sources["sample_desc"]
        assert "field_storage_location" in sample_desc.columns
        assert sample_desc["field_storage_location"].notna().sum() > 0

    def test_producer_location_separate_from_sampling_location(self, all_data_sources):
        """Verify producer and sampling locations are separate entities."""
        sample_desc = all_data_sources["sample_desc"]
        producers = all_data_sources["producers"]

        assert "sampling_location" in sample_desc.columns
        assert "prod_location" in producers.columns

        sampling_locs = set(sample_desc["sampling_location"].dropna().unique())
        producer_locs = set(producers["prod_location"].dropna().unique())

        assert len(sampling_locs) > 0
        assert len(producer_locs) > 0
