import pandas as pd
from unittest.mock import MagicMock, patch

from ca_biositing.pipeline.etl.transform.analysis.gasification_archive import (
    build_gasification_archive_records,
)


def _gas_rec_df(**overrides):
    base = {
        "record_id": ["REC001"],
        "resource_id": [1],
        "experiment_id": [2],
        "resource_name": ["Rice Straw"],
        "reactor_name": ["Fluidized Bed"],
        "reactor_type_id": [3],
    }
    base.update(overrides)
    return pd.DataFrame(base)


@patch("ca_biositing.pipeline.etl.transform.analysis.gasification_archive.get_run_logger")
def test_happy_path_builds_archive_record(mock_logger):
    mock_logger.return_value = MagicMock()

    gas_rec_df = _gas_rec_df()
    raw_data_df = pd.DataFrame(
        {
            "record_id": ["REC001"],
            "raw_data_url": ["http://example.com/sheet1"],
        }
    )

    result = build_gasification_archive_records.fn(gas_rec_df, raw_data_df)

    assert result == [
        {
            "record_id": "REC001",
            "gsheet_url": "http://example.com/sheet1",
            "resource_id": 1,
            "experiment_id": 2,
            "resource_name": "Rice Straw",
            "reactor_name": "Fluidized Bed",
            "reactor_type_id": 3,
        }
    ]


@patch("ca_biositing.pipeline.etl.transform.analysis.gasification_archive.get_run_logger")
def test_falls_back_to_lower_priority_url_column(mock_logger):
    mock_logger.return_value = MagicMock()

    gas_rec_df = _gas_rec_df()
    raw_data_df = pd.DataFrame(
        {
            "record_id": ["REC001"],
            "Experiment_setup_url": ["http://example.com/setup"],
        }
    )

    result = build_gasification_archive_records.fn(gas_rec_df, raw_data_df)

    assert len(result) == 1
    assert result[0]["gsheet_url"] == "http://example.com/setup"


@patch("ca_biositing.pipeline.etl.transform.analysis.gasification_archive.get_run_logger")
def test_record_id_match_is_case_insensitive(mock_logger):
    mock_logger.return_value = MagicMock()

    gas_rec_df = _gas_rec_df(record_id=["rec001"])
    raw_data_df = pd.DataFrame(
        {
            "record_id": ["REC001"],
            "raw_data_url": ["http://example.com/sheet1"],
        }
    )

    result = build_gasification_archive_records.fn(gas_rec_df, raw_data_df)

    assert len(result) == 1
    assert result[0]["record_id"] == "rec001"


@patch("ca_biositing.pipeline.etl.transform.analysis.gasification_archive.get_run_logger")
def test_no_match_or_no_url_excludes_row(mock_logger):
    mock_logger.return_value = MagicMock()

    gas_rec_df = _gas_rec_df()

    # No matching record_id at all
    no_match_df = pd.DataFrame({"record_id": ["OTHER"], "raw_data_url": ["http://example.com"]})
    assert build_gasification_archive_records.fn(gas_rec_df, no_match_df) == []

    # Matching record_id but no usable URL column
    no_url_col_df = pd.DataFrame({"record_id": ["REC001"], "note": ["n/a"]})
    assert build_gasification_archive_records.fn(gas_rec_df, no_url_col_df) == []

    # Matching record_id but URL value doesn't look like a URL
    bad_url_df = pd.DataFrame({"record_id": ["REC001"], "raw_data_url": ["not-a-url"]})
    assert build_gasification_archive_records.fn(gas_rec_df, bad_url_df) == []


@patch("ca_biositing.pipeline.etl.transform.analysis.gasification_archive.get_run_logger")
def test_dedupes_by_gsheet_url_keeping_first_occurrence(mock_logger):
    mock_logger.return_value = MagicMock()

    gas_rec_df = _gas_rec_df(
        record_id=["REC001", "REC002"],
        resource_id=[1, 99],
        experiment_id=[2, 99],
        resource_name=["Rice Straw", "Other"],
        reactor_name=["Fluidized Bed", "Other"],
        reactor_type_id=[3, 99],
    )
    raw_data_df = pd.DataFrame(
        {
            "record_id": ["REC001", "REC002"],
            "raw_data_url": ["http://example.com/shared", "http://example.com/shared"],
        }
    )

    result = build_gasification_archive_records.fn(gas_rec_df, raw_data_df)

    assert len(result) == 1
    assert result[0]["record_id"] == "REC001"
