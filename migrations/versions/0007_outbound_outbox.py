"""Outbound delivery outbox.

Revision ID: 0007_outbound_outbox
Revises: 0006_ai_token_metrics
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_outbound_outbox"
down_revision = "0006_ai_token_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "outbound_deliveries" in set(sa.inspect(bind).get_table_names()):
        return
    op.create_table(
        "outbound_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("payload_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("conversation_id", "message_id", "channel", "recipient", "status", "next_attempt_at", "created_at"):
        op.create_index(f"ix_outbound_deliveries_{column}", "outbound_deliveries", [column])


def downgrade() -> None:
    bind = op.get_bind()
    if "outbound_deliveries" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("outbound_deliveries")
