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
        mapping_keys = set(json.load(f).keys())

    missing = csv_headers - mapping_keys
    extra = mapping_keys - csv_headers
    ok = True

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
