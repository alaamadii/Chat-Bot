import logging
import os
import time
from datetime import datetime, timezone

import httpx

from delivery.models import DeliveryStatus, FormattedMessage

logger = logging.getLogger(__name__)


class DeliveryEngine:
    """Deliver formatted messages to supported channels with bounded retries."""

    def send(self, msg: FormattedMessage, channel: str, user_id: str, send_network: bool = True) -> DeliveryStatus:
        timestamp = datetime.now(timezone.utc).isoformat()
        if channel == "web_chat":
            return DeliveryStatus(success=True, channel=channel, timestamp=timestamp)
        if channel == "whatsapp":
            if not send_network:
                return DeliveryStatus(success=True, channel=channel, timestamp=timestamp)
            return self._send_whatsapp(msg.text, user_id, timestamp)
        return DeliveryStatus(success=False, channel=channel, timestamp=timestamp, error_details=f"Unsupported delivery channel: {channel}")

    def _send_whatsapp(self, text: str, recipient: str, timestamp: str) -> DeliveryStatus:
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        api_version = os.getenv("WHATSAPP_API_VERSION", "v23.0")
        max_attempts = max(1, int(os.getenv("DELIVERY_MAX_ATTEMPTS", "3")))
        retry_base = max(0.0, float(os.getenv("DELIVERY_RETRY_BASE_SECONDS", "0.25")))

        if not token or not phone_number_id:
            return DeliveryStatus(success=False, channel="whatsapp", timestamp=timestamp, error_details="WhatsApp credentials are not configured")

        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": text}}
        headers = {"Authorization": f"Bearer {token}"}
        last_error = "Delivery failed"

        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
                response.raise_for_status()
                logger.info("whatsapp message delivered", extra={"channel": "whatsapp", "event": "delivery_success", "attempt": attempt})
                return DeliveryStatus(success=True, channel="whatsapp", timestamp=timestamp)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                retryable = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (
                    isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500
                )
                if not retryable or attempt >= max_attempts:
                    break
                time.sleep(retry_base * (2 ** (attempt - 1)))

        logger.error("whatsapp delivery failed", extra={"channel": "whatsapp", "event": "delivery_failed", "attempts": max_attempts})
        return DeliveryStatus(success=False, channel="whatsapp", timestamp=timestamp, error_details=last_error)


engine = DeliveryEngine()
