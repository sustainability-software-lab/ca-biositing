"""Unit tests for `analysis/metadata/resource_insights_engine.py`."""

from __future__ import annotations

import math
from typing import Any

from analysis.metadata.resource_insights_engine import (
    DIXON_MIN_RSD_PCT,
    _canonical_domain_slug,
    compute_dataset_outlier_screening,
    compute_proximate_closure_strata,
)


def _make_row(
    *,
    resource_name: str = "Almond Hulls",
    prepared_sample: str = "PS-001",
    analysis_type: str = "Proximate Analysis",
    parameter: str = "Ash",
    unit: str = "%",
    prep_method: str = "Milled",
    experiment: str = "EXP-01",
    record_id: str = "REC-1",
    replicate: int = 1,
    value: float = 10.0,
    qc_status: str = "pass",
    note: str = "",
) -> dict[str, Any]:
    """Create a synthetic observation row for `compute_dataset_outlier_screening`."""
    return {
        "resource_name": resource_name,
        "prepared_sample": prepared_sample,
        "analysis_type": analysis_type,
        "parameter": parameter,
        "unit": unit,
        "prep_method": prep_method,
        "experiment": experiment,
        "record_id": record_id,
        "replicate": replicate,
        "value": value,
        "qc_status": qc_status,
        "note": note,
    }


def test_dixon_q_false_positive_suppressed_on_near_identical_replicates() -> None:
    """Dixon's Q must not flag a group when rsd_within_pct < DIXON_MIN_RSD_PCT (10%)."""
    vals = [3.11, 3.11, 3.11, 3.15]
    rows = [
        _make_row(record_id=f"REC-{i + 1}", replicate=i + 1, value=v)
        for i, v in enumerate(vals)
    ]
    out = compute_dataset_outlier_screening({"Almond Hulls": rows})
    res_out = out["Almond Hulls"]
    groups = res_out["by_tab"]["proximate"]["replicate_groups"]
    assert len(groups) == 1
    grp = groups[0]

    assert DIXON_MIN_RSD_PCT == 10.0
    assert grp["dixon_q"] == 1.0
    assert grp["dixon_crit"] == 0.829
    assert grp["rsd_within_pct"] is not None
    assert grp["rsd_within_pct"] < DIXON_MIN_RSD_PCT
    assert grp["raw_dixon"] is False
    assert grp["active_flagged"] is False
    assert grp["flagged_active"] is False
    assert grp["has_identical_replicates"] is False


def test_dixon_q_true_positive_activated_when_rsd_at_or_above_10_pct() -> None:
    """Dixon's Q flags a group when dixon_q > dixon_crit and rsd_within_pct >= 10.0."""
    vals = [10.0, 10.1, 10.2, 22.0]
    rows = [
        _make_row(record_id=f"REC-{i + 1}", replicate=i + 1, value=v)
        for i, v in enumerate(vals)
    ]
    out = compute_dataset_outlier_screening({"Almond Hulls": rows})
    grp = out["Almond Hulls"]["by_tab"]["proximate"]["replicate_groups"][0]

    assert grp["dixon_q"] is not None and grp["dixon_q"] > 0.829
    assert grp["rsd_within_pct"] is not None and grp["rsd_within_pct"] >= 10.0
    assert grp["raw_dixon"] is True
    assert grp["active_flagged"] is True
    assert grp["flagged_active"] is True
    assert grp["has_identical_replicates"] is False


