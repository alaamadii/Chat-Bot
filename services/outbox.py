import os
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select, update

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
        now = datetime.utcnow()
        lease_seconds = max(5, int(os.getenv("OUTBOX_PROCESSING_LEASE_SECONDS", "60")))

        with SessionLocal() as db:
            claim = db.execute(
                update(OutboundDelivery)
                .where(
                    OutboundDelivery.id == item_id,
                    OutboundDelivery.attempt_count < OutboundDelivery.max_attempts,
                    or_(
                        OutboundDelivery.status == "pending",
                        and_(
                            OutboundDelivery.status == "processing",
                            OutboundDelivery.next_attempt_at <= now,
                        ),
                    ),
                )
                .values(
                    status="processing",
                    attempt_count=OutboundDelivery.attempt_count + 1,
                    next_attempt_at=now + timedelta(seconds=lease_seconds),
                )
            )
            db.commit()

            item = db.get(OutboundDelivery, item_id)
            if not item:
                raise ValueError("Outbox item not found")

            if not claim.rowcount:
                if item.status == "sent":
                    return DeliveryStatus(
                        success=True,
                        channel=item.channel,
                        timestamp=(item.sent_at or now).isoformat(),
                    )
                if item.status == "dead" or item.attempt_count >= item.max_attempts:
                    if item.status != "dead":
                        item.status = "dead"
                        db.commit()
                    return DeliveryStatus(
                        success=False,
                        channel=item.channel,
                        timestamp=now.isoformat(),
                        error_details=item.last_error or "Delivery exhausted retries",
                    )
                return DeliveryStatus(
                    success=False,
                    channel=item.channel,
                    timestamp=now.isoformat(),
                    error_details="Delivery already claimed by another worker",
                )

            channel = item.channel
            recipient = item.recipient
            text = item.payload_text
            attempt = item.attempt_count
            max_attempts = item.max_attempts

        result = engine.send(
            FormattedMessage(text=text),
            channel,
            recipient,
            send_network=channel == "whatsapp",
        )

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
                    item.next_attempt_at = datetime.utcnow() + timedelta(
                        seconds=base * (2 ** max(attempt - 1, 0))
                    )
            db.commit()
        return result

    def process_pending(self, limit: int = 50) -> dict:
        now = datetime.utcnow()
        with SessionLocal() as db:
            ids = list(
                db.scalars(
                    select(OutboundDelivery.id)
                    .where(
                        or_(
                            and_(
                                OutboundDelivery.status == "pending",
                                OutboundDelivery.next_attempt_at <= now,
                            ),
                            and_(
                                OutboundDelivery.status == "processing",
                                OutboundDelivery.next_attempt_at <= now,
                            ),
                        )
                    )
                    .order_by(OutboundDelivery.created_at.asc())
                    .limit(limit)
                ).all()
            )

        sent = failed = skipped = 0
        for item_id in ids:
            result = self.deliver_now(item_id)
            if result.success:
                sent += 1
            elif result.error_details == "Delivery already claimed by another worker":
                skipped += 1
            else:
                failed += 1
        return {
            "processed": sent + failed,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
        }

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
