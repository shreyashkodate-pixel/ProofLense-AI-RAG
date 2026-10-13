"""ProofLens AI — Integration Tests for Health & Readiness Probes.

Verifies process liveness, database connectivity detection, and pgvector readiness
under healthy and failure conditions.
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_application


def test_health_live_endpoint(client: TestClient):
    """Verify /health/live returns HTTP 200 unauthenticated."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_ready_healthy():
    """Verify /health/ready returns HTTP 200 when database and pgvector are healthy."""
    settings = Settings(ENVIRONMENT="test", AUTH_ENABLED=True)
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.health.check_db_connectivity", new=AsyncMock(return_value=True)), \
         patch("app.api.v1.health.check_pgvector_extension", new=AsyncMock(return_value=True)):
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "connected"
            assert data["pgvector"] is True


def test_health_ready_database_disconnected():
    """Verify /health/ready returns HTTP 503 when database is unreachable."""
    settings = Settings(ENVIRONMENT="test", AUTH_ENABLED=True)
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.health.check_db_connectivity", new=AsyncMock(return_value=False)):
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["error_code"] == "SERVICE_UNAVAILABLE"
            assert "Database connection failed" in data["message"]
            assert data["details"]["database"] == "disconnected"


def test_health_ready_pgvector_extension_missing():
    """Verify /health/ready returns HTTP 503 when pgvector extension is missing."""
    settings = Settings(ENVIRONMENT="test", AUTH_ENABLED=True)
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.health.check_db_connectivity", new=AsyncMock(return_value=True)), \
         patch("app.api.v1.health.check_pgvector_extension", new=AsyncMock(return_value=False)):
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["error_code"] == "SERVICE_UNAVAILABLE"
            assert "pgvector extension is not installed" in data["message"]
            assert data["details"]["pgvector"] is False
