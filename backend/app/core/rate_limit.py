"""Simple in-memory sliding-window rate limiter.

Good enough for a single-process deployment. For multiple workers/instances,
replace the storage with Redis (same interface).
"""
import threading
import time
from collections import defaultdict, deque

from app.core.exceptions import RateLimitError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise RateLimitError("Too many requests. Please wait a minute and try again.")
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
