"""Knowledge documents and chunks.

Revision ID: 0003_knowledge_documents
Revises: 0002_ai_quality
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_knowledge_documents"
down_revision = "0002_ai_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "knowledge_documents" not in existing:
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("source", sa.String(length=500), nullable=False),
            sa.Column("content_type", sa.String(length=50), nullable=False),
            sa.Column("checksum", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("checksum"),
        )
        op.create_index("ix_knowledge_documents_title", "knowledge_documents", ["title"])
        op.create_index("ix_knowledge_documents_checksum", "knowledge_documents", ["checksum"], unique=True)
        op.create_index("ix_knowledge_documents_created_by", "knowledge_documents", ["created_by"])
        op.create_index("ix_knowledge_documents_created_at", "knowledge_documents", ["created_at"])

    existing = set(sa.inspect(bind).get_table_names())
    if "knowledge_chunks" not in existing:
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_document_index"),
        )
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
        op.create_index("ix_knowledge_chunks_created_at", "knowledge_chunks", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "knowledge_chunks" in existing:
        op.drop_table("knowledge_chunks")
    if "knowledge_documents" in existing:
        op.drop_table("knowledge_documents")
