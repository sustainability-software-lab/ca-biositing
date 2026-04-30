"""
ETL Extract: County Almond Agricultural Reports

Extracts almond county ag report data from the combined Google Sheet tab.
"""

from .factory import create_extractor

GSHEET_NAME = "1vHCpd14aa-Vc_WzWXxUlU6FxcI5IOR30Bi6v3Wjqon8"

parameters = create_extractor(GSHEET_NAME, "parameters")
price_production_county_ag_reports = create_extractor(GSHEET_NAME, "price_production_county_ag_reports")
