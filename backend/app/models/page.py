"""ProofLens AI — DocumentPage Model.

Preserves exact physical page-level provenance extracted from uploaded PDFs.
"""

import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chunk import DocumentChunk
    from app.models.document import Document


class DocumentPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a physical single page extracted from a PDF."""

    __tablename__ = "document_pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="page",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
