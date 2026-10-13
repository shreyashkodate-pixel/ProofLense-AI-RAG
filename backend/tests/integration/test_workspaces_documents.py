"""ProofLens AI — Integration Tests for Workspaces & Document Ingestion APIs.

Verifies passkey gatekeeper enforcement, workspace scope isolation, streaming size limits,
magic byte validation, duplicate detection, atomic worker claiming, and safe deletion.
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_application
from app.models.document import Document
from app.models.workspace import Workspace
from app.services.storage.factory import get_storage_service


@pytest.fixture
def test_app():
    """Create test application with test settings and dependency overrides."""
    settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        MAX_UPLOAD_FILE_SIZE_BYTES=10_485_760,  # 10 MB
        MAX_UPLOAD_FILES_PER_BATCH=5,
    )
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def auth_headers():
    return {"X-Workspace-Key": "test-passkey-secret-123456"}


# ------------------------------------------------------------------------------
# 1. Access Passkey Gatekeeper Tests
# ------------------------------------------------------------------------------

def test_endpoints_require_passkey(test_app):
    """Verify workspace and document endpoints return 401 when X-Workspace-Key is missing."""
    with TestClient(test_app) as client:
        # Workspaces endpoints
        assert client.post("/api/v1/workspaces", json={"name": "Test"}).status_code == 401
        assert client.get("/api/v1/workspaces").status_code == 401

        # Documents endpoint
        ws_id = uuid.uuid4()
        assert client.get(f"/api/v1/workspaces/{ws_id}/documents").status_code == 401


# ------------------------------------------------------------------------------
# 2. Workspace CRUD Tests
# ------------------------------------------------------------------------------

def test_create_and_list_workspaces(test_app, auth_headers):
    """Verify workspace creation and listing."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(
        id=uuid.uuid4(),
        name="Research Team Workspace",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.repositories.workspace_repo.create_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.workspace_repo.list_workspaces", new=AsyncMock(return_value=[fake_ws])):
        with TestClient(test_app) as client:
            # Create workspace
            res = client.post(
                "/api/v1/workspaces",
                json={"name": "Research Team Workspace"},
                headers=auth_headers,
            )
            assert res.status_code == 201
            assert res.json()["name"] == "Research Team Workspace"
            assert res.json()["id"] == str(fake_ws.id)

            # List workspaces
            list_res = client.get("/api/v1/workspaces", headers=auth_headers)
            assert list_res.status_code == 200
            assert len(list_res.json()) == 1


def test_get_workspace_not_found(test_app, auth_headers):
    """Verify 404 when querying non-existent workspace."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=None)):
        with TestClient(test_app) as client:
            res = client.get(f"/api/v1/workspaces/{uuid.uuid4()}", headers=auth_headers)
            assert res.status_code == 404
            assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


# ------------------------------------------------------------------------------
# 3. Secure Streaming PDF Uploads & Validation Tests
# ------------------------------------------------------------------------------

def test_upload_rejects_non_pdf_magic_bytes(test_app, auth_headers):
    """Verify rejection of non-PDF files missing %PDF- header."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=uuid.uuid4(), name="WS")
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)):
        with TestClient(test_app) as client:
            # Fake text file pretending to be PDF
            fake_file = io.BytesIO(b"Plain text content without PDF signature")
            files = [("files", ("fake.pdf", fake_file, "application/pdf"))]

            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert res.status_code == 400
            assert res.json()["error_code"] == "INVALID_PDF_SIGNATURE"


def test_upload_enforces_size_limit(test_app, auth_headers):
    """Verify upload aborts with HTTP 413 when file size exceeds MAX_UPLOAD_FILE_SIZE_BYTES."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    # Configure a tiny 500-byte limit for testing
    tight_settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        MAX_UPLOAD_FILE_SIZE_BYTES=500,
    )
    test_app.state.settings = tight_settings
    test_app.dependency_overrides[get_settings] = lambda: tight_settings

    fake_ws = Workspace(id=uuid.uuid4(), name="WS")
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)):
        with TestClient(test_app) as client:
            # 1000 bytes exceeds 500 byte limit
            large_content = b"%PDF-" + b"A" * 1000
            files = [("files", ("large.pdf", io.BytesIO(large_content), "application/pdf"))]

            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert res.status_code == 413
            assert res.json()["error_code"] == "FILE_TOO_LARGE"


def test_upload_enforces_batch_file_count_limit(test_app, auth_headers):
    """Verify batch limit rejects uploads with more than MAX_UPLOAD_FILES_PER_BATCH files."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=uuid.uuid4(), name="WS")
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)):
        with TestClient(test_app) as client:
            # 6 files exceeds default limit of 5
            files = [
                ("files", (f"file_{i}.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf"))
                for i in range(6)
            ]
            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert res.status_code == 400
            assert res.json()["error_code"] == "BATCH_LIMIT_EXCEEDED"


