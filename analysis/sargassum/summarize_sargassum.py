import json
from collections import defaultdict, Counter

with open("/Users/pjsmitty301/.gemini/antigravity/brain/42a5010b-7235-40e6-8c99-569580ebe1ec/scratch/sargassum_enriched.json") as f:
    data = json.load(f)

lookups = data["lookups"]

print("=== RESOURCE ===")
for r in data["resources"]:
    print(r)

print("\n=== FIELD SAMPLES ===")
for fs in data["field_samples"]:
    loc = lookups.get("location_address", {}).get(str(fs["sampling_location_id"]), {})
    print(f"ID {fs['id']}: {fs['name']} | provider={fs['provider_codename']} | collected={fs['collection_timestamp']} | loc={loc}")

print("\n=== PREPARED SAMPLES ===")
for ps in data["prepared_samples"]:
    preparer = lookups.get("contact", {}).get(str(ps["preparer_id"]), {})
    prep_name = f"{preparer.get('first_name') or ''} {preparer.get('last_name') or ''}".strip() or preparer.get("name") or preparer.get("email")
    print(f"ID {ps['id']}: {ps['name']} | field_sample={ps['field_sample_name']} | method={ps['prep_method_name']} | date={ps['prep_date']} | preparer={prep_name} | note={ps['note']}")

# Map record_id -> record metadata across all tables
record_map = {}
for tbl, rows in data["records"].items():
    print(f"\n=== TABLE: {tbl} ({len(rows)} records) ===")
    qc_counts = Counter(r.get("qc_pass") for r in rows)
    ps_counts = Counter(r.get("prepared_sample_name") for r in rows)
    exp_counts = Counter(r.get("experiment_name") for r in rows)
    method_counts = Counter(r.get("method_name") for r in rows)
    print("  QC:", dict(qc_counts))
    print("  Prepared Samples:", dict(ps_counts))
    print("  Experiments:", dict(exp_counts))
    print("  Methods:", dict(method_counts))
    # Check extra columns for fermentation / pretreatment
    if tbl == "fermentation_record":
        strains = Counter(lookups.get("strain", {}).get(str(r.get("strain_id")), {}).get("name") for r in rows)
        bioconv = Counter(lookups.get("bioconversion_method", {}).get(str(r.get("bioconversion_method_id")), {}).get("name") for r in rows)
        pt_method = Counter(lookups.get("method", {}).get(str(r.get("pretreatment_method_id")), {}).get("name") for r in rows)
        eh_method = Counter(lookups.get("method", {}).get(str(r.get("eh_method_id")), {}).get("name") for r in rows)
        eh_new = Counter(lookups.get("enz_hydr_method", {}).get(str(r.get("eh_method_id_new")), {}).get("name") for r in rows)
        vessels = Counter(lookups.get("decon_vessel", {}).get(str(r.get("vessel_id")), {}).get("name") for r in rows)
        print("  Strains:", dict(strains))
        print("  Bioconversion method:", dict(bioconv))
        print("  Pretreatment method:", dict(pt_method))
        print("  EH method:", dict(eh_method), "EH new:", dict(eh_new))
        print("  Vessels:", dict(vessels))
    if tbl == "pretreatment_record":
        pt_m = Counter(lookups.get("method", {}).get(str(r.get("pretreatment_method_id")), {}).get("name") for r in rows)
        eh_m = Counter(lookups.get("method", {}).get(str(r.get("eh_method_id")), {}).get("name") for r in rows)
        temps = Counter(r.get("temperature") for r in rows)
        print("  PT method:", dict(pt_m), "EH method:", dict(eh_m), "Temps:", dict(temps))

    for r in rows:
        record_map[r["record_id"]] = (tbl, r)

# Summarize observations by record_type and parameter
obs_by_type = defaultdict(lambda: defaultdict(list))
unmatched_obs = []
for o in data["observations"]:
    rec_info = record_map.get(o["record_id"])
    tbl = rec_info[0] if rec_info else "UNMATCHED"
    obs_by_type[(o["record_type"], tbl)][(o["parameter_name"], o["unit_name"], o["dimension_type_name"], o["dimension_unit_name"])].append(o)

print("\n=== OBSERVATIONS SUMMARY ===")
for (rtype, tbl), params in obs_by_type.items():
    print(f"\nRecord Type: '{rtype}' (Table: {tbl})")
    for (pname, uname, dtype, dunit), obs_list in sorted(params.items()):
        vals = [float(x["value"]) for x in obs_list if x["value"] is not None]
        dvals = set(x["dimension_value"] for x in obs_list if x["dimension_value"] is not None)
        print(f"  - {pname} [{uname}] (n={len(obs_list)}): min={min(vals):.3f}, max={max(vals):.3f}, avg={sum(vals)/len(vals):.3f} | dim={dtype} ({len(dvals)} vals: {sorted(list(dvals))[:5]})")
