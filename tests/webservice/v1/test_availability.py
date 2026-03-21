"""Tests for resource availability API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestGetAvailabilityByResource:
    """Tests for GET /v1/feedstocks/availability/resources/{resource}/geoid/{geoid}"""

    def test_get_availability_success(self, client: TestClient, test_availability_data):
        """Test successful retrieval of resource availability."""
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat_straw/geoid/06067"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "wheat_straw"
        assert data["geoid"] == "06067"
        assert data["from_month"] == 6  # June
        assert data["to_month"] == 8    # August

    def test_get_availability_different_resource(self, client: TestClient, test_availability_data):
        """Test retrieval of availability for different resource."""
        response = client.get(
            "/v1/feedstocks/availability/resources/rice_straw/geoid/06099"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resource"] == "rice_straw"
        assert data["geoid"] == "06099"
        assert data["from_month"] == 9   # September
        assert data["to_month"] == 11    # November

    def test_get_availability_resource_not_found(self, client: TestClient, test_availability_data):
        """Test error when resource doesn't exist."""
        response = client.get(
            "/v1/feedstocks/availability/resources/nonexistent_resource/geoid/06067"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_availability_geoid_not_found(self, client: TestClient, test_availability_data):
        """Test error when geoid doesn't have availability data."""
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat_straw/geoid/99999"
        )
        assert response.status_code == 404

    def test_get_availability_wrong_geoid_for_resource(self, client: TestClient, test_availability_data):
        """Test error when querying correct resource but wrong geoid."""
        # wheat_straw is in 06067, not 06099
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat_straw/geoid/06099"
        )
        assert response.status_code == 404

    def test_get_availability_response_structure(self, client: TestClient, test_availability_data):
        """Test that response has correct structure."""
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat_straw/geoid/06067"
        )
        data = response.json()

        # Verify all required fields are present
        assert "resource" in data
        assert "geoid" in data
        assert "from_month" in data
        assert "to_month" in data

        # Verify types
        assert isinstance(data["resource"], str)
        assert isinstance(data["geoid"], str)
        assert isinstance(data["from_month"], int)
        assert isinstance(data["to_month"], int)

    def test_get_availability_month_range_valid(self, client: TestClient, test_availability_data):
        """Test that month values are in valid range."""
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat_straw/geoid/06067"
        )
        data = response.json()

        # Months should be 1-12
        assert 1 <= data["from_month"] <= 12
        assert 1 <= data["to_month"] <= 12


class TestAvailabilityURLValidation:
    """Tests for URL validation and edge cases."""

    def test_invalid_url_pattern(self, client: TestClient, test_availability_data):
        """Test that invalid URL patterns return 404."""
        response = client.get("/v1/feedstocks/availability/invalid/path")
        assert response.status_code == 404

    def test_url_with_special_characters(self, client: TestClient, test_availability_data):
        """Test URL with special characters in resource name."""
        # Resource names should be lowercase with underscores
        response = client.get(
            "/v1/feedstocks/availability/resources/wheat-straw/geoid/06067"
        )
        # Should return 404 because resource name doesn't match
        assert response.status_code == 404

    def test_url_missing_geoid(self, client: TestClient, test_availability_data):
        """Test URL missing geoid parameter."""
        response = client.get("/v1/feedstocks/availability/resources/wheat_straw")
        # Should be 404 because the route requires geoid
        assert response.status_code in [404, 405]  # 405 Method Not Allowed is also acceptable


class TestAvailabilityDiscovery:
    """Tests for availability discovery endpoints."""

    def test_discovery_resources(self, client: TestClient, test_availability_data):
        response = client.get("/v1/feedstocks/availability/resources")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0
        assert "wheat_straw" in body["values"]
        assert "rice_straw" in body["values"]

    def test_discovery_geoids(self, client: TestClient, test_availability_data):
        response = client.get("/v1/feedstocks/availability/geoids")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0
        assert "06067" in body["values"]
