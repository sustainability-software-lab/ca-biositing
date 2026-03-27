import pandas as pd
from prefect import task, get_run_logger
from sqlmodel import Session, select
from ca_biositing.datamodels.database import engine
from ca_biositing.datamodels.models import AnalysisType

@task(retries=3, retry_delay_seconds=10)
def load_analysis_analysis_type(analysis_types_df: pd.DataFrame):
    """
    Loads the data from the analysis_types DataFrame into the database.

    Iterates over a DataFrame and inserts each product name from the 'analysis_name' column
    into the PrimaryProduct table.
    """
    logger = get_run_logger()
    if analysis_types_df is None or analysis_types_df.empty:
        logger.info("No data to load. Skipping database insertion.")
        return

    column_name = 'analysis_name'
    if column_name not in analysis_types_df.columns:
        logger.error(f"Column '{column_name}' not found in the DataFrame. Aborting load.")
        return

    logger.info(f"Attempting to load {len(analysis_types_df)} analysis names into the database...")

    with Session(engine) as session:
        statement = select(AnalysisType.name)
        existing_analysis_types = session.exec(statement).all()
        existing_analysis_type_names = set(existing_analysis_types)

        records_to_add = []
        for analysis_type in analysis_types_df[column_name]:
            if analysis_type not in existing_analysis_type_names:
                name = AnalysisType(name=analysis_type)
                records_to_add.append(name)
                existing_analysis_type_names.add(analysis_type)

        if records_to_add:
            session.add_all(records_to_add)
            session.commit()
            logger.info(f"Successfully committed {len(records_to_add)} new analysis names to the database.")
        else:
            logger.info("No new analysis names to add. All records already exist in the database.")
