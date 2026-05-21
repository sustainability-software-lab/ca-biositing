import pandas as pd
import pytest
from unittest.mock import MagicMock
from ca_biositing.pipeline.utils.name_id_swap import replace_name_with_id_df
from ca_biositing.datamodels.models import FileObjectMetadata, Resource

def test_replace_name_with_id_df_uri_normalization():
    """Test that URL fragments are stripped specifically for FileObjectMetadata."""

    # Setup mock DB session
    mock_db = MagicMock()

    # Mock the driver name check
    mock_db.bind.url.drivername = "postgresql"

    # Mock record to be returned after "creation"
    mock_record = MagicMock(spec=FileObjectMetadata)
    mock_record.uri = "https://example.com/sheet"
    mock_record.id = 101

    # Setup side effects for database calls:
    # 1. Initial lookup (empty table) -> returns empty list
    # 2. Re-query after flush (fetch the created record) -> returns our mock_record
    mock_db.execute.side_effect = [
        MagicMock(all=lambda: []),
        MagicMock(scalars=lambda: MagicMock(all=lambda: [mock_record]))
    ]

    # Test Data: Various cell-level links and inconsistent casing
    test_df = pd.DataFrame({
        "url": [
            "https://example.com/sheet#gid=1",
            "https://example.com/sheet#gid=2",
            "HTTPS://EXAMPLE.COM/SHEET"
        ]
    })

    # Run utility
    result_df, num_created = replace_name_with_id_df(
        db=mock_db,
        df=test_df,
        ref_model=FileObjectMetadata,
        df_name_column="url",
        model_name_attr="uri",
        id_column_name="id",
        final_column_name="url_id"
    )

    # Assertions
    # We expect only ONE unique normalized URI to be identified and created
    assert num_created == 1
    # All 3 rows should have mapped to ID 101
    assert len(result_df["url_id"].unique()) == 1
    assert result_df["url_id"].iloc[0] == 101

    # Verify that the record added to the DB was the normalized one (no fragment)
    added_record = mock_db.add.call_args[0][0]
    assert added_record.uri == "https://example.com/sheet"

def test_replace_name_with_id_df_no_strip_for_other_models():
    """Test that fragments are NOT stripped for models other than FileObjectMetadata (e.g. Resource)."""

    mock_db = MagicMock()
    mock_db.bind.url.drivername = "postgresql"

    # Mock records
    rec1 = MagicMock(spec=Resource); rec1.name = "tag#1"; rec1.id = 1
    rec2 = MagicMock(spec=Resource); rec2.name = "tag#2"; rec2.id = 2

    mock_db.execute.side_effect = [
        MagicMock(all=lambda: []),
        MagicMock(scalars=lambda: MagicMock(all=lambda: [rec1, rec2]))
    ]

    test_df = pd.DataFrame({
        "resource": ["tag#1", "tag#2"]
    })

    result_df, num_created = replace_name_with_id_df(
        db=mock_db,
        df=test_df,
        ref_model=Resource,
        df_name_column="resource",
        model_name_attr="name",
        id_column_name="id",
        final_column_name="resource_id"
    )

    # For Resource, fragments should NOT be stripped, so two distinct records should be created
    assert num_created == 2
    assert len(result_df["resource_id"].unique()) == 2

    # Verify records added were NOT stripped
    added_names = [call.args[0].name for call in mock_db.add.call_args_list]
    assert "tag#1" in added_names
    assert "tag#2" in added_names
