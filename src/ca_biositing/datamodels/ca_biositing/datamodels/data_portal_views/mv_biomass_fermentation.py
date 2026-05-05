"""
mv_biomass_fermentation.py

Fermentation analysis data with aggregated observations by strain and method.

QC: filtered to exclude "fail" - only includes observations from records that are not marked as failed

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)
"""

from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit
from ca_biositing.datamodels.models.methods_parameters_units.method import Method
from ca_biositing.datamodels.models.aim2_records.bioconversion_method import BioconversionMethod
from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
from ca_biositing.datamodels.models.aim2_records.strain import Strain
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place


PM = aliased(Method, name="pm")
EM = aliased(Method, name="em")
BCM = aliased(BioconversionMethod, name="bcm")
ELAPSED_TIME = func.coalesce(PM.duration, EM.duration, BCM.time_h)

SPECIES_DISPLAY_NAME = func.concat(
    func.upper(func.left(Strain.genus, 1)),
    ". ",
    func.lower(Strain.species)
)

mv_biomass_fermentation = select(
    func.row_number().over(order_by=(FermentationRecord.resource_id, LocationAddress.geography_id, Strain.name, PM.name, EM.name, BCM.name, Parameter.name, Unit.name)).label("id"),
    FermentationRecord.resource_id,
    Resource.name.label("resource_name"),
    LocationAddress.geography_id.label("geoid"),
    Place.county_name.label("county"),
    SPECIES_DISPLAY_NAME.label("strain_name"),
    PM.name.label("pretreatment_method"),
    EM.name.label("enzyme_name"),
    BCM.name.label("bioconversion_method"),
    ELAPSED_TIME.label("elapsed_time"),
    Parameter.name.label("product_name"),
    func.avg(Observation.value).label("avg_value"),
    func.min(Observation.value).label("min_value"),
    func.max(Observation.value).label("max_value"),
    func.stddev(Observation.value).label("std_dev"),
    func.count().label("observation_count"),
    Unit.name.label("unit")
).select_from(FermentationRecord)\
 .join(Resource, FermentationRecord.resource_id == Resource.id)\
 .outerjoin(PreparedSample, FermentationRecord.prepared_sample_id == PreparedSample.id)\
 .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
 .outerjoin(LocationAddress, FieldSample.sampling_location_id == LocationAddress.id)\
 .outerjoin(Place, LocationAddress.geography_id == Place.geoid)\
 .outerjoin(Strain, FermentationRecord.strain_id == Strain.id)\
 .outerjoin(PM, FermentationRecord.pretreatment_method_id == PM.id)\
 .outerjoin(EM, FermentationRecord.eh_method_id == EM.id)\
 .outerjoin(BCM, FermentationRecord.bioconversion_method_id == BCM.id)\
 .join(Observation, func.lower(Observation.record_id) == func.lower(FermentationRecord.record_id))\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(FermentationRecord.qc_pass != "fail")\
 .group_by(FermentationRecord.resource_id, Resource.name, LocationAddress.geography_id, Place.county_name, Strain.name, Strain.genus, Strain.species, PM.name, EM.name, BCM.name, ELAPSED_TIME, Parameter.name, Unit.name)
