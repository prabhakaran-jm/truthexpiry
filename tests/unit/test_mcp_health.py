from __future__ import annotations

import logging
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from truthexpiry.config import ConfigError
from truthexpiry.ops.health import (
    McpReadinessState,
    WorkerReadinessState,
    start_mcp_health_server,
    start_worker_health_server,
)
from truthexpiry.ops.mcp_health import (
    lifecycle_mcp_health_readyz_url,
    probe_mcp_health_readyz,
)
from truthexpiry.ops.mcp_readiness_monitor import McpReadinessMonitor


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(host: str, port: int, path: str) -> tuple[int, dict]:
    import json
    import urllib.error
    import urllib.request

    url = f"http://{host}:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body


def test_lifecycle_mcp_health_readyz_url_derives_from_mcp_url():
    url = lifecycle_mcp_health_readyz_url("http://lifecycle-mcp:8000/mcp")
    assert url == "http://lifecycle-mcp:8001/readyz"


def test_lifecycle_mcp_health_readyz_url_https_and_custom_path():
    url = lifecycle_mcp_health_readyz_url(
        "https://mcp.example:8443/custom/mcp?x=1#frag"
    )
    assert url == "https://mcp.example:8001/readyz"


def test_lifecycle_mcp_health_readyz_url_ipv6_brackets():
    url = lifecycle_mcp_health_readyz_url("http://[2001:db8::1]:8000/mcp")
    assert url == "http://[2001:db8::1]:8001/readyz"


def test_lifecycle_mcp_health_readyz_url_strips_credentials():
    url = lifecycle_mcp_health_readyz_url("https://user:secret@host.example:8000/mcp")
    assert url == "https://host.example:8001/readyz"
    assert "secret" not in url
    assert "user" not in url


def test_lifecycle_mcp_health_readyz_url_honors_explicit_override():
    url = lifecycle_mcp_health_readyz_url(
        "http://127.0.0.1:8000/mcp",
        health_url="http://probe.internal:9000/readyz",
    )
    assert url == "http://probe.internal:9000/readyz"


def test_lifecycle_mcp_health_readyz_url_rejects_invalid_scheme():
    with pytest.raises(
        ConfigError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_URL must use http or https"
    ):
        lifecycle_mcp_health_readyz_url("ftp://example.invalid/mcp")


def test_probe_mcp_health_readyz_returns_true_when_ready():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("ok")
    state.set_tool_registration("ok")
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


def test_monitor_marks_unavailable_on_initial_failure():
    readiness = WorkerReadinessState()
    readiness.set_lifecycle_mcp("not_ready")
    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.2,
        probe=lambda: False,
    )
    monitor.start()
    try:
        assert readiness.checks()["lifecycle_mcp"] == "unavailable"
        assert readiness.is_ready() is False
    finally:
        monitor.stop()


def test_monitor_recovers_without_restart():
    readiness = WorkerReadinessState()
    readiness.set_lifecycle_mcp("not_ready")
    probe_results = iter([False, False, True])

    def _probe() -> bool:
        return next(probe_results, True)

    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.1,
        poll_interval_seconds=0.05,
        probe=_probe,
    )
    monitor.start()
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if readiness.checks()["lifecycle_mcp"] == "ok":
                break
            time.sleep(0.05)
        assert readiness.checks()["lifecycle_mcp"] == "ok"
    finally:
        monitor.stop()


def test_monitor_detects_outage_after_ready():
    readiness = WorkerReadinessState()
    readiness.set_lifecycle_mcp("not_ready")
    probe_state = {"ready": True}

    def _probe() -> bool:
        return probe_state["ready"]

    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.1,
        poll_interval_seconds=0.05,
        probe=_probe,
    )
    monitor.start()
    try:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if readiness.checks()["lifecycle_mcp"] == "ok":
                break
            time.sleep(0.02)
        assert readiness.checks()["lifecycle_mcp"] == "ok"

        probe_state["ready"] = False
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if readiness.checks()["lifecycle_mcp"] == "unavailable":
                break
            time.sleep(0.02)
        assert readiness.checks()["lifecycle_mcp"] == "unavailable"
    finally:
        monitor.stop()


def test_monitor_starts_only_one_thread():
    readiness = WorkerReadinessState()
    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.1,
        probe=lambda: False,
    )
    monitor.start()
    assert monitor.has_live_thread
    monitor.start()
    assert monitor.has_live_thread
    monitor.stop()
    assert not monitor.has_live_thread


def test_monitor_normal_stop_joins_and_clears_thread():
    readiness = WorkerReadinessState()
    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.1,
        poll_interval_seconds=0.05,
        probe=lambda: False,
    )
    monitor.start()
    assert monitor.has_live_thread
    monitor.stop()
    assert not monitor.has_live_thread


def test_monitor_stop_timeout_retains_thread_until_probe_releases(
    caplog: pytest.LogCaptureFixture,
):
    readiness = WorkerReadinessState()
    probe_calls = 0
    probe_blocked = threading.Event()
    release_probe = threading.Event()
    secret_url = "http://bearer-secret@127.0.0.1:8001/readyz"

    def _probe() -> bool:
        nonlocal probe_calls
        probe_calls += 1
        if probe_calls > 1:
            probe_blocked.set()
            release_probe.wait(timeout=5.0)
        return False

    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url=secret_url,
        timeout_seconds=0.01,
        poll_interval_seconds=0.01,
        join_timeout_seconds=0.05,
        probe=_probe,
    )
    monitor.start()
    assert probe_blocked.wait(timeout=2.0)

    with caplog.at_level(logging.WARNING):
        monitor.stop()

    assert monitor.has_live_thread
    serialized = caplog.text.lower()
    assert any(
        getattr(record, "event", "") == "mcp_readiness_monitor_stop_timeout"
        for record in caplog.records
        if record.levelno == logging.WARNING
    )
    assert "bearer-secret" not in serialized
    assert secret_url not in caplog.text

    thread_before = monitor._thread
    monitor.start()
    assert monitor._thread is thread_before

    release_probe.set()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        monitor.stop()
        if not monitor.has_live_thread:
            break
        time.sleep(0.02)
    assert not monitor.has_live_thread


