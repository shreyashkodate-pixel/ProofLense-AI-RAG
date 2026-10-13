"""ProofLens AI — Storage Service Factory.

Provides singleton access to the configured storage service driver.
"""

from functools import lru_cache
from app.core.config import Settings, get_settings
from app.services.storage.base import BaseStorageService
from app.services.storage.local import LocalStorageService


@lru_cache
def get_storage_service() -> BaseStorageService:
    """Return storage service based on application configuration."""
    settings: Settings = get_settings()
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageService(base_dir=settings.LOCAL_STORAGE_DIR)
    else:
        # Fallback to local or throw if cloud driver not yet configured
        return LocalStorageService(base_dir=settings.LOCAL_STORAGE_DIR)
