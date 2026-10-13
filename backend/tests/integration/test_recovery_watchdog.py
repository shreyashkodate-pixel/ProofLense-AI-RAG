"""ProofLens AI — Integration Tests for Ingestion Recovery Watchdog.

Verifies periodic and on-demand recovery sweeping for stalled jobs.
"""

from unittest.mock import AsyncMock, patch
import pytest

from app.services.recovery.watchdog import RecoveryWatchdog


@pytest.mark.asyncio
async def test_recovery_watchdog_run_sweep():
    """Verify RecoveryWatchdog runs sweep and returns count of transitioned jobs."""
    mock_session = AsyncMock()
    mock_session_factory = MagicMock = lambda: AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

    with patch("app.services.recovery.watchdog.get_session_factory", return_value=mock_session_factory), \
         patch("app.services.recovery.watchdog.recover_stale_ingestion_jobs", new=AsyncMock(return_value=3)):
        recovered = await RecoveryWatchdog.run_sweep(timeout_seconds=600)
        assert recovered == 3


@pytest.mark.asyncio
async def test_recovery_watchdog_handles_error():
    """Verify RecoveryWatchdog logs error and returns 0 when database error occurs."""
    mock_session = AsyncMock()
    mock_session_factory = lambda: AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock())

    with patch("app.services.recovery.watchdog.get_session_factory", return_value=mock_session_factory), \
         patch("app.services.recovery.watchdog.recover_stale_ingestion_jobs", side_effect=Exception("DB Error")):
        recovered = await RecoveryWatchdog.run_sweep(timeout_seconds=600)
        assert recovered == 0
