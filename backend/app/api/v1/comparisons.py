"""ProofLens AI — Cross-Document Comparison API Router.

Provides versioned endpoints for comparing topics, claims, metrics, and contracts
across multiple documents within a workspace.
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
from app.schemas.comparison import (
    ComparisonFindingResponse,
    ComparisonRequest,
    ComparisonResponse,
    PerDocumentEvidenceResponse,
    SavedComparisonResponse,
)
from app.schemas.query import CitationResponse, RetrievedEvidenceResponse
from app.services.comparison.comparator import (
    ComparisonError,
    ComparisonInputValidationError,
    ComparisonPipelineError,
    ComparisonResult,
    CrossDocumentComparator,
    DocumentNotFoundError,
    DocumentNotReadyError,
    InsufficientDocumentsError,
    WorkspaceNotFoundError,
    get_cross_document_comparator,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/comparisons",
    tags=["Comparisons"],
    dependencies=[Depends(verify_access_passkey)],
)


@router.post(
    "",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute evidence-grounded cross-document comparison with server-authoritative citations",
)
async def execute_comparison_endpoint(
    workspace_id: uuid.UUID,
    payload: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
    comparator: CrossDocumentComparator = Depends(get_cross_document_comparator),
):
    """Execute cross-document comparative analysis strictly scoped to workspace documents."""
    try:
        result: ComparisonResult = await comparator.execute_comparison(
            session=db,
            workspace_id=workspace_id,
            query_text=payload.query_text,
            document_ids=payload.document_ids,
        )

        findings_responses: list[ComparisonFindingResponse] = []
        for f in result.findings:
            per_doc_responses = [
                PerDocumentEvidenceResponse(
                    document_id=pd.document_id,
                    document_filename=pd.document_filename,
                    statement=pd.statement,
                    citations=[
                        CitationResponse(
                            id=cit.id if cit.id is not None else uuid.uuid4(),
                            chunk_id=cit.chunk_id,
                            document_id=cit.document_id,
                            document_filename=cit.document_filename,
                            page_number=cit.page_number,
                            quoted_snippet=cit.quoted_snippet,
                        )
                        for cit in pd.citations
                    ],
                )
                for pd in f.per_document_evidence
            ]

            findings_responses.append(
                ComparisonFindingResponse(
                    finding_type=f.finding_type,
                    topic=f.topic,
                    summary=f.summary,
                    per_document_evidence=per_doc_responses,
                    citations=[
                        CitationResponse(
                            id=cit.id if cit.id is not None else uuid.uuid4(),
                            chunk_id=cit.chunk_id,
                            document_id=cit.document_id,
                            document_filename=cit.document_filename,
                            page_number=cit.page_number,
                            quoted_snippet=cit.quoted_snippet,
                        )
                        for cit in f.citations
                    ],
                )
            )

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

        return ComparisonResponse(
            comparison_id=result.comparison_id,
            workspace_id=result.workspace_id,
            query_text=result.query_text,
            document_ids=result.document_ids,
            status=result.status,
            is_abstention=result.is_abstention,
            findings=findings_responses,
            synthesis=result.synthesis,
            limitations=result.limitations,
            retrieved_evidence=evidence_responses,
            created_at=result.created_at,
        )

    except WorkspaceNotFoundError as not_found_err:
        logger.warning(
            "Comparison attempted on nonexistent workspace",
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

    except DocumentNotFoundError as doc_not_found:
        logger.warning(
            "Comparison requested nonexistent or cross-workspace document",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(doc_not_found)}},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": str(doc_not_found),
                "details": {"workspace_id": str(workspace_id)},
            },
        ) from doc_not_found

    except (DocumentNotReadyError, InsufficientDocumentsError, ComparisonInputValidationError) as bad_req_err:
        logger.warning(
            "Comparison request validation failed",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(bad_req_err)}},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_COMPARISON_REQUEST",
                "message": str(bad_req_err),
                "details": {"workspace_id": str(workspace_id)},
            },
        ) from bad_req_err

    except ComparisonPipelineError as pipe_err:
        logger.error(
            "Comparison pipeline execution failed",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(pipe_err)}},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "AI_PROVIDER_ERROR",
                "message": "AI provider service or vector retrieval encountered an error. Please retry.",
                "details": {"category": "comparison_pipeline_failure"},
            },
        ) from pipe_err

    except Exception as exc:
        logger.error(
            "Unexpected error in comparison endpoint",
            extra={"extra": {"workspace_id": str(workspace_id), "error": str(exc)}},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the comparison.",
                "details": {},
            },
        ) from exc


def _format_comparison_run_to_response(run: QueryRun) -> SavedComparisonResponse:
    citations: List[CitationResponse] = []
    if run.answer and run.answer.citations:
        for cit in run.answer.citations:
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
    if run.retrieved_evidence:
        for ev in run.retrieved_evidence:
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

    synthesis = run.answer.answer_text if run.answer else ""
    is_abstention = run.answer.is_abstention if run.answer else False

    return SavedComparisonResponse(
        comparison_id=run.id,
        workspace_id=run.workspace_id,
        query_text=run.query_text,
        status=run.status,
        is_abstention=is_abstention,
        top_score=run.top_score,
        synthesis=synthesis,
        citations=citations,
        retrieved_evidence=evidence,
        created_at=run.created_at,
    )


@router.get(
    "",
    response_model=List[SavedComparisonResponse],
    summary="List saved comparison runs for a workspace",
)
async def list_comparisons_endpoint(
    workspace_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Max comparisons to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """List historical comparison runs strictly scoped to the workspace."""
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

    comparison_runs = await query_repo.list_query_runs(
        session=db,
        workspace_id=workspace_id,
        run_type="comparison",
        limit=limit,
        offset=offset,
    )
    return [_format_comparison_run_to_response(run) for run in comparison_runs]


@router.get(
    "/{comparison_id}",
    response_model=SavedComparisonResponse,
    summary="Retrieve a specific saved comparison run by ID",
)
async def get_comparison_endpoint(
    workspace_id: uuid.UUID,
    comparison_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full comparison run with citations and evidence strictly scoped to workspace."""
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

    comparison_run = await query_repo.get_query_run_by_id(
        session=db,
        workspace_id=workspace_id,
        query_run_id=comparison_id,
        run_type="comparison",
    )
    if not comparison_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Comparison '{comparison_id}' not found in workspace '{workspace_id}'.",
                "details": {
                    "workspace_id": str(workspace_id),
                    "comparison_id": str(comparison_id),
                },
            },
        )

    return _format_comparison_run_to_response(comparison_run)
