from prefect import flow, task
import pandas as pd
import numpy as np

@flow(name="Aim 2 Bioconversion ETL", log_prints=True)
def aim2_bioconversion_flow(*args, **kwargs):
    """
    Orchestrates the ETL process for Aim 2 Bioconversion data,
    including Pretreatment and Fermentation Records.
    """
    from prefect import get_run_logger
    from ca_biositing.pipeline.etl.extract import pretreatment_data, bioconversion_data, bioconversion_setup, bioconversion_methods
    from ca_biositing.pipeline.etl.transform.analysis.pretreatment_record import transform_pretreatment_record
    from ca_biositing.pipeline.etl.transform.analysis.fermentation_record import transform_fermentation_record
    from ca_biositing.pipeline.etl.transform.analysis.observation import transform_observation
    from ca_biositing.pipeline.etl.load.analysis.pretreatment_record import load_pretreatment_record
    from ca_biositing.pipeline.etl.load.analysis.fermentation_record import load_fermentation_record
    from ca_biositing.pipeline.etl.load.analysis.method import load_method
    from ca_biositing.pipeline.etl.load.analysis.strain import load_strain
    from ca_biositing.pipeline.etl.load.analysis.observation import load_observation
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group
    from ca_biositing.pipeline.flows.analysis_type import analysis_type_flow

    logger = get_run_logger()
    logger.info("Starting Aim 2 Bioconversion ETL flow...")

    # 0. Dependencies and Lineage Tracking Setup
    # Ensure Analysis Types exist first
    analysis_type_flow()

    etl_run_id = create_etl_run_record(pipeline_name="Aim 2 Bioconversion ETL")

    # --- PART 1: Pretreatment ---
    lineage_group_pre = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Aim 2 Bioconversion - Pretreatment Records"
    )

    logger.info("Extracting Pretreatment data...")
    pretreatment_raw = pretreatment_data.extract()

    if pretreatment_raw is not None and not pretreatment_raw.empty:
        # Transform Observations
        pretreatment_raw_copy = pretreatment_raw.copy()
        pretreatment_raw_copy['analysis_type'] = 'pretreatment'
        # Ensure dataset is present for normalization
        if 'dataset' not in pretreatment_raw_copy.columns:
            pretreatment_raw_copy['dataset'] = 'biocirv'

        obs_pre_df = transform_observation(
            [pretreatment_raw_copy],
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_pre
        )
        if not obs_pre_df.empty:
            load_observation(obs_pre_df)

        # Transform Pretreatment Records
        pretreatment_rec_df = transform_pretreatment_record(
            pretreatment_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_pre
        )
        if not pretreatment_rec_df.empty:
            load_pretreatment_record(pretreatment_rec_df)
    else:
        logger.warning("No Pretreatment data extracted.")

    # --- PART 2: Fermentation ---
    lineage_group_ferm = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Aim 2 Bioconversion - Fermentation Records"
    )

    logger.info("Extracting Fermentation data...")
    logger.info("Extracting BioConversion Methods data...")
    methods_raw = bioconversion_methods.extract()

    if methods_raw is not None and not methods_raw.empty:
        methods_df = methods_raw.copy()
        methods_df.columns = [str(c).strip() for c in methods_df.columns]

        method_id_col = next(
            (col for col in methods_df.columns if col.lower().strip() == 'method_id'),
            None
        )

        if method_id_col is not None:
            method_load_df = pd.DataFrame({'name': methods_df[method_id_col]})
            if 'Description' in methods_df.columns:
                method_load_df['description'] = methods_df['Description']
            time_col = next(
                (col for col in methods_df.columns if col.lower().strip() == 'time_h'),
                None
            )
            if time_col is not None:
                method_load_df['duration'] = methods_df[time_col]
            load_method(method_load_df)
        else:
            logger.warning("BioConversion Methods sheet missing Method_id column; skipping method metadata load.")

    fermentation_raw = bioconversion_data.extract()
    setup_raw = bioconversion_setup.extract()

    if fermentation_raw is not None and not fermentation_raw.empty:
        fermentation_for_transform = fermentation_raw.copy()

        # Link 02.2-BioConversionData rows to 03.3-BioConversionMethods strains.
        # 02.2 BioConv_method -> 03.3 method_id, then map to 03.3 Name (strain.name).
        if methods_raw is not None and not methods_raw.empty:
            methods_map_df = methods_raw.copy()
            methods_map_df.columns = [str(c).strip() for c in methods_map_df.columns]
            logger.info(f"03.3 Methods columns: {list(methods_map_df.columns)}")

            method_key_col = next(
                (col for col in methods_map_df.columns if col.lower().strip() == 'method_id'),
                None
            )
            strain_name_col = next(
                (col for col in methods_map_df.columns if col.lower().strip() == 'name'),
                None
            )
            logger.info(f"02.2 -> 03.3 mapping: method_key_col={method_key_col}, strain_name_col={strain_name_col}")

            data_method_col = next(
                (
                    col for col in fermentation_for_transform.columns
                    if 'bioconv' in str(col).lower().strip()
                    or 'bioconversion' in str(col).lower().strip()
                    or str(col).lower().strip() == 'method_id'
                ),
                None
            )
            logger.info(f"02.2 Fermentation columns (all): {list(fermentation_for_transform.columns)}")
            logger.info(f"02.2 -> 03.3 mapping: data_method_col={data_method_col}")

            if method_key_col and strain_name_col and data_method_col:
                method_to_strain = {
                    str(k).strip().lower(): (str(v).strip() if pd.notna(v) and str(v).strip() else None)
                    for k, v in zip(methods_map_df[method_key_col], methods_map_df[strain_name_col])
                    if pd.notna(k) and str(k).strip()
                }

                mapped_strain = (
                    fermentation_for_transform[data_method_col]
                    .astype(object)
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map(method_to_strain)
                )

                if 'strain' in fermentation_for_transform.columns:
                    fermentation_for_transform['strain'] = fermentation_for_transform['strain'].where(
                        fermentation_for_transform['strain'].notna(),
                        mapped_strain
                    )
                else:
                    fermentation_for_transform['strain'] = mapped_strain

                logger.info(
                    "Mapped strain names from 03.3 methods into fermentation data: "
                    f"{int(fermentation_for_transform['strain'].notna().sum())} rows with non-null strain"
                )
            else:
                logger.warning(
                    f"Could not map 03.3 strains to 02.2 fermentation data. "
                    f"Found: method_key_col={method_key_col}, strain_name_col={strain_name_col}, "
                    f"data_method_col={data_method_col}"
                )

        # Transform Observations
        fermentation_raw_copy = fermentation_for_transform.copy()
        fermentation_raw_copy['analysis_type'] = 'fermentation'
        # Ensure dataset is present for normalization
        if 'dataset' not in fermentation_raw_copy.columns:
            fermentation_raw_copy['dataset'] = 'biocirv'

        obs_ferm_df = transform_observation(
            [fermentation_raw_copy],
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_ferm
        )
        if not obs_ferm_df.empty:
            load_observation(obs_ferm_df)

        # Load Strains from both setup and data sheets.
        # Expect the Google Sheet to provide Name, Genus, Species, Strain columns.
        # Make seeding robust by applying the same name-cleaning used elsewhere
        # and only seeding rows that include at least one taxonomy field (genus/species/strain).
        from ca_biositing.pipeline.utils.cleaning_functions import cleaning as cleaning_mod

        strain_col_map = {
            'name': 'name',
            'genus': 'genus',
            'species': 'species',
            'strain': 'strain',
        }

        strain_rows = []
        excluded_rows = 0
        # Seed strains only from the methods sheet (03.3-BioConversionMethods).
        for source_df in [methods_raw]:
            if source_df is None or source_df.empty:
                continue
            # Work on a copy and run the lightweight name-cleaning to normalize headers/values
            src = source_df.copy()
            # cleaning_mod.clean_names_df standardizes column names (strip/lower) and common value fixes
            try:
                src = cleaning_mod.clean_names_df(src)
            except Exception:
                src.columns = [str(c).strip() for c in src.columns]

            src.columns = [str(c).strip().lower() for c in src.columns]
            # Only proceed if a name column exists
            if 'name' not in src.columns:
                continue

            for _, row in src.iterrows():
                record = {}
                for src_col, dest_col in strain_col_map.items():
                    val = row.get(src_col)
                    if isinstance(val, str):
                        val = val.strip()
                    record[dest_col] = val if val not in ('', 'nan', '-', 'None', None) else None

                # Require a name and at least one taxonomy detail to avoid seeding method codes or unrelated text
                if not record.get('name'):
                    excluded_rows += 1
                    continue
                if not (record.get('genus') or record.get('species') or record.get('strain')):
                    excluded_rows += 1
                    continue

                strain_rows.append(record)

        if strain_rows:
            strains_df = pd.DataFrame(strain_rows)
            strains_df = strains_df.replace({"": np.nan, "nan": np.nan, "-": np.nan, "None": np.nan})
            strains_df = strains_df.dropna(subset=['name']).drop_duplicates(subset=['name'])

            logger.info(f"Unique strains to load: {strains_df['name'].tolist()}")
            logger.info(f"Strain rows excluded during seeding (no taxonomy/name): {excluded_rows}")

            if not strains_df.empty:
                load_strain(strains_df)

        # Transform Fermentation Records
        fermentation_rec_df = transform_fermentation_record(
            fermentation_for_transform,
            etl_run_id=etl_run_id,
            lineage_group_id=lineage_group_ferm
        )
        if not fermentation_rec_df.empty:
            load_fermentation_record(fermentation_rec_df)
    else:
        logger.warning("No Fermentation data extracted.")

    logger.info("Aim 2 Bioconversion ETL flow completed successfully.")

if __name__ == "__main__":
    aim2_bioconversion_flow()
