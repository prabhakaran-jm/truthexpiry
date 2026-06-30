from __future__ import annotations

import socket

import pytest

from truthexpiry.ops.metrics import (
    MetricsRegistry,
    init_metrics,
    reset_metrics,
    start_metrics_server,
)


def test_disallowed_metric_label_rejected():
    registry = MetricsRegistry()
    with pytest.raises(ValueError, match="Disallowed metric label"):
        registry.increment("requests_total", labels={"channel_id": "C123"})


def test_allowed_labels_increment_counter():
    registry = MetricsRegistry()
    registry.increment(
        "requests_total",
        labels={"outcome": "success"},
    )
    snapshot = registry.snapshot()
    assert (
        snapshot["counters"]["requests_total{outcome=success,service=slack-worker}"]
        == 1
    )


def test_stage_failure_counters_increment():
    registry = MetricsRegistry()
    registry.increment("rts_failures_total", labels={})
    registry.increment("extraction_failures_total", labels={})
    registry.increment("lifecycle_failures_total", labels={})
    registry.increment("socket_mode_reconnects_total", labels={})
    snapshot = registry.snapshot()
    assert snapshot["counters"]["rts_failures_total{service=slack-worker}"] == 1
    assert snapshot["counters"]["extraction_failures_total{service=slack-worker}"] == 1


def test_render_prometheus_includes_ready_gauge():
    registry = MetricsRegistry()
    registry.increment("requests_total", labels={"outcome": "success"})
    registry.set_ready("slack-worker", True)
    rendered = registry.render_prometheus()
    assert "requests_total" in rendered
    assert 'ready{service="slack-worker"} 1' in rendered


def test_metrics_http_server_exposes_prometheus_text():
    registry = MetricsRegistry()
    registry.increment("requests_total", labels={"outcome": "success"})
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    start_metrics_server("127.0.0.1", port, registry)
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/metrics", timeout=2
        ) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        assert "requests_total" in body
    finally:
        from truthexpiry.ops.metrics import stop_metrics_server

        stop_metrics_server()


def test_init_metrics_disabled_returns_none():
    reset_metrics()
    assert init_metrics(enabled=False) is None


def test_init_metrics_enabled_returns_registry():
    reset_metrics()
    registry = init_metrics(enabled=True)
    assert registry is not None
    reset_metrics()
