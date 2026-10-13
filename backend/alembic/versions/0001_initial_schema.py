"""Initial schema with pgvector, document hierarchy, and tombstone citations.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-13 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import pgvector
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Workspaces Table
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspaces_id", "workspaces", ["id"])

    # 3. Documents Table
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "content_hash", name="uq_workspace_content_hash"),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # 4. Document Pages Table
    op.create_table(
        "document_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )
    op.create_index("ix_document_pages_id", "document_pages", ["id"])
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])

    # 5. Document Chunks Table
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", UUID(as_uuid=True), sa.ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=False, server_default="gemini-embedding-2"),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    op.create_index("ix_document_chunks_id", "document_chunks", ["id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_page_id", "document_chunks", ["page_id"])

    # HNSW Vector Index for Cosine Distance
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # 6. Query Runs Table
    op.create_table(
        "query_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("run_type", sa.String(50), nullable=False, server_default="query"),
        sa.Column("top_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_query_runs_id", "query_runs", ["id"])
    op.create_index("ix_query_runs_workspace_id", "query_runs", ["workspace_id"])
    op.create_index("ix_query_runs_run_type", "query_runs", ["run_type"])

    # 7. Answers Table
    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("query_run_id", UUID(as_uuid=True), sa.ForeignKey("query_runs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("is_abstention", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_answers_id", "answers", ["id"])
    op.create_index("ix_answers_query_run_id", "answers", ["query_run_id"])

    # 8. Citations Table (Tombstone pattern: ON DELETE SET NULL on chunk_id)
    op.create_table(
        "citations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("answer_id", UUID(as_uuid=True), sa.ForeignKey("answers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_filename", sa.String(255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("quoted_snippet", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_citations_id", "citations", ["id"])
    op.create_index("ix_citations_answer_id", "citations", ["answer_id"])
    op.create_index("ix_citations_chunk_id", "citations", ["chunk_id"])

    # 9. Retrieved Evidence Table
    op.create_table(
        "retrieved_evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("query_run_id", UUID(as_uuid=True), sa.ForeignKey("query_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieved_evidence_id", "retrieved_evidence", ["id"])
    op.create_index("ix_retrieved_evidence_query_run_id", "retrieved_evidence", ["query_run_id"])
    op.create_index("ix_retrieved_evidence_chunk_id", "retrieved_evidence", ["chunk_id"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("retrieved_evidence")
    op.drop_table("citations")
    op.drop_table("answers")
    op.drop_table("query_runs")
    op.drop_table("document_chunks")
    op.drop_table("document_pages")
    op.drop_table("documents")
    op.drop_table("workspaces")
    op.execute("DROP EXTENSION IF EXISTS vector;")
