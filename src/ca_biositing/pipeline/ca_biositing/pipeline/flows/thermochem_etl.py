from prefect import flow, task
import pandas as pd

@flow(name="Thermochemical Conversion ETL", log_prints=True)
def thermochem_etl_flow(force_refresh: bool = False, *args, **kwargs):
    """
    Orchestrates the ETL process for Thermochemical Conversion data,
    including Observations and Gasification Records.
    """
    from prefect import get_run_logger
    from ca_biositing.pipeline.etl.extract import thermochem_data
    from ca_biositing.pipeline.etl.transform.analysis.observation import transform_observation
    from ca_biositing.pipeline.etl.transform.analysis.gasification_record import transform_gasification_record
    from ca_biositing.pipeline.etl.transform.analysis.experiment import transform_experiment
    from ca_biositing.pipeline.etl.load.analysis.observation import load_observation
    from ca_biositing.pipeline.etl.load.analysis.gasification_record import load_gasification_record
    from ca_biositing.pipeline.etl.load.analysis.experiment import load_experiment
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group
    from ca_biositing.pipeline.flows.gasification_archive_pipeline import gasification_archive_subflow

    logger = get_run_logger()
    logger.info("Starting Thermochemical Conversion ETL flow...")

    # 0. Lineage Tracking Setup
    etl_run_id = create_etl_run_record(pipeline_name="Thermochemical Conversion ETL")

    lineage_group = create_lineage_group(
        etl_run_id=etl_run_id,
        note="Thermochemical Conversion - Experiments and Observations"
    )

    # 1. Extraction
    logger.info("Extracting Thermochem data...")
    thermo_exp_raw = thermochem_data.thermo_experiment()
    thermo_data_raw = thermochem_data.thermo_data()

    if thermo_data_raw is not None and not thermo_data_raw.empty:
        # --- PART 0: Experiments ---
        if thermo_exp_raw is not None and not thermo_exp_raw.empty:
            logger.info("Transforming and Loading Experiments...")
            exp_df = transform_experiment(
                raw_dfs=[thermo_exp_raw],
                etl_run_id=etl_run_id,
                lineage_group_id=str(lineage_group)
            )
            if not exp_df.empty:
                load_experiment(exp_df)
            else:
                logger.warning("No experiments produced during transformation.")

        # --- PART 1: Observations ---
        logger.info("Transforming and Loading Observations...")
        obs_raw_copy = thermo_data_raw.copy()
        obs_raw_copy['dataset'] = 'biocirv'

        if 'Record_id' in obs_raw_copy.columns:
            obs_raw_copy['record_id'] = obs_raw_copy['Record_id']
        elif 'Rx_UUID' in obs_raw_copy.columns:
            obs_raw_copy['record_id'] = obs_raw_copy['Rx_UUID']
        elif 'RxID' in obs_raw_copy.columns:
            obs_raw_copy['record_id'] = obs_raw_copy['RxID']

        if 'Analysis_type' not in obs_raw_copy.columns:
            obs_raw_copy['analysis_type'] = 'gasification'
        else:
            obs_raw_copy['analysis_type'] = obs_raw_copy['Analysis_type'].str.lower()

        obs_df = transform_observation(
            [obs_raw_copy],
            etl_run_id=etl_run_id,
            lineage_group_id=str(lineage_group)
        )
        if not obs_df.empty:
            load_observation(obs_df)
        else:
            logger.warning("No observations produced during transformation.")

        # --- PART 2: Gasification Records ---
        logger.info("Transforming and Loading Gasification Records...")
        gas_raw_copy = thermo_data_raw.copy()
        if 'Record_id' in gas_raw_copy.columns:
            gas_raw_copy['record_id'] = gas_raw_copy['Record_id']
        elif 'Rx_UUID' in gas_raw_copy.columns:
            gas_raw_copy['record_id'] = gas_raw_copy['Rx_UUID']
        elif 'RxID' in gas_raw_copy.columns:
            gas_raw_copy['record_id'] = gas_raw_copy['RxID']

        gas_rec_df = transform_gasification_record(
            thermo_data_df=gas_raw_copy,
            thermo_experiment_df=thermo_exp_raw,
            etl_run_id=etl_run_id,
            lineage_group_id=str(lineage_group)
        )

        if not gas_rec_df.empty:
            load_gasification_record(gas_rec_df)

            # --- PART 3: Archival of Gasification Timeseries ---
            archive_data = []
            logger.info(f"Preparing archival for {len(gas_rec_df)} records...")

            for _, row in gas_rec_df.iterrows():
                rid = row['record_id']
                # Case-insensitive match for record_id to account for default cleaning behavior
                match = gas_raw_copy[gas_raw_copy['record_id'].astype(str).str.lower() == str(rid).lower()]

                if not match.empty:
                    gsheet_url = None
                    # Search across possible URL column names (raw or cleaned)
                    # Note: We now preserve casing for raw_data_url in transform
                    for col in ['raw_data_url', 'Raw_data_url', 'Raw_Data_URL', 'Experiment_setup_url', 'Experiment_Setup_URL']:
                        if col in match.columns:
                            val = match.iloc[0].get(col)
                            if val and str(val).startswith('http'):
                                gsheet_url = str(val)
                                break

                    if gsheet_url:
                        archive_data.append({
                            "record_id": rid,
                            "gsheet_url": gsheet_url,
                            "resource_id": row.get('resource_id'),
                            "experiment_id": row.get('experiment_id'),
                            "resource_name": row.get('resource_name'),
                            "reactor_name": row.get('reactor_name'),
                            "reactor_type_id": row.get('reactor_type_id')
                        })

            if archive_data:
                # Deduplicate by gsheet_url to ensure we only trigger archival once per unique spreadsheet
                unique_archive = []
                seen_urls = set()
                for item in archive_data:
                    if item['gsheet_url'] not in seen_urls:
                        unique_archive.append(item)
                        seen_urls.add(item['gsheet_url'])

                logger.info(f"Triggering archival subflow for {len(unique_archive)} unique URLs...")
                gasification_archive_subflow(
                    force_refresh=force_refresh,
                    records_to_archive=unique_archive,
                    etl_run_id=int(etl_run_id),
                    lineage_group_id=int(lineage_group)
                )
            else:
                logger.warning("No valid GSheet URLs found for archival in the extracted records.")
        else:
            logger.warning("No gasification records produced during transformation.")

    else:
        logger.warning("No Thermochem data extracted.")

    logger.info("Thermochemical Conversion ETL flow completed successfully.")

if __name__ == "__main__":
    thermochem_etl_flow()
