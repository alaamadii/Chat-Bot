"""Semantic embedding metadata for knowledge chunks.

Revision ID: 0005_semantic_embeddings
Revises: 0004_webhook_reliability
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_semantic_embeddings"
down_revision = "0004_webhook_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_chunks" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("knowledge_chunks")}
    with op.batch_alter_table("knowledge_chunks") as batch:
        if "embedding_json" not in columns:
            batch.add_column(sa.Column("embedding_json", sa.JSON(), nullable=True))
        if "embedding_provider" not in columns:
            batch.add_column(sa.Column("embedding_provider", sa.String(length=100), nullable=True))
        if "embedding_model" not in columns:
            batch.add_column(sa.Column("embedding_model", sa.String(length=150), nullable=True))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_chunks")}
    if "ix_knowledge_chunks_embedding_provider" not in indexes:
        op.create_index("ix_knowledge_chunks_embedding_provider", "knowledge_chunks", ["embedding_provider"])


def downgrade() -> None:
    bind = op.get_bind()
    if "knowledge_chunks" not in set(sa.inspect(bind).get_table_names()):
        return
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_chunks")}
    if "ix_knowledge_chunks_embedding_provider" in indexes:
        op.drop_index("ix_knowledge_chunks_embedding_provider", table_name="knowledge_chunks")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("knowledge_chunks")}
    with op.batch_alter_table("knowledge_chunks") as batch:
        if "embedding_model" in columns:
            batch.drop_column("embedding_model")
        if "embedding_provider" in columns:
            batch.drop_column("embedding_provider")
        if "embedding_json" in columns:
            batch.drop_column("embedding_json")
