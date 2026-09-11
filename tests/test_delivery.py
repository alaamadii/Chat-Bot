from types import SimpleNamespace

from delivery.engine import DeliveryEngine
from delivery.models import FormattedMessage


def test_whatsapp_delivery_calls_meta_api(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_API_VERSION", "v23.0")

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("delivery.engine.httpx.post", fake_post)

    engine = DeliveryEngine()
    status = engine.send(
        FormattedMessage(text="Hello from the bot"),
        channel="whatsapp",
        user_id="201000000000",
    )

    assert status.success is True
    assert captured["url"] == "https://graph.facebook.com/v23.0/123456/messages"
    assert captured["json"]["to"] == "201000000000"
    assert captured["json"]["text"]["body"] == "Hello from the bot"
    assert captured["headers"]["Authorization"] == "Bearer token"


def test_whatsapp_delivery_fails_cleanly_without_credentials(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)

    engine = DeliveryEngine()
    status = engine.send(
        FormattedMessage(text="Hello"),
        channel="whatsapp",
        user_id="201000000000",
    )

    assert status.success is False
    assert "credentials" in status.error_details.lower()
