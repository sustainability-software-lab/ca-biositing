from sqlmodel import create_engine
import os

# This module provides SQLAlchemy engines for the pipeline package.
# Delegates to ca_biositing.datamodels.config.Settings for URL construction,
# which handles all three environments:
#   - Cloud Run: INSTANCE_CONNECTION_NAME set → Unix socket via Cloud SQL Auth Proxy
#   - Docker Compose: DATABASE_URL set in env → used directly
#   - Local dev: TCP fallback with POSTGRES_HOST/USER/PASSWORD/PORT


def _get_database_url() -> str:
    """Return the database URL for the current environment.

    In local dev (outside Docker and Cloud Run), replace the Docker Compose
    service name 'db' with 'localhost' and use the host-mapped PostgreSQL port
    so the URL resolves from the host machine.
    """
    from ca_biositing.datamodels.config import settings
    db_url = settings.database_url
    # Only substitute when running outside Docker and outside Cloud Run
    if not os.path.exists("/.dockerenv") and not os.getenv("INSTANCE_CONNECTION_NAME"):
        db_url = db_url.replace("@db:5432", f"@localhost:{settings.POSTGRES_PORT}")
        db_url = db_url.replace("@db:", f"@localhost:{settings.POSTGRES_PORT}")
    return db_url


DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL)


def get_engine():
    """Return a SQLAlchemy engine with connection pool settings for ETL tasks."""
    return create_engine(
        _get_database_url(),
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )
