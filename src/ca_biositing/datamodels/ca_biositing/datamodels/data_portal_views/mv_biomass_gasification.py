"""
mv_biomass_gasification.py

Gasification analysis data with aggregated observations by reactor type, parameter, and geoid.

Includes geoid from the associated field sample's sampling location.

QC: filtered to exclude "fail" - only includes observations from records that are not marked as failed

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_gasification_id ON data_portal.mv_biomass_gasification (id)
"""

from sqlalchemy import select, func, and_

from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.experiment_equipment.decon_vessel import DeconVessel
from ca_biositing.datamodels.models.aim2_records.gasification_record import GasificationRecord
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.places.location_address import LocationAddress


mv_biomass_gasification = select(
    func.row_number().over(order_by=(GasificationRecord.resource_id, LocationAddress.geography_id, DeconVessel.name, Parameter.name, Unit.name)).label("id"),
    GasificationRecord.resource_id,
    Resource.name.label("resource_name"),
    DeconVessel.name.label("reactor_type"),
    Parameter.name.label("parameter_name"),
    LocationAddress.geography_id.label("geoid"),
    func.avg(Observation.value).label("avg_value"),
    func.min(Observation.value).label("min_value"),
    func.max(Observation.value).label("max_value"),
    func.stddev(Observation.value).label("std_dev"),
    func.count().label("observation_count"),
    Unit.name.label("unit")
).select_from(GasificationRecord)\
 .join(Resource, GasificationRecord.resource_id == Resource.id)\
 .outerjoin(PreparedSample, GasificationRecord.prepared_sample_id == PreparedSample.id)\
 .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
 .outerjoin(LocationAddress, FieldSample.sampling_location_id == LocationAddress.id)\
 .outerjoin(DeconVessel, GasificationRecord.reactor_type_id == DeconVessel.id)\
 .join(Observation, func.lower(Observation.record_id) == func.lower(GasificationRecord.record_id))\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(
     and_(
         GasificationRecord.qc_pass != "fail",
         get_resource_filter(Resource)
     )
 )\
 .group_by(
     GasificationRecord.resource_id,
     Resource.name,
     LocationAddress.geography_id,
     DeconVessel.name,
     Parameter.name,
     Unit.name
 )
