"""ProofLens AI — RAG Orchestrator Service.

Coordinates end-to-end evidence-grounded Q&A:
1. Workspace Scope Verification.
2. Query Embedding via Phase 5 GeminiEmbeddingService.
3. Candidate Retrieval via pgvector with HNSW cosine distance (<=>).
4. Prompt-Injection Resistant XML Evidence Framing.
5. Structured Answer Synthesis via GeminiGeneratorService (outside open DB transactions).
6. Server-Authoritative Citation Validation.
7. Persistence of QueryRun, RetrievedEvidence, Answer, and Citations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.repositories import query_repo, workspace_repo
from app.repositories.query_repo import CandidateChunk
from app.services.ai.embedding import GeminiEmbeddingService, get_embedding_service
from app.services.ai.generator import (
    GeneratedAnswer,
    GeminiGeneratorService,
    get_gemini_generator,
)
from app.services.rag.validator import (
    CitationValidationResult,
    CitationValidator,
    ValidatedCitation,
    get_citation_validator,
)


class RAGError(Exception):
    """Base exception for RAG orchestration errors."""
    pass


class WorkspaceNotFoundError(RAGError):
    """Raised when the specified workspace does not exist."""
    pass


class RAGPipelineError(RAGError):
    """Raised when an internal error occurs during retrieval or generation."""
    pass


@dataclass(frozen=True)
class RAGQueryResult:
    """End-to-end execution result for a grounded Q&A run."""

    query_run_id: uuid.UUID
    workspace_id: uuid.UUID
    query_text: str
    status: str
    answer_text: str
    is_abstention: bool
    top_score: Optional[float]
    citations: List[ValidatedCitation] = field(default_factory=list)
    retrieved_evidence: List[CandidateChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RAGOrchestrator:
    """Full RAG pipeline coordinator."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        embedding_service: Optional[GeminiEmbeddingService] = None,
        generator_service: Optional[GeminiGeneratorService] = None,
        citation_validator: Optional[CitationValidator] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or get_embedding_service(self.settings)
        self.generator_service = generator_service or get_gemini_generator(self.settings)
        self.citation_validator = citation_validator or get_citation_validator()

    async def execute_query(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> RAGQueryResult:
        """Execute complete grounded Q&A pipeline.

        Args:
            session: Async database session.
            workspace_id: UUID of the workspace scope.
            query_text: User question string.
            top_k: Optional retrieval ceiling.

        Returns:
            RAGQueryResult with verified citations and evidence.

        Raises:
            WorkspaceNotFoundError: If workspace does not exist.
            RAGPipelineError: If an unrecoverable pipeline failure occurs.
        """
        clean_query = query_text.strip()
        k_val = top_k or self.settings.RAG_TOP_K_RETRIEVAL

        logger.info(
            "Starting grounded Q&A query execution",
            extra={"extra": {"workspace_id": str(workspace_id), "top_k": k_val}},
        )

        # 1. Verify workspace exists
        workspace = await workspace_repo.get_workspace(session, workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found.")

        # 2. Generate 768-dim query embedding (network call outside DB lock)
        try:
            embeddings = await self.embedding_service.embed_texts([clean_query])
            query_vector = embeddings[0]
        except Exception as embed_err:
            logger.error("Failed to generate query embedding", extra={"extra": {"error": str(embed_err)}})
            raise RAGPipelineError(f"Query embedding generation failed: {embed_err}") from embed_err

        # 3. Retrieve workspace-scoped candidate chunks
        candidates = await query_repo.search_candidate_chunks(
            session=session,
            workspace_id=workspace_id,
            query_vector=query_vector,
            top_k=k_val,
        )

        top_score = candidates[0].similarity_score if candidates else None

        # 4. Handle empty candidate set (e.g. no documents or no chunks in workspace)
        if not candidates:
            logger.info(
                "No candidate chunks retrieved for workspace; abstaining cleanly",
                extra={"extra": {"workspace_id": str(workspace_id)}},
            )
            abstention_text = (
                "I do not have sufficient document evidence in this workspace to answer your question."
            )
            # Persist query run and abstention answer in short transaction
            query_run = await query_repo.create_query_run(
                session=session,
                workspace_id=workspace_id,
                query_text=clean_query,
                top_score=None,
                status="completed",
            )
            await query_repo.persist_answer_and_citations(
                session=session,
                query_run_id=query_run.id,
                answer_text=abstention_text,
                is_abstention=True,
                citations_data=[],
            )

            return RAGQueryResult(
                query_run_id=query_run.id,
                workspace_id=workspace_id,
                query_text=clean_query,
                status="completed",
                answer_text=abstention_text,
                is_abstention=True,
                top_score=None,
                citations=[],
                retrieved_evidence=[],
                created_at=query_run.created_at,
            )

        # 5. Synthesize grounded answer with Gemini (network call outside DB transaction)
        try:
            model_answer: GeneratedAnswer = await self.generator_service.generate_grounded_answer(
                question=clean_query,
                candidates=candidates,
            )
        except Exception as gen_err:
            logger.error("Failed to generate grounded answer", extra={"extra": {"error": str(gen_err)}})
            raise RAGPipelineError(f"Answer generation failed: {gen_err}") from gen_err

        # 6. Server-Authoritative Citation Validation
        val_result: CitationValidationResult = self.citation_validator.validate_citations(
            answer_text=model_answer.answer_text,
            is_abstention=model_answer.is_abstention,
            proposed_citations=model_answer.citations,
            candidate_chunks=candidates,
            workspace_id=workspace_id,
        )

        # 7. Database Persistence (dedicated short transaction)
        query_run = await query_repo.create_query_run(
            session=session,
            workspace_id=workspace_id,
            query_text=clean_query,
            top_score=top_score,
            status="completed",
        )

        await query_repo.persist_retrieved_evidence(
            session=session,
            query_run_id=query_run.id,
            candidates=candidates,
        )

        citations_payload = [
            {
                "chunk_id": cit.chunk_id,
                "document_filename": cit.document_filename,
                "page_number": cit.page_number,
                "quoted_snippet": cit.quoted_snippet,
            }
            for cit in val_result.citations
        ]

        persisted_res = await query_repo.persist_answer_and_citations(
            session=session,
            query_run_id=query_run.id,
            answer_text=val_result.answer_text,
            is_abstention=val_result.is_abstention,
            citations_data=citations_payload,
        )

        persisted_citations: List[Any] = []
        if isinstance(persisted_res, tuple) and len(persisted_res) == 2:
            _, persisted_citations = persisted_res
        elif isinstance(persisted_res, list):
            persisted_citations = persisted_res

        # Attach persisted database Citation.id to validated citations
        final_citations: List[ValidatedCitation] = []
        for idx, v_cit in enumerate(val_result.citations):
            p_cit = persisted_citations[idx] if idx < len(persisted_citations) else None
            final_citations.append(
                ValidatedCitation(
                    id=getattr(p_cit, "id", None) if p_cit is not None else None,
                    chunk_id=v_cit.chunk_id,
                    document_id=v_cit.document_id,
                    document_filename=v_cit.document_filename,
                    page_number=v_cit.page_number,
                    quoted_snippet=v_cit.quoted_snippet,
                )
            )

        logger.info(
            "Grounded Q&A query execution completed successfully",
            extra={
                "extra": {
                    "query_run_id": str(query_run.id),
                    "is_abstention": val_result.is_abstention,
                    "citations_count": len(final_citations),
                }
            },
        )

        return RAGQueryResult(
            query_run_id=query_run.id,
            workspace_id=workspace_id,
            query_text=clean_query,
            status="completed",
            answer_text=val_result.answer_text,
            is_abstention=val_result.is_abstention,
            top_score=top_score,
            citations=final_citations,
            retrieved_evidence=candidates,
            created_at=query_run.created_at,
        )


def get_rag_orchestrator(
    settings: Settings = Depends(get_settings),
) -> RAGOrchestrator:
    """Dependency factory for RAGOrchestrator."""
    return RAGOrchestrator(
        settings=settings,
        embedding_service=get_embedding_service(settings),
        generator_service=get_gemini_generator(settings),
        citation_validator=get_citation_validator(),
    )
