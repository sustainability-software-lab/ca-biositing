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

data = {}

with engine.connect() as conn:
    # 1. Resource info + lookups
    resources = conn.execute(
        text("""
            SELECT r.*,
                   rc.name as resource_class_name,
                   rs.name as resource_subclass_name,
                   pap.name as primary_ag_product_name
            FROM resource r
            LEFT JOIN resource_class rc ON r.resource_class_id = rc.id
            LEFT JOIN resource_subclass rs ON r.resource_subclass_id = rs.id
            LEFT JOIN primary_ag_product pap ON r.primary_ag_product_id = pap.id
            WHERE lower(r.name) LIKE '%sargassum%' OR lower(r.description) LIKE '%sargassum%'
        """)
    ).mappings().all()
    data["resources"] = [dict(r) for r in resources]
    resource_ids = [r["id"] for r in resources]

    # 1b. Other resource tables
    for r_tbl in [
        "resource_availability",
        "resource_counterfactual",
        "resource_image",
        "resource_price_record",
        "resource_transport_record",
        "resource_storage_record",
        "resource_end_use_record",
        "resource_production_record",
    ]:
        try:
            rows = conn.execute(
                text(f"SELECT * FROM {r_tbl} WHERE resource_id = ANY(:rids)"),
                {"rids": resource_ids}
            ).mappings().all()
            if rows:
                data[r_tbl] = [dict(r) for r in rows]
        except Exception as e:
            conn.rollback()

    # 2. Field samples
    fs_rows = conn.execute(
        text("""
            SELECT fs.*,
                   r.name as resource_name,
                   p.codename as provider_codename,
                   c.name as collector_name,
                   u_amt.name as amount_unit,
                   la.geography_id as geoid,
                   la.city as city,
                   pl.county_name as county_name,
                   pl.state_name as state_name,
                   fsm.name as storage_method,
                   cm.name as collection_method,
                   hm.name as harvest_method
            FROM field_sample fs
            LEFT JOIN resource r ON fs.resource_id = r.id
            LEFT JOIN provider p ON fs.provider_id = p.id
            LEFT JOIN contact c ON fs.collector_id = c.id
            LEFT JOIN unit u_amt ON fs.amount_collected_unit_id = u_amt.id
            LEFT JOIN location_address la ON fs.sampling_location_id = la.id
            LEFT JOIN place pl ON la.geography_id = pl.geoid
            LEFT JOIN field_storage_method fsm ON fs.field_storage_method_id = fsm.id
            LEFT JOIN collection_method cm ON fs.collection_method_id = cm.id
            LEFT JOIN harvest_method hm ON fs.harvest_method_id = hm.id
            WHERE fs.resource_id = ANY(:rids)
               OR lower(fs.name) LIKE '%sargassum%'
               OR lower(fs.note) LIKE '%sargassum%'
        """),
        {"rids": resource_ids}
    ).mappings().all()
    data["field_samples"] = [dict(fs) for fs in fs_rows]
    fs_ids = [fs["id"] for fs in fs_rows]

    # 3. Prepared samples
    ps_rows = conn.execute(
        text("""
            SELECT ps.*,
                   fs.name as field_sample_name,
                   fs.resource_id as fs_resource_id,
                   pm.name as prep_method_name,
                   pm.description as prep_method_desc,
                   c.name as preparer_name
            FROM prepared_sample ps
            LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
            LEFT JOIN preparation_method pm ON ps.prep_method_id = pm.id
            LEFT JOIN contact c ON ps.preparer_id = c.id
            WHERE ps.field_sample_id = ANY(:fsids)
               OR lower(ps.name) LIKE '%sargassum%'
               OR lower(ps.note) LIKE '%sargassum%'
        """),
        {"fsids": fs_ids}
    ).mappings().all()
    data["prepared_samples"] = [dict(ps) for ps in ps_rows]
    ps_ids = [ps["id"] for ps in ps_rows]

    # 4. Analytical & Processing Records
    record_tables = [
        "proximate_record",
        "ultimate_record",
        "compositional_record",
        "icp_record",
        "xrf_record",
        "calorimetry_record",
        "xrd_record",
        "ftnir_record",
        "rgb_record",
        "autoclave_record",
        "fermentation_record",
        "gasification_record",
        "pretreatment_record",
    ]

    all_record_ids = []
    data["records"] = {}
    for tbl in record_tables:
        try:
            rows = conn.execute(
                text(f"""
                    SELECT rec.*,
                           r.name as resource_name,
                           ps.name as prepared_sample_name,
                           fs.name as field_sample_name,
                           pm.name as prep_method_name,
                           m.name as method_name,
                           ms.name as method_standard_name,
                           c.name as analyst_name,
                           e.name as experiment_name,
                           d.name as dataset_name
                    FROM {tbl} rec
                    LEFT JOIN resource r ON rec.resource_id = r.id
                    LEFT JOIN prepared_sample ps ON rec.prepared_sample_id = ps.id
                    LEFT JOIN field_sample fs ON ps.field_sample_id = fs.id
                    LEFT JOIN preparation_method pm ON ps.prep_method_id = pm.id
                    LEFT JOIN method m ON rec.method_id = m.id
                    LEFT JOIN method_standard ms ON m.method_standard_id = ms.id
                    LEFT JOIN contact c ON rec.analyst_id = c.id
                    LEFT JOIN experiment e ON rec.experiment_id = e.id
                    LEFT JOIN dataset d ON rec.dataset_id = d.id
                    WHERE rec.resource_id = ANY(:rids)
                       OR rec.prepared_sample_id = ANY(:psids)
                       OR lower(rec.record_id) LIKE '%sargassum%'
                       OR lower(rec.note) LIKE '%sargassum%'
                """),
                {"rids": resource_ids, "psids": ps_ids}
            ).mappings().all()
            if rows:
                data["records"][tbl] = [dict(r) for r in rows]
                for row in rows:
                    all_record_ids.append(row["record_id"])
        except Exception as e:
            print(f"Error querying {tbl}: {e}")
            conn.rollback()

    # 5. Observations
    obs_rows = conn.execute(
        text("""
            SELECT o.*,
                   p.name as parameter_name,
                   p.description as parameter_desc,
                   u.name as unit_name,
                   dt.name as dimension_type_name,
                   du.name as dimension_unit_name,
                   d.name as dataset_name
            FROM observation o
            LEFT JOIN parameter p ON o.parameter_id = p.id
            LEFT JOIN unit u ON o.unit_id = u.id
            LEFT JOIN dimension_type dt ON o.dimension_type_id = dt.id
            LEFT JOIN unit du ON o.dimension_unit_id = du.id
            LEFT JOIN dataset d ON o.dataset_id = d.id
            WHERE o.record_id = ANY(:rec_ids)
               OR lower(o.record_id) LIKE '%sargassum%'
               OR lower(o.note) LIKE '%sargassum%'
            ORDER BY o.record_type, o.record_id, p.name
        """),
        {"rec_ids": all_record_ids}
    ).mappings().all()
    data["observations"] = [dict(o) for o in obs_rows]

    # 6. Check materialized views (analysis_data_view, analysis_average_view) for sargassum
    try:
        adv_rows = conn.execute(
            text("SELECT * FROM ca_biositing.analysis_data_view WHERE lower(resource) LIKE '%sargassum%'")
        ).mappings().all()
        data["analysis_data_view"] = [dict(r) for r in adv_rows]
    except Exception as e:
        print(f"Error querying analysis_data_view: {e}")
        conn.rollback()

    try:
        aav_rows = conn.execute(
            text("SELECT * FROM ca_biositing.analysis_average_view WHERE lower(resource) LIKE '%sargassum%'")
        ).mappings().all()
        data["analysis_average_view"] = [dict(r) for r in aav_rows]
    except Exception as e:
        print(f"Error querying analysis_average_view: {e}")
        conn.rollback()

output_path = "/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/sargassum_data.json"
with open(output_path, "w") as f:
    json.dump(data, f, default=serialize, indent=2)

print("Summary:")
print(f"Resources: {len(data['resources'])}")
print(f"Field Samples: {len(data['field_samples'])}")
print(f"Prepared Samples: {len(data['prepared_samples'])}")
for k, v in data["records"].items():
    print(f"  Record table {k}: {len(v)} rows")
print(f"Observations: {len(data['observations'])}")
print(f"analysis_data_view: {len(data.get('analysis_data_view', []))}")
print(f"analysis_average_view: {len(data.get('analysis_average_view', []))}")
