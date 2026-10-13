"""ProofLens AI — Unit Tests for Supabase Cloud Storage Driver.

Verifies path traversal defense, file persistence via Supabase REST API,
download streaming, existence probing, and error handling.
"""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.services.storage.supabase import SupabaseStorageService


@pytest.fixture
def supabase_storage():
    """Create SupabaseStorageService instance with test configuration."""
    return SupabaseStorageService(
        supabase_url="https://xyzproject.supabase.co",
        service_role_key="sb-secret-key-test-token",
        bucket_name="prooflens-documents",
    )


@pytest.mark.asyncio
async def test_supabase_save_and_get_file(supabase_storage: SupabaseStorageService):
    """Verify uploading and downloading file bytes via Supabase Storage REST API."""
    content = b"%PDF-1.4 test document binary bytes"
    rel_path = "workspaces/ws-test-1/doc-1_sample.pdf"

    mock_post_resp = httpx.Response(status_code=200, json={"Key": f"prooflens-documents/{rel_path}"})
    mock_get_resp = httpx.Response(status_code=200, content=content)

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_post_resp)) as mock_post, \
         patch.object(httpx.AsyncClient, "get", new=AsyncMock(return_value=mock_get_resp)) as mock_get:

        saved_path = await supabase_storage.save_file(rel_path, content)
        assert saved_path == rel_path
        mock_post.assert_awaited_once()

        downloaded_bytes = await supabase_storage.get_file(saved_path)
        assert downloaded_bytes == content
        mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_supabase_file_exists(supabase_storage: SupabaseStorageService):
    """Verify file_exists handles 200 OK as True and 404 Not Found as False."""
    rel_path = "workspaces/ws-test-1/doc-exists.pdf"

    # Test file exists (200)
    mock_head_200 = httpx.Response(status_code=200)
    with patch.object(httpx.AsyncClient, "head", new=AsyncMock(return_value=mock_head_200)):
        assert await supabase_storage.file_exists(rel_path) is True

    # Test file does not exist (404)
    mock_head_404 = httpx.Response(status_code=404)
    with patch.object(httpx.AsyncClient, "head", new=AsyncMock(return_value=mock_head_404)):
        assert await supabase_storage.file_exists(rel_path) is False


@pytest.mark.asyncio
async def test_supabase_delete_file(supabase_storage: SupabaseStorageService):
    """Verify delete_file issues DELETE request and returns True on success."""
    rel_path = "workspaces/ws-test-1/doc-delete.pdf"

    mock_delete_resp = httpx.Response(status_code=200, json={"message": "Successfully deleted"})
    with patch.object(httpx.AsyncClient, "delete", new=AsyncMock(return_value=mock_delete_resp)) as mock_delete:
        deleted = await supabase_storage.delete_file(rel_path)
        assert deleted is True
        mock_delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_supabase_path_traversal_prevention(supabase_storage: SupabaseStorageService):
    """Verify path traversal attacks attempting directory escape are rejected with ValueError."""
    malicious_path = "../../../etc/shadow"

    with pytest.raises(ValueError) as exc_info:
        await supabase_storage.save_file(malicious_path, b"evil")

    assert "Path traversal detected" in str(exc_info.value)

    with pytest.raises(ValueError):
        await supabase_storage.get_file(malicious_path)

    with pytest.raises(ValueError):
        await supabase_storage.delete_file(malicious_path)


@pytest.mark.asyncio
async def test_supabase_upload_error_handling(supabase_storage: SupabaseStorageService):
    """Verify non-200/201 response during upload raises RuntimeError."""
    mock_err_resp = httpx.Response(status_code=500, text="Internal Server Error")
    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_err_resp)):
        with pytest.raises(RuntimeError) as exc_info:
            await supabase_storage.save_file("test/doc.pdf", b"data")
        assert "Supabase Storage upload failed" in str(exc_info.value)
