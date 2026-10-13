"""ProofLens AI — Recovery Watchdog Service.

Sweeps for timed-out or interrupted background ingestion tasks.
"""

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.lifespan import recover_stale_ingestion_jobs
from app.core.logging import logger


class RecoveryWatchdog:
    """Service sweeping and recovering stalled ingestion jobs."""

    @staticmethod
    async def run_sweep(timeout_seconds: int = None) -> int:
        """Execute a database sweep recovering interrupted jobs."""
        settings = get_settings()
        timeout = timeout_seconds or settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                recovered_count = await recover_stale_ingestion_jobs(session, timeout)
                return recovered_count
            except Exception as exc:
                logger.error(f"Error during watchdog recovery sweep: {exc}")
                return 0
