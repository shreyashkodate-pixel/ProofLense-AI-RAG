"""ProofLens AI — Health & Readiness Probes.

Exposes unauthenticated probes for infrastructure orchestrators (Render/Docker)
verifying process liveness and database/pgvector readiness.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import check_db_connectivity, check_pgvector_extension, get_db
from app.core.errors import ErrorResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Unauthenticated process liveness probe."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Unauthenticated database and pgvector readiness probe.

    Returns HTTP 200 if database and pgvector extension are healthy.
    Returns HTTP 503 if database connectivity fails or pgvector is missing.
    """
    db_connected = await check_db_connectivity(db)
    if not db_connected:
        payload = ErrorResponse(
            error_code="SERVICE_UNAVAILABLE",
            message="Database connection failed.",
            details={"database": "disconnected", "pgvector": False},
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    pgvector_ready = await check_pgvector_extension(db)
    if not pgvector_ready:
        payload = ErrorResponse(
            error_code="SERVICE_UNAVAILABLE",
            message="Database pgvector extension is not installed or enabled.",
            details={"database": "connected", "pgvector": False},
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return {
        "status": "ready",
        "database": "connected",
        "pgvector": True,
    }
