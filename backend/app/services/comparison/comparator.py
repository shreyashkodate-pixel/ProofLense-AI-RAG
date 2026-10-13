"""ProofLens AI — Cross-Document Comparison Engine.

Coordinates balanced multi-document vector retrieval, two-stage evidence sufficiency
evaluation, Gemini-powered comparative synthesis, server-authoritative citation validation,
and atomic database persistence per PRD FR-07 and TECHNICAL-DESIGN.md.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.repositories import document_repo, query_repo, workspace_repo
from app.repositories.query_repo import CandidateChunk
from app.services.ai.embedding import GeminiEmbeddingService, get_embedding_service
from app.services.ai.generator import (
    GeminiGeneratorService,
    GeneratedComparisonResult,
    get_gemini_generator,
)
from app.services.rag.abstention import (
    EvidenceSufficiencyEvaluator,
    get_evidence_sufficiency_evaluator,
)
from app.services.rag.validator import (
    CitationValidator,
    ComparisonValidationResult,
    ValidatedCitation,
    ValidatedComparisonFinding,
    get_citation_validator,
)


class ComparisonError(Exception):
    """Base exception for cross-document comparison errors."""
    pass


class ComparisonInputValidationError(ComparisonError):
    """Raised when comparison request input parameters are invalid."""
    pass


class WorkspaceNotFoundError(ComparisonError):
    """Raised when specified workspace does not exist."""
    pass


class DocumentNotFoundError(ComparisonError):
    """Raised when a specified document is not found within the workspace scope."""
    pass


class DocumentNotReadyError(ComparisonError):
    """Raised when a selected document has not completed ingestion or embedding."""
    pass


class InsufficientDocumentsError(ComparisonError):
    """Raised when fewer than two ready documents are available for comparison."""
    pass


class ComparisonPipelineError(ComparisonError):
    """Raised when an internal retrieval, generation, or validation failure occurs."""
    pass


@dataclass(frozen=True)
class ComparisonResult:
    """End-to-end result of cross-document comparison execution."""

    comparison_id: uuid.UUID
    workspace_id: uuid.UUID
    query_text: str
    document_ids: List[uuid.UUID]
    status: str
    is_abstention: bool
    findings: List[ValidatedComparisonFinding]
    synthesis: str
    limitations: Optional[str]
    retrieved_evidence: List[CandidateChunk]
    created_at: datetime


class CrossDocumentComparator:
    """Coordinates evidence-grounded comparative analysis across multiple documents."""

    def __init__(
        self,
        settings: Settings,
        embedding_service: GeminiEmbeddingService,
        generator_service: GeminiGeneratorService,
        citation_validator: CitationValidator,
        sufficiency_evaluator: Optional[EvidenceSufficiencyEvaluator] = None,
    ) -> None:
        self.settings = settings
        self.embedding_service = embedding_service
        self.generator_service = generator_service
        self.citation_validator = citation_validator
        self.sufficiency_evaluator = sufficiency_evaluator or EvidenceSufficiencyEvaluator(
            default_threshold=settings.RAG_MIN_SIMILARITY_THRESHOLD
        )

    async def execute_comparison(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        query_text: str,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> ComparisonResult:
        """Execute a cross-document comparative analysis.

        Args:
            session: Async database session.
            workspace_id: UUID of the workspace scope.
            query_text: Comparison question, claim, or topic.
            document_ids: Optional list of document UUIDs to compare (min 2, max 5).

        Returns:
            ComparisonResult with validated findings, per-document evidence, and citations.
        """
        # 1. Input sanitization & validation
        clean_query = query_text.strip() if query_text else ""
        if len(clean_query) < 3:
            raise ComparisonInputValidationError("Comparison query must be at least 3 characters.")
        if len(clean_query) > 1000:
            raise ComparisonInputValidationError("Comparison query must not exceed 1000 characters.")

        # 2. Verify workspace existence
        workspace = await workspace_repo.get_workspace(session, workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found.")

        # 3. Document scope and eligibility validation
        selected_documents = []
        if document_ids is not None:
            # Deduplicate requested IDs preserving input order
            unique_ids = list(dict.fromkeys(document_ids))
            if len(unique_ids) < 2:
                raise InsufficientDocumentsError(
                    "Cross-document comparison requires at least 2 distinct documents."
                )
            if len(unique_ids) > 5:
                raise ComparisonInputValidationError(
                    "Comparison is limited to a maximum of 5 documents."
                )

            # Fetch requested documents strictly scoped to workspace
            docs = await document_repo.get_documents_by_ids(session, workspace_id, unique_ids)
            doc_by_id = {d.id: d for d in docs}

            for requested_id in unique_ids:
                doc = doc_by_id.get(requested_id)
                if not doc:
                    raise DocumentNotFoundError(
                        f"Document '{requested_id}' does not exist in workspace '{workspace_id}'."
                    )
                if doc.status != "ready":
                    raise DocumentNotReadyError(
                        f"Document '{doc.filename}' ({doc.id}) is not ready for comparison (status: '{doc.status}')."
                    )
                selected_documents.append(doc)
        else:
            # Automatic document selection: fetch all ready documents up to 5
            ready_docs = await document_repo.get_ready_documents(session, workspace_id, limit=5)
            if len(ready_docs) < 2:
                raise InsufficientDocumentsError(
                    "At least two ready documents are required in the workspace to perform a comparison."
                )
            selected_documents = ready_docs

        compared_doc_ids = [d.id for d in selected_documents]

        # 4. Generate query embedding (network call outside DB lock)
        try:
            embeddings = await self.embedding_service.embed_texts([clean_query])
            query_vector = embeddings[0]
        except Exception as embed_err:
            logger.error("Failed to generate comparison query embedding", extra={"extra": {"error": str(embed_err)}})
            raise ComparisonPipelineError(f"Query embedding generation failed: {embed_err}") from embed_err

        # 5. Balanced per-document vector retrieval
        candidates = await query_repo.search_candidates_per_document(
            session=session,
            workspace_id=workspace_id,
            query_vector=query_vector,
            document_ids=compared_doc_ids,
            per_doc_k=3,
        )

        # 6. Two-stage evidence sufficiency evaluation
        threshold = self.settings.RAG_MIN_SIMILARITY_THRESHOLD
        is_sufficient, top_score = self.sufficiency_evaluator.evaluate_vector_sufficiency(
            candidates=candidates,
            threshold=threshold,
        )

        if not is_sufficient:
            # Deterministic Vector Abstention: bypass Gemini LLM call
            abstention_synthesis = self.sufficiency_evaluator.get_comparison_abstention_text()
            abstention_limitations = (
                f"No candidate evidence passages met the similarity threshold ({threshold:.2f}) "
                f"across the selected documents."
            )

            query_run, _, _ = await query_repo.persist_comparison_run(
                session=session,
                workspace_id=workspace_id,
                query_text=clean_query,
                top_score=top_score,
                synthesis_text=abstention_synthesis,
                is_abstention=True,
                candidates=[],
                citations_data=[],
                status="insufficient_evidence",
            )

            return ComparisonResult(
                comparison_id=query_run.id,
                workspace_id=workspace_id,
                query_text=clean_query,
                document_ids=compared_doc_ids,
                status="insufficient_evidence",
                is_abstention=True,
                findings=[],
                synthesis=abstention_synthesis,
                limitations=abstention_limitations,
                retrieved_evidence=[],
                created_at=query_run.created_at,
            )

        # Stage 2: Filter passing chunks meeting or exceeding similarity threshold
        passing_candidates = self.sufficiency_evaluator.filter_passing_chunks(
            candidates=candidates,
            threshold=threshold,
        )

        if not passing_candidates:
            # Deterministic Vector Abstention if no chunks qualify
            abstention_synthesis = self.sufficiency_evaluator.get_comparison_abstention_text()
            abstention_limitations = (
                f"No candidate evidence passages met the similarity threshold ({threshold:.2f}) "
                f"across the selected documents."
            )

            query_run, _, _ = await query_repo.persist_comparison_run(
                session=session,
                workspace_id=workspace_id,
                query_text=clean_query,
                top_score=top_score,
                synthesis_text=abstention_synthesis,
                is_abstention=True,
                candidates=[],
                citations_data=[],
                status="insufficient_evidence",
            )

            return ComparisonResult(
                comparison_id=query_run.id,
                workspace_id=workspace_id,
                query_text=clean_query,
                document_ids=compared_doc_ids,
                status="insufficient_evidence",
                is_abstention=True,
                findings=[],
                synthesis=abstention_synthesis,
                limitations=abstention_limitations,
                retrieved_evidence=[],
                created_at=query_run.created_at,
            )

        # 7. Synthesize grounded comparison with Gemini (network call outside DB transaction)
        try:
            model_comparison: GeneratedComparisonResult = await self.generator_service.generate_comparison(
                question=clean_query,
                candidates=passing_candidates,
            )
        except Exception as gen_err:
            logger.error("Failed to generate comparative analysis", extra={"extra": {"error": str(gen_err)}})
            raise ComparisonPipelineError(f"Comparison generation failed: {gen_err}") from gen_err

        # 8. Server-Authoritative Citation and Finding Validation
        val_result: ComparisonValidationResult = self.citation_validator.validate_comparison_findings(
            model_result=model_comparison,
            candidate_chunks=passing_candidates,
            workspace_id=workspace_id,
            documents=selected_documents,
        )

        # 9. Database persistence in atomic transaction
        citations_payload = [
            {
                "chunk_id": cit.chunk_id,
                "document_filename": cit.document_filename,
                "page_number": cit.page_number,
                "quoted_snippet": cit.quoted_snippet,
            }
            for cit in val_result.all_validated_citations
        ]

        query_run, _, persisted_citations = await query_repo.persist_comparison_run(
            session=session,
            workspace_id=workspace_id,
            query_text=clean_query,
            top_score=top_score,
            synthesis_text=val_result.synthesis,
            is_abstention=val_result.is_abstention,
            candidates=candidates,
            citations_data=citations_payload,
            status="insufficient_evidence" if val_result.is_abstention else "completed",
        )

        # Map persisted database Citation.id back to validated citations
        chunk_to_persisted_id: Dict[uuid.UUID, uuid.UUID] = {}
        for p_cit in persisted_citations:
            if hasattr(p_cit, "chunk_id") and p_cit.chunk_id and hasattr(p_cit, "id"):
                chunk_to_persisted_id[p_cit.chunk_id] = p_cit.id

        # Update findings with persisted citation IDs
        final_findings: List[ValidatedComparisonFinding] = []
        for finding in val_result.findings:
            updated_per_doc = []
            finding_persisted_citations = []

            for per_doc in finding.per_document_evidence:
                doc_persisted_citations = []
                for cit in per_doc.citations:
                    persisted_id = chunk_to_persisted_id.get(cit.chunk_id)
                    hydrated_cit = ValidatedCitation(
                        id=persisted_id,
                        chunk_id=cit.chunk_id,
                        document_id=cit.document_id,
                        document_filename=cit.document_filename,
                        page_number=cit.page_number,
                        quoted_snippet=cit.quoted_snippet,
                    )
                    doc_persisted_citations.append(hydrated_cit)
                    finding_persisted_citations.append(hydrated_cit)

                updated_per_doc.append(
                    type(per_doc)(
                        document_id=per_doc.document_id,
                        document_filename=per_doc.document_filename,
                        statement=per_doc.statement,
                        citations=doc_persisted_citations,
                    )
                )

            final_findings.append(
                ValidatedComparisonFinding(
                    finding_type=finding.finding_type,
                    topic=finding.topic,
                    summary=finding.summary,
                    per_document_evidence=updated_per_doc,
                    citations=finding_persisted_citations,
                )
            )

        logger.info(
            "Cross-document comparison completed successfully",
            extra={
                "extra": {
                    "comparison_id": str(query_run.id),
                    "document_count": len(compared_doc_ids),
                    "is_abstention": val_result.is_abstention,
                    "findings_count": len(final_findings),
                }
            },
        )

        return ComparisonResult(
            comparison_id=query_run.id,
            workspace_id=workspace_id,
            query_text=clean_query,
            document_ids=compared_doc_ids,
            status=query_run.status,
            is_abstention=val_result.is_abstention,
            findings=final_findings,
            synthesis=val_result.synthesis,
            limitations=val_result.limitations,
            retrieved_evidence=candidates,
            created_at=query_run.created_at,
        )


def get_cross_document_comparator(
    settings: Settings = Depends(get_settings),
) -> CrossDocumentComparator:
    """Dependency factory for CrossDocumentComparator."""
    return CrossDocumentComparator(
        settings=settings,
        embedding_service=get_embedding_service(settings),
        generator_service=get_gemini_generator(settings),
        citation_validator=get_citation_validator(),
        sufficiency_evaluator=get_evidence_sufficiency_evaluator(),
    )
