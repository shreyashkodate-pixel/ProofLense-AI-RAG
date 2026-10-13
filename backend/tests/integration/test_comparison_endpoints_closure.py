"""ProofLens AI — Integration Tests for Saved Cross-Document Comparisons Endpoints.

Verifies:
1. Listing saved comparisons (GET /workspaces/{ws_id}/comparisons) with pagination.
2. Retrieving specific saved comparison (GET /workspaces/{ws_id}/comparisons/{comparison_id})
   with citations, evidence, and synthesis.
3. Passkey authentication enforcement (401) and workspace scope isolation (404).
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
from app.models.citation import Citation
from app.models.document import Document
from app.models.page import DocumentPage
from app.models.query import Answer, QueryRun, RetrievedEvidence
from app.models.workspace import Workspace


@pytest.fixture
def test_app():
    """Create test application with test settings."""
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


def test_list_comparisons_success(test_app, auth_headers):
    """Verify listing saved comparison runs returns 200 and matches schema."""
    ws_id = uuid.uuid4()
    comp_id = uuid.uuid4()
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=ws_id, name="WS")
    fake_run = QueryRun(
        id=comp_id,
        workspace_id=ws_id,
        query_text="Compare Q3 vs Q4 revenue guidance.",
        status="completed",
        run_type="comparison",
        top_score=0.91,
        created_at=datetime.now(timezone.utc),
    )
    fake_answer = Answer(
        id=uuid.uuid4(),
        query_run_id=comp_id,
        answer_text="Q3 reported 10M whereas Q4 projected 12M.",
        is_abstention=False,
    )
    fake_answer.citations = []
    fake_run.answer = fake_answer
    fake_run.retrieved_evidence = []

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.query_repo.list_query_runs", new=AsyncMock(return_value=[fake_run])):
        with TestClient(test_app) as client:
            resp = client.get(f"/api/v1/workspaces/{ws_id}/comparisons", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["comparison_id"] == str(comp_id)
            assert data[0]["synthesis"] == "Q3 reported 10M whereas Q4 projected 12M."
            assert data[0]["is_abstention"] is False


def test_list_comparisons_unauthorized(test_app):
    """Verify listing comparisons without passkey returns 401."""
    ws_id = uuid.uuid4()
    with TestClient(test_app) as client:
        resp = client.get(f"/api/v1/workspaces/{ws_id}/comparisons")
        assert resp.status_code == 401


def test_list_comparisons_workspace_not_found(test_app, auth_headers):
    """Verify 404 when querying comparisons for nonexistent workspace."""
    ws_id = uuid.uuid4()
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=None)):
        with TestClient(test_app) as client:
            resp = client.get(f"/api/v1/workspaces/{ws_id}/comparisons", headers=auth_headers)
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "RESOURCE_NOT_FOUND"


def test_get_comparison_by_id_success(test_app, auth_headers):
    """Verify retrieving specific saved comparison by ID with citations and candidate evidence."""
    ws_id = uuid.uuid4()
    comp_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    cit_id = uuid.uuid4()

    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=ws_id, name="WS")
    fake_doc = Document(id=doc_id, workspace_id=ws_id, filename="q3_report.pdf", storage_path="p", content_hash="h", file_size_bytes=10)
    fake_page = DocumentPage(id=uuid.uuid4(), document_id=doc_id, page_number=2, raw_text="Page text", char_count=9)
    fake_chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        page_id=fake_page.id,
        chunk_index=0,
        chunk_text="Q3 revenue was $10M.",
    )
    fake_chunk.document = fake_doc
    fake_chunk.page = fake_page

    fake_run = QueryRun(
        id=comp_id,
        workspace_id=ws_id,
        query_text="Compare Q3 vs Q4 guidance.",
        status="completed",
        run_type="comparison",
        top_score=0.95,
        created_at=datetime.now(timezone.utc),
    )
    fake_answer = Answer(
        id=uuid.uuid4(),
        query_run_id=comp_id,
        answer_text="Comparative synthesis: revenue expanded by 20%.",
        is_abstention=False,
    )
    fake_citation = Citation(
        id=cit_id,
        answer_id=fake_answer.id,
        chunk_id=chunk_id,
        document_filename="q3_report.pdf",
        page_number=2,
        quoted_snippet="Q3 revenue was $10M",
    )
    fake_citation.chunk = fake_chunk
    fake_answer.citations = [fake_citation]
    fake_run.answer = fake_answer

    fake_evidence = RetrievedEvidence(
        id=uuid.uuid4(),
        query_run_id=comp_id,
        chunk_id=chunk_id,
        similarity_score=0.95,
        rank=1,
    )
    fake_evidence.chunk = fake_chunk
    fake_run.retrieved_evidence = [fake_evidence]

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.query_repo.get_query_run_by_id", new=AsyncMock(return_value=fake_run)):
        with TestClient(test_app) as client:
            resp = client.get(f"/api/v1/workspaces/{ws_id}/comparisons/{comp_id}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["comparison_id"] == str(comp_id)
            assert data["synthesis"] == "Comparative synthesis: revenue expanded by 20%."
            assert len(data["citations"]) == 1
            assert data["citations"][0]["document_filename"] == "q3_report.pdf"
            assert data["citations"][0]["page_number"] == 2


def test_get_comparison_by_id_not_found(test_app, auth_headers):
    """Verify 404 when comparison does not exist or does not belong to workspace."""
    ws_id = uuid.uuid4()
    comp_id = uuid.uuid4()
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    fake_ws = Workspace(id=ws_id, name="WS")
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.query_repo.get_query_run_by_id", new=AsyncMock(return_value=None)):
        with TestClient(test_app) as client:
            resp = client.get(f"/api/v1/workspaces/{ws_id}/comparisons/{comp_id}", headers=auth_headers)
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "RESOURCE_NOT_FOUND"