def test_has_identical_replicates_floating_point_tolerance() -> None:
    """has_identical_replicates is True for n>=2 when all values match within 1e-9 or 4-decimal rounding."""
    # Case 1: n=3 within 1e-9
    vals = [5.0000000001, 5.0000000002, 5.0000000003]
    rows = [
        _make_row(record_id=f"REC-{i + 1}", replicate=i + 1, value=v)
        for i, v in enumerate(vals)
    ]
    out = compute_dataset_outlier_screening({"Almond Hulls": rows})
    grp = out["Almond Hulls"]["by_tab"]["proximate"]["replicate_groups"][0]
    assert grp["n"] == 3
    assert grp["has_identical_replicates"] is True
    assert grp["raw_dixon"] is False

    # Case 2: n=2 identical pair
    rows_n2 = [
        _make_row(record_id="N2-1", replicate=1, value=5.0),
        _make_row(record_id="N2-2", replicate=2, value=5.0),
    ]
    grp_n2 = compute_dataset_outlier_screening({"Almond Hulls": rows_n2})[
        "Almond Hulls"
    ]["by_tab"]["proximate"]["replicate_groups"][0]
    assert grp_n2["n"] == 2
    assert grp_n2["has_identical_replicates"] is True

    # Case 3: n=3 where only 2 of 3 are identical -> must be False
    rows_partial = [
        _make_row(record_id="P-1", replicate=1, value=5.0),
        _make_row(record_id="P-2", replicate=2, value=5.0),
        _make_row(record_id="P-3", replicate=3, value=5.2),
    ]
    grp_partial = compute_dataset_outlier_screening({"Almond Hulls": rows_partial})[
        "Almond Hulls"
    ]["by_tab"]["proximate"]["replicate_groups"][0]
    assert grp_partial["n"] == 3
    assert grp_partial["has_identical_replicates"] is False

    # Case 4: n=1 singleton -> must be False
    rows_n1 = [_make_row(record_id="N1-1", replicate=1, value=5.0)]
    grp_n1 = compute_dataset_outlier_screening({"Almond Hulls": rows_n1})[
        "Almond Hulls"
    ]["by_tab"]["proximate"]["replicate_groups"][0]
    assert grp_n1["n"] == 1
    assert grp_n1["has_identical_replicates"] is False


def test_between_sd_single_vs_two_prepared_samples() -> None:
    """Verify between_sd is None for k=1 and sample SD of group means for k=2."""
    # Case 1: Single prepared sample (k = 1)
    rows_k1 = [
        _make_row(prepared_sample="PS-A", record_id="A1", replicate=1, value=40.0),
        _make_row(prepared_sample="PS-A", record_id="A2", replicate=2, value=40.2),
    ]
    out_k1 = compute_dataset_outlier_screening({"Almond Hulls": rows_k1})
    grp_k1 = out_k1["Almond Hulls"]["by_tab"]["proximate"]["replicate_groups"][0]
    param_k1 = out_k1["Almond Hulls"]["by_tab"]["proximate"]["param_rsd_table"][0]

    assert grp_k1["between_sd"] is None
    assert grp_k1["between_k_groups"] == 1
    assert param_k1["between_sd"] is None
    assert param_k1["between_k_groups"] == 1

    # Case 2: Two prepared samples (k = 2) with group means 40.1 and 43.9
    rows_k2 = [
        _make_row(
            prepared_sample="PS-A",
            prep_method="Milled",
            unit="%",
            record_id="A1",
            replicate=1,
            value=40.0,
        ),
        _make_row(
            prepared_sample="PS-A",
            prep_method="Milled",
            unit="%",
            record_id="A2",
            replicate=2,
            value=40.2,
        ),
        _make_row(
            prepared_sample="PS-B",
            prep_method="Milled",
            unit="%",
            record_id="B1",
            replicate=1,
            value=44.0,
        ),
        _make_row(
            prepared_sample="PS-B",
            prep_method="Milled",
            unit="%",
            record_id="B2",
            replicate=2,
            value=43.8,
        ),
    ]
    out_k2 = compute_dataset_outlier_screening({"Almond Hulls": rows_k2})
    grps_k2 = out_k2["Almond Hulls"]["by_tab"]["proximate"]["replicate_groups"]
    param_k2 = out_k2["Almond Hulls"]["by_tab"]["proximate"]["param_rsd_table"][0]

    expected_between_sd = round(
        math.sqrt(((40.1 - 42.0) ** 2 + (43.9 - 42.0) ** 2) / 1), 3
    )
    assert expected_between_sd == 2.687
    assert len(grps_k2) == 2
    for g in grps_k2:
        assert g["between_sd"] == expected_between_sd
        assert g["between_k_groups"] == 2
    assert param_k2["between_sd"] == expected_between_sd
    assert param_k2["between_k_groups"] == 2
    assert param_k2["prep_method"] == "Milled"


