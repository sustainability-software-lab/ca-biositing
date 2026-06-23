"""Validate that resource_info.csv headers are in sync with resource_info_header_mapping.json."""

import csv
import json
import sys
from pathlib import Path

ASSETS_DIR = Path("resources/assets")


def validate() -> bool:
    with open(ASSETS_DIR / "resource_info.csv", newline="") as f:
        csv_headers = set(csv.DictReader(f).fieldnames or [])

    with open(ASSETS_DIR / "resource_info_header_mapping.json") as f:
        mapping = json.load(f)
        mapping_keys = set(mapping.keys())
        mapping_values = set(mapping.values())

    # Check if headers match either keys (snake_case) or values (Title Case)
    # The GSheet/CSV usually has Title Case headers.
    missing = csv_headers - mapping_values
    extra = mapping_values - csv_headers
    ok = True

    # If Title Case match fails, try snake_case match (fallback)
    if missing and not (csv_headers - mapping_keys):
        missing = set()
        extra = set()

    if missing:
        print(f"Headers in CSV but missing from mapping: {sorted(missing)}")
        ok = False
    if extra:
        print(f"Keys in mapping but missing from CSV: {sorted(extra)}")
        ok = False

    if ok:
        print(f"Validation passed: {len(csv_headers)} headers in sync.")

    return ok


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
