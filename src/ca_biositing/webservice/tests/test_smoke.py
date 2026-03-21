"""Integration smoke tests for all API endpoints.

These tests require a running server with seeded data. Run with:
    CA_BIOSITING_BASE_URL=http://localhost:8000 \\
    CA_BIOSITING_TEST_USERNAME=... \\
    CA_BIOSITING_TEST_PASSWORD=... \\
    pytest src/ca_biositing/webservice/tests/test_smoke.py -m integration -v
"""

import os

import httpx
import pytest


# ---------------------------------------------------------------------------
# Discovery endpoint smoke tests (11 tests)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_discovery_analysis_resources(client):
    resp = client.get("/v1/feedstocks/analysis/resources")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_analysis_geoids(client):
    resp = client.get("/v1/feedstocks/analysis/geoids")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_analysis_parameters(client):
    resp = client.get("/v1/feedstocks/analysis/parameters")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_census_crops(client):
    resp = client.get("/v1/feedstocks/usda/census/crops")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_census_resources(client):
    resp = client.get("/v1/feedstocks/usda/census/resources")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_census_geoids(client):
    resp = client.get("/v1/feedstocks/usda/census/geoids")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_census_parameters(client):
    resp = client.get("/v1/feedstocks/usda/census/parameters")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_survey_crops(client):
    resp = client.get("/v1/feedstocks/usda/survey/crops")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_survey_resources(client):
    resp = client.get("/v1/feedstocks/usda/survey/resources")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_survey_geoids(client):
    resp = client.get("/v1/feedstocks/usda/survey/geoids")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


@pytest.mark.integration
def test_discovery_survey_parameters(client):
    resp = client.get("/v1/feedstocks/usda/survey/parameters")
    assert resp.status_code == 200
    body = resp.json()
    assert "values" in body
    assert isinstance(body["values"], list)


# ---------------------------------------------------------------------------
# Data endpoint smoke tests (5 tests)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_smoke_analysis_endpoints(client):
    """Smoke test analysis data endpoints using values from discovery."""
    resources = client.get("/v1/feedstocks/analysis/resources").json()["values"]
    geoids = client.get("/v1/feedstocks/analysis/geoids").json()["values"]

    assert resources, "No resources returned by analysis discovery"
    assert geoids, "No geoids returned by analysis discovery — ETL data may be missing"

    # Find a resource+geoid combo that actually has data
    resource, geoid, parameter = None, None, None
    for r in resources[:10]:
        for g in geoids[:10]:
            list_resp = client.get(f"/v1/feedstocks/analysis/resources/{r}/geoid/{g}/parameters")
            if list_resp.status_code == 200 and list_resp.json().get("data"):
                resource, geoid = r, g
                parameter = list_resp.json()["data"][0]["parameter"]
                break
        if resource:
            break

    assert resource, "Could not find any resource+geoid combo with analysis data"

    resp = client.get(
        f"/v1/feedstocks/analysis/resources/{resource}/geoid/{geoid}/parameters/{parameter}"
    )
    assert resp.status_code == 200
    assert resp.json()

    resp = client.get(
        f"/v1/feedstocks/analysis/resources/{resource}/geoid/{geoid}/parameters"
    )
    assert resp.status_code == 200
    assert resp.json()


@pytest.mark.integration
def test_smoke_availability_endpoint(client):
    """Smoke test availability endpoint using discovery."""
    resources = client.get("/v1/feedstocks/availability/resources").json()["values"]
    geoids = client.get("/v1/feedstocks/availability/geoids").json()["values"]

    assert resources, "No resources returned by availability discovery"
    assert geoids, "No geoids returned by availability discovery"

    resource = resources[0]
    geoid = geoids[0]
    resp = client.get(f"/v1/feedstocks/availability/resources/{resource}/geoid/{geoid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resource"] == resource
    assert body["geoid"] == geoid
    assert isinstance(body["from_month"], int)
    assert isinstance(body["to_month"], int)


@pytest.mark.integration
def test_smoke_census_by_crop_endpoints(client):
    """Smoke test census crop-based data endpoints using values from discovery."""
    crops = client.get("/v1/feedstocks/usda/census/crops").json()["values"]
    geoids = client.get("/v1/feedstocks/usda/census/geoids").json()["values"]

    assert crops, "No crops returned by census discovery"
    assert geoids, "No geoids returned by census discovery"

    # Find a crop+geoid combo that actually has data
    crop, geoid, parameter = None, None, None
    for c in crops[:5]:
        for g in geoids[:20]:
            list_resp = client.get(f"/v1/feedstocks/usda/census/crops/{c}/geoid/{g}/parameters")
            if list_resp.status_code == 200 and list_resp.json().get("data"):
                crop, geoid = c, g
                parameter = list_resp.json()["data"][0]["parameter"]
                break
        if crop:
            break

    assert crop, "Could not find any crop+geoid combo with census data"

    resp = client.get(
        f"/v1/feedstocks/usda/census/crops/{crop}/geoid/{geoid}/parameters/{parameter}"
    )
    assert resp.status_code == 200
    assert resp.json()

    resp = client.get(
        f"/v1/feedstocks/usda/census/crops/{crop}/geoid/{geoid}/parameters"
    )
    assert resp.status_code == 200
    assert resp.json()


