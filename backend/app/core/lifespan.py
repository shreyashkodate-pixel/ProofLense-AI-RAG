"""ProofLens AI — Lifespan Database Verification & Recovery Watchdog.

Performs startup vector dimension compatibility validation and recovers
interrupted/stale document ingestion jobs per TECHNICAL-DESIGN.md Section 2.3 & 4.2.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import logger


class VectorDimensionMismatchError(RuntimeError):
    """Raised when database vector column dimension does not match application settings."""
    pass


async def verify_vector_dimension_compatibility(
    session: AsyncSession,
    expected_dim: int,
) -> bool:
    """Verify that document_chunks.embedding dimension matches EMBEDDING_DIMENSIONS.

    Queries PostgreSQL system catalog pg_attribute. If the table does not exist yet,
    returns False without raising an error. If the column exists with a mismatched dimension,
    raises VectorDimensionMismatchError immediately.
    """
    check_table_sql = text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'document_chunks'
        );
    """)
    table_exists = (await session.execute(check_table_sql)).scalar()
    if not table_exists:
        logger.warning(
            "document_chunks table does not exist yet. Ensure migrations are applied."
        )
        return False

    dim_query = text("""
        SELECT atttypmod 
        FROM pg_attribute 
        WHERE attrelid = 'document_chunks'::regclass 
          AND attname = 'embedding';
    """)
    result = await session.execute(dim_query)
    actual_dim = result.scalar()

    if actual_dim is None:
        logger.warning("document_chunks.embedding column not found or untyped.")
        return False

    # In pgvector, atttypmod directly represents the dimension integer
    if actual_dim != expected_dim:
        error_msg = (
            f"FATAL: Database vector column dimension ({actual_dim}) does not match "
            f"EMBEDDING_DIMENSIONS ({expected_dim}). Run migration before starting."
        )
        logger.critical(error_msg)
        raise VectorDimensionMismatchError(error_msg)

    logger.info(
        f"Verified vector schema compatibility: document_chunks.embedding is dimension {actual_dim}."
    )
    return True


async def recover_stale_ingestion_jobs(
    session: AsyncSession,
    timeout_seconds: int,
) -> int:
    """Watchdog transitioning stale 'processing' jobs to 'failed' state.

    Only updates records where processing_started_at is older than the timeout window.
    """
    check_table_sql = text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'documents'
        );
    """)
    table_exists = (await session.execute(check_table_sql)).scalar()
    if not table_exists:
        return 0

    recover_sql = text("""
        UPDATE documents 
        SET status = 'failed', 
            error_message = 'Processing timed out or was interrupted by a server restart. Please retry.'
        WHERE status = 'processing' 
          AND processing_started_at < NOW() - (INTERVAL '1 second' * :timeout_seconds)
        RETURNING id;
    """)
    result = await session.execute(recover_sql, {"timeout_seconds": timeout_seconds})
    recovered_ids = result.fetchall()
    count = len(recovered_ids)
    if count > 0:
        logger.warning(
            f"Lifespan watchdog recovered {count} stale/interrupted document processing jobs."
        )
        await session.commit()
    return count
