import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
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


rate_limiter = SlidingWindowRateLimiter()


def client_key(request: Request, scope: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return f"{scope}:{host}"


def enforce_public_rate_limit(request: Request, scope: str) -> None:
    limit = int(os.getenv("PUBLIC_RATE_LIMIT", "60"))
    window = int(os.getenv("PUBLIC_RATE_WINDOW_SECONDS", "60"))
    rate_limiter.check(client_key(request, scope), limit=limit, window_seconds=window)