@pytest.mark.integration
def test_smoke_census_by_resource_endpoints(client):
    """Smoke test census resource-based data endpoints using values from discovery."""
    resources = client.get("/v1/feedstocks/usda/census/resources").json()["values"]
    geoids = client.get("/v1/feedstocks/usda/census/geoids").json()["values"]

    assert resources, "No resources returned by census discovery"
    assert geoids, "No geoids returned by census discovery"

    # Find a resource+geoid combo that actually has data
    resource, geoid, parameter = None, None, None
    for r in resources[:5]:
        for g in geoids[:20]:
            list_resp = client.get(f"/v1/feedstocks/usda/census/resources/{r}/geoid/{g}/parameters")
            if list_resp.status_code == 200 and list_resp.json().get("data"):
                resource, geoid = r, g
                parameter = list_resp.json()["data"][0]["parameter"]
                break
        if resource:
            break

    assert resource, "Could not find any resource+geoid combo with census data"

    resp = client.get(
        f"/v1/feedstocks/usda/census/resources/{resource}/geoid/{geoid}/parameters/{parameter}"
    )
    assert resp.status_code == 200
    assert resp.json()

    resp = client.get(
        f"/v1/feedstocks/usda/census/resources/{resource}/geoid/{geoid}/parameters"
    )
    assert resp.status_code == 200
    assert resp.json()


@pytest.mark.integration
def test_smoke_survey_by_crop_endpoints(client):
    """Smoke test survey crop-based data endpoints using values from discovery."""
    crops = client.get("/v1/feedstocks/usda/survey/crops").json()["values"]
    geoids = client.get("/v1/feedstocks/usda/survey/geoids").json()["values"]

    assert crops, "No crops returned by survey discovery"
    assert geoids, "No geoids returned by survey discovery"

    # Find a crop+geoid combo that actually has data
    crop, geoid, parameter = None, None, None
    for c in crops[:5]:
        for g in geoids[:20]:
            list_resp = client.get(f"/v1/feedstocks/usda/survey/crops/{c}/geoid/{g}/parameters")
            if list_resp.status_code == 200 and list_resp.json().get("data"):
                crop, geoid = c, g
                parameter = list_resp.json()["data"][0]["parameter"]
                break
        if crop:
            break

    assert crop, "Could not find any crop+geoid combo with survey data"

    resp = client.get(
        f"/v1/feedstocks/usda/survey/crops/{crop}/geoid/{geoid}/parameters/{parameter}"
    )
    assert resp.status_code == 200
    assert resp.json()

    resp = client.get(
        f"/v1/feedstocks/usda/survey/crops/{crop}/geoid/{geoid}/parameters"
    )
    assert resp.status_code == 200
    assert resp.json()


@pytest.mark.integration
def test_smoke_survey_by_resource_endpoints(client):
    """Smoke test survey resource-based data endpoints using values from discovery."""
    resources = client.get("/v1/feedstocks/usda/survey/resources").json()["values"]
    geoids = client.get("/v1/feedstocks/usda/survey/geoids").json()["values"]

    assert resources, "No resources returned by survey discovery"
    assert geoids, "No geoids returned by survey discovery"

    # Find a resource+geoid combo that actually has data
    resource, geoid, parameter = None, None, None
    for r in resources[:5]:
        for g in geoids[:20]:
            list_resp = client.get(f"/v1/feedstocks/usda/survey/resources/{r}/geoid/{g}/parameters")
            if list_resp.status_code == 200 and list_resp.json().get("data"):
                resource, geoid = r, g
                parameter = list_resp.json()["data"][0]["parameter"]
                break
        if resource:
            break

    assert resource, "Could not find any resource+geoid combo with survey data"

    resp = client.get(
        f"/v1/feedstocks/usda/survey/resources/{resource}/geoid/{geoid}/parameters/{parameter}"
    )
    assert resp.status_code == 200
    assert resp.json()

    resp = client.get(
        f"/v1/feedstocks/usda/survey/resources/{resource}/geoid/{geoid}/parameters"
    )
    assert resp.status_code == 200
    assert resp.json()


# ---------------------------------------------------------------------------
# Infrastructure endpoint smoke tests (6 tests)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_root_endpoint(base_url):
    """Root endpoint is accessible without authentication."""
    with httpx.Client(base_url=base_url) as c:
        resp = c.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


@pytest.mark.integration
def test_health_endpoint(base_url):
    """Health check endpoint returns 200."""
    with httpx.Client(base_url=base_url) as c:
        resp = c.get("/v1/health")
    assert resp.status_code == 200


@pytest.mark.integration
def test_auth_login(base_url):
    """Login with valid credentials returns an access token."""
    username = os.getenv("CA_BIOSITING_TEST_USERNAME")
    password = os.getenv("CA_BIOSITING_TEST_PASSWORD")
    if not username or not password:
        pytest.skip("CA_BIOSITING_TEST_USERNAME/PASSWORD env vars not set")
    with httpx.Client(base_url=base_url) as c:
        resp = c.post("/v1/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.integration
def test_auth_refresh(client):
    """Token refresh returns a new access token for an authenticated user."""
    resp = client.post("/v1/auth/refresh")
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.integration
def test_auth_logout(client):
    """Logout endpoint returns 200."""
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 200


@pytest.mark.integration
def test_auth_protected_without_token(base_url):
    """Protected endpoint returns 401 when no token is provided."""
    with httpx.Client(base_url=base_url) as c:
        resp = c.get("/v1/feedstocks/analysis/resources")
    assert resp.status_code == 401
