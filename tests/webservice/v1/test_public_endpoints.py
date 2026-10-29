"""Integration tests for unauthenticated /v1/public BioCirV dataset endpoints."""

from __future__ import annotations

import concurrent.futures
import importlib
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ca_biositing.datamodels.database import get_session
from ca_biositing.datamodels.models import (
    AgTreatment,
    CalorimetryRecord,
    CompositionalRecord,
    FieldSample,
    FieldSampleCondition,
    IcpRecord,
    LocationAddress,
    Observation,
    Parameter,
    Place,
    PreparationMethod,
    PreparedSample,
    PrimaryAgProduct,
    ProcessingMethod,
    Provider,
    ProximateRecord,
    Resource,
    ResourceClass,
    ResourceSubclass,
    UltimateRecord,
    Unit,
    XrfRecord,
)
from ca_biositing.webservice.config import config
from ca_biositing.webservice.main import app
from ca_biositing.webservice.services.public_dataset_service import (
    PublicDatasetService,
    clear_discovery_cache,
)
from ca_biositing.webservice.v1.public.router import reset_public_rate_limiter

public_router_module = importlib.import_module(
    "ca_biositing.webservice.v1.public.router"
)


@pytest.fixture(autouse=True)
def reset_caches_and_rate_limiter():
    """Reset the discovery TTL cache and public rate limiter around each test."""
    clear_discovery_cache()
    reset_public_rate_limiter()
    yield
    clear_discovery_cache()
    reset_public_rate_limiter()


