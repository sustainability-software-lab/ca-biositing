"""Pytest configuration and fixtures for datamodels tests."""

import pytest
from sqlmodel import create_engine, Session, SQLModel


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options={"schema_translate_map": {"auth": None}},  # SQLite has no schemas
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session
