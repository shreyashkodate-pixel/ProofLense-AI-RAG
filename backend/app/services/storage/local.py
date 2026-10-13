"""ProofLens AI — Local Filesystem Storage Service.

Implements storage abstraction on local disk with directory traversal protection.
"""

from pathlib import Path
from app.core.logging import logger
from app.services.storage.base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """Local filesystem storage driver for development and offline testing."""

    def __init__(self, base_dir: str = "./data/uploads") -> None:
        self.base_path = Path(base_dir).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it remains safely within base_path."""
        clean_rel = relative_path.lstrip("/\\")
        target_path = (self.base_path / clean_rel).resolve()
        if not target_path.is_relative_to(self.base_path):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target_path

    async def save_file(self, relative_path: str, content: bytes) -> str:
        """Save file bytes safely to disk."""
        target_path = self._resolve_safe_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        # Return path relative to base directory
        return str(target_path.relative_to(self.base_path)).replace("\\", "/")

    async def get_file(self, relative_path: str) -> bytes:
        """Read file bytes from disk."""
        target_path = self._resolve_safe_path(relative_path)
        if not target_path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target_path.read_bytes()

    async def delete_file(self, relative_path: str) -> bool:
        """Delete file from disk idempotently."""
        try:
            target_path = self._resolve_safe_path(relative_path)
            if target_path.is_file():
                target_path.unlink()
                logger.info(f"Deleted physical file: {relative_path}")
            return True
        except Exception as exc:
            logger.warning(f"Failed to delete physical file {relative_path}: {exc}")
            return False

    async def file_exists(self, relative_path: str) -> bool:
        """Check if file exists on disk."""
        target_path = self._resolve_safe_path(relative_path)
        return target_path.is_file()
