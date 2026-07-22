import os
import yaml
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from pathlib import Path

YAML_CONFIG_PATH: str = "audit/config.yaml"

class AuditorSettings(BaseSettings):
    # litellm reads ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN from env automatically
    LLM_MODEL: str = "openai/gemini-2.5-flash"
    LLM_MAX_TOKENS: int = 8192
    LLM_BASE_URL: str = "https://api.cborg.lbl.gov"

    # Audit Thresholds
    ZSCORE_THRESHOLD: float = 1.0
    MIN_GROUP_SIZE: int = 3
    EVIDENTLY_DRIFT_THRESHOLD: float = 0.1

    # Exclusions & Whitelists
    EXCLUDED_RESOURCES: List[str] = []
    PARAMETER_WHITELISTS: Dict[str, List[str]] = {
        "compositional": [],
        "proximate": [],
        "ultimate": []
    }

    # Paths
    OUTPUT_ROOT: str = "audit/output"
    EXPECTATIONS_ROOT: str = "audit/expectations"
    PROFILES_SUBDIR: str = "profiles"
    EVIDENTLY_SUBDIR: str = "evidently"

    # Staging database — auditor reads from here, never production
    # Falls back to the datamodels DATABASE_URL if not set
    STAGING_DATABASE_URL: Optional[str] = None

    # Output formatting
    SUMMARY_MAX_CELL_CHARS: Optional[int] = None

    # Google Sheets Anomaly Tracker
    ANOMALY_TRACKER_SHEET_KEY: str = ""          # Spreadsheet key from URL
    ANOMALY_TRACKER_CREDENTIALS: str = "credentials.json"  # Same as ETL pipeline
    ANOMALY_TRACKER_WORKSHEET: str = "Anomalies"

    class Config:
        env_prefix = "AUDITOR_"
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

def load_yaml_config(yaml_path: str = YAML_CONFIG_PATH) -> AuditorSettings:
    """
    Loads configuration from YAML and merges with environment variables.
    Env vars (via AuditorSettings default Pydantic behavior) take precedence.
    """
    yaml_data = {}
    if Path(yaml_path).exists():
        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}

    # Flatten YAML structure to match AuditorSettings fields
    flat_data = {}

    if "thresholds" in yaml_data:
        t = yaml_data["thresholds"]
        flat_data["ZSCORE_THRESHOLD"] = t.get("zscore_threshold")
        flat_data["MIN_GROUP_SIZE"] = t.get("min_group_size")
        flat_data["EVIDENTLY_DRIFT_THRESHOLD"] = t.get("evidently_drift_threshold")

    if "excluded_resources" in yaml_data:
        flat_data["EXCLUDED_RESOURCES"] = yaml_data["excluded_resources"]

    if "parameter_whitelists" in yaml_data:
        flat_data["PARAMETER_WHITELISTS"] = yaml_data["parameter_whitelists"]

    if "llm" in yaml_data:
        l = yaml_data["llm"]
        flat_data["LLM_MODEL"] = l.get("model")
        flat_data["LLM_MAX_TOKENS"] = l.get("max_tokens")
        flat_data["LLM_BASE_URL"] = l.get("base_url")

    if "output" in yaml_data:
        o = yaml_data["output"]
        flat_data["OUTPUT_ROOT"] = o.get("root")
        flat_data["EXPECTATIONS_ROOT"] = o.get("expectations_root")
        flat_data["PROFILES_SUBDIR"] = o.get("profiles_subdir")
        flat_data["EVIDENTLY_SUBDIR"] = o.get("evidently_subdir")
        flat_data["SUMMARY_MAX_CELL_CHARS"] = o.get("summary_max_cell_chars")

    if "google_sheets" in yaml_data:
        g = yaml_data["google_sheets"]
        flat_data["ANOMALY_TRACKER_SHEET_KEY"] = g.get("sheet_key")
        flat_data["ANOMALY_TRACKER_CREDENTIALS"] = g.get("credentials")
        flat_data["ANOMALY_TRACKER_WORKSHEET"] = g.get("worksheet")

    # Filter out None and empty strings so Pydantic defaults (and env vars) are used
    flat_data = {k: v for k, v in flat_data.items() if v is not None and v != ""}

    # Initialize settings. Pydantic-settings will automatically
    # override these with environment variables if present.
    return AuditorSettings(**flat_data)

settings = load_yaml_config()
