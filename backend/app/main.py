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

from app.api.v1.comparisons import router as comparisons_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.queries import router as queries_router
from app.api.v1.workspaces import router as workspaces_router
from app.core.config import Settings, get_settings
from app.core.database import close_engine, get_engine
from app.core.errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.lifespan import (
    recover_stale_ingestion_jobs,
    verify_vector_dimension_compatibility,
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

    # Shutdown logic: Close database connection pool
    await close_engine()
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

    # 4. Mount API Routers
    app.include_router(health_router)
    app.include_router(workspaces_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(queries_router, prefix="/api/v1")
    app.include_router(comparisons_router, prefix="/api/v1")

    # 5. Foundation Endpoints (Phase 1 Baseline)
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint returning basic service metadata."""
        return {
            "name": "ProofLens AI API",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "status": "online",
        }

    @app.get("/api/v1/auth-test", tags=["Security"], dependencies=[Depends(verify_access_passkey)])
    async def auth_test_endpoint():
        """Protected endpoint validating demo passkey gatekeeper functionality."""
        return {"authenticated": True, "message": "Passkey verified successfully."}

    return app


app = create_application()
