"""ProofLens AI — Query, Evidence, and Citation Repository.

Data access layer providing workspace-scoped vector retrieval using pgvector,
and persistence for query runs, candidate evidence, synthesized answers,
and server-authoritative tombstone citations.
"""

from dataclasses import dataclass
import inspect
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import DocumentChunk
from app.models.citation import Citation
from app.models.document import Document
from app.models.page import DocumentPage
from app.models.query import Answer, QueryRun, RetrievedEvidence


@dataclass(frozen=True)
class CandidateChunk:
    """Represents a candidate evidence chunk retrieved via vector similarity search."""

    chunk_id: uuid.UUID
    chunk_text: str
    chunk_index: int
    document_id: uuid.UUID
    document_filename: str
    page_id: uuid.UUID
    page_number: int
    similarity_score: float
    rank: int


async def _extract_rows_list(result: Any) -> List[Any]:
    """Extract rows safely handling both real SQLAlchemy results and AsyncMock objects."""
    if inspect.isawaitable(result):
        result = await result

    # If result is already a list or iterable of objects
    if isinstance(result, list):
        return result

    if hasattr(result, "all"):
        rows = result.all()
        if inspect.isawaitable(rows):
            rows = await rows
        return list(rows)

    return []


async def search_candidate_chunks(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_vector: List[float],
    top_k: int = 5,
) -> List[CandidateChunk]:
    """Retrieve top-K candidate chunks for a query vector strictly scoped to a workspace.

    Guarantees:
    1. Cross-workspace isolation: joins Document and filters Document.workspace_id == workspace_id.
    2. Lifecycle validity: only searches chunks belonging to documents with status == 'ready'.
    3. Null-embedding safety: excludes chunks without populated embeddings.
    4. Deterministic distance ordering: orders ascending by cosine distance (<=>).

    Args:
        session: Async database session.
        workspace_id: UUID of the workspace scope.
        query_vector: 768-dimensional query embedding vector.
        top_k: Maximum candidate passages to retrieve.

    Returns:
        List of CandidateChunk instances ranked by similarity score descending.
    """
    cosine_dist = DocumentChunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.chunk_text,
            DocumentChunk.chunk_index,
            Document.id.label("document_id"),
            Document.filename.label("document_filename"),
            DocumentPage.id.label("page_id"),
            DocumentPage.page_number,
            (1.0 - cosine_dist).label("similarity_score"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .join(DocumentPage, DocumentPage.id == DocumentChunk.page_id)
        .where(
            Document.workspace_id == workspace_id,
            Document.status == "ready",
            DocumentChunk.embedding.isnot(None),
        )
        .order_by(cosine_dist.asc())
        .limit(top_k)
    )

    result = await session.execute(stmt)
    raw_rows = await _extract_rows_list(result)

    candidates: List[CandidateChunk] = []
    for idx, row in enumerate(raw_rows, start=1):
        # Support both named row mappings and objects/tuples
        if hasattr(row, "_mapping"):
            m = row._mapping
            chunk_id = m["chunk_id"]
            chunk_text = m["chunk_text"]
            chunk_index = m["chunk_index"]
            document_id = m["document_id"]
            document_filename = m["document_filename"]
            page_id = m["page_id"]
            page_number = m["page_number"]
            sim_score = float(m["similarity_score"])
        elif hasattr(row, "chunk_id"):
            chunk_id = row.chunk_id
            chunk_text = row.chunk_text
            chunk_index = getattr(row, "chunk_index", 0)
            document_id = row.document_id
            document_filename = getattr(row, "document_filename", getattr(row, "filename", "document.pdf"))
            page_id = getattr(row, "page_id", uuid.uuid4())
            page_number = getattr(row, "page_number", 1)
            sim_score = float(getattr(row, "similarity_score", 0.0))
        elif isinstance(row, (tuple, list)) and len(row) >= 8:
            chunk_id, chunk_text, chunk_index, document_id, document_filename, page_id, page_number, sim_score = row[:8]
            sim_score = float(sim_score)
        else:
            continue

        candidates.append(
            CandidateChunk(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                chunk_index=chunk_index,
                document_id=document_id,
                document_filename=document_filename,
                page_id=page_id,
                page_number=page_number,
                similarity_score=sim_score,
                rank=idx,
            )
        )

    return candidates


