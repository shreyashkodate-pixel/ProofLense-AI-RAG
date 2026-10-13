"""ProofLens AI — Cross-Document Comparison API Router.

Provides versioned endpoints for comparing topics, claims, metrics, and contracts
across multiple documents within a workspace.
Protected by the Application-Level Access Passkey Gatekeeper.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import verify_access_passkey
from app.schemas.comparison import (
    ComparisonFindingResponse,
    ComparisonRequest,
    ComparisonResponse,
    PerDocumentEvidenceResponse,
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
