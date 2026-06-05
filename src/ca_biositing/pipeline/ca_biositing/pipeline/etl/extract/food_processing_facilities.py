"""
Extract tasks for CARB food processing facilities Google Sheet.

Also provides extract_seed_csv() — a plain (non-Prefect) function that loads
previously geocoded rows from a local CSV file so the DB can be seeded
instantly without re-running 6000+ geocoder API calls.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .factory import create_extractor

logger = logging.getLogger(__name__)

GSHEET_NAME = "food_manufacturers_and_processors_carb"
WORKSHEET_ALL_FACILITIES = "all facilities"
WORKSHEET_GEOCODER_TEST_SET = "test set for geocoder"

# ---------------------------------------------------------------------------
# Seed CSV path resolution
# ---------------------------------------------------------------------------
# Priority 1: SEED_CSV_PATH environment variable (set this in Docker to a
#             stable, Python-version-independent path, e.g. /app/seed_food_processor_facilities.csv)
# Priority 2: __file__-relative fallback for local development.
#
# WHY the env-var is needed in Docker:
#   Locally __file__ resolves inside the source tree and the .parent.parent.parent
#   traversal lands at …/ca_biositing/pipeline/ where utils/ lives.
#   Inside Docker the source is volume-mounted into site-packages:
#     /app/.pixi/envs/etl/lib/python3.12/site-packages/ca_biositing/pipeline/
#   The traversal still works IF the Python minor version matches the mount path
#   (python3.12 vs python3.13).  Rather than rely on that fragile assumption,
#   docker-compose mounts the CSV to a fixed path and sets SEED_CSV_PATH to
#   point there — making the resolution completely version-independent.
_SEED_CSV_FALLBACK: Path = (
    Path(__file__).resolve()
    .parent.parent.parent  # …/pipeline/ca_biositing/pipeline/
    / "utils"
    / "seed_food_processor_facilities.csv"
)

_env_override = os.environ.get("SEED_CSV_PATH")
_SEED_CSV_PATH: Path = Path(_env_override) if _env_override else _SEED_CSV_FALLBACK

extract_all_facilities = create_extractor(
    GSHEET_NAME,
    WORKSHEET_ALL_FACILITIES,
    task_name="extract_food_processing_facilities_all",
)

extract_geocoder_test_set = create_extractor(
    GSHEET_NAME,
    WORKSHEET_GEOCODER_TEST_SET,
    task_name="extract_food_processing_facilities_geocoder_test_set",
)


def extract_seed_csv(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load the seed CSV from the utils directory.

    Returns a DataFrame when the file exists, or None when it does not (so the
    flow degrades gracefully when the CSV has not been generated yet).

    Parameters
    ----------
    path:
        Override the default CSV path (used in tests).
    """
    csv_path = path if path is not None else _SEED_CSV_PATH

    logger.info("[seed] Resolved seed CSV path: %s", csv_path)

    if not csv_path.exists():
        logger.warning(
            "[seed] WARNING: Seed CSV not found at %s — skipping seed step. "
            "Set SEED_CSV_PATH env var to override (e.g. /app/seed_food_processor_facilities.csv in Docker).",
            csv_path,
        )
        return None

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    # Convert empty strings to None so downstream code receives proper NaN/None
    df = df.replace({"": None})

    logger.info(
        "[seed] Loaded %d rows from seed CSV: %s", len(df), csv_path
    )
    return df


__all__ = [
    "extract_all_facilities",
    "extract_geocoder_test_set",
    "extract_seed_csv",
    "_SEED_CSV_PATH",
]