def test_upload_detects_existing_duplicate_hash(test_app, auth_headers):
    """Verify duplicate upload returns HTTP 409 DUPLICATE_DOCUMENT."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=uuid.uuid4(), name="WS")
    existing_doc = Document(
        id=uuid.uuid4(),
        workspace_id=fake_ws.id,
        filename="existing.pdf",
        content_hash="some-hash",
        file_size_bytes=100,
        storage_path="path.pdf",
        status="ready",
    )

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.document_repo.get_document_by_hash", new=AsyncMock(return_value=existing_doc)):
        with TestClient(test_app) as client:
            files = [("files", ("duplicate.pdf", io.BytesIO(b"%PDF-1.4 test content"), "application/pdf"))]
            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert res.status_code == 409
            assert res.json()["error_code"] == "DUPLICATE_DOCUMENT"


def test_upload_success(test_app, auth_headers):
    """Verify successful upload persists physical file and creates document record."""
    mock_db = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.save_file.return_value = "workspaces/ws-id/doc_file.pdf"

    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_storage_service] = lambda: mock_storage

    fake_ws = Workspace(id=uuid.uuid4(), name="WS")
    created_doc = Document(
        id=uuid.uuid4(),
        workspace_id=fake_ws.id,
        filename="report.pdf",
        content_hash="abc123hash",
        file_size_bytes=50,
        storage_path="workspaces/ws-id/doc_file.pdf",
        status="pending",
        processing_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.document_repo.get_document_by_hash", new=AsyncMock(return_value=None)), \
         patch("app.repositories.document_repo.create_document", new=AsyncMock(return_value=created_doc)):
        with TestClient(test_app) as client:
            files = [("files", ("report.pdf", io.BytesIO(b"%PDF-1.4 valid content"), "application/pdf"))]
            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert res.status_code == 201
            data = res.json()
            assert data["total_uploaded"] == 1
            assert data["uploaded"][0]["filename"] == "report.pdf"
            assert data["uploaded"][0]["status"] == "pending"


# ------------------------------------------------------------------------------
# 4. Scope Isolation, Safe Deletion & Retry Tests
# ------------------------------------------------------------------------------

def test_cross_workspace_isolation_returns_404(test_app, auth_headers):
    """Verify accessing a document using mismatched workspace ID returns 404, not 403."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=None)):
        with TestClient(test_app) as client:
            res = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}",
                headers=auth_headers,
            )
            assert res.status_code == 404
            assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


def test_safe_two_step_deletion(test_app, auth_headers):
    """Verify safe deletion locks row, commits DB deletion, and purges physical file."""
    mock_db = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.delete_file.return_value = True

    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_storage_service] = lambda: mock_storage

    fake_doc = Document(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        filename="del.pdf",
        content_hash="hash",
        file_size_bytes=10,
        storage_path="workspaces/path/del.pdf",
        status="ready",
    )

    with patch("app.repositories.document_repo.lock_document_for_deletion", new=AsyncMock(return_value=fake_doc)), \
         patch("app.repositories.document_repo.delete_document", new=AsyncMock()):
        with TestClient(test_app) as client:
            res = client.delete(
                f"/api/v1/workspaces/{fake_doc.workspace_id}/documents/{fake_doc.id}",
                headers=auth_headers,
            )
            assert res.status_code == 204
            mock_storage.delete_file.assert_awaited_once_with("workspaces/path/del.pdf")


def test_retry_non_failed_document_rejected(test_app, auth_headers):
    """Verify retry is rejected when document is not in 'failed' status."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    doc = Document(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        filename="active.pdf",
        content_hash="hash",
        file_size_bytes=10,
        storage_path="path.pdf",
        status="processing",  # Not failed!
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=doc)):
        with TestClient(test_app) as client:
            res = client.post(
                f"/api/v1/workspaces/{doc.workspace_id}/documents/{doc.id}/retry",
                headers=auth_headers,
            )
            assert res.status_code == 400
            assert res.json()["error_code"] == "DOCUMENT_NOT_FAILED"


def test_retry_failed_document_atomic_claim(test_app, auth_headers):
    """Verify retry atomically claims failed document transitioning it to processing."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    failed_doc = Document(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        filename="failed.pdf",
        content_hash="hash",
        file_size_bytes=10,
        storage_path="path.pdf",
        status="failed",
    )

    claimed_doc = Document(
        id=failed_doc.id,
        workspace_id=failed_doc.workspace_id,
        filename="failed.pdf",
        content_hash="hash",
        file_size_bytes=10,
        storage_path="path.pdf",
        status="processing",
        processing_attempts=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=failed_doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)):
        with TestClient(test_app) as client:
            res = client.post(
                f"/api/v1/workspaces/{failed_doc.workspace_id}/documents/{failed_doc.id}/retry",
                headers=auth_headers,
            )
            assert res.status_code == 200
            assert res.json()["status"] == "processing"
            assert res.json()["processing_attempts"] == 1
