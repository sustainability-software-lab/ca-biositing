import os
from sqlmodel import Session, select, func
from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.models import (
    CompositionalRecord,
    CalorimetryRecord,
    FtnirRecord,
    IcpRecord,
    ProximateRecord,
    FermentationRecord,
    GasificationRecord,
    UsdaSurveyRecord,
    UsdaCensusRecord,
    UsdaCommodity,
    Dataset,
    Resource
)
from sqlalchemy import text
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_summary_stats():
    # Ensure we use localhost for host since we are running outside docker
    os.environ["POSTGRES_HOST"] = "localhost"
    engine = get_engine()
    summary = {}

    with Session(engine) as session:
        # 1. Aim 1 Record Counts
        summary["aim1_counts"] = {
            "compositional": session.exec(select(func.count()).select_from(CompositionalRecord)).one(),
            "calorimetry": session.exec(select(func.count()).select_from(CalorimetryRecord)).one(),
            "ftnir": session.exec(select(func.count()).select_from(FtnirRecord)).one(),
            "icp": session.exec(select(func.count()).select_from(IcpRecord)).one(),
            "proximate": session.exec(select(func.count()).select_from(ProximateRecord)).one(),
        }

        # 2. Aim 2 Record Counts
        summary["aim2_counts"] = {
            "fermentation": session.exec(select(func.count()).select_from(FermentationRecord)).one(),
            "gasification": session.exec(select(func.count()).select_from(GasificationRecord)).one(),
        }

        # 3. USDA & Commodities
        summary["usda_stats"] = {
            "survey_records": session.exec(select(func.count()).select_from(UsdaSurveyRecord)).one(),
            "census_records": session.exec(select(func.count()).select_from(UsdaCensusRecord)).one(),
            "distinct_commodities": session.exec(select(func.count(func.distinct(UsdaCommodity.name)))).one(),
        }

        # 4. Records by Dataset Type
        dataset_counts = session.exec(
            select(Dataset.record_type, func.count())
            .group_by(Dataset.record_type)
        ).all()
        summary["records_by_dataset_type"] = {str(k): v for k, v in dataset_counts}

        # 5. Filter Quality Assessment (Raw vs QC'd in Views)
        # We compare base table counts vs materialized view counts
        with engine.connect() as conn:
            # Note: mv_biomass_composition is a UNION of many tables.
            # To assess filter quality, we look at the 'observation_count' column in the view vs total observations.
            total_observations = conn.execute(text("SELECT count(*) FROM observation")).scalar()

            summary["filter_assessment"] = {
                "total_observations_in_db": total_observations,
                "composition_view": {
                    "view_row_count": conn.execute(text("SELECT count(*) FROM data_portal.mv_biomass_composition")).scalar(),
                    "total_observations_represented": conn.execute(text("SELECT sum(observation_count) FROM data_portal.mv_biomass_composition")).scalar()
                },
                "fermentation_view": {
                    "raw_records": session.exec(select(func.count()).select_from(FermentationRecord)).one(),
                    "view_records": conn.execute(text("SELECT count(*) FROM data_portal.mv_biomass_fermentation")).scalar()
                },
                "gasification_view": {
                    "raw_records": session.exec(select(func.count()).select_from(GasificationRecord)).one(),
                    "view_records": conn.execute(text("SELECT count(*) FROM data_portal.mv_biomass_gasification")).scalar()
                }
            }

    return summary

if __name__ == "__main__":
    try:
        stats = get_summary_stats()
        print(json.dumps(stats, indent=2, cls=DecimalEncoder))
    except Exception as e:
        print(f"Error generating summary: {e}")
        import traceback
        traceback.print_exc()
