from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Defines the application settings, loaded from environment variables.
    """
    # This is the only setting our application code currently needs.
    # Pydantic will automatically find this variable in the .env file.
    DATABASE_URL: str

    # Configure Pydantic to:
    # 1. Look for a .env file.
    # 2. Ignore extra variables found in the .env file (like POSTGRES_USER etc.)
    #    This resolves the ValidationError.
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    Using lru_cache ensures the .env file is read only once.
    """
    return Settings()
