from prefect import flow, task
import pandas as pd
import numpy as np

@flow(name="Aim 2 Bioconversion ETL", log_prints=True)
def aim2_bioconversion_flow(*args, **kwargs):
    """
    Orchestrates the ETL process for Aim 2 Bioconversion data,
    including Bioconversion Methods, Strains, and Fermentation Records.
    """
    from prefect import get_run_logger
    from ca_biositing.pipeline.etl.extract import (
        pretreatment_data,
        bioconversion_data,
        bioconversion_setup,
        bioconversion_methods,
        pretreatment_setup,
        enz_hydr_methods
    )
    from ca_biositing.pipeline.etl.transform.analysis.pretreatment_record import transform_pretreatment_record
    from ca_biositing.pipeline.etl.transform.analysis.pretreatment_setup import transform_pretreatment_setup
    from ca_biositing.pipeline.etl.transform.analysis.enz_hydr_method import transform_enz_hydr_method
    from ca_biositing.pipeline.etl.transform.analysis.bioconversion_method import transform_bioconversion_method
    from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
    from ca_biositing.pipeline.etl.transform.analysis.observation import transform_observation
    from ca_biositing.pipeline.etl.load.analysis.pretreatment_record import load_pretreatment_record
    from ca_biositing.pipeline.etl.load.analysis.pretreatment_setup import load_pretreatment_setup
    from ca_biositing.pipeline.etl.load.analysis.enz_hydr_method import load_enz_hydr_method
    from ca_biositing.pipeline.etl.load.analysis.bioconversion_method import load_bioconversion_method
    from ca_biositing.pipeline.etl.load.analysis.fermentation_record import load_fermentation_record
    from ca_biositing.pipeline.etl.load.analysis.method import load_method
    from ca_biositing.pipeline.etl.load.analysis.strain import load_strain
    from ca_biositing.pipeline.etl.load.analysis.observation import load_observation
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group
    from ca_biositing.pipeline.flows.analysis_type import analysis_type_flow

    logger = get_run_logger()
    logger.info("Starting Aim 2 Bioconversion ETL flow...")

    # 0. Dependencies and Lineage Tracking Setup
    analysis_type_flow()
    etl_run_id = create_etl_run_record(pipeline_name="Aim 2 Bioconversion ETL")

    # --- PART 1: Pretreatment Setup & Records ---
    lineage_group_pre = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Aim 2 Bioconversion - Pretreatment Setup and Records"
    )

    # 1.1 Pretreatment Setup
    logger.info("Extracting Pretreatment Setup data...")
    pre_setup_raw = pretreatment_setup.extract()
    if pre_setup_raw is not None and not pre_setup_raw.empty:
        pre_setup_df = transform_pretreatment_setup(
            pre_setup_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_pre
        )
        if not pre_setup_df.empty:
            load_pretreatment_setup(pre_setup_df)

    # 1.2 Pretreatment Records
    logger.info("Extracting Pretreatment data...")
    pretreatment_raw = pretreatment_data.extract()

    if pretreatment_raw is not None and not pretreatment_raw.empty:
        # Observations
        pretreatment_raw_copy = pretreatment_raw.copy()
        pretreatment_raw_copy['analysis_type'] = 'pretreatment'
        if 'dataset' not in pretreatment_raw_copy.columns:
            pretreatment_raw_copy['dataset'] = 'biocirv'

        obs_pre_df = transform_observation(
            [pretreatment_raw_copy],
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_pre
        )
        if not obs_pre_df.empty:
            load_observation(obs_pre_df)

        # Pretreatment Records
        pretreatment_rec_df = transform_pretreatment_record(
            pretreatment_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_pre
        )
        if not pretreatment_rec_df.empty:
            load_pretreatment_record(pretreatment_rec_df)

    # --- PART 2: Bioconversion Methods & Strains ---
    lineage_group_methods = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Aim 2 Bioconversion - Methods and Strains"
    )

    logger.info("Extracting BioConversion Methods data...")
    methods_raw = bioconversion_methods.extract()

    if methods_raw is not None and not methods_raw.empty:
        # 0. Load Enz Hydr Methods
        logger.info("Extracting Enz Hydr Methods data...")
        eh_methods_raw = enz_hydr_methods.extract()
        if eh_methods_raw is not None and not eh_methods_raw.empty:
            eh_methods_df = transform_enz_hydr_method(
                eh_methods_raw,
                etl_run_id=etl_run_id,
                lineage_group_id=lineage_group_methods
            )
            if not eh_methods_df.empty:
                load_enz_hydr_method(eh_methods_df)

        # 1. Load Strains first (since BioconversionMethod depends on them)
        # Extract name, genus, species, strain, description, note from 03.3
        from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod

        strain_rows = []
        src = methods_raw.copy()
        try:
            src = cleaning_mod.clean_names_df(src)
        except Exception:
            src.columns = [str(c).strip().lower() for c in src.columns]

        # Map sheet columns to Strain model
        # Assuming sheet has 'Strain_name', 'Genus', 'Species', 'Strain', 'Description', 'Note'
        strain_col_map = {
            'strain_name': 'name',
            'genus': 'genus',
            'species': 'species',
            'strain': 'strain',
            'description': 'description',
            'note': 'note'
        }

        for _, row in src.iterrows():
            record = {}
            for src_col, dest_col in strain_col_map.items():
                val = row.get(src_col)
                if isinstance(val, str):
                    val = val.strip()
                record[dest_col] = val if val not in ('', 'nan', '-', 'None', None) else None

            if record.get('name'):
                strain_rows.append(record)

        if strain_rows:
            strains_df = pd.DataFrame(strain_rows).drop_duplicates(subset=['name'])
            load_strain(strains_df)

        # 2. Load BioconversionMethods
        bcm_df = transform_bioconversion_method(
            methods_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_methods
        )
        if not bcm_df.empty:
            load_bioconversion_method(bcm_df)

    # --- PART 3: Fermentation ---
    lineage_group_ferm = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Aim 2 Bioconversion - Fermentation Records"
    )

    logger.info("Extracting Fermentation data...")
    fermentation_raw = bioconversion_data.extract()

    if fermentation_raw is not None and not fermentation_raw.empty:
        # Observations
        fermentation_raw_copy = fermentation_raw.copy()
        fermentation_raw_copy['analysis_type'] = 'fermentation'
        if 'dataset' not in fermentation_raw_copy.columns:
            fermentation_raw_copy['dataset'] = 'biocirv'

        obs_ferm_df = transform_observation(
            [fermentation_raw_copy],
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_ferm
        )
        if not obs_ferm_df.empty:
            load_observation(obs_ferm_df)

        # Fermentation Records
        fermentation_rec_df = transform_fermentation_record(
            fermentation_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_ferm
        )
        if not fermentation_rec_df.empty:
            load_fermentation_record(fermentation_rec_df)

    logger.info("Aim 2 Bioconversion ETL flow completed successfully.")

if __name__ == "__main__":
    aim2_bioconversion_flow()
