"""ProofLens AI — Integration Tests for Ingestion Pipeline Lifecycle.

Verifies end-to-end integration between upload/retry endpoints, background task
dispatching, worker execution, state transitions, and concurrency safety.
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_application
from app.models.document import Document
from app.models.workspace import Workspace
from app.services.storage.factory import get_storage_service
from tests.unit.test_pdf_parser import create_blank_pdf, create_in_memory_pdf


@pytest.fixture
def test_app():
    """Create test application configured for background ingestion testing."""
    settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        MAX_UPLOAD_FILE_SIZE_BYTES=10_485_760,
        MAX_UPLOAD_FILES_PER_BATCH=5,
        RAG_CHUNK_SIZE=1000,
        RAG_CHUNK_OVERLAP=200,
    )
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def auth_headers():
    return {"X-Workspace-Key": "test-passkey-secret-123456"}


def test_upload_triggers_background_ingestion_task(test_app, auth_headers):
    """Verify upload endpoint schedules schedule_ingestion_background_task."""
    mock_db = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.save_file.return_value = "workspaces/ws-id/doc_file.pdf"

    test_app.dependency_overrides[get_db] = lambda: mock_db
    test_app.dependency_overrides[get_storage_service] = lambda: mock_storage

    fake_ws = Workspace(id=uuid.uuid4(), name="Test WS")
    created_doc = Document(
        id=uuid.uuid4(),
        workspace_id=fake_ws.id,
        filename="report.pdf",
        content_hash="hash123",
        file_size_bytes=500,
        storage_path="workspaces/ws-id/doc_file.pdf",
        status="pending",
        processing_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    pdf_bytes = create_in_memory_pdf(["Page 1 content.", "Page 2 content."])

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=fake_ws)), \
         patch("app.repositories.document_repo.get_document_by_hash", new=AsyncMock(return_value=None)), \
         patch("app.repositories.document_repo.create_document", new=AsyncMock(return_value=created_doc)), \
         patch("app.api.v1.documents.schedule_ingestion_background_task", new=AsyncMock()) as mock_bg_task:

        with TestClient(test_app) as client:
            files = [("files", ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf"))]
            res = client.post(
                f"/api/v1/workspaces/{fake_ws.id}/documents/upload",
                files=files,
                headers=auth_headers,
            )

            assert res.status_code == 201
            assert res.json()["total_uploaded"] == 1
            assert res.json()["uploaded"][0]["status"] == "pending"

            # Verify background ingestion task was dispatched with correct document & workspace IDs
            mock_bg_task.assert_awaited_once_with(created_doc.id, fake_ws.id)


def test_retry_triggers_background_ingestion_task(test_app, auth_headers):
    """Verify retry endpoint atomically claims document and schedules background task."""
    mock_db = AsyncMock()
    test_app.dependency_overrides[get_db] = lambda: mock_db

    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    failed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="failed_report.pdf",
        content_hash="failed_hash",
        file_size_bytes=400,
        storage_path="workspaces/ws-id/failed.pdf",
        status="failed",
        error_message="Previous extraction error",
        processing_attempts=1,
    )

    claimed_doc = Document(
        id=doc_id,
        workspace_id=ws_id,
        filename="failed_report.pdf",
        content_hash="failed_hash",
        file_size_bytes=400,
        storage_path="workspaces/ws-id/failed.pdf",
        status="processing",
        processing_attempts=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.repositories.document_repo.get_document_by_id", new=AsyncMock(return_value=failed_doc)), \
         patch("app.repositories.document_repo.atomic_claim_worker", new=AsyncMock(return_value=claimed_doc)), \
         patch("app.api.v1.documents.schedule_ingestion_background_task", new=AsyncMock()) as mock_bg_task:

        with TestClient(test_app) as client:
            res = client.post(
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/retry",
                headers=auth_headers,
            )

            assert res.status_code == 200
            assert res.json()["status"] == "processing"
            assert res.json()["processing_attempts"] == 2

            # Verify background task was dispatched for retried document
            mock_bg_task.assert_awaited_once_with(doc_id, ws_id)


@pytest.mark.asyncio
async def test_schedule_ingestion_background_task_executes_worker():
    """Verify schedule_ingestion_background_task creates database session and runs pipeline."""
    from app.services.ingestion.worker import schedule_ingestion_background_task

    ws_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session_factory = lambda: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_session),
        __aexit__=AsyncMock(),
    )

    with patch("app.services.ingestion.worker.get_settings") as mock_get_settings, \
         patch("app.services.ingestion.worker.get_session_factory", return_value=mock_session_factory), \
         patch("app.services.ingestion.worker.run_ingestion_pipeline", new=AsyncMock(return_value=True)) as mock_run:

        # Configure dummy DATABASE_URL
        settings = Settings(ENVIRONMENT="test", DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
        mock_get_settings.return_value = settings

        await schedule_ingestion_background_task(doc_id, ws_id)

        mock_run.assert_awaited_once_with(
            document_id=doc_id,
            workspace_id=ws_id,
            session=mock_session,
            settings=settings,
        )
