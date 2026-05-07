"""
mv_biomass_sample_stats.py

Sample statistics aggregated across all analytical record types.

QC: filtered to pass only - only counts records with qc_pass = "pass"

Required index:
    CREATE UNIQUE INDEX idx_mv_biomass_sample_stats_resource_id ON data_portal.mv_biomass_sample_stats (resource_id)
"""

from sqlalchemy import select, func, union_all, cast, Integer, and_
from ca_biositing.datamodels.data_portal_views.common import get_resource_filter
from ca_biositing.datamodels.models.resource_information.resource import Resource
from ca_biositing.datamodels.models.aim1_records.compositional_record import CompositionalRecord
from ca_biositing.datamodels.models.aim1_records.proximate_record import ProximateRecord
from ca_biositing.datamodels.models.aim1_records.ultimate_record import UltimateRecord
from ca_biositing.datamodels.models.aim1_records.xrf_record import XrfRecord
from ca_biositing.datamodels.models.aim1_records.icp_record import IcpRecord
from ca_biositing.datamodels.models.aim1_records.calorimetry_record import CalorimetryRecord
from ca_biositing.datamodels.models.aim1_records.xrd_record import XrdRecord
from ca_biositing.datamodels.models.aim1_records.ftnir_record import FtnirRecord
from ca_biositing.datamodels.models.aim2_records.fermentation_record import FermentationRecord
from ca_biositing.datamodels.models.aim2_records.gasification_record import GasificationRecord
from ca_biositing.datamodels.models.aim2_records.pretreatment_record import PretreatmentRecord
from ca_biositing.datamodels.models.field_sampling.field_sample import FieldSample
from ca_biositing.datamodels.models.sample_preparation.prepared_sample import PreparedSample
from ca_biositing.datamodels.models.people.provider import Provider


def get_sample_stats_query(model):
    """Generate a select statement for a specific analysis record type.
    QC: filtered to exclude "fail" - only include records that are not marked as failed"""
    return select(
        model.resource_id,
        model.prepared_sample_id,
        model.dataset_id
    ).where(model.qc_pass != "fail")


sample_queries = [
    get_sample_stats_query(CompositionalRecord),
    get_sample_stats_query(ProximateRecord),
    get_sample_stats_query(UltimateRecord),
    get_sample_stats_query(XrfRecord),
    get_sample_stats_query(IcpRecord),
    get_sample_stats_query(CalorimetryRecord),
    get_sample_stats_query(XrdRecord),
    get_sample_stats_query(FtnirRecord),
    get_sample_stats_query(FermentationRecord),
    get_sample_stats_query(GasificationRecord),
    get_sample_stats_query(PretreatmentRecord)
]

all_samples = union_all(*sample_queries).subquery()

mv_biomass_sample_stats = select(
    Resource.id.label("resource_id"),
    Resource.name.label("resource_name"),
    func.count(func.distinct(all_samples.c.prepared_sample_id)).label("sample_count"),
    func.count(func.distinct(Provider.id)).label("supplier_count"),
    func.count(func.distinct(all_samples.c.dataset_id)).label("dataset_count"),
    func.count().label("total_record_count")
).select_from(Resource)\
 .outerjoin(all_samples, all_samples.c.resource_id == Resource.id)\
 .where(get_resource_filter(Resource))\
 .outerjoin(PreparedSample, cast(all_samples.c.prepared_sample_id, Integer) == PreparedSample.id)\
 .outerjoin(FieldSample, PreparedSample.field_sample_id == FieldSample.id)\
 .outerjoin(Provider, FieldSample.provider_id == Provider.id)\
 .group_by(Resource.id, Resource.name)
