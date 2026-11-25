"""Pytest configuration and fixtures for pipeline tests."""

import hashlib
import struct
from unittest.mock import patch

import pytest
from sqlalchemy import event
from sqlmodel import create_engine, Session, SQLModel


def _sqlite_safe_after_create(table, bind, **kw):
    """Restore columns saved by GeoAlchemy2's before_create without calling SpatiaLite functions."""
    from geoalchemy2 import Geometry, Geography
    from geoalchemy2.admin.dialects.sqlite import _check_spatial_type

    # Restore original column list (same as GeoAlchemy2 does)
    table.columns = table.info.pop("_saved_columns")
    for col in table.columns:
        if _check_spatial_type(col.type, Geometry, bind.dialect):
            col.type = col._actual_type
            del col._actual_type
    # Skip RecoverGeometryColumn and spatial index creation

    # Re-add deferred indexes
    for idx in table.info.pop("_after_create_indexes"):
        table.indexes.add(idx)
        idx.create(bind=bind)


def _wkt_to_ewkb_hex(wkt_str, srid=-1):
    """Convert a WKT string to EWKB hex for GeoAlchemy2 compatibility."""
    from shapely import wkt, wkb
    geom = wkt.loads(wkt_str)
    wkb_bytes = geom.wkb
    # Inject SRID flag into WKB to produce EWKB
    byte_order = wkb_bytes[0]
    fmt = '<I' if byte_order == 1 else '>I'
    sfmt = '<i' if byte_order == 1 else '>i'
    wkb_type = struct.unpack(fmt, wkb_bytes[1:5])[0]
    ewkb_type = wkb_type | 0x20000000  # set SRID flag
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
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options={"schema_translate_map": {"auth": None}},  # SQLite has no schemas
    )

    # Register mock functions for SQLite to support GeoAlchemy2 without SpatiaLite
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        def sqlite_md5(value):
            if value is None:
                return None
            return hashlib.md5(str(value).encode()).hexdigest()

        dbapi_connection.create_function("md5", 1, sqlite_md5, deterministic=True)

        # Mock SpatiaLite geometry functions used by GeoAlchemy2 for insert/select
        def _geom_from_ewkt(value):
            """Store WKT string (strip SRID prefix if present)."""
            if value is None:
                return None
            if isinstance(value, str) and ";" in value:
                return value.split(";", 1)[1]
            return str(value)

        def _as_ewkb(value):
            """Convert stored WKT to EWKB hex so GeoAlchemy2's result processor works."""
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

    # Strip PostgreSQL-specific ::text casts so SQLite can execute the DDL
    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def strip_pg_casts(conn, cursor, statement, parameters, context, executemany):
        if "::text" in statement:
            statement = statement.replace("::text", "")
        return statement, parameters

    # Patch only GeoAlchemy2's after_create to skip SpatiaLite calls (RecoverGeometryColumn)
    # but still restore saved columns. before_create runs normally to swap geometry → dummy text.
    import geoalchemy2.admin.dialects.sqlite as ga2_sqlite

    with patch.object(ga2_sqlite, "after_create", _sqlite_safe_after_create):
        from ca_biositing.datamodels.models import LandiqRecord
        # LandiqRecord.metadata contains all tables because they are in the same Base/Metadata
        LandiqRecord.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)

    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session
