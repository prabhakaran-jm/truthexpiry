from __future__ import annotations

import pytest

from truthexpiry.ops.metrics import MetricsRegistry, init_metrics, reset_metrics


def test_disallowed_metric_label_rejected():
    registry = MetricsRegistry()
    with pytest.raises(ValueError, match="Disallowed metric label"):
        registry.increment("requests_total", labels={"channel_id": "C123"})


def test_allowed_labels_increment_counter():
    registry = MetricsRegistry()
    registry.increment(
        "requests_total",
        labels={"service": "slack-worker", "outcome": "success"},
    )
    snapshot = registry.snapshot()
    assert (
        snapshot["counters"]["requests_total{outcome=success,service=slack-worker}"]
        == 1
    )


def test_init_metrics_disabled_returns_none():
    reset_metrics()
    assert init_metrics(enabled=False) is None


def test_init_metrics_enabled_returns_registry():
    reset_metrics()
    registry = init_metrics(enabled=True)
    assert registry is not None
    reset_metrics()
