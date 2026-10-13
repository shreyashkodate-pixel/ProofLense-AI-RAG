"""ProofLens AI — Integration Tests for Schema Compatibility & Startup Watchdog.

Verifies that vector dimension mismatches are caught immediately and that
stale background jobs are recovered without crashing.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.lifespan import (
    VectorDimensionMismatchError,
    recover_stale_ingestion_jobs,
    verify_vector_dimension_compatibility,
)


@pytest.mark.asyncio
async def test_dimension_compatibility_matching():
    """Verify startup validation succeeds when database vector column matches EMBEDDING_DIMENSIONS."""
    mock_session = AsyncMock()

    # 1. Table exists -> True
    # 2. Vector dimension -> 768
    mock_session.execute.side_effect = [
        MagicMock(scalar=lambda: True),
        MagicMock(scalar=lambda: 768),
    ]

    is_compatible = await verify_vector_dimension_compatibility(
        mock_session,
        expected_dim=768,
    )
    assert is_compatible is True


@pytest.mark.asyncio
async def test_dimension_compatibility_mismatch_raises_error():
    """Verify startup validation raises fatal error when database vector dimension does not match."""
    mock_session = AsyncMock()

    # 1. Table exists -> True
    # 2. Vector dimension -> 1536 (mismatched with expected 768)
    mock_session.execute.side_effect = [
        MagicMock(scalar=lambda: True),
        MagicMock(scalar=lambda: 1536),
    ]

    with pytest.raises(VectorDimensionMismatchError) as exc_info:
        await verify_vector_dimension_compatibility(mock_session, expected_dim=768)

    assert "FATAL: Database vector column dimension (1536) does not match EMBEDDING_DIMENSIONS (768)" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dimension_compatibility_table_missing():
    """Verify check handles missing table gracefully without crashing."""
    mock_session = AsyncMock()
    # Table does not exist -> False
    mock_session.execute.return_value = MagicMock(scalar=lambda: False)

    is_compatible = await verify_vector_dimension_compatibility(mock_session, expected_dim=768)
    assert is_compatible is False


@pytest.mark.asyncio
async def test_recover_stale_ingestion_jobs():
    """Verify recovery watchdog transitions stale jobs and returns affected count."""
    mock_session = AsyncMock()

    # 1. Table exists -> True
    # 2. Update query returns 2 recovered rows
    mock_session.execute.side_effect = [
        MagicMock(scalar=lambda: True),
        MagicMock(fetchall=lambda: [("uuid-1",), ("uuid-2",)]),
    ]

    count = await recover_stale_ingestion_jobs(mock_session, timeout_seconds=600)
    assert count == 2
    mock_session.commit.assert_awaited_once()
