"""Unit tests for the /health endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ca_biositing.webservice.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_returns_200_when_db_available():
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch("ca_biositing.webservice.main.get_engine", return_value=mock_engine):
        resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["db"] == "connected"
    assert body["ready_for_mcp"] is True


def test_health_returns_503_when_db_unavailable():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("connection refused")

    with patch("ca_biositing.webservice.main.get_engine", return_value=mock_engine):
        resp = client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["db"] == "disconnected"
    assert body["ready_for_mcp"] is False
