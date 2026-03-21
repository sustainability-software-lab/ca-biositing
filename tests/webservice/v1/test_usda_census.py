"""Tests for USDA Census data API endpoints.

This module tests all four census endpoint patterns:
- Get single parameter by crop
- Get single parameter by resource
- List all parameters by crop
- List all parameters by resource
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ca_biositing.datamodels.models import Observation, UsdaCensusRecord, UsdaCommodity


class TestGetCensusByCrop:
    """Test cases for getting census data by USDA crop name."""

    def test_get_single_parameter_success(self, client: TestClient, test_census_data):
        """Test successful retrieval of single parameter by crop."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usda_crop"] == "CORN"
        assert data["resource"] is None
        assert data["geoid"] == "06001"
        assert data["parameter"] == "acres"
        assert data["value"] == 25000.0
        assert data["unit"] == "acres"

    def test_get_parameter_with_dimension(self, client: TestClient, test_census_data):
        """Test retrieval of parameter with dimension data."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/yield_per_acre"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["parameter"] == "yield_per_acre"
        assert data["value"] == 150.0
        assert data["dimension"] == "area"
        assert data["dimension_value"] == 1.0
        assert data["dimension_unit"] == "acres"

    def test_crop_not_found(self, client: TestClient, test_census_data):
        """Test 404 when crop doesn't exist."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/FAKE_CROP/geoid/06001/parameters/acres"
        )

        assert response.status_code == 404
        assert "FAKE_CROP" in response.json()["detail"]
        assert "not found" in response.json()["detail"].lower()

    def test_parameter_not_found_for_crop(self, client: TestClient, test_census_data):
        """Test 404 when parameter doesn't exist for crop/geoid."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/nonexistent_param"
        )

        assert response.status_code == 404
        assert "nonexistent_param" in response.json()["detail"]
        assert "not found" in response.json()["detail"].lower()

    def test_geoid_not_found(self, client: TestClient, test_census_data):
        """Test 404 when geoid has no data for crop."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/99999/parameters/acres"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetCensusByResource:
    """Test cases for getting census data by resource name."""

    def test_get_single_parameter_success(self, client: TestClient, test_census_data):
        """Test successful retrieval of single parameter by resource."""
        response = client.get(
            "/v1/feedstocks/usda/census/resources/corn_grain/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usda_crop"] is None
        assert data["resource"] == "corn_grain"
        assert data["geoid"] == "06001"
        assert data["parameter"] == "acres"
        assert data["value"] == 25000.0
        assert data["unit"] == "acres"

    def test_resource_not_found(self, client: TestClient, test_census_data):
        """Test 404 when resource doesn't exist."""
        response = client.get(
            "/v1/feedstocks/usda/census/resources/fake_resource/geoid/06001/parameters/acres"
        )

        assert response.status_code == 404
        assert "fake_resource" in response.json()["detail"]
        assert "not found" in response.json()["detail"].lower()

    def test_parameter_not_found_for_resource(self, client: TestClient, test_census_data):
        """Test 404 when parameter doesn't exist for resource/geoid."""
        response = client.get(
            "/v1/feedstocks/usda/census/resources/corn_grain/geoid/06001/parameters/fake_param"
        )

        assert response.status_code == 404
        assert "fake_param" in response.json()["detail"]
        assert "not found" in response.json()["detail"].lower()


class TestListCensusByCrop:
    """Test cases for listing all census parameters by crop."""

    def test_list_all_parameters_success(self, client: TestClient, test_census_data):
        """Test successful listing of all parameters for crop."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usda_crop"] == "CORN"
        assert data["resource"] is None
        assert data["geoid"] == "06001"
        assert "data" in data
        assert len(data["data"]) == 3  # acres, production, yield_per_acre

        # Check that all expected parameters are present
        params = [item["parameter"] for item in data["data"]]
        assert "acres" in params
        assert "production" in params
        assert "yield_per_acre" in params

    def test_list_parameters_structure(self, client: TestClient, test_census_data):
        """Test that list response has correct structure."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify each data item has required fields
        for item in data["data"]:
            assert "parameter" in item
            assert "value" in item
            assert "unit" in item
            assert isinstance(item["value"], (int, float))
            assert isinstance(item["unit"], str)

    def test_list_crop_not_found(self, client: TestClient, test_census_data):
        """Test 404 when listing parameters for nonexistent crop."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/FAKE_CROP/geoid/06001/parameters"
        )

        assert response.status_code == 404
        assert "FAKE_CROP" in response.json()["detail"]

    def test_list_no_data_for_geoid(self, client: TestClient, test_census_data):
        """Test empty list when no data exists for crop/geoid combination."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/99999/parameters"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usda_crop"] == "CORN"
        assert data["geoid"] == "99999"
        assert data["data"] == []


