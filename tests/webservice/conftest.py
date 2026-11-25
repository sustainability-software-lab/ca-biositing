"""Pytest fixtures for webservice auth tests.

Provides shared SQLite in-memory engine, SQLModel Session, and TestClient with
an overridden get_session dependency for auth unit and integration tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models import ApiUser
from ca_biositing.webservice.main import app
from ca_biositing.webservice.services.auth_service import get_password_hash


@pytest.fixture(name="auth_engine", scope="function")
def auth_engine_fixture():
    """In-memory SQLite engine with only the api_user table created.

    StaticPool forces all sessions to share the same single connection,
    so tables created at setup time are visible to every subsequent Session.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"auth": None}},  # SQLite has no schemas
    )
    # Create only the api_user table (avoids PostGIS-specific tables)
    with engine.begin() as conn:
        ApiUser.__table__.create(conn, checkfirst=True)
    yield engine
    engine.dispose()


@pytest.fixture(name="auth_session", scope="function")
def auth_session_fixture(auth_engine):
    """SQLModel Session over the in-memory api_user database.

    Uses SQLModel Session so session.exec() works in auth_service and dependencies.
    Each test gets a fresh session; the engine is function-scoped so isolation
    is achieved via a new in-memory DB per test.
    """
    with Session(auth_engine) as session:
        yield session


@pytest.fixture(name="auth_client", scope="function")
def auth_client_fixture(auth_engine):
    """FastAPI TestClient with get_session overridden to use the in-memory DB.

    Creates its own Session per request (mirrors the real get_session behaviour)
    so that auth service code and FastAPI dependencies use the same in-memory DB.
    """
    def override_get_session():
        with Session(auth_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    # raise_server_exceptions=False so server-side DB errors return as 500 HTTP
    # responses rather than raising Python exceptions in the test body.
    # Auth errors (401, 403) are returned normally before DB queries happen.
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture(name="admin_user", scope="function")
def admin_user_fixture(auth_engine) -> ApiUser:
    """Create and return a test admin user in the in-memory DB."""
    with Session(auth_engine) as session:
        user = ApiUser(
            username="admin",
            hashed_password=get_password_hash("adminpass"),
            email="admin@test.com",
            is_admin=True,
            disabled=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(name="regular_user", scope="function")
def regular_user_fixture(auth_engine) -> ApiUser:
    """Create and return a non-admin test user in the in-memory DB."""
    with Session(auth_engine) as session:
        user = ApiUser(
            username="user",
            hashed_password=get_password_hash("userpass"),
            email="user@test.com",
            is_admin=False,
            disabled=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(name="disabled_user", scope="function")
def disabled_user_fixture(auth_engine) -> ApiUser:
    """Create and return a disabled test user in the in-memory DB."""
    with Session(auth_engine) as session:
        user = ApiUser(
            username="disabled",
            hashed_password=get_password_hash("disabledpass"),
            is_admin=False,
            disabled=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture(name="admin_token", scope="function")
def admin_token_fixture(auth_client, admin_user) -> str:
    """Log in the admin user and return a Bearer token string."""
    resp = auth_client.post(
        "/v1/auth/token",
        data={"username": "admin", "password": "adminpass"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(name="user_token", scope="function")
def user_token_fixture(auth_client, regular_user) -> str:
    """Log in the regular user and return a Bearer token string."""
    resp = auth_client.post(
        "/v1/auth/token",
        data={"username": "user", "password": "userpass"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]
