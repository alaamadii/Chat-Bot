import os
from datetime import datetime, timedelta

from sqlalchemy import select

from db.database import SessionLocal
from db.reliability_models import OutboundDelivery
from delivery.engine import engine
from delivery.models import DeliveryStatus, FormattedMessage


class OutboxService:
    def enqueue(
        self,
        *,
        channel: str,
        recipient: str,
        text: str,
        conversation_id: str | None = None,
        message_id: str | None = None,
        max_attempts: int | None = None,
    ) -> OutboundDelivery:
        attempts = max_attempts or int(os.getenv("OUTBOX_MAX_ATTEMPTS", "5"))
        with SessionLocal() as db:
            item = OutboundDelivery(
                conversation_id=conversation_id,
                message_id=message_id,
                channel=channel,
                recipient=recipient,
                payload_text=text,
                max_attempts=max(1, attempts),
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            db.expunge(item)
            return item

    def deliver_now(self, item_id: str) -> DeliveryStatus:
        with SessionLocal() as db:
            item = db.get(OutboundDelivery, item_id)
            if not item:
                raise ValueError("Outbox item not found")
            if item.status == "sent":
                return DeliveryStatus(success=True, channel=item.channel, timestamp=(item.sent_at or datetime.utcnow()).isoformat())
            if item.status == "dead":
                return DeliveryStatus(success=False, channel=item.channel, timestamp=datetime.utcnow().isoformat(), error_details=item.last_error or "Delivery exhausted retries")
            if item.attempt_count >= item.max_attempts:
                item.status = "dead"
                db.commit()
                return DeliveryStatus(success=False, channel=item.channel, timestamp=datetime.utcnow().isoformat(), error_details=item.last_error or "Delivery exhausted retries")

            item.status = "processing"
            item.attempt_count += 1
            db.commit()
            channel = item.channel
            recipient = item.recipient
            text = item.payload_text
            attempt = item.attempt_count
            max_attempts = item.max_attempts

        result = engine.send(FormattedMessage(text=text), channel, recipient, send_network=channel == "whatsapp")

        with SessionLocal() as db:
            item = db.get(OutboundDelivery, item_id)
            if not item:
                return result
            if result.success:
                item.status = "sent"
                item.sent_at = datetime.utcnow()
                item.last_error = None
            else:
                item.last_error = result.error_details or "Delivery failed"
                if attempt >= max_attempts:
                    item.status = "dead"
                else:
                    base = float(os.getenv("OUTBOX_RETRY_BASE_SECONDS", "5"))
                    item.status = "pending"
                    item.next_attempt_at = datetime.utcnow() + timedelta(seconds=base * (2 ** max(attempt - 1, 0)))
            db.commit()
        return result

    def process_pending(self, limit: int = 50) -> dict:
        now = datetime.utcnow()
        with SessionLocal() as db:
            ids = list(db.scalars(
                select(OutboundDelivery.id)
                .where(
                    OutboundDelivery.status == "pending",
                    OutboundDelivery.next_attempt_at <= now,
                )
                .order_by(OutboundDelivery.created_at.asc())
                .limit(limit)
            ).all())
        sent = failed = 0
        for item_id in ids:
            result = self.deliver_now(item_id)
            if result.success:
                sent += 1
            else:
                failed += 1
        return {"processed": len(ids), "sent": sent, "failed": failed}

    def get(self, item_id: str) -> dict | None:
        with SessionLocal() as db:
            item = db.get(OutboundDelivery, item_id)
            if not item:
                return None
            return {
                "id": item.id,
                "conversation_id": item.conversation_id,
                "message_id": item.message_id,
                "channel": item.channel,
                "recipient": item.recipient,
                "status": item.status,
                "attempt_count": item.attempt_count,
                "max_attempts": item.max_attempts,
                "last_error": item.last_error,
                "next_attempt_at": item.next_attempt_at.isoformat(),
                "created_at": item.created_at.isoformat(),
                "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            }


outbox = OutboxService()