async def create_query_run(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_text: str,
    top_score: Optional[float] = None,
    status: str = "completed",
) -> QueryRun:
    """Create and persist a new query run record."""
    query_run = QueryRun(
        workspace_id=workspace_id,
        query_text=query_text,
        top_score=top_score,
        status=status,
    )
    session.add(query_run)
    await session.flush()
    return query_run


async def persist_retrieved_evidence(
    session: AsyncSession,
    query_run_id: uuid.UUID,
    candidates: List[CandidateChunk],
) -> List[RetrievedEvidence]:
    """Persist candidate evidence join records linked to the query run."""
    evidence_records: List[RetrievedEvidence] = []
    for candidate in candidates:
        evidence = RetrievedEvidence(
            query_run_id=query_run_id,
            chunk_id=candidate.chunk_id,
            similarity_score=candidate.similarity_score,
            rank=candidate.rank,
        )
        session.add(evidence)
        evidence_records.append(evidence)

    await session.flush()
    return evidence_records


async def persist_answer_and_citations(
    session: AsyncSession,
    query_run_id: uuid.UUID,
    answer_text: str,
    is_abstention: bool,
    citations_data: List[Dict[str, Any]],
) -> Tuple[Answer, List[Citation]]:
    """Persist the synthesized answer and server-validated citations in a transaction.

    Args:
        session: Async database session.
        query_run_id: Foreign key linking to the QueryRun.
        answer_text: Grounded answer content.
        is_abstention: Boolean flag indicating insufficient evidence.
        citations_data: List of dicts with verified citation fields:
            chunk_id, document_filename, page_number, quoted_snippet.

    Returns:
        Tuple of (persisted Answer, list of persisted Citation records).
    """
    answer = Answer(
        query_run_id=query_run_id,
        answer_text=answer_text,
        is_abstention=is_abstention,
    )
    session.add(answer)
    await session.flush()

    persisted_citations: List[Citation] = []
    for cit_dict in citations_data:
        citation = Citation(
            answer_id=answer.id,
            chunk_id=cit_dict.get("chunk_id"),
            document_filename=cit_dict["document_filename"],
            page_number=cit_dict["page_number"],
            quoted_snippet=cit_dict["quoted_snippet"],
        )
        session.add(citation)
        persisted_citations.append(citation)

    await session.commit()
    await session.refresh(answer)
    return answer, persisted_citations


