import os
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

def get_schema():
    os.environ["POSTGRES_HOST"] = "localhost"
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'data_portal'
            ORDER BY table_name, ordinal_position;
        """))
        for row in result:
            print(f"{row.table_name} | {row.column_name} | {row.data_type}")

if __name__ == "__main__":
    get_schema()