class TestListCensusByResource:
    """Test cases for listing all census parameters by resource."""

    def test_list_all_parameters_success(self, client: TestClient, test_census_data):
        """Test successful listing of all parameters for resource."""
        response = client.get(
            "/v1/feedstocks/usda/census/resources/corn_grain/geoid/06001/parameters"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usda_crop"] is None
        assert data["resource"] == "corn_grain"
        assert data["geoid"] == "06001"
        assert "data" in data
        assert len(data["data"]) == 3

    def test_list_resource_not_found(self, client: TestClient, test_census_data):
        """Test 404 when listing parameters for nonexistent resource."""
        response = client.get(
            "/v1/feedstocks/usda/census/resources/fake_resource/geoid/06001/parameters"
        )

        assert response.status_code == 404
        assert "fake_resource" in response.json()["detail"]


class TestParameterValidation:
    """Test cases for URL path validation logic.

    Note: With RESTful paths, FastAPI handles most validation automatically.
    Invalid URLs return 404 instead of 422.
    """

    def test_invalid_url_pattern(self, client: TestClient, test_census_data):
        """Test 404 when using invalid URL pattern."""
        # Try to access non-existent endpoint
        response = client.get(
            "/v1/feedstocks/usda/census/invalid/path"
        )

        assert response.status_code == 404


class TestMultipleCrops:
    """Test cases with multiple crops to ensure correct filtering."""

    def test_get_different_crops(self, client: TestClient, test_census_data):
        """Test that different crops return different data."""
        # Get CORN data
        response_corn = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        # Get SOYBEANS data
        response_soybeans = client.get(
            "/v1/feedstocks/usda/census/crops/SOYBEANS/geoid/06001/parameters/acres"
        )

        assert response_corn.status_code == 200
        assert response_soybeans.status_code == 200

        corn_data = response_corn.json()
        soybean_data = response_soybeans.json()

        # Values should be different
        assert corn_data["value"] == 25000.0
        assert soybean_data["value"] == 15000.0
        assert corn_data["usda_crop"] == "CORN"
        assert soybean_data["usda_crop"] == "SOYBEANS"

    def test_list_different_crops_different_counts(self, client: TestClient, test_census_data):
        """Test that different crops have different parameter counts."""
        # CORN has 3 parameters
        response_corn = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters"
        )

        # SOYBEANS has 1 parameter
        response_soybeans = client.get(
            "/v1/feedstocks/usda/census/crops/SOYBEANS/geoid/06001/parameters"
        )

        assert response_corn.status_code == 200
        assert response_soybeans.status_code == 200

        assert len(response_corn.json()["data"]) == 3
        assert len(response_soybeans.json()["data"]) == 1


class TestLatestRecordSelection:
    """Tests for selecting the most recent USDA census record."""

    def test_prefers_latest_year_for_same_crop_and_geoid(
        self,
        client: TestClient,
        session: Session,
        test_census_data,
    ):
        """When multiple years exist, the service should use the newest year."""
        session.add(
            UsdaCensusRecord(
                id=10,
                dataset_id=1,
                geoid="06001",
                commodity_code=1,
                year=2023,
            )
        )
        session.add(
            Observation(
                id=1010,
                record_id="10",
                dataset_id=1,
                record_type="usda_census_record",
                parameter_id=1,
                value=26000.0,
                unit_id=1,
            )
        )
        session.commit()

        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        assert response.json()["value"] == 26000.0

    def test_breaks_same_year_ties_by_highest_record_id(
        self,
        client: TestClient,
        session: Session,
        test_census_data,
    ):
        """When year ties, the larger source record ID should be selected."""
        session.add_all([
            UsdaCensusRecord(
                id=11,
                dataset_id=1,
                geoid="06001",
                commodity_code=1,
                year=2024,
            ),
            UsdaCensusRecord(
                id=12,
                dataset_id=1,
                geoid="06001",
                commodity_code=1,
                year=2024,
            ),
        ])
        session.add_all([
            Observation(
                id=1011,
                record_id="11",
                dataset_id=1,
                record_type="usda_census_record",
                parameter_id=1,
                value=27000.0,
                unit_id=1,
            ),
            Observation(
                id=1012,
                record_id="12",
                dataset_id=1,
                record_type="usda_census_record",
                parameter_id=1,
                value=28000.0,
                unit_id=1,
            ),
        ])
        session.commit()

        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        assert response.json()["value"] == 28000.0


