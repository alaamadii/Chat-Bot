from sqlalchemy import select

from db.database import SessionLocal
from db.models import AuditEvent


def record_audit(actor: str, action: str, resource_type: str, resource_id: str | None = None, details: dict | None = None) -> None:
    with SessionLocal() as db:
        db.add(AuditEvent(actor=actor, action=action, resource_type=resource_type, resource_id=resource_id, details=details or {}))
        db.commit()


def list_audit_events(limit: int = 100) -> list[dict]:
    with SessionLocal() as db:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        rows = list(db.scalars(stmt).all())
        return [
            {
                "id": row.id,
                "actor": row.actor,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "details": row.details,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
