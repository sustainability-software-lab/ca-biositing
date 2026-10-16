import json
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

def serialize(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

engine = get_engine()

with open("/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/sargassum_data.json") as f:
    data = json.load(f)

with engine.connect() as conn:
    lookups = {}
    for tbl in [
        "contact",
        "method",
        "method_category",
        "method_standard",
        "experiment",
        "strain",
        "bioconversion_method",
        "pretreatment_setup",
        "enz_hydr_method",
        "decon_vessel",
        "equipment",
        "location_address",
        "preparation_method",
        "provider",
        "dataset",
    ]:
        try:
            rows = conn.execute(text(f"SELECT * FROM {tbl}")).mappings().all()
            lookups[tbl] = {r["id"]: dict(r) for r in rows}
        except Exception as e:
            print(f"Skipping {tbl}: {e}")
            conn.rollback()

data["lookups"] = lookups

output_path = "/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/sargassum_enriched.json"
with open(output_path, "w") as f:
    json.dump(data, f, default=serialize, indent=2)

print("Saved enriched data to", output_path)
