"""ProofLens AI — Standardized Error Envelopes & Handlers.

Ensures all client-facing errors adhere to the uniform JSON envelope
defined in TECHNICAL-DESIGN.md Section 5.1 without exposing raw tracebacks.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.logging import logger


class ErrorResponse(BaseModel):
    """Standardized API Error Envelope."""

    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual error details")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO-8601 timestamp of when the error occurred",
    )


class AppSecurityException(HTTPException):
    """Exception for authentication and passkey failures."""

    def __init__(
        self,
        message: str = "Invalid or missing access passkey.",
        error_code: str = "UNAUTHORIZED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": error_code,
                "message": message,
                "details": details or {},
            },
            headers={"WWW-Authenticate": "Passkey"},
        )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardized handler for HTTPExceptions."""
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        error_code = exc.detail.get("error_code", "HTTP_ERROR")
        message = exc.detail.get("message", "An HTTP error occurred.")
        details = exc.detail.get("details", {})
    else:
        # Default error code based on status code
        error_code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
        }.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail)
        details = {}

    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized handler for Pydantic RequestValidationErrors."""
    errors = exc.errors()
    simplified_errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in errors
    ]
    payload = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed. Verify input fields and types.",
        details={"validation_errors": simplified_errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global catch-all exception handler preventing raw traceback leakage."""
    logger.error(f"Unhandled exception during request processing: {exc}", exc_info=True)
    payload = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        details={},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(),
    )
