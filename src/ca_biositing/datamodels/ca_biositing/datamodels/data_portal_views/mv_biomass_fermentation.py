"""
mv_biomass_fermentation.py

Fermentation analysis data with aggregated observations by strain and method.

QC: filtered to exclude "fail" - only includes observations from records that are not marked as failed

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)
"""

from sqlalchemy import select, func, and_, or_, case, cast, Numeric
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
from ca_biositing.datamodels.models.aim2_records.pretreatment_setup import PretreatmentSetup
from ca_biositing.datamodels.models.aim2_records.enz_hydr_method import EnzymaticHydrolysisMethod
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.places.location_address import LocationAddress
from ca_biositing.datamodels.models.places.place import Place


PM = aliased(Method, name="pm")
EM = aliased(Method, name="em")
BCM = aliased(BioconversionMethod, name="bcm")
PS = aliased(PretreatmentSetup, name="ps")
PSDM = aliased(Method, name="psdm")
EHM = aliased(EnzymaticHydrolysisMethod, name="ehm")
ELAPSED_TIME = func.coalesce(PM.duration, EM.duration, BCM.time_h, EHM.time_h)

# Updated labels based on user feedback
# Primary mapping is now raw Decon_method (via pretreatment_method_id mapping to Method.name)
_raw_pretreatment = func.coalesce(PM.name, PS.pretreatment_exper_name)
PRETREATMENT_LABEL = case(
    (func.lower(_raw_pretreatment) == "cho10pc", "Cholinium Lysinate 140°C"),
    (func.lower(_raw_pretreatment) == "h2o140c", "Water 140°C"),
    (func.lower(_raw_pretreatment) == "none20c", "No Pretreatment"),
    (func.lower(_raw_pretreatment) == "butknt140c", "Butylamine 140°C"),
    else_=_raw_pretreatment,
)
# Display enzyme_formulation, keyed by method_id if formulation is null
ENZYME_LABEL = func.coalesce(EHM.enzyme_formulation, EHM.method_id)

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
    PRETREATMENT_LABEL.label("pretreatment_method"),
    ENZYME_LABEL.label("enzyme_name"),
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
 .outerjoin(PS, FermentationRecord.pretreatment_setup_id == PS.id)\
 .outerjoin(PSDM, PS.decon_method_id == PSDM.id)\
 .outerjoin(EM, FermentationRecord.eh_method_id == EM.id)\
 .outerjoin(EHM, FermentationRecord.eh_method_id_new == EHM.id)\
 .outerjoin(BCM, FermentationRecord.bioconversion_method_id == BCM.id)\
 .where(FermentationRecord.qc_pass != "fail")\
 .group_by(
     FermentationRecord.resource_id,
     LocationAddress.geography_id,
     Strain.name,
     PRETREATMENT_LABEL,
     ENZYME_LABEL,
     BCM.name,
     ELAPSED_TIME
).subquery()

mv_biomass_fermentation = select(
    func.row_number().over(order_by=(FermentationRecord.resource_id, LocationAddress.geography_id, Strain.name, PRETREATMENT_LABEL, ENZYME_LABEL, BCM.name, Parameter.name, Unit.name)).label("id"),
    FermentationRecord.resource_id,
    Resource.name.label("resource_name"),
    LocationAddress.geography_id.label("geoid"),
    Place.county_name.label("county"),
    SPECIES_DISPLAY_NAME.label("strain_name"),
    PRETREATMENT_LABEL.label("pretreatment_method"),
    ENZYME_LABEL.label("enzyme_name"),
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
 .outerjoin(PS, FermentationRecord.pretreatment_setup_id == PS.id)\
 .outerjoin(PSDM, PS.decon_method_id == PSDM.id)\
 .outerjoin(EM, FermentationRecord.eh_method_id == EM.id)\
 .outerjoin(EHM, FermentationRecord.eh_method_id_new == EHM.id)\
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
         func.coalesce(PRETREATMENT_LABEL, "") == func.coalesce(fermentation_qc_stats.c.pretreatment_method, ""),
         func.coalesce(ENZYME_LABEL, "") == func.coalesce(fermentation_qc_stats.c.enzyme_name, ""),
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
             # If required metrics are missing or sugart0 is 0, we bypass validation
             fermentation_qc_stats.c.avg_sugar_cons.is_(None),
             fermentation_qc_stats.c.avg_sugart0.is_(None),
             fermentation_qc_stats.c.avg_sugart0 == 0,
             # Otherwise, validate sugar consumption consistency (abs error <= 100%)
             func.abs(
                 fermentation_qc_stats.c.avg_sugar_cons -
                 ((fermentation_qc_stats.c.avg_sugart0 - fermentation_qc_stats.c.avg_sugarteof) / cast(fermentation_qc_stats.c.avg_sugart0, Numeric)) * 100
             ) <= 100
         )
     )
  )\
 .group_by(FermentationRecord.resource_id, Resource.name, LocationAddress.geography_id, Place.county_name, Strain.name, Strain.genus, Strain.species, PRETREATMENT_LABEL, ENZYME_LABEL, BCM.name, ELAPSED_TIME, Parameter.name, Unit.name)\
 .having(
     or_(
         func.lower(Parameter.name).not_like('%yield%'),
         and_(
             func.avg(Observation.value) >= 0,
             func.avg(Observation.value) <= 105
         )
     )
  )
