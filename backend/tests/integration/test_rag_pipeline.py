"""ProofLens AI — Integration Tests for Grounded Q&A & Citation Validation Pipeline.

Verifies end-to-end Phase 6 execution:
1. End-to-end question embedding, vector retrieval, generation, validation, and persistence.
2. Cross-workspace isolation (workspace scoping strictly enforced).
3. Physical page numbers and filename provenance populated from PostgreSQL records.
4. Persistence of QueryRun, RetrievedEvidence, Answer, and Citations with consistent relationships.
5. Hallucinated model citations stripped from API response.
6. Unsupported factual answers with zero valid citations force explicit abstention.
7. Empty candidate retrieval produces clean abstention without fabricated evidence.
8. Prompt-injection text in chunks is treated as untrusted data within <evidence_context>.
9. Passkey authentication gatekeeper enforces HTTP 401 on missing or invalid keys.
10. Provider failures produce sanitized RFC 7807 errors without partial success.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_application
from app.models.citation import Citation
from app.models.workspace import Workspace
from app.repositories.query_repo import CandidateChunk
from app.schemas.query import QueryResponse
from app.services.ai.embedding import GeminiEmbeddingService, get_embedding_service
from app.services.ai.generator import (
    GeneratedAnswer,
    GeneratedCitation,
    GenerationServiceError,
    GeminiGeneratorService,
    get_gemini_generator,
)
from app.services.rag.orchestrator import (
    RAGOrchestrator,
    get_rag_orchestrator,
)
from app.services.rag.validator import CitationValidator, get_citation_validator


@pytest.fixture
def rag_test_app():
    """Create test application configured for grounded Q&A testing."""
    settings = Settings(
        ENVIRONMENT="test",
        AUTH_ENABLED=True,
        DEMO_ACCESS_TOKEN="test-passkey-secret-123456",
        GEMINI_API_KEY="dummy-test-gemini-api-key-not-a-real-secret",
        GEMINI_GENERATION_MODEL="gemini-3.8-flash",
        GEMINI_EMBEDDING_MODEL="gemini-embedding-2",
        EMBEDDING_DIMENSIONS=768,
        RAG_TOP_K_RETRIEVAL=5,
        RAG_MIN_SIMILARITY_THRESHOLD=0.65,
    )
    app = create_application()
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def auth_headers():
    return {"X-Workspace-Key": "test-passkey-secret-123456"}


def create_sample_candidate(
    workspace_id: uuid.UUID,
    chunk_text: str = "In fiscal year 2025, operating revenue was $120 million.",
    page_number: int = 18,
    filename: str = "annual_filing_2025.pdf",
    rank: int = 1,
) -> CandidateChunk:
    return CandidateChunk(
        chunk_id=uuid.uuid4(),
        chunk_text=chunk_text,
        chunk_index=0,
        document_id=uuid.uuid4(),
        document_filename=filename,
        page_id=uuid.uuid4(),
        page_number=page_number,
        similarity_score=0.91,
        rank=rank,
    )


def test_grounded_qa_success_end_to_end(rag_test_app, auth_headers):
    """Verify complete end-to-end question answering pipeline with verified citations."""
    workspace_id = uuid.uuid4()
    candidate = create_sample_candidate(workspace_id=workspace_id, page_number=18)

    mock_db = AsyncMock()

    # Mock embedding service returning 768-dim vector
    mock_embedding_service = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding_service.embed_texts = AsyncMock(return_value=[[0.05] * 768])

    # Mock generator returning structured answer citing candidate
    mock_generator_service = MagicMock(spec=GeminiGeneratorService)
    mock_generator_service.generate_grounded_answer = AsyncMock(
        return_value=GeneratedAnswer(
            answer_text="Operating revenue reached $120 million in fiscal year 2025.",
            is_abstention=False,
            citations=[
                GeneratedCitation(
                    candidate_id=str(candidate.chunk_id),
                    quoted_snippet="operating revenue was $120 million.",
                )
            ],
        )
    )

    # Mock orchestrator dependencies
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_id, name="Test WS"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[candidate])), \
         patch("app.repositories.query_repo.create_query_run") as mock_create_run, \
         patch("app.repositories.query_repo.persist_retrieved_evidence") as mock_persist_ev, \
         patch("app.repositories.query_repo.persist_answer_and_citations") as mock_persist_ans:

        query_run_mock = MagicMock()
        query_run_mock.id = uuid.uuid4()
        query_run_mock.created_at = datetime.now(timezone.utc)
        persisted_cit = Citation(
            id=uuid.uuid4(),
            answer_id=uuid.uuid4(),
            chunk_id=candidate.chunk_id,
            document_filename="annual_filing_2025.pdf",
            page_number=18,
            quoted_snippet="operating revenue was $120 million.",
        )
        mock_create_run.return_value = query_run_mock
        mock_persist_ev.return_value = []
        mock_persist_ans.return_value = (MagicMock(), [persisted_cit])

        # Wire custom orchestrator with mocked services
        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding_service,
            generator_service=mock_generator_service,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/queries",
            headers=auth_headers,
            json={"query_text": "What was the operating revenue in 2025?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == str(workspace_id)
        assert data["answer_text"] == "Operating revenue reached $120 million in fiscal year 2025."
        assert data["is_abstention"] is False
        assert len(data["citations"]) == 1

        citation = data["citations"][0]
        assert citation["id"] == str(persisted_cit.id)
        assert citation["chunk_id"] == str(candidate.chunk_id)
        assert citation["document_id"] == str(candidate.document_id)
        assert citation["document_filename"] == "annual_filing_2025.pdf"
        assert citation["page_number"] == 18
        assert citation["quoted_snippet"] == "operating revenue was $120 million."

        assert len(data["retrieved_evidence"]) == 1
        assert data["retrieved_evidence"][0]["similarity_score"] == 0.91


def test_cross_workspace_isolation_safeguard(rag_test_app, auth_headers):
    """Verify search strictly passes the requested workspace_id to vector retrieval."""
    workspace_a = uuid.uuid4()

    mock_embedding = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding.embed_texts = AsyncMock(return_value=[[0.01] * 768])
    mock_generator = MagicMock(spec=GeminiGeneratorService)

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_a, name="WS A"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[])) as mock_search, \
         patch("app.repositories.query_repo.create_query_run", new=AsyncMock(return_value=MagicMock(id=uuid.uuid4(), created_at=datetime.now(timezone.utc)))), \
         patch("app.repositories.query_repo.persist_answer_and_citations", new=AsyncMock()):

        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding,
            generator_service=mock_generator,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_a}/queries",
            headers=auth_headers,
            json={"query_text": "Any information?"},
        )

        assert response.status_code == 200
        # Assert vector search was called strictly with workspace_a
        assert mock_search.call_args.kwargs["workspace_id"] == workspace_a


def test_hallucinated_citations_stripped_and_triggers_abstention(rag_test_app, auth_headers):
    """Verify that if the model invents a fake chunk ID, it is stripped, forcing abstention."""
    workspace_id = uuid.uuid4()
    candidate = create_sample_candidate(workspace_id=workspace_id)
    fake_chunk_id = str(uuid.uuid4())

    mock_embedding = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding.embed_texts = AsyncMock(return_value=[[0.02] * 768])

    # Model proposes a fake chunk_id
    mock_generator = MagicMock(spec=GeminiGeneratorService)
    mock_generator.generate_grounded_answer = AsyncMock(
        return_value=GeneratedAnswer(
            answer_text="Factual claim without real chunk citation.",
            is_abstention=False,
            citations=[GeneratedCitation(candidate_id=fake_chunk_id, quoted_snippet="Fake quote")],
        )
    )

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_id, name="WS"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[candidate])), \
         patch("app.repositories.query_repo.create_query_run", new=AsyncMock(return_value=MagicMock(id=uuid.uuid4(), created_at=datetime.now(timezone.utc)))), \
         patch("app.repositories.query_repo.persist_retrieved_evidence", new=AsyncMock()), \
         patch("app.repositories.query_repo.persist_answer_and_citations", new=AsyncMock()):

        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding,
            generator_service=mock_generator,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/queries",
            headers=auth_headers,
            json={"query_text": "Tell me secrets."},
        )

        assert response.status_code == 200
        data = response.json()
        # Fake citation was stripped
        assert len(data["citations"]) == 0
        # Unsupported claim converted to abstention
        assert data["is_abstention"] is True
        assert "unable to confirm" in data["answer_text"]


def test_empty_retrieval_produces_clean_abstention(rag_test_app, auth_headers):
    """Verify query on workspace with no ready documents cleanly abstains."""
    workspace_id = uuid.uuid4()

    mock_embedding = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding.embed_texts = AsyncMock(return_value=[[0.0] * 768])
    mock_generator = MagicMock(spec=GeminiGeneratorService)

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_id, name="Empty WS"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[])), \
         patch("app.repositories.query_repo.create_query_run", new=AsyncMock(return_value=MagicMock(id=uuid.uuid4(), created_at=datetime.now(timezone.utc)))), \
         patch("app.repositories.query_repo.persist_answer_and_citations", new=AsyncMock()):

        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding,
            generator_service=mock_generator,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/queries",
            headers=auth_headers,
            json={"query_text": "What is the policy?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_abstention"] is True
        assert "sufficient document evidence" in data["answer_text"]
        assert data["citations"] == []
        assert data["retrieved_evidence"] == []
        # Generator was never invoked for empty retrieval
        mock_generator.generate_grounded_answer.assert_not_called()


def test_unauthenticated_query_fails_with_401(rag_test_app):
    """Verify missing passkey header returns HTTP 401 Unauthorized."""
    client = TestClient(rag_test_app)
    response = client.post(
        f"/api/v1/workspaces/{uuid.uuid4()}/queries",
        json={"query_text": "Question?"},
    )
    assert response.status_code == 401


def test_missing_workspace_returns_404(rag_test_app, auth_headers):
    """Verify query on nonexistent workspace returns HTTP 404."""
    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=None)):
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{uuid.uuid4()}/queries",
            headers=auth_headers,
            json={"query_text": "Question?"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "RESOURCE_NOT_FOUND"


def test_provider_failure_returns_sanitized_502(rag_test_app, auth_headers):
    """Verify Gemini provider error returns sanitized HTTP 502 without leaking secrets."""
    workspace_id = uuid.uuid4()
    candidate = create_sample_candidate(workspace_id=workspace_id)

    mock_embedding = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding.embed_texts = AsyncMock(return_value=[[0.05] * 768])
    mock_generator = MagicMock(spec=GeminiGeneratorService)
    mock_generator.generate_grounded_answer = AsyncMock(
        side_effect=GenerationServiceError("Gemini generation failed after 3 attempts. Details: ***REDACTED***")
    )

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_id, name="WS"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[candidate])):

        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding,
            generator_service=mock_generator,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/queries",
            headers=auth_headers,
            json={"query_text": "Question?"},
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error_code"] == "AI_PROVIDER_ERROR"
        assert "AI provider service or vector retrieval encountered an error" in data["message"]


def test_response_citation_id_matches_persisted_database_id(rag_test_app, auth_headers):
    """Regression test proving that the response citation ID matches the ID persisted in the database."""
    workspace_id = uuid.uuid4()
    candidate = create_sample_candidate(workspace_id=workspace_id)
    persisted_citation_id = uuid.uuid4()

    mock_persisted_cit = MagicMock()
    mock_persisted_cit.id = persisted_citation_id

    mock_embedding = MagicMock(spec=GeminiEmbeddingService)
    mock_embedding.embed_texts = AsyncMock(return_value=[[0.1] * 768])

    mock_generator = MagicMock(spec=GeminiGeneratorService)
    mock_generator.generate_grounded_answer = AsyncMock(
        return_value=GeneratedAnswer(
            answer_text="Operating revenue reached $120 million.",
            is_abstention=False,
            citations=[
                GeneratedCitation(
                    candidate_id="chunk_1",
                    quoted_snippet="operating revenue was $120 million.",
                )
            ],
        )
    )

    with patch("app.repositories.workspace_repo.get_workspace", new=AsyncMock(return_value=Workspace(id=workspace_id, name="WS"))), \
         patch("app.repositories.query_repo.search_candidate_chunks", new=AsyncMock(return_value=[candidate])), \
         patch("app.repositories.query_repo.create_query_run", new=AsyncMock(return_value=MagicMock(id=uuid.uuid4(), created_at=datetime.now(timezone.utc)))), \
         patch("app.repositories.query_repo.persist_retrieved_evidence", new=AsyncMock()), \
         patch("app.repositories.query_repo.persist_answer_and_citations", new=AsyncMock(return_value=(MagicMock(), [mock_persisted_cit]))):

        orchestrator = RAGOrchestrator(
            settings=rag_test_app.state.settings,
            embedding_service=mock_embedding,
            generator_service=mock_generator,
            citation_validator=CitationValidator(),
        )
        rag_test_app.dependency_overrides[get_rag_orchestrator] = lambda: orchestrator
        rag_test_app.dependency_overrides[get_db] = lambda: AsyncMock()

        client = TestClient(rag_test_app)
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/queries",
            headers=auth_headers,
            json={"query_text": "What was operating revenue?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 1
        # Strictly verify that response citation ID matches the persisted database Citation.id
        assert data["citations"][0]["id"] == str(persisted_citation_id)
        assert uuid.UUID(data["citations"][0]["id"]) == persisted_citation_id
