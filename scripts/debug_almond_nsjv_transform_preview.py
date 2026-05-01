from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from prefect import flow


def _mock_normalize_dataframes(df: pd.DataFrame, normalize_columns: dict[str, Any]):
    out = df.copy()
    for source_col in normalize_columns:
        id_col = f"{source_col}_id"
        if id_col not in out.columns:
            out[id_col] = pd.NA
    return [out]


def _write_payload(payload: Any, output_dir: Path, prefix: str) -> None:
    if isinstance(payload, pd.DataFrame):
        output_path = output_dir / f"{prefix}.csv"
        payload.to_csv(output_path, index=False)
        print(f"wrote {output_path}")
        return

    if isinstance(payload, dict):
        for key, value in payload.items():
            child_prefix = f"{prefix}__{key}" if prefix else key
            _write_payload(value, output_dir, child_prefix)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview almond NSJV transform outputs without running load."
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Optional project root for Google Sheets credential resolution.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/test/almond_nsjv_transform_preview",
        help="Directory to write raw and transformed preview CSVs.",
    )
    args = parser.parse_args()

    from ca_biositing.pipeline.etl.extract import almond_nsjv as almond_extract
    from ca_biositing.pipeline.etl.transform.analysis import almond_nsjv as almond_transform

    almond_transform.normalize_dataframes = _mock_normalize_dataframes
    almond_transform._load_place_lookup = lambda: {
        "merced": "06047",
        "san joaquin": "06077",
        "san_joaquin": "06077",
        "stanislaus": "06099",
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    @flow(name="Almond NSJV Transform Preview", log_prints=True)
    def _preview_flow(project_root: str | None):
        raw_payloads = {
            "parameters": almond_extract.parameters.fn(project_root=project_root),
            "price_production_county_ag_reports": almond_extract.price_production_county_ag_reports.fn(project_root=project_root),
        }
        transformed = {
            "parameter": almond_transform.transform_county_ag_parameters.fn(
                data_sources=raw_payloads,
                etl_run_id="preview_run",
                lineage_group_id="preview_lineage",
            ),
            "records": almond_transform.transform_county_ag_records.fn(
                data_sources=raw_payloads,
                etl_run_id="preview_run",
                lineage_group_id="preview_lineage",
            ),
            "observation": pd.DataFrame(
                [{
                    "note": "Observation preview skipped in no-DB mode; implement load lookups first.",
                    "etl_run_id": "preview_run",
                    "lineage_group_id": "preview_lineage",
                }]
            ),
        }
        return raw_payloads, transformed

    raw_payloads, transformed = _preview_flow(args.project_root)

    _write_payload(raw_payloads, output_dir, "raw")
    _write_payload(transformed, output_dir, "transformed")

    print("Preview generation complete.")


if __name__ == "__main__":
    main()