class TestCropNormalizationMatching:
    """Tests for exact, case- and space-insensitive crop matching."""

    def test_get_by_crop_matches_case_and_whitespace_variants(
        self, client: TestClient, test_census_data
    ):
        """CORN ALL should match with mixed case and repeated internal spaces."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CoRn%20%20%20AlL/geoid/06047/parameters/acres"
        )

        assert response.status_code == 200
        assert response.json()["value"] == 18000.0

    def test_get_by_crop_does_not_prefix_match(self, client: TestClient, test_census_data):
        """CORN should not match CORN ALL on a geoid where only CORN ALL exists."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06047/parameters/acres"
        )

        assert response.status_code == 404

    def test_list_by_crop_matches_collapsed_spaces(self, client: TestClient, test_census_data):
        """Double spaces in input should normalize to single-space exact match."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/corn%20%20all/geoid/06047/parameters"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["parameter"] == "acres"
        assert data["data"][0]["value"] == 18000.0

    def test_get_by_crop_does_not_match_different_phrase(
        self, client: TestClient, test_census_data
    ):
        """Different phrase should not match even if it contains the same first word."""
        response = client.get(
            "/v1/feedstocks/usda/census/crops/corn%20altogether/geoid/06047/parameters/acres"
        )

        assert response.status_code == 404

    def test_get_by_crop_prefers_api_name_match_over_name_match(
        self,
        client: TestClient,
        session: Session,
        test_census_data,
    ):
        """Prefer api_name match when another commodity only matches by legacy name."""
        session.add(
            UsdaCommodity(id=4, name="corn", api_name="maize", usda_code="00123")
        )
        session.add(
            UsdaCensusRecord(
                id=4,
                dataset_id=1,
                geoid="06001",
                commodity_code=4,
                year=2022,
            )
        )
        session.add(
            Observation(
                id=997,
                record_id="4",
                dataset_id=1,
                record_type="usda_census_record",
                parameter_id=1,
                value=999999.0,
                unit_id=1,
            )
        )
        session.commit()

        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        assert response.json()["value"] == 25000.0


class TestObservationQueryRegression:
    """Regression tests for ETL observation key format."""

    def test_ignores_legacy_observation_record_format(
        self,
        client: TestClient,
        session: Session,
        test_census_data,
    ):
        """Ensure census endpoints read ETL-style observation keys."""
        # Insert legacy-style observation row that should not be selected.
        session.add(
            Observation(
                id=999,
                record_id="census_1_acres",
                dataset_id=1,
                record_type="census",
                parameter_id=1,
                value=999999.0,
                unit_id=1,
            )
        )
        session.commit()

        response = client.get(
            "/v1/feedstocks/usda/census/crops/CORN/geoid/06001/parameters/acres"
        )

        assert response.status_code == 200
        assert response.json()["value"] == 25000.0


class TestCensusDiscovery:
    """Tests for USDA census discovery endpoints."""

    def test_discovery_crops(self, client: TestClient, test_census_data):
        response = client.get("/v1/feedstocks/usda/census/crops")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0

    def test_discovery_resources(self, client: TestClient, test_census_data):
        response = client.get("/v1/feedstocks/usda/census/resources")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0

    def test_discovery_geoids(self, client: TestClient, test_census_data):
        response = client.get("/v1/feedstocks/usda/census/geoids")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0

    def test_discovery_parameters(self, client: TestClient, test_census_data):
        response = client.get("/v1/feedstocks/usda/census/parameters")
        assert response.status_code == 200
        body = response.json()
        assert "values" in body
        assert isinstance(body["values"], list)
        assert len(body["values"]) > 0
