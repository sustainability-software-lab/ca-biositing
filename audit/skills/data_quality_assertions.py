# audit/skills/data_quality_assertions.py
import great_expectations as gx
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import json

def run_data_quality_assertions(
    df: pd.DataFrame,
    suite_path: str,
) -> Dict:
    """
    Runs GX assertions against the dataframe using a pre-defined suite.
    """
    context = gx.get_context()

    with open(suite_path, 'r') as f:
        suite_dict = json.load(f)

    suite_name = suite_dict.get("expectation_suite_name", "audit_suite")

    # In GX 0.18.x, we use add_or_update_expectation_suite
    from great_expectations.core.expectation_suite import ExpectationSuite
    suite = ExpectationSuite(**suite_dict)
    context.add_or_update_expectation_suite(expectation_suite=suite)

    # Use the fluent API to validate
    datasource_name = f"ds_{suite_name}"
    asset_name = f"asset_{suite_name}"

    try:
        datasource = context.sources.add_pandas(name=datasource_name)
    except Exception:
        datasource = context.get_datasource(datasource_name)

    try:
        asset = datasource.add_dataframe_asset(name=asset_name)
    except Exception:
        asset = datasource.get_asset(asset_name)

    batch_request = asset.build_batch_request(dataframe=df)
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    result = validator.validate()
    return result.to_json_dict()
