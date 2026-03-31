"""Generate a static OpenAPI JSON spec from the FastAPI app.

Run with:
    pixi run -e webservice generate-openapi

Outputs to docs/api/openapi.json. No database connection is required —
FastAPI builds the schema purely from route and model definitions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"


def main() -> None:
    try:
        from ca_biositing.webservice.main import app
    except ImportError as e:
        print(f"ERROR: Could not import webservice app: {e}", file=sys.stderr)
        print("Run this script in the webservice environment:", file=sys.stderr)
        print("    pixi run -e webservice generate-openapi", file=sys.stderr)
        sys.exit(1)

    schema = app.openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2))
    print(f"OpenAPI spec written to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
