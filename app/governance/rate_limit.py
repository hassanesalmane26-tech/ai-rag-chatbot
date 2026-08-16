"""Small bounded in-process abuse boundary; distributed enforcement belongs at the edge."""

import threading
import time


class FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60, max_buckets: int = 10000):
        self.limit, self.window_seconds, self.max_buckets = limit, window_seconds, max_buckets
        self._buckets: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int, int]:
        now = int(time.time())
        window = now // self.window_seconds
        with self._lock:
            if len(self._buckets) >= self.max_buckets:
                self._buckets = {k: v for k, v in self._buckets.items() if v[0] >= window - 1}
            bucket_window, used = self._buckets.get(key, (window, 0))
            if bucket_window != window:
                bucket_window, used = window, 0
            used += 1
            self._buckets[key] = (bucket_window, used)
        retry_after = self.window_seconds - (now % self.window_seconds)
        return used <= self.limit, max(0, self.limit - used), retry_after
