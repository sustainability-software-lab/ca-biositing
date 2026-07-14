from pydantic_settings import BaseSettings
from typing import Optional

class AuditorSettings(BaseSettings):
    # litellm reads ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN from env automatically
    LLM_MODEL: str = "gemini/gemini-3-flash-high"
    LLM_MAX_TOKENS: int = 4096

    # Audit Thresholds
    ZSCORE_THRESHOLD: float = 3.0
    MIN_GROUP_SIZE: int = 3

    # Paths
    OUTPUT_ROOT: str = "audit/output"
    EXPECTATIONS_ROOT: str = "audit/expectations"

    # Staging database — auditor reads from here, never production
    # Falls back to the datamodels DATABASE_URL if not set
    STAGING_DATABASE_URL: Optional[str] = None

    # Google Sheets Anomaly Tracker
    ANOMALY_TRACKER_SHEET_KEY: str = ""          # Spreadsheet key from URL
    ANOMALY_TRACKER_CREDENTIALS: str = "credentials.json"  # Same as ETL pipeline
    ANOMALY_TRACKER_WORKSHEET: str = "Anomalies"

    class Config:
        env_prefix = "AUDITOR_"
        case_sensitive = True

settings = AuditorSettings()
