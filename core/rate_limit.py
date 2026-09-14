import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status
from redis import Redis, RedisError


class SlidingWindowRateLimiter:
    """Single-process fallback limiter used when Redis is not configured."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                    headers={"Retry-After": str(window_seconds)},
                )
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class RedisRateLimiter:
    """Atomic fixed-window limiter shared by all API replicas."""

    SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

    def __init__(self) -> None:
        self._client: Redis | None = None
        self._url: str | None = None
        self._lock = Lock()

    def _get_client(self, url: str) -> Redis:
        with self._lock:
            if self._client is None or self._url != url:
                self._client = Redis.from_url(
                    url,
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                    health_check_interval=30,
                )
                self._url = url
            return self._client

    def check(self, key: str, *, limit: int, window_seconds: int) -> bool:
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return False
        client = self._get_client(url)
        redis_key = f"chatbot:rate-limit:{key}"
        current, ttl = client.eval(self.SCRIPT, 1, redis_key, max(1, window_seconds))
        if int(current) > limit:
            retry_after = max(1, int(ttl))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )
        return True

    def ping(self) -> bool:
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            return False
        return bool(self._get_client(url).ping())

    def reset(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None
            self._url = None


rate_limiter = SlidingWindowRateLimiter()
redis_rate_limiter = RedisRateLimiter()


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def client_key(request: Request, scope: str) -> str:
    host = request.client.host if request.client else "unknown"
    if _truthy("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            host = forwarded
    return f"{scope}:{host}"


def enforce_public_rate_limit(request: Request, scope: str) -> None:
    limit = max(1, int(os.getenv("PUBLIC_RATE_LIMIT", "60")))
    window = max(1, int(os.getenv("PUBLIC_RATE_WINDOW_SECONDS", "60")))
    key = client_key(request, scope)

    try:
        if redis_rate_limiter.check(key, limit=limit, window_seconds=window):
            return
    except RedisError as exc:
        if _truthy("REDIS_REQUIRED"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Distributed runtime unavailable",
            ) from exc

    rate_limiter.check(key, limit=limit, window_seconds=window)
