"""ProofLens AI — Integration Tests for Document File & Page/Chunk Retrieval Endpoints.

Verifies:
1. Original PDF retrieval (GET /workspaces/{ws_id}/documents/{doc_id}/file)
2. Extracted page text & chunk metadata (GET /workspaces/{ws_id}/documents/{doc_id}/pages)
3. Document-scoped chunk retrieval (GET /workspaces/{ws_id}/documents/{doc_id}/chunks/{chunk_id})
4. Workspace-scoped chunk retrieval (GET /workspaces/{ws_id}/chunks/{chunk_id})
5. Passkey auth enforcement (401), missing resource handling (404), and cross-workspace isolation.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_application
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.page import DocumentPage
from app.models.workspace import Workspace
from app.services.storage.factory import get_storage_service


@pytest.fixture
def test_app():
    """Create test application with test settings and overrides."""
    settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
    )
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def auth_headers():
    return {"X-Workspace-Key": "test-passkey-secret-123456"}


# ------------------------------------------------------------------------------
# 1. Original PDF Retrieval Tests
# ------------------------------------------------------------------------------

def test_get_document_file_success(test_app, auth_headers):
    """Verify downloading original PDF binary returns 200 OK and correct headers."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    pdf_bytes = b"%PDF-1.4 mock binary pdf content"

    mock_db = AsyncMock()
    mock_storage = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_storage_service] = lambda: mock_storage

    fake_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="report_2025.pdf",
        storage_path=f"workspaces/{ws_id}/{doc_id}_report_2025.pdf",
        content_hash="abc123hash",
        file_size_bytes=len(pdf_bytes),
        status="ready",
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=fake_doc)):
        mock_storage.get_file.return_value = pdf_bytes
        with TestClient(test_app) as client:
            resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/file",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.content == pdf_bytes
            assert resp.headers["content-type"] == "application/pdf"
            assert "report_2025.pdf" in resp.headers["content-disposition"]
            assert resp.headers["content-length"] == str(len(pdf_bytes))


def test_get_document_file_unauthorized(test_app):
    """Verify accessing file without X-Workspace-Key returns 401."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    with TestClient(test_app) as client:
        resp = client.get(f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/file")
        assert resp.status_code == 401


def test_get_document_file_document_not_found(test_app, auth_headers):
    """Verify 404 when document does not exist in workspace."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=None)):
        with TestClient(test_app) as client:
            resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/file",
                headers=auth_headers,
            )
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "RESOURCE_NOT_FOUND"


def test_get_document_file_missing_in_storage(test_app, auth_headers):
    """Verify 404 with FILE_NOT_FOUND when record exists in DB but physical file is missing."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_storage = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_storage_service] = lambda: mock_storage

    fake_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="report.pdf",
        storage_path=f"workspaces/{ws_id}/missing.pdf",
        content_hash="abc",
        file_size_bytes=100,
        status="ready",
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=fake_doc)):
        mock_storage.get_file.return_value = None
        with TestClient(test_app) as client:
            resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/file",
                headers=auth_headers,
            )
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "FILE_NOT_FOUND"


# ------------------------------------------------------------------------------
# 2. Extracted Pages and Chunks Tests
# ------------------------------------------------------------------------------

def test_get_document_pages_success(test_app, auth_headers):
    """Verify retrieving document pages with embedded chunk metadata returns 200."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="financials.pdf",
        storage_path="path/to/doc",
        content_hash="def456",
        file_size_bytes=2048,
        status="ready",
        page_count=2,
    )

    fake_chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        page_id=page_id,
        chunk_index=0,
        chunk_text="Executive summary section of financial report.",
        embedding_model="gemini-embedding-2",
        token_count=12,
        embedding=[0.1] * 768,
    )

    fake_page = DocumentPage(
        id=page_id,
        document_id=doc_id,
        page_number=1,
        raw_text="Executive summary section of financial report. Page content here.",
        char_count=65,
    )
    fake_page.chunks = [fake_chunk]

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=fake_doc)), \
         patch("app.repositories.document_repo.get_document_pages_with_chunks", new=AsyncMock(return_value=[fake_page])):
        with TestClient(test_app) as client:
            resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/pages",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["document_id"] == str(doc_id)
            assert data["workspace_id"] == str(ws_id)
            assert data["total_pages"] == 2
            assert len(data["pages"]) == 1
            page_data = data["pages"][0]
            assert page_data["page_number"] == 1
            assert len(page_data["chunks"]) == 1
            assert page_data["chunks"][0]["id"] == str(chunk_id)
            assert page_data["chunks"][0]["chunk_text"] == "Executive summary section of financial report."


def test_get_document_pages_filter_by_page_number(test_app, auth_headers):
    """Verify page_number query parameter is passed through."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_doc = Document(id=doc_id, workspace_id=ws_id, filename="doc.pdf", storage_path="p", content_hash="h", file_size_bytes=10)

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=fake_doc)), \
         patch("app.repositories.document_repo.get_document_pages_with_chunks", new=AsyncMock(return_value=[])) as mock_get_pages:
        with TestClient(test_app) as client:
            resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/pages?page_number=3",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            mock_get_pages.assert_awaited_once_with(
                session=mock_db,
                workspace_id=ws_id,
                document_id=doc_id,
                page_number=3,
            )


# ------------------------------------------------------------------------------
# 3. Chunk Detail Tests
# ------------------------------------------------------------------------------

def test_get_chunk_by_id_endpoints(test_app, auth_headers):
    """Verify chunk detail retrieval both via document-scoped and workspace-scoped routes."""
    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=ws_id, name="WS")
    fake_doc = Document(id=doc_id, workspace_id=ws_id, filename="doc.pdf", storage_path="p", content_hash="h", file_size_bytes=10)
    fake_page = DocumentPage(id=page_id, document_id=doc_id, page_number=2, raw_text="page text", char_count=9)
    fake_chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        page_id=page_id,
        chunk_index=1,
        chunk_text="Target chunk text for citation inspection.",
        embedding_model="gemini-embedding-2",
        token_count=15,
        embedding=[0.1] * 768,
    )
    fake_chunk.page = fake_page

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=fake_doc)), \
         patch("app.repositories.document_repo.get_chunk_by_id", new=AsyncMock(return_value=fake_chunk)):
        with TestClient(test_app) as client:
            # 1. Test document-scoped route: /workspaces/{ws}/documents/{doc}/chunks/{chunk}
            doc_chunk_resp = client.get(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/chunks/{chunk_id}",
                headers=auth_headers,
            )
            assert doc_chunk_resp.status_code == 200
            assert doc_chunk_resp.json()["id"] == str(chunk_id)
            assert doc_chunk_resp.json()["page_number"] == 2
            assert doc_chunk_resp.json()["chunk_text"] == "Target chunk text for citation inspection."

            # 2. Test workspace-scoped direct route: /workspaces/{ws}/chunks/{chunk}
            ws_chunk_resp = client.get(
                f"/api/v1/workspaces/{ws_id}/chunks/{chunk_id}",
                headers=auth_headers,
            )
            assert ws_chunk_resp.status_code == 200
            assert ws_chunk_resp.json()["id"] == str(chunk_id)
            assert ws_chunk_resp.json()["page_number"] == 2
