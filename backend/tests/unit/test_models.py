"""ProofLens AI — Unit Tests for Database Schema & Model Metadata.

Verifies table mappings, foreign key cascade behaviors, tombstone citation constraints,
and vector dimension definitions without requiring live database access.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipDirection

from app.models import (
    Answer,
    Base,
    Citation,
    Document,
    DocumentChunk,
    DocumentPage,
    QueryRun,
    RetrievedEvidence,
    Workspace,
)


def test_models_registered_in_metadata():
    """Verify all required Phase 2 tables are properly registered in Base metadata."""
    tables = Base.metadata.tables.keys()
    expected_tables = {
        "workspaces",
        "documents",
        "document_pages",
        "document_chunks",
        "query_runs",
        "answers",
        "citations",
        "retrieved_evidence",
    }
    for table_name in expected_tables:
        assert table_name in tables, f"Expected table '{table_name}' missing from metadata."


def test_document_unique_constraint():
    """Verify documents table enforces (workspace_id, content_hash) uniqueness."""
    table = Base.metadata.tables["documents"]
    unique_constraints = [c.name for c in table.constraints if hasattr(c, "columns")]
    assert "uq_workspace_content_hash" in unique_constraints

    uc = next(c for c in table.constraints if c.name == "uq_workspace_content_hash")
    col_names = {col.name for col in uc.columns}
    assert col_names == {"workspace_id", "content_hash"}


def test_document_page_unique_constraint():
    """Verify document_pages enforces (document_id, page_number) uniqueness."""
    table = Base.metadata.tables["document_pages"]
    uc = next(c for c in table.constraints if c.name == "uq_document_page")
    col_names = {col.name for col in uc.columns}
    assert col_names == {"document_id", "page_number"}


def test_document_chunk_unique_constraint_and_vector():
    """Verify document_chunks enforces (document_id, chunk_index) and uses Vector(768)."""
    table = Base.metadata.tables["document_chunks"]
    uc = next(c for c in table.constraints if c.name == "uq_document_chunk_index")
    col_names = {col.name for col in uc.columns}
    assert col_names == {"document_id", "chunk_index"}

    embedding_col = table.columns["embedding"]
    assert isinstance(embedding_col.type, Vector)
    assert embedding_col.type.dim == 768


def test_citation_tombstone_foreign_key():
    """Verify Citation.chunk_id is nullable and configured with ON DELETE SET NULL."""
    table = Base.metadata.tables["citations"]
    chunk_fk = next(fk for fk in table.foreign_keys if fk.column.table.name == "document_chunks")

    assert chunk_fk.ondelete == "SET NULL"
    assert table.columns["chunk_id"].nullable is True

    # Verify historical snapshot fields are NOT nullable
    assert table.columns["document_filename"].nullable is False
    assert table.columns["page_number"].nullable is False
    assert table.columns["quoted_snippet"].nullable is False


def test_cascading_deletions():
    """Verify cascading delete configurations on child models."""
    doc_table = Base.metadata.tables["documents"]
    ws_fk = next(fk for fk in doc_table.foreign_keys if fk.column.table.name == "workspaces")
    assert ws_fk.ondelete == "CASCADE"

    page_table = Base.metadata.tables["document_pages"]
    page_fk = next(fk for fk in page_table.foreign_keys if fk.column.table.name == "documents")
    assert page_fk.ondelete == "CASCADE"

    chunk_table = Base.metadata.tables["document_chunks"]
    chunk_doc_fk = next(fk for fk in chunk_table.foreign_keys if fk.column.table.name == "documents")
    assert chunk_doc_fk.ondelete == "CASCADE"
