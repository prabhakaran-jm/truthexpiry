from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Literal

Outcome = Literal["success", "failure", "unavailable"]


class MetricsRegistry:
    """Bounded in-memory metrics with optional Prometheus export."""

    _ALLOWED_LABELS = frozenset({"service", "outcome", "failure_category"})

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._ready: dict[str, int] = {}

    def increment(
        self,
        name: str,
        *,
        labels: Mapping[str, str] | None = None,
        amount: int = 1,
    ) -> None:
        label_items = self._normalize_labels(labels or {})
        key = (name, label_items)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def observe_duration(self, name: str, seconds: float) -> None:
        millis = int(seconds * 1000)
        self.increment(name, labels={"outcome": "success"}, amount=millis)

    def set_ready(self, service: str, ready: bool) -> None:
        with self._lock:
            self._ready[service] = 1 if ready else 0

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = {
                self._format_key(name, labels): value
                for (name, labels), value in self._counters.items()
            }
            return {"counters": counters, "ready": dict(self._ready)}

    def _normalize_labels(
        self, labels: Mapping[str, str]
    ) -> tuple[tuple[str, str], ...]:
        for key in labels:
            if key not in self._ALLOWED_LABELS:
                raise ValueError(f"Disallowed metric label: {key}")
        return tuple(sorted(labels.items()))

    @staticmethod
    def _format_key(name: str, labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return name
        parts = ",".join(f"{key}={value}" for key, value in labels)
        return f"{name}{{{parts}}}"


_metrics: MetricsRegistry | None = None


def init_metrics(*, enabled: bool) -> MetricsRegistry | None:
    global _metrics
    if not enabled:
        _metrics = None
        return None
    _metrics = MetricsRegistry()
    return _metrics


def get_metrics() -> MetricsRegistry | None:
    return _metrics


def reset_metrics() -> None:
    global _metrics
    _metrics = None


class _NoOpMetrics:
    def increment(self, *args: object, **kwargs: object) -> None:
        return

    def observe_duration(self, *args: object, **kwargs: object) -> None:
        return

    def set_ready(self, *args: object, **kwargs: object) -> None:
        return


NO_OP_METRICS = _NoOpMetrics()


def metrics_or_noop() -> MetricsRegistry | _NoOpMetrics:
    return get_metrics() or NO_OP_METRICS
