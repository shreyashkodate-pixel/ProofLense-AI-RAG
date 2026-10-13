"""ProofLens AI — Application-Level Access Passkey Security Gatekeeper.

Implements constant-time token comparison (secrets.compare_digest) for the
X-Workspace-Key header, ensuring zero timing-leak vulnerabilities and strict
fail-closed access protection for public demos.
"""

import secrets
from typing import Optional
from fastapi import Depends, Header, status

from app.core.config import Settings, get_settings
from app.core.errors import AppSecurityException


X_WORKSPACE_KEY_HEADER = "X-Workspace-Key"


def verify_access_passkey(
    x_workspace_key: Optional[str] = Header(None, alias=X_WORKSPACE_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> bool:
    """FastAPI dependency validating the access passkey header in constant time.

    Bypasses validation solely when AUTH_ENABLED is False (permitted in dev/test)
    or when no DEMO_ACCESS_TOKEN is configured in local non-production environments.
    """

    # In development/test, authentication may be explicitly toggled off
    if not settings.AUTH_ENABLED:
        return True

    # If no token is configured in local development, allow through
    if not settings.DEMO_ACCESS_TOKEN:
        if settings.ENVIRONMENT == "production":
            # This branch should never be hit due to startup validation, but acts as fail-closed defense
            raise AppSecurityException(
                message="Application is misconfigured: access control is missing.",
                error_code="CONFIGURATION_ERROR",
            )
        return True

    # When a token is configured, X-Workspace-Key is mandatory
    if not x_workspace_key or not x_workspace_key.strip():
        raise AppSecurityException(
            message=f"Missing required access passkey in '{X_WORKSPACE_KEY_HEADER}' header.",
            error_code="UNAUTHORIZED",
            details={"required_header": X_WORKSPACE_KEY_HEADER},
        )

    # Constant-time comparison prevents timing analysis
    is_valid = secrets.compare_digest(
        x_workspace_key.strip().encode("utf-8"),
        settings.DEMO_ACCESS_TOKEN.strip().encode("utf-8"),
    )

    if not is_valid:
        raise AppSecurityException(
            message="Invalid access passkey provided in request header.",
            error_code="UNAUTHORIZED",
            details={"header": X_WORKSPACE_KEY_HEADER},
        )

    return True