@pytest.fixture(name="public_client")
def public_client_fixture(session: Session):
    """Create a TestClient that ONLY overrides get_session (no auth overrides).

    Verifies that /v1/public/* routes genuinely require no JWT token or API key.
    """

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    # Ensure get_current_user is NOT overridden
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="seeded_public_data")
def seeded_public_data_fixture(session: Session):
    """Seed comprehensive Stage 1 analytical data, QC edge cases, and sensitive fields."""
    unit_pct = Unit(id=100, name="percent")
    unit_mj_kg = Unit(id=101, name="MJ/kg")
    unit_ppm = Unit(id=102, name="ppm")
    session.add_all([unit_pct, unit_mj_kg, unit_ppm])

    p_ash = Parameter(id=100, name="ash", standard_unit_id=100)
    p_moisture = Parameter(id=101, name="moisture", standard_unit_id=100)
    p_vs = Parameter(id=102, name="volatile solids", standard_unit_id=100)
    p_glucan = Parameter(id=103, name="glucan", standard_unit_id=100)
    p_xylan = Parameter(id=104, name="xylan", standard_unit_id=100)
    p_lignin = Parameter(id=105, name="lignin", standard_unit_id=100)
    p_hhv = Parameter(id=106, name="higher_heating_value", standard_unit_id=101)
    p_ca_icp = Parameter(id=107, name="Ca", standard_unit_id=102)
    p_k_xrf = Parameter(id=108, name="K", standard_unit_id=100)
    p_carbon = Parameter(id=109, name="carbon", standard_unit_id=100)
    session.add_all(
        [
            p_ash,
            p_moisture,
            p_vs,
            p_glucan,
            p_xylan,
            p_lignin,
            p_hhv,
            p_ca_icp,
            p_k_xrf,
            p_carbon,
        ]
    )

    rc = ResourceClass(id=100, name="Ag Residue")
    rsc = ResourceSubclass(id=100, name="Nut Hull")
    ag = PrimaryAgProduct(id=100, name="Almond")
    session.add_all([rc, rsc, ag])

    res_almond = Resource(
        id=100,
        name="almond_hulls",
        resource_code="ALM-01",
        resource_class_id=100,
        resource_subclass_id=100,
        primary_ag_product_id=100,
        description="California almond hulls",
    )
    res_sargassum = Resource(
        id=101,
        name="sargassum",
        resource_code="SARG-01",
        resource_class_id=100,
        resource_subclass_id=100,
        primary_ag_product_id=100,
    )
    session.add_all([res_almond, res_sargassum])

    place_yolo = Place(geoid="06113", state_name="California", county_name="Yolo")
    session.add(place_yolo)

    loc = LocationAddress(
        id=100,
        geography_id="06113",
        address_line1="999 Confidential Grower Rd",
        city="Davis",
        zip="95616",
        lat=38.5449,
        lon=-121.7405,
        is_anonymous=False,
    )
    session.add(loc)

    prov_ok = Provider(id=100, codename="PROV-ALPHA")
    prov_jaguar = Provider(id=101, codename="Jaguar")
    session.add_all([prov_ok, prov_jaguar])

    ag_t1 = AgTreatment(id=100, name="Conventional")
    ag_t2 = AgTreatment(id=101, name="Irrigated")
    pm_1 = ProcessingMethod(id=100, name="Hulling")
    prep_m = PreparationMethod(id=100, name="Knife Milled 2mm")
    session.add_all([ag_t1, ag_t2, pm_1, prep_m])

    fs_ok = FieldSample(
        id=100,
        name="FS-ALM-100",
        resource_id=100,
        provider_id=100,
        sampling_location_id=100,
        collection_timestamp=datetime(2025, 9, 15, 10, 0),
        sample_collection_source="Commercial Huller",
        amount_collected=Decimal("5.0"),
        amount_collected_unit_id=101,
        note="PRIVATE FIELD NOTE: Contact John Doe at 555-0199",
    )
    fs_jaguar = FieldSample(
        id=101,
        name="FS-JAG-101",
        resource_id=100,
        provider_id=101,
        sampling_location_id=100,
    )
    session.add_all([fs_ok, fs_jaguar])

    # Multiple FieldSampleCondition rows to test anti-fan-out pre-aggregation
    fsc1 = FieldSampleCondition(
        id=100, field_sample_id=100, ag_treatment_id=100, processing_method_id=100
    )
    fsc2 = FieldSampleCondition(
        id=101, field_sample_id=100, ag_treatment_id=101, processing_method_id=100
    )
    session.add_all([fsc1, fsc2])

    ps_ok = PreparedSample(
        id=100,
        name="PS-ALM-100",
        field_sample_id=100,
        prep_method_id=100,
        prep_date=date(2025, 9, 20),
        note="PRIVATE PREP NOTE: Internal lab rack #42",
    )
    ps_jaguar = PreparedSample(
        id=101,
        name="PS-JAG-101",
        field_sample_id=101,
        prep_method_id=100,
    )
    session.add_all([ps_ok, ps_jaguar])

    # Valid proximate records (ash replicates 10.0 and 14.0 -> mean 12.0, moisture 8.0, vs 80.0 -> sum 100.0 in [95, 105])
    prox_1 = ProximateRecord(
        id=100,
        record_id="pub_prox_1",
        dataset_id=1,
        experiment_id=10,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=1,
        technical_replicate_total=2,
        qc_pass="pass",
        note="SECRET RECORD NOTE",
    )
    prox_2 = ProximateRecord(
        id=101,
        record_id="pub_prox_2",
        dataset_id=1,
        experiment_id=10,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=2,
        technical_replicate_total=2,
        qc_pass="pass",
    )
    prox_fail = ProximateRecord(
        id=102,
        record_id="pub_prox_fail",
        dataset_id=1,
        experiment_id=10,
        resource_id=100,
        prepared_sample_id=100,
        qc_pass="fail",
    )
    prox_null = ProximateRecord(
        id=103,
        record_id="pub_prox_unreviewed",
        dataset_id=1,
        experiment_id=10,
        resource_id=100,
        prepared_sample_id=100,
        qc_pass=None,
    )
    # Compositional with NULL experiment_id (sum = 80.0 >= 40)
    comp_1 = CompositionalRecord(
        id=100,
        record_id="pub_comp_1",
        dataset_id=1,
        experiment_id=None,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=1,
        technical_replicate_total=1,
        qc_pass="pass",
    )
    cal_1 = CalorimetryRecord(
        id=100,
        record_id="pub_cal_1",
        dataset_id=1,
        experiment_id=None,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=1,
        technical_replicate_total=1,
        qc_pass="pass",
    )
    icp_1 = IcpRecord(
        id=100,
        record_id="pub_icp_1",
        dataset_id=1,
        experiment_id=None,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=1,
        technical_replicate_total=1,
        qc_pass="pass",
    )
    xrf_1 = XrfRecord(
        id=100,
        record_id="pub_xrf_1",
        dataset_id=1,
        experiment_id=None,
        resource_id=100,
        prepared_sample_id=100,
        technical_replicate_no=1,
        technical_replicate_total=1,
        qc_pass="pass",
    )
    ult_1 = UltimateRecord(
        id=100,
        record_id="pub_ult_1",
        dataset_id=1,
        experiment_id=None,
        resource_id=100,
        prepared_sample_id=100,
        qc_pass="pass",
    )
    session.add_all(
        [prox_1, prox_2, prox_fail, prox_null, comp_1, cal_1, icp_1, xrf_1, ult_1]
    )

    session.add_all(
        [
            Observation(
                id=1000,
                record_id="pub_prox_1",
                record_type="proximate analysis",
                parameter_id=100,
                value=10.0,
                unit_id=100,
                note="SECRET OBS NOTE",
            ),
            Observation(
                id=1001,
                record_id="pub_prox_2",
                record_type="proximate analysis",
                parameter_id=100,
                value=14.0,
                unit_id=100,
            ),
            Observation(
                id=1002,
                record_id="pub_prox_1",
                record_type="proximate analysis",
                parameter_id=101,
                value=8.0,
                unit_id=100,
            ),
            Observation(
                id=1003,
                record_id="pub_prox_1",
                record_type="proximate analysis",
                parameter_id=102,
                value=80.0,
                unit_id=100,
            ),
            Observation(
                id=1004,
                record_id="pub_prox_fail",
                record_type="proximate analysis",
                parameter_id=100,
                value=99.9,
                unit_id=100,
            ),
            Observation(
                id=1005,
                record_id="pub_comp_1",
                record_type="compositional analysis",
                parameter_id=103,
                value=35.0,
                unit_id=100,
            ),
            Observation(
                id=1006,
                record_id="pub_comp_1",
                record_type="compositional analysis",
                parameter_id=104,
                value=20.0,
                unit_id=100,
            ),
            Observation(
                id=1007,
                record_id="pub_comp_1",
                record_type="compositional analysis",
                parameter_id=105,
                value=25.0,
                unit_id=100,
            ),
            Observation(
                id=1008,
                record_id="pub_cal_1",
                record_type="calorimetry analysis",
                parameter_id=106,
                value=18.5,
                unit_id=101,
            ),
            Observation(
                id=1009,
                record_id="pub_icp_1",
                record_type="icp analysis",
                parameter_id=107,
                value=1250.0,
                unit_id=102,
            ),
            Observation(
                id=1010,
                record_id="pub_xrf_1",
                record_type="xrf analysis",
                parameter_id=108,
                value=2.4,
                unit_id=100,
            ),
            Observation(
                id=1011,
                record_id="pub_ult_1",
                record_type="ultimate analysis",
                parameter_id=109,
                value=48.0,
                unit_id=100,
            ),
            Observation(
                id=1012,
                record_id="pub_prox_unreviewed",
                record_type="proximate analysis",
                parameter_id=100,
                value=77.7,
                unit_id=100,
            ),
        ]
    )
    session.commit()


