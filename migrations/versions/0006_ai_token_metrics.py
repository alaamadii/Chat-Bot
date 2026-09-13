"""AI token usage metrics.

Revision ID: 0006_ai_token_metrics
Revises: 0005_semantic_embeddings
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_ai_token_metrics"
down_revision = "0005_semantic_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "ai_interaction_metrics" not in set(sa.inspect(bind).get_table_names()):
        return
    columns = {column["name"] for column in sa.inspect(bind).get_columns("ai_interaction_metrics")}
    with op.batch_alter_table("ai_interaction_metrics") as batch:
        if "input_tokens" not in columns:
            batch.add_column(sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"))
        if "output_tokens" not in columns:
            batch.add_column(sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    bind = op.get_bind()
    if "ai_interaction_metrics" not in set(sa.inspect(bind).get_table_names()):
        return
    columns = {column["name"] for column in sa.inspect(bind).get_columns("ai_interaction_metrics")}
    with op.batch_alter_table("ai_interaction_metrics") as batch:
        if "output_tokens" in columns:
            batch.drop_column("output_tokens")
        if "input_tokens" in columns:
            batch.drop_column("input_tokens")
