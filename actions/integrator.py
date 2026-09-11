import logging
import os
import uuid

import httpx

from intake.models import NormalizedMessage

logger = logging.getLogger(__name__)


class APIIntegrator:
    """External business integrations with safe local fallback."""

    def create_crm_lead(self, message: NormalizedMessage) -> str:
        webhook = os.getenv("CRM_WEBHOOK_URL")
        lead_id = f"LD-{uuid.uuid4().hex[:8].upper()}"
        if not webhook:
            logger.info("crm webhook not configured; storing local lead reference", extra={"event": "crm_local_fallback"})
            return lead_id

        payload = {
            "lead_id": lead_id,
            "user_id": message.user_id,
            "channel": message.channel,
            "message": message.clean_text,
            "session_id": message.session_id,
        }
        headers = {}
        token = os.getenv("CRM_WEBHOOK_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = httpx.post(webhook, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json() if response.content else {}
            return str(data.get("id") or data.get("lead_id") or lead_id)
        except (httpx.HTTPError, ValueError):
            logger.exception("crm integration failed", extra={"event": "crm_delivery_failed"})
            return lead_id

    def check_order_status(self, user_id: str) -> str:
        webhook = os.getenv("ORDER_STATUS_WEBHOOK_URL")
        if not webhook:
            return "Order integration is not configured"
        try:
            response = httpx.get(webhook, params={"user_id": user_id}, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return str(data.get("status") or "Status unavailable")
        except (httpx.HTTPError, ValueError):
            logger.exception("order integration failed", extra={"event": "order_lookup_failed"})
            return "Status unavailable"


integrator = APIIntegrator()
