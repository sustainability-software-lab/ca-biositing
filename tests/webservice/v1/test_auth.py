"""Tests for authentication API endpoints.

These tests use the auth_client / auth_engine fixtures from
tests/webservice/conftest.py, which use SQLModel Sessions so that
authenticate_user's session.exec() calls work correctly.
"""

from __future__ import annotations


class TestLogin:
    """Tests for POST /v1/auth/token."""

    def test_valid_credentials_returns_token(self, auth_client, admin_user):
        resp = auth_client.post(
            "/v1/auth/token",
            data={"username": "admin", "password": "adminpass"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, auth_client, admin_user):
        resp = auth_client.post(
            "/v1/auth/token",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_unknown_user_returns_401(self, auth_client):
        resp = auth_client.post(
            "/v1/auth/token",
            data={"username": "nonexistentuser", "password": "somepassword"},
        )
        assert resp.status_code == 401


class TestRegister:
    """Tests for POST /v1/auth/register."""

    def test_admin_creates_user(self, auth_client, admin_token):
        resp = auth_client.post(
            "/v1/auth/register",
            json={"username": "newuser", "password": "securepassword123"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser"
        assert "id" in body

    def test_non_admin_cannot_register(self, auth_client, user_token):
        resp = auth_client.post(
            "/v1/auth/register",
            json={"username": "another", "password": "securepassword123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403


class TestRefresh:
    """Tests for POST /v1/auth/refresh."""

    def test_valid_token_returns_new_token(self, auth_client, admin_token):
        resp = auth_client.post(
            "/v1/auth/refresh",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_no_token_returns_401(self, auth_client):
        resp = auth_client.post("/v1/auth/refresh")
        assert resp.status_code == 401


class TestLogout:
    """Tests for POST /v1/auth/logout."""

    def test_logout_returns_200(self, auth_client):
        resp = auth_client.post("/v1/auth/logout")
        assert resp.status_code == 200


class TestProtectedEndpoint:
    """Tests that protected feedstock endpoints enforce authentication."""

    def test_no_token_returns_401(self, auth_client):
        resp = auth_client.get("/v1/feedstocks/analysis/resources")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, auth_client):
        resp = auth_client.get(
            "/v1/feedstocks/analysis/resources",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401
