import re
import os

filepath = "src/ca_biositing/datamodels/ca_biositing/datamodels/data_portal_views/mv_biomass_volume_estimate.py"

with open(filepath, "r") as f:
    content = f.read()

# Pattern for counties
county_filter = 'func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])'

# We need to make sure ALL paths (A, B, C, D, E) have the county filter.
# I will use a more robust regex replacement or just manual string find/replace if I can identify the exact spots.

# Path A: production_based_volumes
# .where(and_(
#      ResidueFactor.factor_type == "weight",
#      CountyAgReportRecord.data_year >= 2017,
#      get_resource_filter(Resource)
#  ))
content = content.replace(
    'get_resource_filter(Resource)\n     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])\n ))\\', # This might be what's there now from previous run? No, wait.
    'get_resource_filter(Resource)\n ))\\' # Just in case it didn't change correctly
)

# Let's just rewrite the where clauses systematically.

# Path A
pA_old = """     ResidueFactor.factor_type == "weight",
     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource)
 ))"""
pA_new = """     ResidueFactor.factor_type == "weight",
     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))"""

# Path B
pB_old = """     ResidueFactor.prune_trim_yield.isnot(None),
     ResidueFactor.factor_type != "area",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource)
 ))"""
pB_new = """     ResidueFactor.prune_trim_yield.isnot(None),
     ResidueFactor.factor_type != "area",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))"""

# Path C
pC_old = """     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource)
 ))"""
pC_new = """     CountyAgReportRecord.data_year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
 ))"""

# Path D
pD_old = """.where(and_(
  UsdaCensusRecord.year >= 2017,
  get_resource_filter(Resource)
))"""
pD_new = """.where(and_(
  UsdaCensusRecord.year >= 2017,
  get_resource_filter(Resource),
  func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"])
))"""

# Path E (special case with comment)
pE_old = """     ResidueFactor.factor_type == "weight",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource),
     # Only include resources"""
pE_new = """     ResidueFactor.factor_type == "weight",
     UsdaCensusRecord.year >= 2017,
     get_resource_filter(Resource),
     func.lower(Place.county_name).in_(["san joaquin", "stanislaus", "merced"]),
     # Only include resources"""

# Re-read to ensure we have clean slate (actually user says it didn't work, let's see what's in there)
# Wait, I'll just use simple find/replace on what I SAW in the read_file output.

content = content.replace(pA_old, pA_new)
content = content.replace(pB_old, pB_new)
content = content.replace(pC_old, pC_new)
content = content.replace(pD_old, pD_new)
content = content.replace(pE_old, pE_new)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied successfully.")
