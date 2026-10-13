"""ProofLens AI — QueryRun, Answer, and RetrievedEvidence Models.

Tracks question answering execution sessions, candidate evidence ranking,
and grounded synthesized answers.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.citation import Citation
    from app.models.chunk import DocumentChunk
    from app.models.workspace import Workspace


class QueryRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a question answering or research query execution."""

    __tablename__ = "query_runs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    top_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="query_runs")
    answer: Mapped[Optional["Answer"]] = relationship(
        "Answer",
        back_populates="query_run",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    retrieved_evidence: Mapped[List["RetrievedEvidence"]] = relationship(
        "RetrievedEvidence",
        back_populates="query_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RetrievedEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Join record tracking candidate chunks retrieved for a specific query run."""

    __tablename__ = "retrieved_evidence"

    query_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    query_run: Mapped["QueryRun"] = relationship("QueryRun", back_populates="retrieved_evidence")
    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk")


class Answer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Synthesized answer record linked to a query run and supporting citations."""

    __tablename__ = "answers"

    query_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_abstention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    query_run: Mapped["QueryRun"] = relationship("QueryRun", back_populates="answer")
    citations: Mapped[List["Citation"]] = relationship(
        "Citation",
        back_populates="answer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
