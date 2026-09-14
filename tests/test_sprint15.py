import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_chatbot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("WEB_SESSION_SECRET", "test-web-session-secret")

from db.database import init_db
from db.repository import conversation_repository
from intake.main import app
from services import realtime


class FakePublisher:
    def __init__(self):
        self.calls = []
        self.closed = False

    def publish(self, channel, payload):
        self.calls.append((channel, payload))
        return 1

    def close(self):
        self.closed = True


def test_publish_message_uses_conversation_channel(monkeypatch):
    fake = FakePublisher()
    monkeypatch.setattr(realtime, "_get_sync_client", lambda: fake)

    payload = {
        "id": "message-1",
        "conversation_id": "conversation-1",
        "role": "agent",
        "text": "hello",
    }
    assert realtime.publish_message(payload) is True
    assert fake.closed is True
    assert fake.calls[0][0] == "chatbot:conversation:conversation-1"
    assert json.loads(fake.calls[0][1])["id"] == "message-1"


def test_message_insert_is_published_after_persistence(monkeypatch):
    init_db()
    fake = FakePublisher()
    monkeypatch.setattr(realtime, "_get_sync_client", lambda: fake)

    user_id = "realtime-user-" + str(uuid.uuid4())
    conversation = conversation_repository.get_or_create_conversation(user_id, "web_chat")
    message_id = conversation_repository.add_text_message(
        conversation_id=conversation.id,
        role="agent",
        user_id="agent",
        channel="web_chat",
        text="A live reply",
    )

    assert fake.calls
    channel, raw = fake.calls[-1]
    event = json.loads(raw)
    assert channel == f"chatbot:conversation:{conversation.id}"
    assert event["id"] == message_id
    assert event["role"] == "agent"
    assert event["text"] == "A live reply"


def test_distributed_sse_route_precedes_legacy_polling_route():
    matching = [
        route for route in app.routes
        if getattr(route, "path", None) == "/web/conversations/{conversation_id}/events"
    ]
    assert len(matching) == 2
    assert matching[0].endpoint.__name__ == "distributed_web_conversation_events"
