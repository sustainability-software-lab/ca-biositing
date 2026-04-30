"""
Data portal materialized views package.

This package provides SQLAlchemy select() expressions for data portal materialized views.
Each view is defined in its own module for clarity and maintainability.

For backward compatibility, all views are re-exported here. Code that previously imported
from data_portal_views.py can continue to work unchanged:

    from ca_biositing.datamodels.data_portal_views import mv_biomass_search
"""

# Import all view definitions
from .mv_biomass_availability import mv_biomass_availability
from .mv_biomass_composition import mv_biomass_composition
from .mv_billion_ton_county_production import mv_billion_ton_county_production
from .mv_biomass_sample_stats import mv_biomass_sample_stats
from .mv_biomass_fermentation import mv_biomass_fermentation
from .mv_biomass_gasification import mv_biomass_gasification
from .mv_biomass_pricing import mv_biomass_pricing
from .mv_usda_county_production import mv_usda_county_production
from .mv_biomass_search import mv_biomass_search
from .mv_biomass_end_uses import mv_biomass_end_uses
from .mv_biomass_volume_estimate import mv_biomass_volume_estimate

__all__ = [
    "mv_biomass_availability",
    "mv_biomass_composition",
    "mv_billion_ton_county_production",
    "mv_biomass_sample_stats",
    "mv_biomass_fermentation",
    "mv_biomass_gasification",
    "mv_biomass_pricing",
    "mv_usda_county_production",
    "mv_biomass_search",
    "mv_biomass_end_uses",
    "mv_biomass_volume_estimate",
]
