import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(limit: int, window_seconds: int):
    """In-memory sliding-window limiter (per process). Disabled when ENV=test."""

    def dep(request: Request):
        if get_settings().env == "test":
            return
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
        q.append(now)

    return dep
