"""
Test suite for Fermentation Record ETL pipeline (Phase 3).

Tests the fermentation_record transform with new method fields:
- decon_method (pretreatment_method_id)
- eh_method (eh_method_id)
"""

import pytest
import pandas as pd
import pathlib
import inspect


class TestFermentationRecordTransform:
    """Test the transform step for fermentation records with new method fields."""

    def test_transform_module_exists(self):
        """Verify that the fermentation_record transform module can be imported."""
        from ca_biositing.pipeline.etl.transform.analysis import fermentation_record
        assert fermentation_record is not None
        assert hasattr(fermentation_record, 'transform_fermentation_record')

    def test_decon_method_in_normalize_columns(self):
        """Verify that decon_method is in the normalize_columns dictionary."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        assert 'decon_method' in source
        assert "'decon_method': (Method, 'name')" in source

    def test_eh_method_in_normalize_columns(self):
        """Verify that eh_method is in the normalize_columns dictionary."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        assert 'eh_method' in source
        assert "'eh_method': (Method, 'name')" in source

    def test_decon_method_rename_mapping(self):
        """Verify that decon_method_id maps to pretreatment_method_id."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        # Check that the rename logic includes the mapping
        assert "'decon_method_id': 'pretreatment_method_id'" in source

    def test_eh_method_rename_mapping(self):
        """Verify that eh_method_id maps to eh_method_id."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        # Check that the rename logic includes the mapping
        assert "'eh_method_id': 'eh_method_id'" in source

    def test_strain_rename_mapping(self):
        """Verify that strain_id maps to strain_id."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        # Check that the rename logic includes the mapping
        assert "'strain_id': 'strain_id'" in source

    def test_transform_normalize_columns_structure(self):
        """Test that normalize_columns dict is properly structured for method fields."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        # Verify the structure includes both Method normalizations
        assert "'decon_method': (Method, 'name')" in source
        assert "'eh_method': (Method, 'name')" in source


class TestFermentationRecordModel:
    """Test the FermentationRecord model with new method fields."""

    def test_fermentation_record_has_pretreatment_method_id(self):
        """Verify FermentationRecord model has pretreatment_method_id field."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        assert hasattr(FermentationRecord, 'pretreatment_method_id')

    def test_fermentation_record_has_eh_method_id(self):
        """Verify FermentationRecord model has eh_method_id field."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        assert hasattr(FermentationRecord, 'eh_method_id')

    def test_fermentation_record_has_strain_id(self):
        """Verify FermentationRecord model has strain_id field."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        assert hasattr(FermentationRecord, 'strain_id')

    def test_pretreatment_method_id_is_foreign_key(self):
        """Verify pretreatment_method_id is a foreign key to method table."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        # Check the field definition exists
        field_info = FermentationRecord.model_fields.get('pretreatment_method_id')
        assert field_info is not None
        assert getattr(field_info, "foreign_key", None) == "method.id"

    def test_eh_method_id_is_foreign_key(self):
        """Verify eh_method_id is a foreign key to method table."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        # Check the field definition exists
        field_info = FermentationRecord.model_fields.get('eh_method_id')
        assert field_info is not None
        assert getattr(field_info, "foreign_key", None) == "method.id"

    def test_strain_id_is_foreign_key(self):
        """Verify strain_id is a foreign key to strain table."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        # Check the field definition exists
        field_info = FermentationRecord.model_fields.get('strain_id')
        assert field_info is not None
        assert getattr(field_info, "foreign_key", None) == "strain.id"

    def test_fermentation_record_has_method_id(self):
        """Verify FermentationRecord inherits method_id from Aim2RecordBase (bioconversion method FK)."""
        from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
        assert hasattr(FermentationRecord, 'method_id')

    def test_method_id_is_foreign_key_to_method(self):
        """Verify inherited method_id is a foreign key to method table."""
        from ca_biositing.datamodels.models.base import Aim2RecordBase
        field_info = Aim2RecordBase.model_fields.get('method_id')
        assert field_info is not None
        assert getattr(field_info, "foreign_key", None) == "method.id"

    def test_method_model_has_duration(self):
        """Verify Method model has duration field."""
        from ca_biositing.datamodels.models.methods_parameters_units.method import Method

        assert hasattr(Method, 'duration')


