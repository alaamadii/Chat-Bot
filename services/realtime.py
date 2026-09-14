import json
import logging
import os
from collections.abc import AsyncIterator

from redis import Redis, RedisError
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import event

from db.models import Message

logger = logging.getLogger(__name__)
CHANNEL_PREFIX = "chatbot:conversation"


def channel_name(conversation_id: str) -> str:
    return f"{CHANNEL_PREFIX}:{conversation_id}"


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def _get_sync_client() -> Redis | None:
    url = _redis_url()
    if not url:
        return None
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        health_check_interval=30,
    )


def publish_message(payload: dict) -> bool:
    client = _get_sync_client()
    if client is None:
        return False
    try:
        client.publish(
            channel_name(str(payload["conversation_id"])),
            json.dumps(payload, separators=(",", ":"), default=str),
        )
        return True
    except RedisError:
        logger.warning("realtime publish failed", exc_info=True)
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


@event.listens_for(Message, "after_insert")
def _publish_inserted_message(mapper, connection, target: Message) -> None:
    publish_message({
        "id": target.id,
        "conversation_id": target.conversation_id,
        "role": target.role,
        "user_id": target.user_id,
        "channel": target.channel,
        "text": target.text,
        "metadata": target.metadata_json or {},
        "created_at": target.created_at.isoformat() if target.created_at else None,
    })


async def subscribe(conversation_id: str) -> AsyncIterator[dict | None]:
    """Yield Redis messages; None is a keepalive tick. Raises RedisError on backend failure."""
    url = _redis_url()
    if not url:
        raise RedisError("Redis realtime backend is not configured")

    client = AsyncRedis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=2.0,
        health_check_interval=30,
    )
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel_name(conversation_id))
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if message is None:
                yield None
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                payload = json.loads(data)
            except (TypeError, json.JSONDecodeError):
                logger.warning("invalid realtime payload ignored")
                continue
            yield payload
    finally:
        try:
            await pubsub.unsubscribe(channel_name(conversation_id))
        finally:
            await pubsub.aclose()
            await client.aclose()
