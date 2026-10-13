"""ProofLens AI — Supabase Cloud Object Storage Driver.

Implements storage abstraction on Supabase Storage REST API with secure headers,
idempotent upload, and proper error handling.
"""

from typing import Optional
import httpx
from app.core.logging import logger
from app.services.storage.base import BaseStorageService


class SupabaseStorageService(BaseStorageService):
    """Supabase Cloud Object Storage driver for production environments."""

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        bucket_name: str = "prooflens-documents",
        timeout: float = 30.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key.strip()
        self.bucket_name = bucket_name.strip()
        self.timeout = timeout
        self.base_api_url = f"{self.supabase_url}/storage/v1"

    def _headers(self, content_type: Optional[str] = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apiKey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _clean_path(self, relative_path: str) -> str:
        clean = relative_path.lstrip("/\\").replace("\\", "/")
        if ".." in clean.split("/"):
            raise ValueError(f"Path traversal detected in storage path: {relative_path}")
        return clean

    async def save_file(self, relative_path: str, content: bytes) -> str:
        """Upload file bytes to Supabase Storage bucket with upsert semantics."""
        path = self._clean_path(relative_path)
        url = f"{self.base_api_url}/object/{self.bucket_name}/{path}"
        headers = self._headers(content_type="application/pdf")
        headers["x-upsert"] = "true"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, content=content, headers=headers)
                if response.status_code not in (200, 201):
                    raise RuntimeError(
                        f"Supabase Storage upload failed with status {response.status_code}: {response.text}"
                    )
                logger.info(f"Successfully saved file to Supabase Storage: {path}")
                return path
            except httpx.RequestError as exc:
                logger.error(f"Network error uploading to Supabase Storage: {exc}")
                raise RuntimeError(f"Storage network failure: {exc}") from exc

    async def get_file(self, relative_path: str) -> bytes:
        """Download file bytes from Supabase Storage bucket."""
        path = self._clean_path(relative_path)
        url = f"{self.base_api_url}/object/authenticated/{self.bucket_name}/{path}"
        headers = self._headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    raise FileNotFoundError(f"File not found in Supabase Storage: {relative_path}")
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Supabase Storage download failed with status {response.status_code}: {response.text}"
                    )
                return response.content
            except httpx.RequestError as exc:
                logger.error(f"Network error downloading from Supabase Storage: {exc}")
                raise RuntimeError(f"Storage network failure: {exc}") from exc

    async def delete_file(self, relative_path: str) -> bool:
        """Delete file from Supabase Storage bucket idempotently."""
        path = self._clean_path(relative_path)
        url = f"{self.base_api_url}/object/{self.bucket_name}/{path}"
        headers = self._headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(url, headers=headers)
                if response.status_code in (200, 204, 404):
                    logger.info(f"Deleted file from Supabase Storage: {path}")
                    return True
                logger.warning(
                    f"Unexpected status deleting from Supabase Storage ({response.status_code}): {response.text}"
                )
                return False
            except Exception as exc:
                logger.warning(f"Failed to delete file from Supabase Storage {relative_path}: {exc}")
                return False

    async def file_exists(self, relative_path: str) -> bool:
        """Check if file exists in Supabase Storage bucket."""
        path = self._clean_path(relative_path)
        url = f"{self.base_api_url}/object/authenticated/{self.bucket_name}/{path}"
        headers = self._headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.head(url, headers=headers)
                return response.status_code == 200
            except Exception:
                return False
