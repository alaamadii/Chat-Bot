import httpx

from delivery.engine import DeliveryEngine


def test_whatsapp_retries_transient_server_error(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone")
    monkeypatch.setenv("DELIVERY_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("DELIVERY_RETRY_BASE_SECONDS", "0")
    attempts = {"count": 0}

    class Response:
        status_code = 200
        def raise_for_status(self):
            attempts["count"] += 1
            if attempts["count"] < 3:
                request = httpx.Request("POST", "https://example.test")
                response = httpx.Response(503, request=request)
                raise httpx.HTTPStatusError("temporary", request=request, response=response)

    monkeypatch.setattr("delivery.engine.httpx.post", lambda *args, **kwargs: Response())
    result = DeliveryEngine()._send_whatsapp("hello", "123", "now")
    assert result.success is True
    assert attempts["count"] == 3


def test_whatsapp_does_not_retry_client_error(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone")
    monkeypatch.setenv("DELIVERY_MAX_ATTEMPTS", "3")
    attempts = {"count": 0}

    def fail(*args, **kwargs):
        attempts["count"] += 1
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("bad request", request=request, response=response)

    monkeypatch.setattr("delivery.engine.httpx.post", fail)
    result = DeliveryEngine()._send_whatsapp("hello", "123", "now")
    assert result.success is False
    assert attempts["count"] == 1
