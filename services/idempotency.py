from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.database import SessionLocal
from db.reliability_models import WebhookEvent


class WebhookIdempotencyService:
    def begin(self, provider: str, external_event_id: str) -> bool:
        if not external_event_id:
            return True
        with SessionLocal() as db:
            existing = db.scalar(
                select(WebhookEvent).where(
                    WebhookEvent.provider == provider,
                    WebhookEvent.external_event_id == external_event_id,
                )
            )
            if existing:
                if existing.status == "failed":
                    existing.status = "processing"
                    existing.processed_at = None
                    db.commit()
                    return True
                return False

            db.add(WebhookEvent(provider=provider, external_event_id=external_event_id))
            try:
                db.commit()
                return True
            except IntegrityError:
                db.rollback()
                return False

    def complete(self, provider: str, external_event_id: str) -> None:
        self._finish(provider, external_event_id, "completed")

    def fail(self, provider: str, external_event_id: str) -> None:
        self._finish(provider, external_event_id, "failed")

    def _finish(self, provider: str, external_event_id: str, status: str) -> None:
        if not external_event_id:
            return
        with SessionLocal() as db:
            event = db.scalar(
                select(WebhookEvent).where(
                    WebhookEvent.provider == provider,
                    WebhookEvent.external_event_id == external_event_id,
                )
            )
            if event:
                event.status = status
                event.processed_at = datetime.utcnow()
                db.commit()


webhook_idempotency = WebhookIdempotencyService()
