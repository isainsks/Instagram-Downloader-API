import threading
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    requests: int
    resets_at: float


class FixedWindowRateLimiter:
    """Thread-safe, in-memory fixed-window rate limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, identity: str, limit: int, window_seconds: int) -> tuple[int, int]:
        now = time.time()

        with self._lock:
            bucket = self._buckets.get(identity)
            if bucket is None or now >= bucket.resets_at:
                bucket = _Bucket(requests=0, resets_at=now + window_seconds)
                self._buckets[identity] = bucket

            retry_after = max(1, int(bucket.resets_at - now) + 1)
            if bucket.requests >= limit:
                return -1, retry_after

            bucket.requests += 1
            remaining = max(0, limit - bucket.requests)

            if len(self._buckets) > 10_000:
                self._buckets = {
                    key: value
                    for key, value in self._buckets.items()
                    if value.resets_at > now
                }

            return remaining, retry_after
