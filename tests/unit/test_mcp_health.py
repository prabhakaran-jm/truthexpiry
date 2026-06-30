from __future__ import annotations

import socket
import time

from truthexpiry.ops.event_dedup import (
    BoundedEventIdCache,
    init_event_dedup_cache,
    reset_event_dedup_cache,
)
from truthexpiry.ops.health import McpReadinessState, start_mcp_health_server
from truthexpiry.ops.mcp_health import (
    lifecycle_mcp_health_readyz_url,
    probe_mcp_health_readyz,
)
from truthexpiry.ops.readiness import wait_for_mcp_readiness


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_lifecycle_mcp_health_readyz_url_derives_from_mcp_url():
    url = lifecycle_mcp_health_readyz_url("http://lifecycle-mcp:8000/mcp")
    assert url == "http://lifecycle-mcp:8001/readyz"


def test_lifecycle_mcp_health_readyz_url_honors_explicit_override():
    url = lifecycle_mcp_health_readyz_url(
        "http://127.0.0.1:8000/mcp",
        health_url="http://probe.internal:9000/readyz",
    )
    assert url == "http://probe.internal:9000/readyz"


def test_probe_mcp_health_readyz_returns_true_when_ready():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("ok")
    port = _find_free_port()
    server = start_mcp_health_server("127.0.0.1", port, state)
    try:
        ready = probe_mcp_health_readyz(
            health_readyz_url=f"http://127.0.0.1:{port}/readyz",
            timeout_seconds=2.0,
        )
        assert ready is True
    finally:
        server.stop()


def test_probe_mcp_health_readyz_returns_false_when_not_ready():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("not_ready")
    port = _find_free_port()
    server = start_mcp_health_server("127.0.0.1", port, state)
    try:
        ready = probe_mcp_health_readyz(
            health_readyz_url=f"http://127.0.0.1:{port}/readyz",
            timeout_seconds=2.0,
        )
        assert ready is False
    finally:
        server.stop()


def test_wait_for_mcp_readiness_polls_until_ready():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("not_ready")
    port = _find_free_port()
    server = start_mcp_health_server("127.0.0.1", port, state)
    try:

        def _mark_ready_later() -> None:
            time.sleep(0.2)
            state.set_dataset("ok")

        import threading

        threading.Thread(target=_mark_ready_later, daemon=True).start()
        ready = wait_for_mcp_readiness(
            health_readyz_url=f"http://127.0.0.1:{port}/readyz",
            timeout_seconds=2.0,
            client_timeout_seconds=1.0,
            poll_interval_seconds=0.1,
        )
        assert ready is True
    finally:
        server.stop()


def test_bounded_event_id_cache_detects_duplicates():
    cache = BoundedEventIdCache(ttl_seconds=60.0, max_size=10)
    assert cache.is_duplicate("Ev001") is False
    assert cache.is_duplicate("Ev001") is True


def test_bounded_event_id_cache_evicts_expired_entries():
    cache = BoundedEventIdCache(ttl_seconds=0.05, max_size=10)
    assert cache.is_duplicate("Ev002") is False
    time.sleep(0.06)
    assert cache.is_duplicate("Ev002") is False


def test_bounded_event_id_cache_enforces_max_size():
    cache = BoundedEventIdCache(ttl_seconds=60.0, max_size=2)
    assert cache.is_duplicate("EvA") is False
    assert cache.is_duplicate("EvB") is False
    assert cache.is_duplicate("EvC") is False
    assert cache.is_duplicate("EvB") is True
    assert cache.is_duplicate("EvA") is False


def test_init_event_dedup_cache_disabled_returns_none():
    reset_event_dedup_cache()
    assert init_event_dedup_cache(enabled=False) is None
    assert init_event_dedup_cache(enabled=True) is not None
    reset_event_dedup_cache()
