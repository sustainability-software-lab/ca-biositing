import os
import pandas as pd
from sqlalchemy import text
os.environ["POSTGRES_HOST"] = "localhost"
from ca_biositing.datamodels.database import get_engine

def main():
    engine = get_engine()
    tables = [
        'xrd_record', 'ftnir_record', 'fermentation_record',
        'pretreatment_record', 'gasification_record'
    ]
    for table in tables:
        try:
            with engine.connect() as conn:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"{table}: {count}")
        except Exception as e:
            print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    main()