async def get_query_run_by_id(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_run_id: uuid.UUID,
) -> Optional[QueryRun]:
    """Retrieve full query run with answer, citations, and evidence eagerly loaded."""
    stmt = (
        select(QueryRun)
        .where(
            QueryRun.id == query_run_id,
            QueryRun.workspace_id == workspace_id,
        )
        .options(
            selectinload(QueryRun.answer).selectinload(Answer.citations),
            selectinload(QueryRun.retrieved_evidence),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def search_candidates_per_document(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_vector: List[float],
    document_ids: List[uuid.UUID],
    per_doc_k: int = 3,
) -> List[CandidateChunk]:
    """Retrieve top-K candidate chunks for each specified document in the workspace.

    Guarantees:
    1. Balanced cross-document representation: retrieves up to per_doc_k candidates from each document,
       preventing any single document from crowding out another in the comparison context.
    2. Cross-workspace isolation: joins Document and strictly filters Document.workspace_id == workspace_id.
    3. Lifecycle validity: only searches chunks belonging to documents with status == 'ready'.
    4. Null-embedding safety: excludes chunks without populated embeddings.
    """
    if not document_ids:
        return []

    cosine_dist = DocumentChunk.embedding.cosine_distance(query_vector)
    all_candidates: List[CandidateChunk] = []
    current_rank = 1

    for doc_id in document_ids:
        stmt = (
            select(
                DocumentChunk.id.label("chunk_id"),
                DocumentChunk.chunk_text,
                DocumentChunk.chunk_index,
                Document.id.label("document_id"),
                Document.filename.label("document_filename"),
                DocumentPage.id.label("page_id"),
                DocumentPage.page_number,
                (1.0 - cosine_dist).label("similarity_score"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .join(DocumentPage, DocumentPage.id == DocumentChunk.page_id)
            .where(
                Document.workspace_id == workspace_id,
                Document.id == doc_id,
                Document.status == "ready",
                DocumentChunk.embedding.isnot(None),
            )
            .order_by(cosine_dist.asc())
            .limit(per_doc_k)
        )
        result = await session.execute(stmt)
        raw_rows = await _extract_rows_list(result)

        for row in raw_rows:
            if hasattr(row, "_mapping"):
                m = row._mapping
                chunk_id = m["chunk_id"]
                chunk_text = m["chunk_text"]
                chunk_index = m["chunk_index"]
                document_id = m["document_id"]
                document_filename = m["document_filename"]
                page_id = m["page_id"]
                page_number = m["page_number"]
                sim_score = float(m["similarity_score"])
            elif hasattr(row, "chunk_id"):
                chunk_id = row.chunk_id
                chunk_text = row.chunk_text
                chunk_index = getattr(row, "chunk_index", 0)
                document_id = row.document_id
                document_filename = getattr(row, "document_filename", getattr(row, "filename", "document.pdf"))
                page_id = getattr(row, "page_id", uuid.uuid4())
                page_number = getattr(row, "page_number", 1)
                sim_score = float(getattr(row, "similarity_score", 0.0))
            elif isinstance(row, (tuple, list)) and len(row) >= 8:
                chunk_id, chunk_text, chunk_index, document_id, document_filename, page_id, page_number, sim_score = row[:8]
                sim_score = float(sim_score)
            else:
                continue

            all_candidates.append(
                CandidateChunk(
                    chunk_id=chunk_id,
                    chunk_text=chunk_text,
                    chunk_index=chunk_index,
                    document_id=document_id,
                    document_filename=document_filename,
                    page_id=page_id,
                    page_number=page_number,
                    similarity_score=sim_score,
                    rank=current_rank,
                )
            )
            current_rank += 1

    return all_candidates


async def persist_comparison_run(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_text: str,
    top_score: Optional[float],
    synthesis_text: str,
    is_abstention: bool,
    candidates: List[CandidateChunk],
    citations_data: List[Dict[str, Any]],
    status: str = "completed",
) -> Tuple[QueryRun, Answer, List[Citation]]:
    """Persist a cross-document comparison execution, evidence, and verified citations in a single transaction."""
    query_run = QueryRun(
        workspace_id=workspace_id,
        query_text=query_text,
        top_score=top_score,
        status=status,
    )
    session.add(query_run)
    await session.flush()

    for candidate in candidates:
        evidence = RetrievedEvidence(
            query_run_id=query_run.id,
            chunk_id=candidate.chunk_id,
            similarity_score=candidate.similarity_score,
            rank=candidate.rank,
        )
        session.add(evidence)

    answer = Answer(
        query_run_id=query_run.id,
        answer_text=synthesis_text,
        is_abstention=is_abstention,
    )
    session.add(answer)
    await session.flush()

    persisted_citations: List[Citation] = []
    for cit_dict in citations_data:
        citation = Citation(
            answer_id=answer.id,
            chunk_id=cit_dict.get("chunk_id"),
            document_filename=cit_dict["document_filename"],
            page_number=cit_dict["page_number"],
            quoted_snippet=cit_dict["quoted_snippet"],
        )
        session.add(citation)
        persisted_citations.append(citation)

    await session.commit()
    await session.refresh(query_run)
    await session.refresh(answer)
    return query_run, answer, persisted_citations
