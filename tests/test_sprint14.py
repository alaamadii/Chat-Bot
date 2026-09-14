import os
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("WEB_SESSION_SECRET", "test-web-session-secret")

from fastapi.testclient import TestClient
from redis import RedisError
from starlette.requests import Request

from core.rate_limit import client_key, redis_rate_limiter
from db.database import SessionLocal, init_db
from db.reliability_models import OutboundDelivery
from delivery.models import DeliveryStatus
from intake.main import app
from services.outbox import outbox


class FakeRedis:
    def __init__(self, *, count=1, ttl=60, fail=False):
        self.count = count
        self.ttl = ttl
        self.fail = fail

    def eval(self, script, keys, key, window):
        if self.fail:
            raise RedisError("redis unavailable")
        return [self.count, self.ttl]

    def ping(self):
        if self.fail:
            raise RedisError("redis unavailable")
        return True

    def close(self):
        return None


def _install_fake(monkeypatch, fake):
    url = "redis://fake:6379/0"
    monkeypatch.setenv("REDIS_URL", url)
    redis_rate_limiter._client = fake
    redis_rate_limiter._url = url


def test_redis_rate_limit_is_shared_when_configured(monkeypatch):
    fake = FakeRedis(count=3, ttl=19)
    _install_fake(monkeypatch, fake)
    monkeypatch.setenv("PUBLIC_RATE_LIMIT", "2")
    monkeypatch.setenv("PUBLIC_RATE_WINDOW_SECONDS", "60")

    with TestClient(app) as client:
        response = client.post("/web/session")

    assert response.status_code == 429
    assert response.headers["retry-after"] == "19"
    redis_rate_limiter.reset()


def test_required_redis_failure_returns_503(monkeypatch):
    _install_fake(monkeypatch, FakeRedis(fail=True))
    monkeypatch.setenv("REDIS_REQUIRED", "true")

    with TestClient(app) as client:
        response = client.post("/web/session")

    assert response.status_code == 503
    redis_rate_limiter.reset()


def test_proxy_header_is_only_trusted_when_enabled(monkeypatch):
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"203.0.113.10")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    })

    monkeypatch.setenv("TRUST_PROXY_HEADERS", "false")
    assert client_key(request, "scope") == "scope:127.0.0.1"

    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    assert client_key(request, "scope") == "scope:203.0.113.10"


def test_outbox_processing_lease_prevents_duplicate_delivery(monkeypatch):
    init_db()
    monkeypatch.setenv("OUTBOX_PROCESSING_LEASE_SECONDS", "60")
    calls = {"count": 0}

    def fake_send(msg, channel, recipient, send_network=True):
        calls["count"] += 1
        return DeliveryStatus(success=True, channel=channel, timestamp=datetime.utcnow().isoformat())

    monkeypatch.setattr("services.outbox.engine.send", fake_send)
    item = outbox.enqueue(
        channel="whatsapp",
        recipient="15550001111",
        text="hello",
        max_attempts=3,
    )

    with SessionLocal() as db:
        row = db.get(OutboundDelivery, item.id)
        row.status = "processing"
        row.next_attempt_at = datetime.utcnow() + timedelta(seconds=60)
        db.commit()

    claimed = outbox.deliver_now(item.id)
    assert claimed.success is False
    assert claimed.error_details == "Delivery already claimed by another worker"
    assert calls["count"] == 0

    with SessionLocal() as db:
        row = db.get(OutboundDelivery, item.id)
        row.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()

    recovered = outbox.deliver_now(item.id)
    assert recovered.success is True
    assert calls["count"] == 1
    assert outbox.get(item.id)["status"] == "sent"
