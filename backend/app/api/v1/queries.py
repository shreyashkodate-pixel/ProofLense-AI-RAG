"""ProofLens AI — Grounded Queries API Router.

Provides versioned endpoints for executing evidence-grounded question answering,
retrieving candidate chunks, and validating page-level citations.
Protected by the Application-Level Access Passkey Gatekeeper.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import verify_access_passkey
from app.schemas.query import (
    CitationResponse,
    QueryRequest,
    QueryResponse,
    RetrievedEvidenceResponse,
)
from app.services.rag.orchestrator import (
    RAGError,
    RAGPipelineError,
    RAGQueryResult,
    RAGOrchestrator,
    WorkspaceNotFoundError,
    get_rag_orchestrator,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/queries",
    tags=["Queries"],
    dependencies=[Depends(verify_access_passkey)],
)


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute evidence-grounded Q&A query with server-authoritative citations",
)
async def execute_query_endpoint(
    workspace_id: uuid.UUID,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: RAGOrchestrator = Depends(get_rag_orchestrator),
):
    """Execute grounded question answering strictly scoped to workspace documents."""
    try:
        result: RAGQueryResult = await orchestrator.execute_query(
            session=db,
            workspace_id=workspace_id,
            query_text=payload.query_text,
            top_k=payload.top_k,
        )

        citation_responses = [
            CitationResponse(
                id=cit.id if cit.id is not None else uuid.uuid4(),
                chunk_id=cit.chunk_id,
                document_id=cit.document_id,
                document_filename=cit.document_filename,
                page_number=cit.page_number,
                quoted_snippet=cit.quoted_snippet,
            )
            for cit in result.citations
        ]

        evidence_responses = [
            RetrievedEvidenceResponse(
                chunk_id=ev.chunk_id,
                document_id=ev.document_id,
                document_filename=ev.document_filename,
                page_number=ev.page_number,
                snippet=ev.chunk_text[:300].strip(),
                similarity_score=ev.similarity_score,
                rank=ev.rank,
            )
            for ev in result.retrieved_evidence
        ]

        return QueryResponse(
            query_run_id=result.query_run_id,
            workspace_id=result.workspace_id,
            query_text=result.query_text,
            status=result.status,
            answer_text=result.answer_text,
            is_abstention=result.is_abstention,
            top_score=result.top_score,
            citations=citation_responses,
            retrieved_evidence=evidence_responses,
            created_at=result.created_at,
        )

    except WorkspaceNotFoundError as not_found_err:
        logger.warning(
            "Query attempted on nonexistent workspace",
            extra={"extra": {"workspace_id": str(workspace_id)}},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' does not exist.",
                "details": {"workspace_id": str(workspace_id)},
            },
        ) from not_found_err

    except RAGPipelineError as pipe_err:
        logger.error(
            "RAG pipeline execution failed",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(pipe_err)}},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "AI_PROVIDER_ERROR",
                "message": "AI provider service or vector retrieval encountered an error. Please retry.",
                "details": {"category": "rag_pipeline_failure"},
            },
        ) from pipe_err

    except Exception as exc:
        logger.error(
            "Unexpected error in query endpoint",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(exc)}},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the query.",
                "details": {},
            },
        ) from exc
