"""ProofLens AI — Unit Tests for Local Storage Driver.

Verifies path traversal defense, file persistence, retrieval, and idempotent deletions.
"""

import tempfile
import pytest
from pathlib import Path

from app.services.storage.local import LocalStorageService


@pytest.fixture
def temp_storage():
    """Create a temporary directory for local storage testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield LocalStorageService(base_dir=temp_dir)


@pytest.mark.asyncio
async def test_save_and_get_file(temp_storage: LocalStorageService):
    """Verify saving file bytes and retrieving them intact."""
    content = b"%PDF-1.4 test dummy pdf content"
    rel_path = "workspaces/ws-1/doc-1_sample.pdf"

    saved_path = await temp_storage.save_file(rel_path, content)
    assert saved_path == "workspaces/ws-1/doc-1_sample.pdf"
    assert await temp_storage.file_exists(saved_path) is True

    retrieved = await temp_storage.get_file(saved_path)
    assert retrieved == content


@pytest.mark.asyncio
async def test_idempotent_delete_file(temp_storage: LocalStorageService):
    """Verify deleting a file removes it and subsequent deletion does not raise error."""
    content = b"%PDF-1.4 test dummy pdf content"
    rel_path = "workspaces/ws-1/doc-to-delete.pdf"

    saved_path = await temp_storage.save_file(rel_path, content)
    assert await temp_storage.file_exists(saved_path) is True

    # First delete
    assert await temp_storage.delete_file(saved_path) is True
    assert await temp_storage.file_exists(saved_path) is False

    # Second delete (idempotent)
    assert await temp_storage.delete_file(saved_path) is True


@pytest.mark.asyncio
async def test_path_traversal_prevention(temp_storage: LocalStorageService):
    """Verify path traversal attacks attempting to escape storage base_dir are rejected."""
    malicious_path = "../../../etc/passwd"

    with pytest.raises(ValueError) as exc_info:
        await temp_storage.save_file(malicious_path, b"malicious")

    assert "Path traversal detected" in str(exc_info.value)
