"""Tests for analysis data API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestGetAnalysisByResource:
    """Tests for GET /v1/feedstocks/analysis/resources/{resource}/geoid/{geoid}/parameters/{parameter}"""

    def test_get_analysis_success(self, client: TestClient, test_analysis_data):
        """Test successful retrieval of analysis parameter."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06001/parameters/ash"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "almond_hulls"
        assert data["geoid"] == "06001"
        assert data["parameter"] == "ash"
        assert data["value"] == 5.2
        assert data["unit"] == "percent"

    def test_get_analysis_ultimate_type(self, client: TestClient, test_analysis_data):
        """Test retrieval of ultimate analysis parameter."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06001/parameters/carbon"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "almond_hulls"
        assert data["parameter"] == "carbon"
        assert data["value"] == 45.3

    def test_get_analysis_compositional_type(self, client: TestClient, test_analysis_data):
        """Test retrieval of compositional analysis parameter."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/corn_stover/geoid/06013/parameters/cellulose"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "corn_stover"
        assert data["geoid"] == "06013"
        assert data["parameter"] == "cellulose"
        assert data["value"] == 38.7

    def test_get_analysis_resource_not_found(self, client: TestClient, test_analysis_data):
        """Test error when resource doesn't exist."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/nonexistent_resource/geoid/06001/parameters/ash"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_analysis_parameter_not_found(self, client: TestClient, test_analysis_data):
        """Test error when parameter doesn't exist for resource."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06001/parameters/nonexistent_param"
        )
        assert response.status_code == 404
        assert "parameter" in response.json()["detail"].lower()

    def test_get_analysis_geoid_not_found(self, client: TestClient, test_analysis_data):
        """Test error when geoid doesn't have data for resource."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/99999/parameters/ash"
        )
        assert response.status_code == 404

    def test_get_analysis_wrong_geoid_for_resource(self, client: TestClient, test_analysis_data):
        """Test error when querying correct resource but wrong geoid."""
        # almond_hulls is in 06001, not 06013
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06013/parameters/ash"
        )
        assert response.status_code == 404


class TestListAnalysisByResource:
    """Tests for GET /v1/feedstocks/analysis/resources/{resource}/geoid/{geoid}/parameters"""

    def test_list_analysis_success(self, client: TestClient, test_analysis_data):
        """Test successful listing of all analysis parameters for a resource."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06001/parameters"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "almond_hulls"
        assert data["geoid"] == "06001"
        assert len(data["data"]) == 3  # ash, moisture (proximate) + carbon (ultimate)

        # Check that all parameters are present
        params = [item["parameter"] for item in data["data"]]
        assert "ash" in params
        assert "moisture" in params
        assert "carbon" in params

    def test_list_analysis_structure(self, client: TestClient, test_analysis_data):
        """Test response structure for list endpoint."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/06001/parameters"
        )
        data = response.json()

        # Verify structure
        assert "resource" in data
        assert "geoid" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        # Check first item structure
        if data["data"]:
            item = data["data"][0]
            assert "parameter" in item
            assert "value" in item
            assert "unit" in item

    def test_list_analysis_resource_not_found(self, client: TestClient, test_analysis_data):
        """Test error when resource doesn't exist."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/nonexistent_resource/geoid/06001/parameters"
        )
        assert response.status_code == 404

    def test_list_analysis_no_data(self, client: TestClient, test_analysis_data):
        """Test when resource exists but no data for geoid."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond_hulls/geoid/99999/parameters"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "almond_hulls"
        assert data["geoid"] == "99999"
        assert data["data"] == []

    def test_list_analysis_compositional_only(self, client: TestClient, test_analysis_data):
        """Test resource with only compositional analysis data."""
        response = client.get(
            "/v1/feedstocks/analysis/resources/corn_stover/geoid/06013/parameters"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["parameter"] == "cellulose"


class TestAnalysisURLValidation:
    """Tests for URL validation and edge cases."""

    def test_invalid_url_pattern(self, client: TestClient, test_analysis_data):
        """Test that invalid URL patterns return 404."""
        response = client.get("/v1/feedstocks/analysis/invalid/path")
        assert response.status_code == 404

    def test_url_with_special_characters(self, client: TestClient, test_analysis_data):
        """Test URL with special characters in resource name."""
        # Resource names should be lowercase with underscores
        response = client.get(
            "/v1/feedstocks/analysis/resources/almond-hulls/geoid/06001/parameters/ash"
        )
        # Should return 404 because resource name doesn't match
        assert response.status_code == 404


class TestAnalysisDiscovery:
    """Tests for analysis discovery endpoints."""

    def test_discovery_resources(self, client: TestClient, test_analysis_data):
        response = client.get("/v1/feedstocks/analysis/resources")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0

    def test_discovery_geoids(self, client: TestClient, test_analysis_data):
        response = client.get("/v1/feedstocks/analysis/geoids")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)

    def test_discovery_parameters(self, client: TestClient, test_analysis_data):
        response = client.get("/v1/feedstocks/analysis/parameters")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0