def test_between_sd_stratified_by_prep_method_no_cross_method_conflation() -> None:
    """Different prep_method strata must not be conflated when computing between_sd."""
    rows = [
        _make_row(
            prepared_sample="PS-AR",
            prep_method="As-received",
            parameter="Moisture",
            unit="%",
            record_id="AR1",
            replicate=1,
            value=49.8,
        ),
        _make_row(
            prepared_sample="PS-AR",
            prep_method="As-received",
            parameter="Moisture",
            unit="%",
            record_id="AR2",
            replicate=2,
            value=50.2,
        ),
        _make_row(
            prepared_sample="PS-DR",
            prep_method="Dried",
            parameter="Moisture",
            unit="%",
            record_id="DR1",
            replicate=1,
            value=9.9,
        ),
        _make_row(
            prepared_sample="PS-DR",
            prep_method="Dried",
            parameter="Moisture",
            unit="%",
            record_id="DR2",
            replicate=2,
            value=10.1,
        ),
    ]
    out = compute_dataset_outlier_screening({"Almond Hulls": rows})
    grps = out["Almond Hulls"]["by_tab"]["proximate"]["replicate_groups"]
    params = out["Almond Hulls"]["by_tab"]["proximate"]["param_rsd_table"]

    assert len(grps) == 2
    for g in grps:
        assert g["between_k_groups"] == 1
        assert g["between_sd"] is None
        assert g["rsd_between_pct"] is None

    assert len(params) == 2
    by_method = {p["prep_method"]: p for p in params}
    assert set(by_method.keys()) == {"As-received", "Dried"}
    for p in by_method.values():
        assert p["between_k_groups"] == 1
        assert p["between_sd"] is None
        assert p["between_rsd_pct"] is None


def test_replicate_group_key_six_part_canonical_format() -> None:
    """Every replicate group must emit a 6-part lowercase :: canonical key."""
    domain_cases = [
        ("Proximate Analysis", "proximate"),
        ("Ultimate Analysis", "ultimate"),
        ("Compositional Analysis", "compositional"),
        ("Calorimetry", "calorimetry"),
        ("XRD Crystallinity", "xrd"),
        ("ICP-OES / ICP-MS", "icp"),
        ("ICP Elemental Analysis", "icp"),
        ("XRF Elemental", "xrf"),
        ("XRF Elemental Analysis", "xrf"),
        ("Ash", "xrf"),
        ("Pretreatment", "pretreatment"),
        ("Pretreatment & Hydrolysis", "pretreatment"),
        ("Fermentation", "fermentation"),
        ("Fermentation (Bioconversion)", "fermentation"),
        ("Gasification", "gasification"),
        ("proximate_record", "proximate"),
        ("", "unknown"),
        (None, "unknown"),
    ]
    for raw_label, expected_slug in domain_cases:
        assert _canonical_domain_slug(raw_label) == expected_slug

    rows = [
        _make_row(
            resource_name="Rice Straw",
            prepared_sample="RS-Prep-01",
            analysis_type="Compositional Analysis",
            parameter="Glucan",
            prep_method="Wiley Milled",
            experiment="EXP-2025-A",
            record_id="R1",
            replicate=1,
            value=36.4,
        ),
        _make_row(
            resource_name="Rice Straw",
            prepared_sample="RS-Prep-01",
            analysis_type="Compositional Analysis",
            parameter="Glucan",
            prep_method="Wiley Milled",
            experiment="EXP-2025-A",
            record_id="R2",
            replicate=2,
            value=36.8,
        ),
        {
            **_make_row(
                resource_name="Rice Straw",
                prepared_sample="RS-Prep-01",
                analysis_type="Pretreatment & Hydrolysis",
                parameter="Glucose Yield",
                prep_method="Wiley Milled",
                experiment="EXP-PT-01",
                record_id="PT1",
                replicate=1,
                value=82.0,
            ),
            "pt_method": "Dilute Acid",
            "eh_method": "CTec3",
        },
        {
            **_make_row(
                resource_name="Rice Straw",
                prepared_sample="RS-Prep-01",
                analysis_type="Fermentation (Bioconversion)",
                parameter="Ethanol Concentration",
                prep_method="Wiley Milled",
                experiment="EXP-FM-01",
                record_id="FM1",
                replicate=1,
                value=38.5,
            ),
            "pt_method": "Dilute Acid",
            "strain": "S. cerevisiae D5A",
            "time_h": 48,
        },
    ]
    out = compute_dataset_outlier_screening({"Rice Straw": rows})
    grp = out["Rice Straw"]["by_tab"]["compositional"]["replicate_groups"][0]
    key = grp["replicate_group_key"]
    parts = key.split("::")

    assert len(parts) == 6
    assert key == "rice straw::rs-prep-01::compositional::glucan::wiley milled::exp-2025-a"

    pt_grp = out["Rice Straw"]["by_tab"]["pretreatment"]["replicate_groups"][0]
    assert (
        pt_grp["replicate_group_key"]
        == "rice straw::rs-prep-01::pretreatment::glucose yield::dilute acid · ctec3::exp-pt-01"
    )

    fm_grp = out["Rice Straw"]["by_tab"]["fermentation"]["replicate_groups"][0]
    assert (
        fm_grp["replicate_group_key"]
        == "rice straw::rs-prep-01::fermentation::ethanol concentration::dilute acid · s. cerevisiae d5a @ 48h::exp-fm-01"
    )


