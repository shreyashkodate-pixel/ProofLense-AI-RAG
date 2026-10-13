"""ProofLens AI — FastAPI Application Entrypoint.

Configures application lifecycle, CORS middleware, in-memory rate limiting,
error handlers, and baseline health/security endpoints.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import Depends, FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings, get_settings
from app.core.errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import logger, setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import verify_access_passkey


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    # 1. Initialize logging
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "ProofLens AI backend starting up",
        extra={"extra": {"environment": settings.ENVIRONMENT, "port": settings.PORT}},
    )

    # 2. Strict startup validation has executed via get_settings()
    logger.info("Application configuration successfully validated.")

    yield

    # Shutdown logic
    logger.info("ProofLens AI backend shutting down.")


def create_application() -> FastAPI:
    """Factory function for FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="ProofLens AI API",
        description="Evidence-first document intelligence platform with verifiable page-level citations.",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. In-Memory Rate Limiting Middleware
    app.add_middleware(RateLimitMiddleware)

    # 3. Standardized Exception Handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 4. Foundation Endpoints (Phase 1)
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint returning basic service metadata."""
        return {
            "name": "ProofLens AI API",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "status": "online",
        }

    @app.get("/health/live", tags=["Health"], status_code=status.HTTP_200_OK)
    async def liveness_probe():
        """Unauthenticated process liveness probe for container orchestrators."""
        return {"status": "alive"}

    @app.get("/api/v1/auth-test", tags=["Security"], dependencies=[Depends(verify_access_passkey)])
    async def auth_test_endpoint():
        """Protected endpoint validating demo passkey gatekeeper functionality."""
        return {"authenticated": True, "message": "Passkey verified successfully."}

    return app


app = create_application()
