from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded exclusively from environment variables.

    No credentials are stored here. Set DATABASE_URL in the environment
    before use (the pixi migrate/webservice tasks are responsible for this).
    """

    DATABASE_URL: str

    model_config = SettingsConfigDict(
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    """
    return Settings()