def test_public_resources_list_and_lookup_without_auth(
    public_client: TestClient, seeded_public_data
):
    """Verify /v1/public/resources and /v1/public/resources/{resource} work with no auth."""
    resp = public_client.get("/v1/public/resources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["release_stage"] == "stage_1"
    assert body["schema_version"] == "1.0.0"
    assert body["total"] == 1
    assert len(body["data"]) == 1

    res = body["data"][0]
    assert "id" not in res
    assert "resource_id" not in res
    assert res["resource_name"] == "almond_hulls"
    assert res["resource_code"] == "ALM-01"
    assert res["field_sample_count"] == 1
    assert res["prepared_sample_count"] == 1
    assert res["provider_count"] == 1
    assert res["county_count"] == 1
    assert res["replicate_record_count"] == 6
    assert res["observation_count"] == 10
    assert res["has_proximate"] is True
    assert res["has_compositional"] is True
    assert res["has_calorimetry"] is True
    assert res["has_icp"] is True
    assert res["has_xrf"] is True

    # Lookup by string name (case-insensitive)
    resp_name = public_client.get("/v1/public/resources/ALMOND_HULLS")
    assert resp_name.status_code == 200
    assert resp_name.json()["resource_name"] == "almond_hulls"

    # Lookup by resource_code
    resp_code = public_client.get("/v1/public/resources/ALM-01")
    assert resp_code.status_code == 200
    assert resp_code.json()["resource_name"] == "almond_hulls"

    # Excluded resource 'sargassum' must return 404
    resp_sarg = public_client.get("/v1/public/resources/sargassum")
    assert resp_sarg.status_code == 404


def test_public_samples_no_fanout_and_detail(
    public_client: TestClient, seeded_public_data
):
    """Verify /v1/public/samples does not fan out on multiple FieldSampleConditions."""
    resp = public_client.get("/v1/public/samples")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    sample = body["data"][0]
    assert "id" not in sample
    assert "prepared_sample_id" not in sample
    assert "field_sample_id" not in sample
    assert sample["prepared_sample_name"] == "PS-ALM-100"
    assert sample["field_sample_name"] == "FS-ALM-100"
    assert sample["provider_codename"] == "PROV-ALPHA"
    assert sample["county_name"] == "Yolo"
    assert sample["ag_treatment_name"] == "Conventional; Irrigated"
    assert sample["processing_method_name"] == "Hulling"
    # 6 distinct Stage 1 analytical records vs 10 parameter-level observations
    assert sample["replicate_record_count"] == 6
    assert sample["observation_count"] == 10

    # Single sample lookup by prepared_sample_name
    resp_detail = public_client.get("/v1/public/samples/PS-ALM-100")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["prepared_sample_name"] == "PS-ALM-100"

    # Sample summary sub-route by prepared_sample_name
    resp_sub_summary = public_client.get(
        "/v1/public/samples/PS-ALM-100/summary",
        params={"parameter_name": "ash"},
    )
    assert resp_sub_summary.status_code == 200
    assert resp_sub_summary.json()["total"] == 1
    assert resp_sub_summary.json()["data"][0]["mean_value"] == pytest.approx(12.0)

    # Nonexistent sample returns 404
    assert public_client.get("/v1/public/samples/PS-NONEXISTENT").status_code == 404


def test_public_observations_and_filters(
    public_client: TestClient, seeded_public_data
):
    """Verify /v1/public/analysis/observations filters and excludes Stage 2 / failed rows."""
    resp = public_client.get("/v1/public/analysis/observations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 10

    # Filter by analysis_type, parameter_name, and prepared_sample_name
    resp_ash = public_client.get(
        "/v1/public/analysis/observations",
        params={
            "analysis_type": "proximate analysis",
            "parameter_name": "ash",
            "prepared_sample_name": "PS-ALM-100",
            "field_sample_name": "FS-ALM-100",
        },
    )
    assert resp_ash.status_code == 200
    ash_data = resp_ash.json()["data"]
    assert len(ash_data) == 2
    assert sorted(r["value"] for r in ash_data) == [10.0, 14.0]
    assert {r["technical_replicate_no"] for r in ash_data} == {1, 2}

    # Ultimate analysis (excluded from Stage 1) must return 0 observations
    resp_ult = public_client.get(
        "/v1/public/analysis/observations",
        params={"analysis_type": "ultimate analysis"},
    )
    assert resp_ult.status_code == 200
    assert resp_ult.json()["total"] == 0


def test_public_sample_summaries_and_resource_summaries(
    public_client: TestClient, seeded_public_data
):
    """Verify replicate averaging in /sample-summaries and /summaries including std_dev."""
    resp_ss = public_client.get(
        "/v1/public/analysis/sample-summaries",
        params={"parameter_name": "ash", "prepared_sample_name": "PS-ALM-100"},
    )
    assert resp_ss.status_code == 200
    ss_rows = resp_ss.json()["data"]
    assert len(ss_rows) == 1
    ss = ss_rows[0]
    assert ss["prepared_sample_name"] == "PS-ALM-100"
    assert ss["mean_value"] == pytest.approx(12.0)
    assert ss["std_dev"] == pytest.approx(2.8284, rel=1e-3)
    assert ss["min_value"] == pytest.approx(10.0)
    assert ss["max_value"] == pytest.approx(14.0)
    assert ss["replicate_count"] == 2

    resp_as = public_client.get(
        "/v1/public/analysis/summaries",
        params={"parameter_name": "ash", "county_name": "Yolo"},
    )
    assert resp_as.status_code == 200
    as_rows = resp_as.json()["data"]
    assert len(as_rows) == 1
    summary = as_rows[0]
    assert summary["resource_name"] == "almond_hulls"
    assert summary["county_name"] == "Yolo"
    assert summary["mean_value"] == pytest.approx(12.0)
    assert summary["std_dev"] == pytest.approx(2.8284, rel=1e-3)
    assert summary["prepared_sample_count"] == 1
    assert summary["field_sample_count"] == 1
    assert summary["observation_count"] == 2


def test_public_discovery_endpoints(
    public_client: TestClient, seeded_public_data
):
    """Verify /v1/public/discovery/* taxonomic endpoints."""
    resp_at = public_client.get("/v1/public/discovery/analysis-types")
    assert resp_at.status_code == 200
    at_map = {
        r["analysis_type"]: r["observation_count"]
        for r in resp_at.json()
    }
    assert at_map == {
        "calorimetry": 1,
        "compositional": 3,
        "icp": 1,
        "proximate": 4,
        "xrf": 1,
    }

    resp_params = public_client.get("/v1/public/discovery/parameters")
    assert resp_params.status_code == 200
    prox_param_names = {
        r["parameter_name"]
        for r in resp_params.json()
        if r["analysis_type"] == "proximate"
    }
    assert prox_param_names == {"ash", "moisture", "volatile solids"}

    resp_counties = public_client.get("/v1/public/discovery/counties")
    assert resp_counties.status_code == 200
    counties = resp_counties.json()
    assert len(counties) == 1
    assert counties[0]["county_name"] == "Yolo"
    assert counties[0]["geoid"] == "06113"
    assert counties[0]["prepared_sample_count"] == 1
    assert counties[0]["observation_count"] == 10


def test_public_bounded_pagination_rejects_limit_over_100(
    public_client: TestClient, seeded_public_data
):
    """Verify invalid pagination bounds (limit<=0, limit>100, skip<0, skip>10000) return HTTP 422."""
    for path in (
        "/v1/public/resources",
        "/v1/public/samples",
        "/v1/public/analysis/observations",
        "/v1/public/analysis/sample-summaries",
        "/v1/public/analysis/summaries",
    ):
        for bad_params in (
            {"limit": 101},
            {"limit": 0},
            {"skip": -1},
            {"skip": 10001},
        ):
            resp = public_client.get(path, params=bad_params)
            assert resp.status_code == 422, (
                f"Expected 422 on {path} with params={bad_params}"
            )


def test_public_rate_limiting_enforces_429_with_retry_after(
    public_client: TestClient, seeded_public_data, monkeypatch
):
    """Verify exceeding public_rate_limit_per_minute returns 429 with Retry-After: 60."""
    monkeypatch.setattr(config, "public_rate_limit_per_minute", 3)

    for _ in range(3):
        r = public_client.get("/v1/public/resources")
        assert r.status_code == 200

    blocked = public_client.get("/v1/public/resources")
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"
    assert "rate limit exceeded" in blocked.json()["detail"].lower()


def test_public_rate_limiter_ignores_spoofed_x_forwarded_for_and_bounds_buckets(
    public_client: TestClient, seeded_public_data, monkeypatch
):
    """Verify spoofed X-Forwarded-For cannot bypass rate limiting or grow buckets unboundedly."""
    monkeypatch.setattr(config, "public_rate_limit_per_minute", 2)
    monkeypatch.setattr(config, "public_rate_limit_trust_x_forwarded_for", False)

    # Even with different X-Forwarded-For headers on every request, untrusted headers are ignored
    r1 = public_client.get(
        "/v1/public/resources", headers={"X-Forwarded-For": "203.0.113.1"}
    )
    r2 = public_client.get(
        "/v1/public/resources", headers={"X-Forwarded-For": "203.0.113.2"}
    )
    r3 = public_client.get(
        "/v1/public/resources", headers={"X-Forwarded-For": "203.0.113.3"}
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert len(public_router_module._ip_rate_buckets) == 1

    # When behind a trusted proxy, the rightmost hop is used (spoofed leftmost hop ignored)
    reset_public_rate_limiter()
    monkeypatch.setattr(config, "public_rate_limit_trust_x_forwarded_for", True)
    p1 = public_client.get(
        "/v1/public/resources",
        headers={"X-Forwarded-For": "10.0.0.1, 198.51.100.42"},
    )
    p2 = public_client.get(
        "/v1/public/resources",
        headers={"X-Forwarded-For": "10.0.0.2, 198.51.100.42"},
    )
    p3 = public_client.get(
        "/v1/public/resources",
        headers={"X-Forwarded-For": "10.0.0.3, 198.51.100.42"},
    )
    assert p1.status_code == 200
    assert p2.status_code == 200
    assert p3.status_code == 429

    # Verify bucket eviction cap prevents unbounded memory growth
    reset_public_rate_limiter()
    monkeypatch.setattr(public_router_module, "_MAX_RATE_LIMIT_BUCKETS", 5)
    for i in range(12):
        public_client.get(
            "/v1/public/resources",
            headers={"X-Forwarded-For": f"198.51.100.{i}"},
        )
    assert len(public_router_module._ip_rate_buckets) <= 5


def test_public_rate_limiter_thread_safety(
    public_client: TestClient, seeded_public_data, monkeypatch
):
    """Verify concurrent burst requests atomically increment the rate-limit counter."""
    monkeypatch.setattr(config, "public_rate_limit_per_minute", 5)

    def _fire(_: int) -> int:
        return public_client.options(
            "/v1/public/resources",
            headers={
                "Origin": "https://observablehq.com",
                "Access-Control-Request-Method": "GET",
            },
        ).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(_fire, range(15)))

    assert statuses.count(204) == 5
    assert statuses.count(429) == 10


def test_public_cors_headers_scoped_to_v1_public(
    public_client: TestClient, seeded_public_data
):
    """Verify permissive CORS (*) applies to /v1/public/* GET and OPTIONS without credentials."""
    origin = "https://observablehq.com"
    resp_get = public_client.get(
        "/v1/public/resources", headers={"Origin": origin}
    )
    assert resp_get.status_code == 200
    assert resp_get.headers.get("Access-Control-Allow-Origin") == "*"
    assert "access-control-allow-credentials" not in {
        k.lower() for k in resp_get.headers.keys()
    }

    resp_opt = public_client.options(
        "/v1/public/resources",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_opt.status_code == 204
    assert resp_opt.headers.get("Access-Control-Allow-Origin") == "*"
    assert "GET" in resp_opt.headers.get("Access-Control-Allow-Methods", "")
    assert resp_opt.headers.get("Access-Control-Max-Age") == "86400"
    assert "access-control-allow-credentials" not in {
        k.lower() for k in resp_opt.headers.keys()
    }

    # Non-public route must NOT receive wildcard CORS for an unlisted origin
    resp_other = public_client.get("/hello", headers={"Origin": origin})
    assert resp_other.status_code == 200
    assert resp_other.headers.get("Access-Control-Allow-Origin") != "*"


def test_public_500_does_not_leak_internal_exception_details(
    seeded_public_data, monkeypatch
):
    """Verify unhandled 500 errors on /v1/public/* redact internal exception strings."""

    def _boom(*args, **kwargs):
        raise RuntimeError(
            "FATAL: password authentication failed for user postgres@10.0.0.5"
        )

    monkeypatch.setattr(PublicDatasetService, "list_resources", _boom)
    safe_client = TestClient(app, raise_server_exceptions=False)
    resp = safe_client.get("/v1/public/resources")
    assert resp.status_code == 500
    body = resp.json()
    assert body == {"detail": "Internal server error"}
    assert "error" not in body
    assert "postgres@10.0.0.5" not in resp.text


def test_public_responses_contain_no_sensitive_or_excluded_strings(
    public_client: TestClient, seeded_public_data
):
    """Verify no street addresses, coordinates, notes, or QC-excluded items appear in JSON."""
    endpoints = [
        "/v1/public/resources",
        "/v1/public/samples",
        "/v1/public/analysis/observations",
        "/v1/public/analysis/sample-summaries",
        "/v1/public/analysis/summaries",
        "/v1/public/discovery/analysis-types",
        "/v1/public/discovery/parameters",
        "/v1/public/discovery/counties",
    ]
    forbidden_substrings = [
        "999 Confidential Grower Rd",
        "38.5449",
        "-121.7405",
        "PRIVATE FIELD NOTE",
        "PRIVATE PREP NOTE",
        "SECRET RECORD NOTE",
        "SECRET OBS NOTE",
        "sargassum",
        "Jaguar",
        "pub_prox_fail",
        "pub_prox_unreviewed",
    ]
    for ep in endpoints:
        resp = public_client.get(ep)
        assert resp.status_code == 200
        raw_text = resp.text
        for forbidden in forbidden_substrings:
            assert forbidden not in raw_text, (
                f"Forbidden substring '{forbidden}' leaked in {ep}"
            )


def test_public_responses_expose_no_surrogate_database_id_fields(
    public_client: TestClient, seeded_public_data
):
    """Verify no internal database integer ID fields appear in any /v1/public JSON payload."""
    forbidden_id_keys = {
        "id",
        "observation_id",
        "resource_id",
        "prepared_sample_id",
        "field_sample_id",
        "experiment_id",
        "raw_data_id",
    }
    paginated_endpoints = [
        "/v1/public/resources",
        "/v1/public/samples",
        "/v1/public/analysis/observations",
        "/v1/public/analysis/sample-summaries",
        "/v1/public/analysis/summaries",
    ]
    for ep in paginated_endpoints:
        resp = public_client.get(ep)
        assert resp.status_code == 200
        rows = resp.json()["data"]
        assert len(rows) > 0
        for row in rows:
            leaked = set(row.keys()) & forbidden_id_keys
            assert not leaked, f"Surrogate ID key(s) {sorted(leaked)} exposed in {ep}"
