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
    if settings.STORAGE_BACKEND == "supabase" and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        from app.services.storage.supabase import SupabaseStorageService
        return SupabaseStorageService(
            supabase_url=settings.SUPABASE_URL,
            service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
            bucket_name=settings.SUPABASE_STORAGE_BUCKET,
        )
    return LocalStorageService(base_dir=settings.LOCAL_STORAGE_DIR)
