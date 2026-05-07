"""
mv_biomass_fermentation.py

Fermentation analysis data with aggregated observations by strain and method.

QC: filtered to exclude "fail" - only includes observations from records that are not marked as failed

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)
"""

from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
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

# QC: Subquery to calculate fermentation QC metrics per group
# Used to validate sugar consumption: sugar_cons ≈ ((sugart0 - sugarteof) / sugart0) * 100
fermentation_qc_stats = select(
    FermentationRecord.resource_id,
    LocationAddress.geography_id.label("geoid"),
    Strain.name.label("strain_name"),
    PM.name.label("pretreatment_method"),
    EM.name.label("enzyme_name"),
    BCM.name.label("bioconversion_method"),
    ELAPSED_TIME.label("elapsed_time"),
    func.avg(case((func.lower(Parameter.name) == "sugar_cons", Observation.value))).label("avg_sugar_cons"),
    func.avg(case((func.lower(Parameter.name) == "sugart0", Observation.value))).label("avg_sugart0"),
    func.avg(case((func.lower(Parameter.name) == "sugarteof", Observation.value))).label("avg_sugarteof")
).select_from(FermentationRecord)\
 .join(Observation, func.lower(Observation.record_id) == func.lower(FermentationRecord.record_id))\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(PreparedSample, FermentationRecord.prepared_sample_id == PreparedSample.id)\
 .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
 .outerjoin(LocationAddress, FieldSample.sampling_location_id == LocationAddress.id)\
 .outerjoin(Strain, FermentationRecord.strain_id == Strain.id)\
 .outerjoin(PM, FermentationRecord.pretreatment_method_id == PM.id)\
 .outerjoin(EM, FermentationRecord.eh_method_id == EM.id)\
 .outerjoin(BCM, FermentationRecord.bioconversion_method_id == BCM.id)\
 .where(FermentationRecord.qc_pass != "fail")\
 .group_by(
     FermentationRecord.resource_id,
     LocationAddress.geography_id,
     Strain.name,
     PM.name,
     EM.name,
     BCM.name,
     ELAPSED_TIME
).subquery()

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
 .join(
     fermentation_qc_stats,
     and_(
         FermentationRecord.resource_id == fermentation_qc_stats.c.resource_id,
         func.coalesce(LocationAddress.geography_id, "") == func.coalesce(fermentation_qc_stats.c.geoid, ""),
         func.coalesce(Strain.name, "") == func.coalesce(fermentation_qc_stats.c.strain_name, ""),
         func.coalesce(PM.name, "") == func.coalesce(fermentation_qc_stats.c.pretreatment_method, ""),
         func.coalesce(EM.name, "") == func.coalesce(fermentation_qc_stats.c.enzyme_name, ""),
         func.coalesce(BCM.name, "") == func.coalesce(fermentation_qc_stats.c.bioconversion_method, ""),
         func.coalesce(ELAPSED_TIME, 0) == func.coalesce(fermentation_qc_stats.c.elapsed_time, 0)
     )
 )\
 .where(
     and_(
         FermentationRecord.qc_pass != "fail",
         get_resource_filter(Resource),
         # Sugar consumption validation with ~100% tolerance
         or_(
             and_(
                 fermentation_qc_stats.c.avg_sugar_cons.is_not(None),
                 fermentation_qc_stats.c.avg_sugart0.is_not(None),
                 fermentation_qc_stats.c.avg_sugart0 != 0
             ).op("IS NOT TRUE")(True), # SQLAlchemy way to handle potential NULLs in or_ logic if needed, but and_ handles it
             # Simple expression: abs(sugar_cons - calc_cons) <= 100
             func.abs(
                 fermentation_qc_stats.c.avg_sugar_cons -
                 ((fermentation_qc_stats.c.avg_sugart0 - fermentation_qc_stats.c.avg_sugarteof) / fermentation_qc_stats.c.avg_sugart0) * 100
             ) <= 100
         )
     )
 )\
 .group_by(FermentationRecord.resource_id, Resource.name, LocationAddress.geography_id, Place.county_name, Strain.name, Strain.genus, Strain.species, PM.name, EM.name, BCM.name, ELAPSED_TIME, Parameter.name, Unit.name)\
 .having(
     or_(
         func.lower(Parameter.name).not_like('%yield%'),
         and_(
             func.avg(Observation.value) >= 0,
             func.avg(Observation.value) <= 105
         )
     )
 )
