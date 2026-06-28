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
    AnalysisType,
    Dataset
)
from sqlalchemy import text

def test_queries():
    engine = get_engine()
    print(f"Testing connection to: {engine.url}")

    with Session(engine) as session:
        # 1. Test basic model query
        comp_count = session.exec(select(func.count()).select_from(CompositionalRecord)).one()
        print(f"Aim 1 - Compositional Records: {comp_count}")

        # 2. Test materialized view query
        with engine.connect() as conn:
            mv_count = conn.execute(text("SELECT count(*) FROM data_portal.mv_biomass_composition")).scalar()
            print(f"Data Portal - mv_biomass_composition: {mv_count}")

        # 3. Test Aim 2 records
        ferm_count = session.exec(select(func.count()).select_from(FermentationRecord)).one()
        print(f"Aim 2 - Fermentation Records: {ferm_count}")

        # 4. Test USDA records
        usda_count = session.exec(select(func.count()).select_from(UsdaSurveyRecord)).one()
        print(f"USDA - Survey Records: {usda_count}")

        # 5. Analysis types
        analysis_counts = session.exec(
            select(Dataset.record_type, func.count(CompositionalRecord.id))
            .select_from(Dataset)
            .join(CompositionalRecord, CompositionalRecord.dataset_id == Dataset.id, isouter=True)
            .group_by(Dataset.record_type)
        ).all()
        print("\nRecords by Analysis Type:")
        for name, count in analysis_counts:
            print(f" - {name}: {count}")

if __name__ == "__main__":
    try:
        test_queries()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
