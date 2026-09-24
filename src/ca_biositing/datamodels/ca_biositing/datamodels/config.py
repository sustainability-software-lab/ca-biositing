from pathlib import Path
import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from typing import Optional

# Determine the project root (directory containing "pixi.toml") to locate the shared .env file.
_project_root = Path(__file__).resolve().parent
while not (_project_root / "pixi.toml").exists():
    parent = _project_root.parent
    if parent == _project_root:  # reached filesystem root without finding pixi.toml
        break
    _project_root = parent
_env_path = _project_root / "resources" / "docker" / ".env"

# Auto-detect execution context: check if running in Docker
_in_docker = os.path.exists("/.dockerenv")


class Settings(BaseSettings):
    """
    Application settings and configuration for the datamodels package.

    Uses Pydantic Settings to load configuration from environment variables
    and .env files.
    """
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "biositing"
    POSTGRES_HOST: str = "db" if _in_docker else "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    # Cloud Run / Cloud SQL Auth Proxy (Unix socket mode)
    INSTANCE_CONNECTION_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def database_url(self) -> str:
        """Constructs the database URL from components if not explicitly set.

        Priority:
        1. Explicit DATABASE_URL (local dev, Alembic, Docker Compose)
        2. INSTANCE_CONNECTION_NAME → Unix socket (Cloud Run via Cloud SQL Auth Proxy)
        3. TCP fallback using POSTGRES_HOST/POSTGRES_PORT
        """
        if self.DATABASE_URL:
            url = make_url(self.DATABASE_URL)
            if url.host == "db" and not _in_docker:
                # resources/docker/.env bakes in the Docker Compose service
                # name "db" as the host; rewrite it for local (non-Docker) runs.
                url = url.set(host="localhost")
            return url.render_as_string(hide_password=False)
        if self.INSTANCE_CONNECTION_NAME:
            user = self.DB_USER or self.POSTGRES_USER
            password = self.DB_PASS or self.POSTGRES_PASSWORD
            socket_path = f"/cloudsql/{self.INSTANCE_CONNECTION_NAME}"
            # Build the URL directly — URL.create() percent-encodes slashes and colons
            # in the host query parameter, which breaks the Unix socket path.
            # URL-encode the password so special chars (@, :, /, %) don't break the URL.
            return (
                f"postgresql://{user}:{quote_plus(password)}@/{self.POSTGRES_DB}"
                f"?host={socket_path}"
            )
        return URL.create(
            drivername="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)


settings = Settings()