class TestStrainModel:
    """Test the Strain model has taxonomy columns."""

    def test_strain_has_genus_field(self):
        """Verify Strain model has genus field."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        assert hasattr(Strain, 'genus')

    def test_strain_has_species_field(self):
        """Verify Strain model has species field."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        assert hasattr(Strain, 'species')

    def test_strain_has_strain_field(self):
        """Verify Strain model has strain field."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        assert hasattr(Strain, 'strain')

    def test_strain_genus_is_optional(self):
        """Verify Strain.genus is nullable."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        field_info = Strain.model_fields.get('genus')
        assert field_info is not None
        assert field_info.default is None

    def test_strain_species_is_optional(self):
        """Verify Strain.species is nullable."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        field_info = Strain.model_fields.get('species')
        assert field_info is not None
        assert field_info.default is None

    def test_strain_strain_is_optional(self):
        """Verify Strain.strain is nullable."""
        from ca_biositing.datamodels.models.aim2_records.strain import Strain
        field_info = Strain.model_fields.get('strain')
        assert field_info is not None
        assert field_info.default is None


class TestMvBiomassFermentationView:
    """Test the mv_biomass_fermentation view with new method fields."""

    def test_view_module_exists(self):
        """Verify that the view module can be imported."""
        from ca_biositing.datamodels.data_portal_views import mv_biomass_fermentation
        assert mv_biomass_fermentation is not None

    def test_view_source_file_references_pretreatment_method_id(self):
        """Verify that mv_biomass_fermentation.py source file contains pretreatment_method_id."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        # The view should join on pretreatment_method_id
        assert 'pretreatment_method_id' in source

    def test_view_source_file_references_eh_method_id(self):
        """Verify that mv_biomass_fermentation.py source file contains eh_method_id."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        # The view should join on eh_method_id
        assert 'eh_method_id' in source

    def test_view_source_file_has_aliases(self):
        """Verify that mv_biomass_fermentation.py uses PM and EM aliases for Method table."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        # Should have PM (pretreatment method) and EM (enzyme method) aliases
        assert 'PM = aliased(Method' in source
        assert 'EM = aliased(Method' in source

    def test_view_source_file_labels_pretreatment_method(self):
        """Verify that mv_biomass_fermentation.py labels pretreatment_method correctly."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        # Should label PRETREATMENT_LABEL as pretreatment_method
        assert 'PRETREATMENT_LABEL.label("pretreatment_method")' in source

    def test_view_source_file_labels_enzyme_method(self):
        """Verify that mv_biomass_fermentation.py labels enzyme_name correctly."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        # Should label ENZYME_LABEL as enzyme_name
        assert 'ENZYME_LABEL.label("enzyme_name")' in source

    def test_view_source_file_labels_elapsed_time(self):
        """Verify that mv_biomass_fermentation.py projects elapsed_time from all four method aliases."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()

        assert 'ELAPSED_TIME = func.coalesce(PM.duration, EM.duration, BCM.time_h, EHM.time_h)' in source
        assert 'ELAPSED_TIME.label("elapsed_time")' in source

    def test_view_source_file_has_bcm_alias(self):
        """Verify that mv_biomass_fermentation.py uses BCM alias for bioconversion method."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        assert 'BCM = aliased(BioconversionMethod' in source

    def test_view_source_file_joins_on_bioconversion_method_id(self):
        """Verify that mv_biomass_fermentation.py joins BCM alias on fermentation_record.bioconversion_method_id."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        assert 'FermentationRecord.bioconversion_method_id == BCM.id' in source

    def test_view_source_file_labels_bioconversion_method(self):
        """Verify that mv_biomass_fermentation.py labels bioconversion_method correctly."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        assert 'BCM.name.label("bioconversion_method")' in source

    def test_view_source_file_labels_strain_name(self):
        """Verify that mv_biomass_fermentation.py projects strain_name from genus and species."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        assert 'SPECIES_DISPLAY_NAME' in source
        assert 'strain_name' in source
        assert 'Strain.genus' in source
        assert 'Strain.species' in source
        assert 'func.upper(func.left(Strain.genus, 1))' in source
        assert 'func.lower(Strain.species)' in source

    def test_view_source_file_groups_by_genus_and_species(self):
        """Verify that mv_biomass_fermentation.py includes Strain.genus and Strain.species in group_by."""
        view_file = pathlib.Path(__file__).parent.parent.parent.parent.parent / "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_fermentation.py"
        source = view_file.read_text()
        assert 'Strain.genus' in source
        assert 'Strain.species' in source


class TestAim2BioconversionFlow:
    """Test the Aim 2 flow startup ordering for fermentation extraction."""

    def test_methods_extract_runs_before_fermentation_extract(self):
        flow_file = pathlib.Path(__file__).parent.parent / "ca_biositing/pipeline/flows/aim2_bioconversion.py"
        source = flow_file.read_text()

        methods_call = "bioconversion_methods.extract()"
        fermentation_call = "bioconversion_data.extract()"

        assert methods_call in source
        assert fermentation_call in source
        assert source.index(methods_call) < source.index(fermentation_call)

    def test_methods_are_loaded_before_fermentation_extract(self):
        flow_file = pathlib.Path(__file__).parent.parent / "ca_biositing/pipeline/flows/aim2_bioconversion.py"
        source = flow_file.read_text()

        load_call = "load_bioconversion_method(bcm_df)"
        fermentation_call = "fermentation_raw = bioconversion_data.extract()"

        assert load_call in source
        assert fermentation_call in source
        assert source.index(load_call) < source.index(fermentation_call)

    def test_bioconversion_method_id_in_transform(self):
        """Verify that transform_fermentation_record uses bioconversion_method_id."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        assert "bioconversion_method_id" in source

    def test_transform_bioconversion_method_id_mapping(self):
        """Verify that transform_fermentation_record maps bioconversion_method_id."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        assert "'bioconversion_method_id': 'bioconversion_method_id'" in source

    def test_strain_seeding_uses_name_genus_species_strain_columns(self):
        """Verify that strain seeding reads name/genus/species/strain columns from the sheet."""
        flow_file = pathlib.Path(__file__).parent.parent / "ca_biositing/pipeline/flows/aim2_bioconversion.py"
        source = flow_file.read_text()
        # New seeding logic uses the taxonomy columns sourced from Strain_name
        assert "'strain_name': 'name'" in source
        assert "'genus': 'genus'" in source
        assert "'species': 'species'" in source
        assert "'strain': 'strain'" in source

    def test_transform_uses_bioconversion_method_for_strain_fk(self):
        """Verify that transform uses BioconversionMethod for strain FK resolution."""
        from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
        source = inspect.getsource(transform_fermentation_record.fn)
        assert "'bioconversion_method': (BioconversionMethod, 'name')" in source

    def test_strain_seeding_reads_methods_sheet_only(self):
        """Verify that strain seed loop reads methods only (03.3-BioConversionMethods)."""
        flow_file = pathlib.Path(__file__).parent.parent / "ca_biositing/pipeline/flows/aim2_bioconversion.py"
        source = flow_file.read_text()
        assert "src = methods_raw.copy()" in source

    def test_flow_uses_new_transform_and_load_tasks(self):
        """Verify new tasks are called in the flow."""
        flow_file = pathlib.Path(__file__).parent.parent / "ca_biositing/pipeline/flows/aim2_bioconversion.py"
        source = flow_file.read_text()
        assert "transform_bioconversion_method" in source
        assert "load_bioconversion_method" in source


class TestMethodLoadTask:
    """Test the method metadata loader task surface."""

    def test_method_load_task_module_exists(self):
        from ca_biositing.pipeline.etl.load.analysis import method

        assert method is not None
        assert hasattr(method, 'load_method')
