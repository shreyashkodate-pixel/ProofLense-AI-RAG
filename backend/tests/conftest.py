"""ProofLens AI — Pytest Configuration & Fixtures.

Configures test clients and dummy settings isolated from external networks and credentials.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limiter
from app.main import create_application


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    """Ensure in-memory rate limiter is cleanly reset before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def dummy_test_settings() -> Settings:
    """Provide isolated test settings without real external credentials."""
    return Settings(
        ENVIRONMENT="test",
        DEBUG=True,
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        GEMINI_API_KEY="test-dummy-gemini-key",
        DATABASE_URL="postgresql+asyncpg://dummy:dummy@localhost:5432/test_db",
        CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000",
    )


@pytest.fixture
def client(dummy_test_settings: Settings) -> TestClient:
    """Create test client with overridden test settings."""
    app = create_application()
    app.state.settings = dummy_test_settings
    app.dependency_overrides[get_settings] = lambda: dummy_test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
