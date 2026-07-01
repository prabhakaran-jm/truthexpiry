from __future__ import annotations

import threading
import time
from collections import OrderedDict


class BoundedEventIdCache:
    """Bounded in-memory Slack ``event_id`` cache for duplicate delivery suppression."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 300.0,
        max_size: int = 10_000,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def is_duplicate(self, event_id: str) -> bool:
        """Record ``event_id`` and return True when it was seen within the TTL window."""
        normalized = event_id.strip()
        if not normalized:
            return False

        now = time.monotonic()
        with self._lock:
            self._evict_expired(now)
            if normalized in self._entries:
                return True
            self._entries[normalized] = now
            if len(self._entries) > self._max_size:
                self._entries.popitem(last=False)
            return False

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self._ttl_seconds
        while self._entries:
            oldest_id, oldest_seen = next(iter(self._entries.items()))
            if oldest_seen >= cutoff:
                break
            self._entries.pop(oldest_id, None)


_event_dedup_cache: BoundedEventIdCache | None = None


def init_event_dedup_cache(*, enabled: bool) -> BoundedEventIdCache | None:
    global _event_dedup_cache
    if not enabled:
        _event_dedup_cache = None
        return None
    cache = BoundedEventIdCache()
    _event_dedup_cache = cache
    return cache


def get_event_dedup_cache() -> BoundedEventIdCache | None:
    return _event_dedup_cache


def reset_event_dedup_cache() -> None:
    global _event_dedup_cache
    _event_dedup_cache = None
