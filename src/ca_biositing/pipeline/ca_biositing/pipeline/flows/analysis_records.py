from prefect import flow, task
# Move imports inside the flow to avoid module-level import hangs

@flow(name="Analysis Records ETL", log_prints=True)
def analysis_records_flow(*args, **kwargs):
    """
    Orchestrates the ETL process for Proximate, Ultimate, Compositional,
    ICP, XRF, Calorimetry, and XRD records, including their associated observations.
    """
    from prefect import get_run_logger
    from ca_biositing.pipeline.etl.extract import proximate, ultimate, cmpana, icp, xrf, calorimetry, xrd
    from ca_biositing.pipeline.etl.transform.analysis.observation import transform_observation
    from ca_biositing.pipeline.etl.transform.analysis.proximate_record import transform_proximate_record
    from ca_biositing.pipeline.etl.transform.analysis.ultimate_record import transform_ultimate_record
    from ca_biositing.pipeline.etl.transform.analysis.compositional_record import transform_compositional_record
    from ca_biositing.pipeline.etl.transform.analysis.icp_record import transform_icp_record
    from ca_biositing.pipeline.etl.transform.analysis.xrf_record import transform_xrf_record
    from ca_biositing.pipeline.etl.transform.analysis.calorimetry_record import transform_calorimetry_record
    from ca_biositing.pipeline.etl.transform.analysis.xrd_record import transform_xrd_record

    from ca_biositing.pipeline.etl.load.analysis.observation import load_observation
    from ca_biositing.pipeline.etl.load.analysis.proximate_record import load_proximate_record
    from ca_biositing.pipeline.etl.load.analysis.ultimate_record import load_ultimate_record
    from ca_biositing.pipeline.etl.load.analysis.compositional_record import load_compositional_record
    from ca_biositing.pipeline.etl.load.analysis.icp_record import load_icp_record
    from ca_biositing.pipeline.etl.load.analysis.xrf_record import load_xrf_record
    from ca_biositing.pipeline.etl.load.analysis.calorimetry_record import load_calorimetry_record
    from ca_biositing.pipeline.etl.load.analysis.xrd_record import load_xrd_record

    logger = get_run_logger()
    logger.info("Starting Analysis Records ETL flow...")

    # 0. Dependencies and Lineage Tracking Setup
    logger.info("Setting up lineage tracking...")
    from ca_biositing.pipeline.utils.lineage import create_etl_run_record, create_lineage_group
    from ca_biositing.pipeline.flows.analysis_type import analysis_type_flow

    # Ensure Analysis Types exist first
    analysis_type_flow()

    etl_run_id = create_etl_run_record(pipeline_name="Analysis Records ETL")
    logger.info(f"ETL Run ID: {etl_run_id}")

    lineage_group_id = create_lineage_group(etl_run_id=etl_run_id, note="Analytical records (Prox, Ult, Comp, ICP, XRF, Cal, XRD)")
    logger.info(f"Lineage Group ID: {lineage_group_id}")

    # 1. Extract
    def safe_extract(extractor, name, analysis_type=None):
        try:
            logger.info(f"Extracting {name} data...")
            df = extractor.extract()
            if df is not None and analysis_type is not None:
                df = df.copy()
                # Drop existing analysis_type columns (including variations like "Analysis Type")
                # to ensure our hard-coded value isn't dropped by later deduplication logic
                cols_to_drop = [c for c in df.columns if str(c).lower().replace(' ', '_').replace('.', '_') == 'analysis_type']
                if cols_to_drop:
                    logger.info(f"Dropping existing analysis_type columns from {name}: {cols_to_drop}")
                    df = df.drop(columns=cols_to_drop)
                df['analysis_type'] = analysis_type
                # Ensure dataset is present for normalization
                if 'dataset' not in df.columns:
                    df['dataset'] = 'biocirv'
            return df
        except (ValueError, IOError):
            logger.exception(f"Failed to extract {name} data")
            return None
        except Exception:
            logger.exception(f"Unexpected error extracting {name} data")
            raise

    prox_raw = safe_extract(proximate, "Proximate", "proximate analysis")
    ult_raw = safe_extract(ultimate, "Ultimate", "ultimate analysis")
    cmpana_raw = safe_extract(cmpana, "Compositional", "compositional analysis")
    icp_raw = safe_extract(icp, "ICP", "icp analysis")
    xrf_raw = safe_extract(xrf, "XRF", "xrf analysis")
    cal_raw = safe_extract(calorimetry, "Calorimetry", "calorimetry analysis")
    xrd_raw = safe_extract(xrd, "XRD", "xrd analysis")

    raw_data = [d for d in [prox_raw, ult_raw, cmpana_raw, icp_raw, xrf_raw, cal_raw, xrd_raw] if d is not None]

    # 2. Transform (Now includes cleaning, coercion, and normalization)
    logger.info("Starting transformations...")

    obs_df = transform_observation(raw_data, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming Proximate records...")
    prox_rec_df = transform_proximate_record(prox_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming Ultimate records...")
    ult_rec_df = transform_ultimate_record(ult_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming Compositional records...")
    comp_rec_df = transform_compositional_record(cmpana_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming ICP records...")
    icp_rec_df = transform_icp_record(icp_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming XRF records...")
    xrf_rec_df = transform_xrf_record(xrf_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming Calorimetry records...")
    cal_rec_df = transform_calorimetry_record(cal_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    logger.info("Transforming XRD records...")
    xrd_rec_df = transform_xrd_record(xrd_raw, etl_run_id=etl_run_id, lineage_group_id=lineage_group_id)

    # 3. Load
    logger.info("Starting database load...")
    # Using tasks normally allows for retries if defined on the tasks
    load_observation(obs_df)
    load_proximate_record(prox_rec_df)
    load_ultimate_record(ult_rec_df)
    load_compositional_record(comp_rec_df)
    load_icp_record(icp_rec_df)
    load_xrf_record(xrf_rec_df)
    load_calorimetry_record(cal_rec_df)
    load_xrd_record(xrd_rec_df)

    logger.info("Analysis Records ETL flow completed successfully.")

if __name__ == "__main__":
    analysis_records_flow()
