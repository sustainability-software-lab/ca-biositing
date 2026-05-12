"""
Materialized view: mv_biomass_availability

Aggregates resource availability data to one row per resource, showing seasonal
availability and average residue factors (dry and wet tons per acre).

Indexes needed:
  CREATE UNIQUE INDEX idx_mv_biomass_availability_resource_id ON data_portal.mv_biomass_availability (resource_id)
"""

from sqlalchemy import select, func, and_
from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.resource_information.resource_availability import ResourceAvailability

mv_biomass_availability = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    func.min(ResourceAvailability.from_month).label("from_month"),
    func.max(ResourceAvailability.to_month).label("to_month"),
    func.bool_or(ResourceAvailability.year_round).label("year_round"),
    func.avg(ResourceAvailability.residue_factor_dry_tons_acre).label("dry_tons_per_acre"),
    func.avg(ResourceAvailability.residue_factor_wet_tons_acre).label("wet_tons_per_acre")
).select_from(ResourceAvailability)\
 .join(Resource, ResourceAvailability.resource_id == Resource.id)\
 .where(get_resource_filter(Resource))\
 .group_by(Resource.id, Resource.name).subquery()
