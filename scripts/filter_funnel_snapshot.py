#!/usr/bin/env python3
"""
Filter funnel snapshot tool.

Computes, in one run, the live-data impact of every data-quality filter
dimension that is (or should be) centralized in
`ca_biositing.datamodels.data_portal_views.common`:

- Base counts for every Aim1/Aim2 record table, observation, resource,
  provider, and experiment.
- `qc_pass` distribution (pass/fail/other) per Aim1/Aim2 record table.
- Row counts for every materialized view in the `ca_biositing` and
  `data_portal` schemas (discovered dynamically via `pg_matviews`).
- The filter funnel for the two highest-impact views
  (`ca_biositing.analysis_data_view` and `data_portal.mv_biomass_composition`):
  rows removed by each individual filter dimension, plus the final row count.
- Retention ratios (view row count / candidate pool) for those two views.

This is the regression guard for the filter-centralization refactor described
in plans/jiggly-crafting-planet.md: run it before and after each phase and
diff the ratios, not the raw counts, since raw counts legitimately shift as
new data is ingested.

Output: a timestamped JSON snapshot under audit/output/filter_baseline/, plus
a human-readable funnel table printed to stdout.

Usage:
    POSTGRES_HOST=localhost python scripts/filter_funnel_snapshot.py
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import aliased

from ca_biositing.datamodels.data_portal_views.common import (
    EXCLUDED_RESOURCES,
    EXCLUDED_PROVIDERS,
    ULTIMATE_PARAMETERS,
)
from ca_biositing.datamodels.database import get_engine
from ca_biositing.datamodels.models import (
    CalorimetryRecord,
    CompositionalRecord,
    DimensionType,
    Experiment,
    FermentationRecord,
    FieldSample,
    FtnirRecord,
    GasificationRecord,
    IcpRecord,
    LocationAddress,
    Observation,
    Parameter,
    PreparedSample,
    PretreatmentRecord,
    Provider,
    ProximateRecord,
    Resource,
    Unit,
    UltimateRecord,
    XrdRecord,
    XrfRecord,
)

AIM1_AIM2_RECORD_MODELS = {
    "compositional_record": CompositionalRecord,
    "proximate_record": ProximateRecord,
    "ultimate_record": UltimateRecord,
    "xrf_record": XrfRecord,
    "icp_record": IcpRecord,
    "calorimetry_record": CalorimetryRecord,
    "xrd_record": XrdRecord,
    "ftnir_record": FtnirRecord,
    "fermentation_record": FermentationRecord,
    "gasification_record": GasificationRecord,
    "pretreatment_record": PretreatmentRecord,
}

def base_counts(conn):
    """Base counts for Aim1/Aim2 record tables, observation, resource, provider, experiment."""
    counts = {}
    for table_name, model in AIM1_AIM2_RECORD_MODELS.items():
        counts[table_name] = conn.execute(select(func.count()).select_from(model)).scalar()
    counts["observation"] = conn.execute(select(func.count()).select_from(Observation)).scalar()
    counts["resource"] = conn.execute(select(func.count()).select_from(Resource)).scalar()
    counts["provider"] = conn.execute(select(func.count()).select_from(Provider)).scalar()
    counts["experiment"] = conn.execute(select(func.count()).select_from(Experiment)).scalar()
    return counts


def qc_pass_distribution(conn):
    """qc_pass distribution (pass/fail/other) per Aim1/Aim2 record table."""
    distribution = {}
    for table_name, model in AIM1_AIM2_RECORD_MODELS.items():
        rows = conn.execute(
            select(model.qc_pass, func.count()).group_by(model.qc_pass)
        ).all()
        dist = {"pass": 0, "fail": 0, "other": 0}
        for qc_pass, count in rows:
            if qc_pass == "pass":
                dist["pass"] += count
            elif qc_pass == "fail":
                dist["fail"] += count
            else:
                dist["other"] += count
        distribution[table_name] = dist
    return distribution


def all_view_row_counts(conn):
    """Row counts for every materialized view in ca_biositing and data_portal schemas."""
    matviews = conn.execute(
        text(
            """
            SELECT schemaname, matviewname
            FROM pg_matviews
            WHERE schemaname IN ('ca_biositing', 'data_portal')
            ORDER BY schemaname, matviewname
            """
        )
    ).all()
    counts = {}
    for schema, view_name in matviews:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{view_name}")).scalar()
        counts[f"{schema}.{view_name}"] = count
    return counts


def _build_raw_candidate_pool():
    """Rebuild the un-filtered candidate pool underlying analysis_data_view / mv_biomass_composition.

    Mirrors the join structure in views.py's _analysis_base, but omits the
    resource/provider/qc filters so each dimension's removal can be measured
    independently against this common baseline.
    """
    analysis_dimension_unit = aliased(Unit, name="fsnap_analysis_du")

    return (
        select(
            Observation.id,
            Observation.record_type,
            Resource.id.label("resource_id"),
            func.lower(Resource.name).label("resource_name"),
            Provider.id.label("provider_id"),
            func.lower(Provider.codename).label("provider_codename"),
            func.coalesce(
                ProximateRecord.experiment_id,
                UltimateRecord.experiment_id,
                CompositionalRecord.experiment_id,
                IcpRecord.experiment_id,
                XrfRecord.experiment_id,
                CalorimetryRecord.experiment_id,
                XrdRecord.experiment_id,
                FermentationRecord.experiment_id,
                PretreatmentRecord.experiment_id,
            ).label("experiment_id"),
            func.coalesce(
                ProximateRecord.qc_pass,
                UltimateRecord.qc_pass,
                CompositionalRecord.qc_pass,
                IcpRecord.qc_pass,
                XrfRecord.qc_pass,
                CalorimetryRecord.qc_pass,
                XrdRecord.qc_pass,
                FermentationRecord.qc_pass,
                PretreatmentRecord.qc_pass,
                "pass",
            ).label("qc_pass"),
            case(
                (func.lower(Observation.record_type).in_(["proximate analysis", "proximate_analysis"]), "proximate"),
                (func.lower(Observation.record_type).in_(["ultimate analysis", "ultimate_analysis"]), "ultimate"),
                (func.lower(Observation.record_type).in_(["compositional analysis", "compositional_analysis"]), "compositional"),
                (func.lower(Observation.record_type).in_(["icp analysis", "icp_analysis", "icp-oes", "icp-ms"]), "icp"),
                else_=func.lower(Observation.record_type),
            ).label("analysis_type_norm"),
            func.lower(Parameter.name).label("parameter_name"),
            func.lower(Unit.name).label("unit"),
            Observation.value,
        )
        .join(Parameter, Observation.parameter_id == Parameter.id)
        .join(Unit, Observation.unit_id == Unit.id)
        .outerjoin(DimensionType, Observation.dimension_type_id == DimensionType.id)
        .outerjoin(analysis_dimension_unit, Observation.dimension_unit_id == analysis_dimension_unit.id)
        .outerjoin(
            ProximateRecord,
            (func.lower(Observation.record_id) == func.lower(ProximateRecord.record_id))
            & (func.lower(Observation.record_type).in_(["proximate analysis", "proximate_analysis"])),
        )
        .outerjoin(
            UltimateRecord,
            (func.lower(Observation.record_id) == func.lower(UltimateRecord.record_id))
            & (func.lower(Observation.record_type).in_(["ultimate analysis", "ultimate_analysis"])),
        )
        .outerjoin(
            CompositionalRecord,
            (func.lower(Observation.record_id) == func.lower(CompositionalRecord.record_id))
            & (func.lower(Observation.record_type).in_(["compositional analysis", "compositional_analysis"])),
        )
        .outerjoin(
            IcpRecord,
            (func.lower(Observation.record_id) == func.lower(IcpRecord.record_id))
            & (
                (func.lower(Observation.record_type) == "icp analysis")
                | (func.lower(Observation.record_type) == "icp_analysis")
                | (func.lower(Observation.record_type) == "icp-oes")
                | (func.lower(Observation.record_type) == "icp-ms")
            ),
        )
        .outerjoin(
            XrfRecord,
            (func.lower(Observation.record_id) == func.lower(XrfRecord.record_id))
            & (func.lower(Observation.record_type).in_(["xrf analysis", "xrf_analysis"])),
        )
        .outerjoin(
            CalorimetryRecord,
            (func.lower(Observation.record_id) == func.lower(CalorimetryRecord.record_id))
            & (func.lower(Observation.record_type).in_(["calorimetry analysis", "calorimetry_analysis"])),
        )
        .outerjoin(
            XrdRecord,
            (func.lower(Observation.record_id) == func.lower(XrdRecord.record_id))
            & (func.lower(Observation.record_type).in_(["xrd analysis", "xrd_analysis"])),
        )
        .outerjoin(
            FermentationRecord,
            (func.lower(Observation.record_id) == func.lower(FermentationRecord.record_id))
            & (func.lower(Observation.record_type) == "fermentation"),
        )
        .outerjoin(
            PretreatmentRecord,
            (func.lower(Observation.record_id) == func.lower(PretreatmentRecord.record_id))
            & (func.lower(Observation.record_type) == "pretreatment"),
        )
        .outerjoin(
            PreparedSample,
            PreparedSample.id
            == func.coalesce(
                ProximateRecord.prepared_sample_id,
                UltimateRecord.prepared_sample_id,
                CompositionalRecord.prepared_sample_id,
                IcpRecord.prepared_sample_id,
                XrfRecord.prepared_sample_id,
                CalorimetryRecord.prepared_sample_id,
                XrdRecord.prepared_sample_id,
                FermentationRecord.prepared_sample_id,
                PretreatmentRecord.prepared_sample_id,
            ),
        )
        .outerjoin(FieldSample, FieldSample.id == PreparedSample.field_sample_id)
        .outerjoin(
            Resource,
            Resource.id
            == func.coalesce(
                ProximateRecord.resource_id,
                UltimateRecord.resource_id,
                CompositionalRecord.resource_id,
                IcpRecord.resource_id,
                XrfRecord.resource_id,
                CalorimetryRecord.resource_id,
                XrdRecord.resource_id,
                FermentationRecord.resource_id,
                PretreatmentRecord.resource_id,
                FieldSample.resource_id,
            ),
        )
        .outerjoin(LocationAddress, LocationAddress.id == FieldSample.sampling_location_id)
        .outerjoin(Provider, Provider.id == FieldSample.provider_id)
        .where(func.lower(Observation.record_type).notin_(["usda_census_record", "usda_survey_record"]))
    ).subquery()


def analysis_data_view_funnel(conn):
    """Filter funnel for ca_biositing.analysis_data_view (ANALYSIS_DATA_VIEW).

    Applies each filter dimension cumulatively, in the same order
    ANALYSIS_DATA_VIEW applies them, and records how many rows each stage
    removes relative to the previous stage.
    """
    pool = _build_raw_candidate_pool()
    funnel = {}

    candidate_pool = conn.execute(select(func.count()).select_from(pool)).scalar()
    funnel["candidate_pool"] = candidate_pool

    stage_cond = pool.c.qc_pass != "fail"
    after_qc = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_qc_fail"] = candidate_pool - after_qc

    stage_cond = and_(
        stage_cond,
        or_(pool.c.resource_name.is_(None), pool.c.resource_name.notin_(EXCLUDED_RESOURCES)),
    )
    after_resource = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_resource_blacklist"] = after_qc - after_resource

    stage_cond = and_(
        stage_cond,
        or_(pool.c.provider_id.is_(None), pool.c.provider_codename.notin_(EXCLUDED_PROVIDERS)),
    )
    after_provider = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_provider_blacklist"] = after_resource - after_provider

    stage_cond = and_(
        stage_cond,
        or_(
            pool.c.analysis_type_norm != "ultimate",
            pool.c.parameter_name.in_(ULTIMATE_PARAMETERS),
        ),
    )
    after_ultimate_whitelist = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_ultimate_whitelist"] = after_provider - after_ultimate_whitelist

    stage_cond = and_(
        stage_cond,
        or_(pool.c.analysis_type_norm != "ultimate", pool.c.value <= 100),
    )
    after_ultimate_max = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_ultimate_value_gt_100"] = after_ultimate_whitelist - after_ultimate_max

    stage_cond = and_(
        stage_cond,
        or_(pool.c.analysis_type_norm != "icp", pool.c.unit == "ppm"),
    )
    after_icp_unit = conn.execute(select(func.count()).select_from(pool).where(stage_cond)).scalar()
    funnel["removed_by_icp_non_ppm_unit"] = after_ultimate_max - after_icp_unit

    unmapped_resource = conn.execute(
        select(func.count()).select_from(pool).where(and_(stage_cond, pool.c.resource_id.is_(None)))
    ).scalar()
    funnel["unmapped_resource"] = unmapped_resource

    final_row_count = conn.execute(text("SELECT COUNT(*) FROM ca_biositing.analysis_data_view")).scalar()
    funnel["final_row_count"] = final_row_count
    funnel["retention_ratio"] = (final_row_count / candidate_pool) if candidate_pool else None

    return funnel


def mv_biomass_composition_funnel(conn):
    """Final row count and retention ratio for data_portal.mv_biomass_composition."""
    candidate_pool = sum(
        conn.execute(select(func.count()).select_from(model)).scalar()
        for model in AIM1_AIM2_RECORD_MODELS.values()
    )
    final_row_count = conn.execute(text("SELECT COUNT(*) FROM data_portal.mv_biomass_composition")).scalar()
    return {
        "candidate_pool_all_record_rows": candidate_pool,
        "final_row_count": final_row_count,
        "retention_ratio": (final_row_count / candidate_pool) if candidate_pool else None,
    }


def run_snapshot():
    engine = get_engine()
    with engine.connect() as conn:
        snapshot = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "database": f"{engine.url.host}:{engine.url.port}/{engine.url.database}",
            },
            "base_counts": base_counts(conn),
            "qc_pass_distribution": qc_pass_distribution(conn),
            "view_row_counts": all_view_row_counts(conn),
            "analysis_data_view_funnel": analysis_data_view_funnel(conn),
            "mv_biomass_composition_funnel": mv_biomass_composition_funnel(conn),
        }

    output_dir = Path("audit/output/filter_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{timestamp_slug}.json"
    with output_path.open("w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    print(f"Filter funnel snapshot saved to {output_path}\n")
    print("=== Base record counts ===")
    for table, count in snapshot["base_counts"].items():
        print(f"  {table}: {count}")

    print("\n=== qc_pass distribution ===")
    for table, dist in snapshot["qc_pass_distribution"].items():
        print(f"  {table}: {dist}")

    print("\n=== Materialized view row counts ===")
    for view, count in snapshot["view_row_counts"].items():
        print(f"  {view}: {count}")

    print("\n=== analysis_data_view filter funnel ===")
    for key, value in snapshot["analysis_data_view_funnel"].items():
        print(f"  {key}: {value}")

    print("\n=== mv_biomass_composition funnel ===")
    for key, value in snapshot["mv_biomass_composition_funnel"].items():
        print(f"  {key}: {value}")

    return snapshot


if __name__ == "__main__":
    run_snapshot()
