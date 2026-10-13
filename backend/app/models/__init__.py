"""ProofLens AI — Models Package.

Exports all SQLAlchemy relational models to ensure unified metadata registration.
"""

from app.models.base import Base
from app.models.citation import Citation
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.page import DocumentPage
from app.models.query import Answer, QueryRun, RetrievedEvidence
from app.models.workspace import Workspace

__all__ = [
    "Base",
    "Workspace",
    "Document",
    "DocumentPage",
    "DocumentChunk",
    "QueryRun",
    "RetrievedEvidence",
    "Answer",
    "Citation",
]
