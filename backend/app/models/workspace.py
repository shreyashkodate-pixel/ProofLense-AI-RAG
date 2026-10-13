"""ProofLens AI — Workspace Model.

Represents an isolated collection of uploaded documents, queries, and research sessions.
"""

from typing import List, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.query import QueryRun


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace entity providing multi-document scope isolation."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Cascading relationships: deleting a workspace removes all child records
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    query_runs: Mapped[List["QueryRun"]] = relationship(
        "QueryRun",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
