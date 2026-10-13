"""ProofLens AI — Citation Model.

Implements the Snapshot Tombstone Citation Pattern:
- References document_chunks(id) ON DELETE SET NULL.
- Persists immutable historical snapshots (document_filename, page_number, quoted_snippet).
- Survives document/chunk deletions as an immutable tombstone linked to the answer.
"""

import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chunk import DocumentChunk
    from app.models.query import Answer


class Citation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Citation entity linking answers to verified chunks with tombstone durability."""

    __tablename__ = "citations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tombstone foreign key: when underlying chunk is deleted, chunk_id is set to NULL
    chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Immutable historical snapshot preserving evidence context permanently
    document_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_snippet: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    answer: Mapped["Answer"] = relationship("Answer", back_populates="citations")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="citations",
    )
