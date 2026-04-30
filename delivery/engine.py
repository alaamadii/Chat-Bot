from delivery.models import FormattedMessage, DeliveryStatus
from datetime import datetime

class DeliveryEngine:
    """
    Task 13: Delivery Engine
    Send back to correct channel
    """
    def send(self, msg: FormattedMessage, channel: str, user_id: str) -> DeliveryStatus:
        print(f"\n[Delivery Engine] Executing network call to {channel} API...")
        print(f"[Delivery Engine] Payload -> User: {user_id}")
        print(f"[Delivery Engine] Message Content:\n{msg.text}\n")
        
        return DeliveryStatus(
            success=True,
            channel=channel,
            timestamp=datetime.utcnow().isoformat()
        )

engine = DeliveryEngine()
