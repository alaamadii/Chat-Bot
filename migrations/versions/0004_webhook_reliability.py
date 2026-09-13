"""Webhook reliability state.

Revision ID: 0004_webhook_reliability
Revises: 0003_knowledge_documents
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_webhook_reliability"
down_revision = "0003_knowledge_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "webhook_events" not in existing:
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("external_event_id", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("received_at", sa.DateTime(), nullable=False),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "external_event_id", name="uq_webhook_event_provider_external"),
        )
        op.create_index("ix_webhook_events_provider", "webhook_events", ["provider"])
        op.create_index("ix_webhook_events_external_event_id", "webhook_events", ["external_event_id"])
        op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
        op.create_index("ix_webhook_events_received_at", "webhook_events", ["received_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if "webhook_events" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("webhook_events")
