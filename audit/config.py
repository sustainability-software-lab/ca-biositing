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

    class Config:
        env_prefix = "AUDITOR_"
        case_sensitive = True

settings = AuditorSettings()
