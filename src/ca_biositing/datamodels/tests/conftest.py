"""Pytest configuration and fixtures for datamodels tests."""

import pytest
from sqlmodel import create_engine, Session, SQLModel

from ca_biositing.datamodels.biocirv_public_views import register_sqlite_udfs


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    register_sqlite_udfs(engine)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session
