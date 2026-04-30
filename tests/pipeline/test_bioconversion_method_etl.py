import pytest
import pandas as pd
import numpy as np
from ca_biositing.pipeline.etl.transform.analysis.bioconversion_method import transform_bioconversion_method
from ca_biositing.datamodels.models import BioconversionMethod, Strain

class TestBioconversionMethodETL:
    def test_transform_bioconversion_method(self):
        # Mock raw data from 03.3-BioConversionMethods

        raw_data = {
            'Method_id': ['M1', 'M2'],
            'Strain_name': ['Strain A', 'Strain B'],
            'Inoculum volume (L)': [0.1, 0.2],
            'Reaction volume (L)': [1.0, 2.0],
            'Temperature (C)': [30, 37],
            'Time (h)': [24, 48],
            'Description': ['Desc 1', 'Desc 2'],
            'Note': ['Note 1', 'Note 2'],
            'Protocol URL': ['http://url1', 'http://url2']
        }
        raw_df = pd.DataFrame(raw_data)

        # We need to mock the normalization lookup for Strain
        # Since normalize_dataframes hits the DB, we might need a more integrated test or mock it.
        # For now, let's just check if the transformation logic handles columns correctly.

        transformed_df = transform_bioconversion_method(raw_df, etl_run_id="1", lineage_group_id="10")

        assert not transformed_df.empty
        assert 'name' in transformed_df.columns
        assert 'strain_name' in transformed_df.columns
        assert 'inoculum_volume_L' in transformed_df.columns
        assert 'temperature_C' in transformed_df.columns
        assert transformed_df.iloc[0]['name'] == 'm1'

    def test_bioconversion_method_model_fields(self):
        assert hasattr(BioconversionMethod, 'name')
        assert hasattr(BioconversionMethod, 'strain_id')
        assert hasattr(BioconversionMethod, 'strain_name')
        assert hasattr(BioconversionMethod, 'inoculum_volume_L')
        assert hasattr(BioconversionMethod, 'reaction_volume_L')
        assert hasattr(BioconversionMethod, 'temperature_C')
        assert hasattr(BioconversionMethod, 'time_h')

    def test_strain_model_fields(self):
        assert hasattr(Strain, 'genus')
        assert hasattr(Strain, 'species')
        assert hasattr(Strain, 'strain')
        assert hasattr(Strain, 'note')
