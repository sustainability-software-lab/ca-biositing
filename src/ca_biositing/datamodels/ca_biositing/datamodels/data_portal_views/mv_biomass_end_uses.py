"""
mv_biomass_end_uses.py

End-use breakdown per resource from ResourceEndUseRecord observations.

Grain: One row per resource × use_case combination.

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_end_uses_resource_use_case ON data_portal.mv_biomass_end_uses (resource_id, use_case)
"""

from sqlalchemy import select, func, case, cast, String, Float, Text, literal

from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.resource_information.resource_end_use_record import ResourceEndUseRecord
from ca_biositing.datamodels.models.resource_information.use_case import UseCase
from ca_biositing.datamodels.models.general_analysis.observation import Observation
from ca_biositing.datamodels.models.methods_parameters_units.parameter import Parameter
from ca_biositing.datamodels.models.methods_parameters_units.unit import Unit


# Aggregate observations by record_id for end-use data
end_use_obs = select(
    Observation.record_id,
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_use_perc_low",
                Observation.value,
            )
        )
    ).label("percentage_low"),
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_use_perc_high",
                Observation.value,
            )
        )
    ).label("percentage_high"),
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_value_low",
                Observation.value,
            )
        )
    ).label("value_low_usd"),
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_value_high",
                Observation.value,
            )
        )
    ).label("value_high_usd"),
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_value_multiplier_low",
                Observation.value,
            )
        )
    ).label("value_multiplier_low"),
    func.avg(
        case(
            (
                func.lower(Parameter.name) == "resource_value_multiplier_high",
                Observation.value,
            )
        )
    ).label("value_multiplier_high"),
    func.max(
        case(
            (
                func.lower(Parameter.name) == "resource_use_perc_low",
                Unit.name,
            )
        )
    ).label("unit"),
    func.max(
        case(
            (
                func.lower(Parameter.name) == "resource_use_trend",
                cast(Observation.note, String),
            )
        )
    ).label("trend"),
    func.max(
        case(
            (
                func.lower(Parameter.name).in_(["resource_value_low", "resource_value_high"]),
                Unit.name,
            )
        )
    ).label("value_unit"),
).select_from(Observation)\
 .join(Parameter, Observation.parameter_id == Parameter.id)\
 .outerjoin(Unit, Observation.unit_id == Unit.id)\
 .where(func.lower(Observation.record_type) == "resource_end_use_record")\
 .group_by(Observation.record_id).subquery()

mv_biomass_end_uses = select(
    ResourceEndUseRecord.resource_id,
    Resource.name.label("resource_name"),
    func.coalesce(UseCase.name, literal("unknown")).label("use_case"),
    cast(func.avg(end_use_obs.c.percentage_low), Float).label("percentage_low"),
    cast(func.avg(end_use_obs.c.percentage_high), Float).label("percentage_high"),
    cast(func.max(end_use_obs.c.trend), Text).label("trend"),
    cast(func.avg(end_use_obs.c.value_low_usd), Float).label("value_low_usd"),
    cast(func.avg(end_use_obs.c.value_high_usd), Float).label("value_high_usd"),
    cast(func.avg(end_use_obs.c.value_multiplier_low), Float).label("value_multiplier_low"),
    cast(func.avg(end_use_obs.c.value_multiplier_high), Float).label("value_multiplier_high"),
    cast(func.max(end_use_obs.c.value_unit), Text).label("value_notes"),
).select_from(ResourceEndUseRecord)\
 .join(Resource, ResourceEndUseRecord.resource_id == Resource.id)\
 .outerjoin(UseCase, ResourceEndUseRecord.use_case_id == UseCase.id)\
 .outerjoin(end_use_obs, cast(ResourceEndUseRecord.id, String) == end_use_obs.c.record_id)\
 .where(ResourceEndUseRecord.resource_id.is_not(None))\
 .group_by(
    ResourceEndUseRecord.resource_id,
    Resource.name,
    func.coalesce(UseCase.name, literal("unknown")),
 )