def test_summary_overall_within_and_between_sd_medians() -> None:
    """Resource summary, tab, param, and group dicts must expose all SD and flag schema aliases."""
    rows = [
        _make_row(
            prepared_sample="PS-1",
            prep_method="Milled",
            parameter="Volatile Solids",
            unit="%",
            record_id="VS-1",
            replicate=1,
            value=80.0,
        ),
        _make_row(
            prepared_sample="PS-1",
            prep_method="Milled",
            parameter="Volatile Solids",
            unit="%",
            record_id="VS-2",
            replicate=2,
            value=81.0,
        ),
        _make_row(
            prepared_sample="PS-2",
            prep_method="Milled",
            parameter="Volatile Solids",
            unit="%",
            record_id="VS-3",
            replicate=1,
            value=84.0,
        ),
        _make_row(
            prepared_sample="PS-2",
            prep_method="Milled",
            parameter="Volatile Solids",
            unit="%",
            record_id="VS-4",
            replicate=2,
            value=85.0,
        ),
    ]
    out = compute_dataset_outlier_screening({"Almond Hulls": rows})
    res = out["Almond Hulls"]
    summary = res["summary"]
    prox_tab = res["by_tab"]["proximate"]
    param_row = prox_tab["param_rsd_table"][0]
    grp_row = prox_tab["replicate_groups"][0]

    assert isinstance(summary["overall_within_sd_median"], float)
    assert isinstance(summary["overall_between_sd_median"], float)
    assert summary["overall_within_sd_median"] == 0.707
    assert summary["overall_between_sd_median"] == 2.828
    assert res["overall_within_sd_median"] == summary["overall_within_sd_median"]
    assert res["overall_between_sd_median"] == summary["overall_between_sd_median"]

    # Verify schema compatibility aliases at group, param, tab, summary, and top-level resource dicts
    assert grp_row["within_sd"] == grp_row["sd"] == 0.707
    assert grp_row["flagged_active"] == grp_row["active_flagged"]
    assert grp_row["between_rsd_pct"] == grp_row["rsd_between_pct"]
    assert (
        param_row["flagged_active"]
        == param_row["flagged_active_groups"]
        == param_row["flagged_replicate_groups"]
    )
    assert (
        prox_tab["flagged_active"]
        == prox_tab["flagged_active_groups"]
        == prox_tab["flagged_replicate_groups"]
    )
    assert (
        res["flagged_active"]
        == res["flagged_active_groups"]
        == res["flagged_replicate_groups"]
        == summary["flagged_active"]
        == summary["flagged_active_groups"]
        == summary["flagged_replicate_groups"]
    )