def test_monitor_repeated_stop_is_safe():
    readiness = WorkerReadinessState()
    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url="http://127.0.0.1:1/readyz",
        timeout_seconds=0.1,
        probe=lambda: False,
    )
    monitor.start()
    monitor.stop()
    monitor.stop()
    monitor.stop()
    assert not monitor.has_live_thread


def test_monitor_transition_logs_exclude_sensitive_data(
    caplog: pytest.LogCaptureFixture,
):
    readiness = WorkerReadinessState()
    readiness.set_lifecycle_mcp("not_ready")
    secret_url = "http://secret-token@127.0.0.1:8001/readyz"
    monitor = McpReadinessMonitor(
        readiness,
        health_readyz_url=secret_url,
        timeout_seconds=0.1,
        probe=lambda: True,
    )
    with caplog.at_level(logging.INFO):
        monitor.start()
        monitor.stop()
    serialized = caplog.text.lower()
    assert "secret-token" not in serialized
    assert secret_url not in caplog.text


def test_worker_stays_live_when_mcp_unavailable_on_startup(
    monkeypatch: pytest.MonkeyPatch,
):
    import app as app_module

    settings = MagicMock()
    settings.validate_runtime.return_value = None
    settings.use_fakes = False
    settings.lifecycle_mcp_url = "http://127.0.0.1:8000/mcp"
    settings.lifecycle_mcp_health_url = None
    settings.lifecycle_mcp_health_port = 8001
    settings.health_host = "127.0.0.1"
    settings.health_port = 18080
    settings.metrics_enabled = False
    settings.dedup_event_ids = False
    settings.shutdown_drain_seconds = 1.0
    settings.mcp_client_timeout_seconds = 0.1

    mock_handler = MagicMock()
    mock_app = MagicMock()
    mock_app.client = MagicMock()

    started = threading.Event()

    def _fake_start() -> None:
        started.set()
        raise KeyboardInterrupt

    mock_handler.start.side_effect = _fake_start

    with (
        patch.object(app_module, "SlackWorkerSettings") as from_env,
        patch.object(
            app_module,
            "create_slack_application",
            return_value=(mock_app, mock_handler),
        ),
        patch.object(app_module, "build_pipeline"),
        patch.object(app_module, "register_listeners"),
        patch.object(app_module, "start_worker_health_server") as start_health,
        patch.object(app_module, "init_shutdown_coordinator") as init_shutdown,
        patch.object(app_module, "SocketModeConnectionMonitor") as socket_cls,
        patch.object(app_module, "McpReadinessMonitor") as monitor_cls,
        patch.object(app_module, "configure_logging"),
        patch.object(app_module, "init_metrics"),
        patch.object(app_module, "init_event_dedup_cache"),
        patch.object(app_module, "metrics_or_noop"),
        patch("dotenv.load_dotenv"),
    ):
        from_env.from_env.return_value = settings
        start_health.return_value = MagicMock()
        coordinator = MagicMock()
        init_shutdown.return_value = coordinator
        socket_cls.return_value = MagicMock()
        monitor_instance = MagicMock()
        monitor_cls.return_value = monitor_instance

        with pytest.raises(KeyboardInterrupt):
            app_module.main()

    mock_handler.start.assert_called_once()
    monitor_instance.start.assert_called_once()
    monitor_instance.stop.assert_called_once()


def test_invalid_mcp_url_exits_before_socket_mode(monkeypatch: pytest.MonkeyPatch):
    import app as app_module

    settings = MagicMock()
    settings.validate_runtime.return_value = None
    settings.use_fakes = False
    settings.lifecycle_mcp_url = "not-a-valid-url"
    settings.lifecycle_mcp_health_url = None
    settings.lifecycle_mcp_health_port = 8001
    settings.health_host = "127.0.0.1"
    settings.health_port = 18080
    settings.metrics_enabled = False
    settings.dedup_event_ids = False
    settings.shutdown_drain_seconds = 1.0

    with (
        patch.object(app_module, "SlackWorkerSettings") as from_env,
        patch.object(app_module, "create_slack_application") as create_app,
        patch.object(
            app_module, "start_worker_health_server", return_value=MagicMock()
        ),
        patch.object(app_module, "init_shutdown_coordinator", return_value=MagicMock()),
        patch.object(app_module, "configure_logging"),
        patch.object(app_module, "init_metrics"),
        patch.object(app_module, "init_event_dedup_cache"),
        patch("dotenv.load_dotenv"),
    ):
        from_env.from_env.return_value = settings
        with pytest.raises(SystemExit) as exc_info:
            app_module.main()
        assert exc_info.value.code == 1
        create_app.assert_not_called()


def test_initial_mcp_failure_worker_readiness_503():
    readiness = WorkerReadinessState()
    readiness.set_configuration("ok")
    readiness.set_lifecycle_mcp("unavailable")
    readiness.set_socket_mode("connecting")
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, readiness)
    try:
        status, body = _request_json("127.0.0.1", port, "/readyz")
        live_status, _ = _request_json("127.0.0.1", port, "/healthz")
        assert live_status == 200
        assert status == 503
        assert body["checks"]["lifecycle_mcp"] == "unavailable"
    finally:
        server.stop()
