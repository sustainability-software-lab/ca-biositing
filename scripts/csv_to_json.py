"""Convert resource_info.csv to resource_info.json."""

import csv
import json
from typing import List, Dict, Union
from pathlib import Path

ASSETS_DIR = Path("resources/assets")


def convert() -> None:
    rows: List[Dict[str, Union[str, bool, float, None]]] = []
    with open(ASSETS_DIR / "resource_info.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed_row: Dict[str, Union[str, bool, float, None]] = {}
            for k, v in row.items():
                if v is None or v == "" or v == "-":
                    processed_row[k] = None
                    continue

                # Handle booleans
                if v.lower() in ("true", "yes", "y"):
                    processed_row[k] = True
                elif v.lower() in ("false", "no", "n"):
                    processed_row[k] = False
                else:
                    # Try numeric conversion for yield/id columns if possible, but keep as string if it fails
                    # actually, let's just stick to the requested boolean for now to be safe,
                    # unless we want to be more ambitious.
                    # The user specifically asked for "Include In Totals" which is boolean.
                    processed_row[k] = v
            rows.append(processed_row)

    with open(ASSETS_DIR / "resource_info.json", "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    convert()
