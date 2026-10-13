"""ProofLens AI — Unit Tests for Security Middleware & Passkey Gatekeeper.

Verifies constant-time passkey enforcement, unauthenticated health probes,
rate limiting, and standard error envelope adherence.
"""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limiter
from app.main import create_application


def test_unauthenticated_health_probe_succeeds(client: TestClient):
    """Verify /health/live probe is accessible without authentication."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_root_endpoint_metadata(client: TestClient):
    """Verify / root metadata endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ProofLens AI API"
    assert data["status"] == "online"


def test_protected_endpoint_rejects_missing_passkey(client: TestClient):
    """Verify protected endpoints return HTTP 401 when X-Workspace-Key is missing."""
    response = client.get("/api/v1/auth-test")
    assert response.status_code == 401
    data = response.json()

    # Validate standard error envelope
    assert data["error_code"] == "UNAUTHORIZED"
    assert "Missing required access passkey" in data["message"]
    assert "timestamp" in data
    assert "details" in data


def test_protected_endpoint_rejects_invalid_passkey(client: TestClient):
    """Verify protected endpoints return HTTP 401 when X-Workspace-Key is wrong."""
    response = client.get(
        "/api/v1/auth-test",
        headers={"X-Workspace-Key": "wrong-incorrect-passkey"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"
    assert "Invalid access passkey" in data["message"]


def test_protected_endpoint_accepts_valid_passkey(client: TestClient):
    """Verify protected endpoint succeeds with the correct X-Workspace-Key."""
    response = client.get(
        "/api/v1/auth-test",
        headers={"X-Workspace-Key": "test-passkey-secret-123456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True


def test_auth_disabled_bypass():
    """Verify authentication can be bypassed in dev/test when AUTH_ENABLED=False."""
    settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=False,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        GEMINI_API_KEY="test-dummy-key",
    )
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/auth-test")
        assert response.status_code == 200
        assert response.json()["authenticated"] is True


def test_in_memory_rate_limiting_enforcement():
    """Verify requests exceeding the configured rate limit receive HTTP 429."""
    # Configure tight rate limit for test
    tight_settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        GEMINI_API_KEY="test-dummy-key",
        RATE_LIMIT_REQUESTS_PER_MINUTE=3,
    )
    app = create_application()
    app.state.settings = tight_settings
    app.dependency_overrides[get_settings] = lambda: tight_settings

    with TestClient(app) as test_client:
        headers = {"X-Workspace-Key": "test-passkey-secret-123456"}

        # Request 1, 2, 3 should succeed
        for _ in range(3):
            res = test_client.get("/api/v1/auth-test", headers=headers)
            assert res.status_code == 200

        # Request 4 should be throttled
        throttled_res = test_client.get("/api/v1/auth-test", headers=headers)
        assert throttled_res.status_code == 429
        data = throttled_res.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in throttled_res.headers
