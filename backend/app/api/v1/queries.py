"""ProofLens AI — Grounded Queries API Router.

Provides versioned endpoints for executing evidence-grounded question answering,
retrieving candidate chunks, and validating page-level citations.
Protected by the Application-Level Access Passkey Gatekeeper.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import verify_access_passkey
from app.models.query import QueryRun
from app.repositories import query_repo, workspace_repo
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


def _format_query_run_to_response(query_run: QueryRun) -> QueryResponse:
    citations: List[CitationResponse] = []
    if query_run.answer and query_run.answer.citations:
        for cit in query_run.answer.citations:
            doc_id = cit.chunk.document_id if (cit.chunk and cit.chunk.document_id) else None
            citations.append(
                CitationResponse(
                    id=cit.id,
                    chunk_id=cit.chunk_id,
                    document_id=doc_id,
                    document_filename=cit.document_filename,
                    page_number=cit.page_number,
                    quoted_snippet=cit.quoted_snippet,
                )
            )

    evidence: List[RetrievedEvidenceResponse] = []
    if query_run.retrieved_evidence:
        for ev in query_run.retrieved_evidence:
            chunk = ev.chunk
            doc_id = chunk.document_id if (chunk and chunk.document_id) else uuid.UUID("00000000-0000-0000-0000-000000000000")
            doc_filename = chunk.document.filename if (chunk and chunk.document) else "document.pdf"
            page_num = chunk.page.page_number if (chunk and chunk.page) else 1
            snippet = chunk.chunk_text[:300].strip() if (chunk and chunk.chunk_text) else ""
            evidence.append(
                RetrievedEvidenceResponse(
                    chunk_id=ev.chunk_id,
                    document_id=doc_id,
                    document_filename=doc_filename,
                    page_number=page_num,
                    snippet=snippet,
                    similarity_score=ev.similarity_score,
                    rank=ev.rank,
                )
            )

    answer_text = query_run.answer.answer_text if query_run.answer else ""
    is_abstention = query_run.answer.is_abstention if query_run.answer else False

    return QueryResponse(
        query_run_id=query_run.id,
        workspace_id=query_run.workspace_id,
        query_text=query_run.query_text,
        status=query_run.status,
        answer_text=answer_text,
        is_abstention=is_abstention,
        top_score=query_run.top_score,
        citations=citations,
        retrieved_evidence=evidence,
        created_at=query_run.created_at,
    )


@router.get(
    "",
    response_model=List[QueryResponse],
    summary="List saved grounded query runs for a workspace",
)
async def list_queries_endpoint(
    workspace_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Max queries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """List historical grounded queries strictly scoped to the workspace."""
    workspace = await workspace_repo.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' does not exist.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )

    query_runs = await query_repo.list_query_runs(
        session=db,
        workspace_id=workspace_id,
        run_type="query",
        limit=limit,
        offset=offset,
    )
    return [_format_query_run_to_response(run) for run in query_runs]


@router.get(
    "/{query_run_id}",
    response_model=QueryResponse,
    summary="Retrieve a specific grounded query run by ID",
)
async def get_query_endpoint(
    workspace_id: uuid.UUID,
    query_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full query run with citations and evidence strictly scoped to workspace."""
    workspace = await workspace_repo.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Workspace '{workspace_id}' does not exist.",
                "details": {"workspace_id": str(workspace_id)},
            },
        )

    query_run = await query_repo.get_query_run_by_id(
        session=db,
        workspace_id=workspace_id,
        query_run_id=query_run_id,
        run_type="query",
    )
    if not query_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Query run '{query_run_id}' not found in workspace '{workspace_id}'.",
                "details": {
                    "workspace_id": str(workspace_id),
                    "query_run_id": str(query_run_id),
                },
            },
        )

    return _format_query_run_to_response(query_run)