def test_proximate_closure_portal_formula_and_outlier_screening_flags() -> None:
    """Verify Data Portal proximate_sum formula (Moisture + Ash + VS [or 100 - FC]) and 95-105% flags."""
    rows = [
        # Stratum 1: (Almond Hulls, EXP-01, Milled) -> Moisture=8.0, Ash=5.0, VS=74.0, FC=13.0
        # Data Portal formula uses VS (74.0) and ignores FC (13.0) when VS is present -> 8 + 5 + 74 = 87.0% (<95% -> flagged)
        _make_row(
            prepared_sample="PS-1",
            experiment="EXP-01",
            prep_method="Milled",
            parameter="Moisture",
            record_id="M1",
            value=8.0,
        ),
        _make_row(
            prepared_sample="PS-1",
            experiment="EXP-01",
            prep_method="Milled",
            parameter="Ash",
            record_id="A1",
            value=5.0,
        ),
        _make_row(
            prepared_sample="PS-1",
            experiment="EXP-01",
            prep_method="Milled",
            parameter="Volatile Solids",
            record_id="V1",
            value=74.0,
        ),
        _make_row(
            prepared_sample="PS-1",
            experiment="EXP-01",
            prep_method="Milled",
            parameter="Fixed Carbon",
            record_id="F1",
            value=13.0,
        ),
        # Stratum 2: (Almond Hulls, EXP-02, Dried) -> Moisture=6.0, Ash=4.0, NO VS, FC=15.0
        # Data Portal formula falls back to (100 - FC) = 85.0 -> 6 + 4 + 85 = 95.0% (in 95-105% -> clean)
        _make_row(
            prepared_sample="PS-2",
            experiment="EXP-02",
            prep_method="Dried",
            parameter="Moisture",
            record_id="M2",
            value=6.0,
        ),
        _make_row(
            prepared_sample="PS-2",
            experiment="EXP-02",
            prep_method="Dried",
            parameter="Ash",
            record_id="A2",
            value=4.0,
        ),
        _make_row(
            prepared_sample="PS-2",
            experiment="EXP-02",
            prep_method="Dried",
            parameter="Fixed Carbon",
            record_id="F2",
            value=15.0,
        ),
        # Stratum 3: (Almond Hulls, EXP-03, Ball Milled) -> Moisture=10.0, Ash=12.0, NO VS, FC=10.0
        # Data Portal formula falls back to (100 - FC) = 90.0 -> 10 + 12 + 90 = 112.0% (>105% -> flagged)
        _make_row(
            prepared_sample="PS-3",
            experiment="EXP-03",
            prep_method="Ball Milled",
            parameter="Moisture",
            record_id="M3",
            value=10.0,
        ),
        _make_row(
            prepared_sample="PS-3",
            experiment="EXP-03",
            prep_method="Ball Milled",
            parameter="Ash",
            record_id="A3",
            value=12.0,
        ),
        _make_row(
            prepared_sample="PS-3",
            experiment="EXP-03",
            prep_method="Ball Milled",
            parameter="Fixed Carbon",
            record_id="F3",
            value=10.0,
        ),
    ]

    strata = compute_proximate_closure_strata({"Almond Hulls": rows})
    s1 = strata[("Almond Hulls", "EXP-01", "Milled")]
    assert s1["proximate_sum_pct"] == 87.0
    assert s1["out_of_bounds"] is True

    s2 = strata[("Almond Hulls", "EXP-02", "Dried")]
    assert s2["proximate_sum_pct"] == 95.0
    assert s2["out_of_bounds"] is False

    s3 = strata[("Almond Hulls", "EXP-03", "Ball Milled")]
    assert s3["proximate_sum_pct"] == 112.0
    assert s3["out_of_bounds"] is True

    out = compute_dataset_outlier_screening({"Almond Hulls": rows})["Almond Hulls"]
    prox_tab = out["by_tab"]["proximate"]
    grps_by_exp = {}
    for g in prox_tab["replicate_groups"]:
        grps_by_exp.setdefault(g["experiment"], []).append(g)

    assert all(g["raw_proximate_sum"] is True for g in grps_by_exp["EXP-01"])
    assert all(g["active_proximate_sum"] is True for g in grps_by_exp["EXP-01"])
    assert all(g["active_flagged"] is True for g in grps_by_exp["EXP-01"])
    assert all(g["proximate_sum_pct"] == 87.0 for g in grps_by_exp["EXP-01"])

    assert all(g["raw_proximate_sum"] is False for g in grps_by_exp["EXP-02"])
    assert all(g["active_proximate_sum"] is False for g in grps_by_exp["EXP-02"])
    assert all(g["active_flagged"] is False for g in grps_by_exp["EXP-02"])
    assert all(g["proximate_sum_pct"] == 95.0 for g in grps_by_exp["EXP-02"])

    assert all(g["raw_proximate_sum"] is True for g in grps_by_exp["EXP-03"])
    assert all(g["active_proximate_sum"] is True for g in grps_by_exp["EXP-03"])
    assert all(g["active_flagged"] is True for g in grps_by_exp["EXP-03"])
    assert all(g["proximate_sum_pct"] == 112.0 for g in grps_by_exp["EXP-03"])

    # 4 groups in EXP-01 + 3 groups in EXP-03 = 7 proximate_sum flagged groups
    assert prox_tab["proximate_sum_count"] == 7
    assert out["summary"]["proximate_sum_count"] == 7
    assert out["proximate_sum_count"] == 7
