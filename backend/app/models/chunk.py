"""ProofLens AI — DocumentChunk Model.

Stores page-bounded semantic chunks and 768-dimension pgvector embeddings.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.citation import Citation
    from app.models.document import Document
    from app.models.page import DocumentPage


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantic text chunk strictly bounded to a physical page."""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # 768-dimensional vector embedding for gemini-embedding-2
    embedding = mapped_column(Vector(768), nullable=True)
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gemini-embedding-2",
    )
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    page: Mapped["DocumentPage"] = relationship("DocumentPage", back_populates="chunks")
    citations: Mapped[List["Citation"]] = relationship(
        "Citation",
        back_populates="chunk",
    )
