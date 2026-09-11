"""AI quality and customer feedback tables.

Revision ID: 0002_ai_quality
Revises: 0001_baseline
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_ai_quality"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "conversation_feedback" not in existing:
        op.create_table(
            "conversation_feedback",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_conversation_feedback_conversation_id", "conversation_feedback", ["conversation_id"])
        op.create_index("ix_conversation_feedback_user_id", "conversation_feedback", ["user_id"])
        op.create_index("ix_conversation_feedback_created_at", "conversation_feedback", ["created_at"])

    if "ai_interaction_metrics" not in existing:
        op.create_table(
            "ai_interaction_metrics",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("conversation_id", sa.String(length=36), nullable=False),
            sa.Column("intent", sa.String(length=100), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model", sa.String(length=100), nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("escalated", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("conversation_id", "intent", "provider", "model", "created_at"):
            op.create_index(f"ix_ai_interaction_metrics_{column}", "ai_interaction_metrics", [column])


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "ai_interaction_metrics" in existing:
        op.drop_table("ai_interaction_metrics")
    if "conversation_feedback" in existing:
        op.drop_table("conversation_feedback")
