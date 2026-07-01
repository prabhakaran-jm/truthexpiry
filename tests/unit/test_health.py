from __future__ import annotations

import json
import socket

import pytest

from truthexpiry.ops.health import (
    SERVICE_SLACK_WORKER,
    McpReadinessState,
    WorkerReadinessState,
    start_mcp_health_server,
    start_worker_health_server,
)
from truthexpiry.ops.structural_check import run_structural_check

SENSITIVE_HEALTH_KEYS = frozenset(
    {
        "token",
        "secret",
        "password",
        "authorization",
        "slack_bot_token",
        "slack_app_token",
        "openai_api_key",
        "auth_token",
        "query",
        "markdown_text",
        "permalink",
    }
)


def _request_json(host: str, port: int, path: str) -> tuple[int, dict]:
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


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_worker_liveness_returns_200():
    state = WorkerReadinessState()
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        status, body = _request_json("127.0.0.1", port, "/healthz")
        assert status == 200
        assert body["status"] == "ok"
        assert body["service"] == SERVICE_SLACK_WORKER
    finally:
        server.stop()


def test_worker_readiness_503_when_socket_mode_connecting():
    state = WorkerReadinessState()
    state.set_configuration("ok")
    state.set_lifecycle_mcp("skipped")
    state.set_socket_mode("connecting")
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        status, body = _request_json("127.0.0.1", port, "/readyz")
        assert status == 503
        assert body["status"] == "not_ready"
        assert body["checks"]["socket_mode"] == "connecting"
    finally:
        server.stop()


def test_worker_readiness_200_when_all_checks_ok():
    state = WorkerReadinessState()
    state.set_configuration("ok")
    state.set_lifecycle_mcp("skipped")
    state.set_socket_mode("ok")
    state.set_draining(False)
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        status, body = _request_json("127.0.0.1", port, "/readyz")
        assert status == 200
        assert body["status"] == "ok"
    finally:
        server.stop()


def test_health_responses_exclude_sensitive_keys():
    state = WorkerReadinessState()
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        for path in ("/healthz", "/readyz"):
            _, body = _request_json("127.0.0.1", port, path)
            serialized = json.dumps(body).lower()
            for key in SENSITIVE_HEALTH_KEYS:
                assert key not in serialized
    finally:
        server.stop()


def test_health_options_rejects_preflight():
    state = WorkerReadinessState()
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(  # noqa: S310
            f"http://127.0.0.1:{port}/readyz",
            method="OPTIONS",
        )
        try:
            urllib.request.urlopen(request, timeout=2.0)  # noqa: S310
            raise AssertionError("expected OPTIONS to fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 405
            assert exc.headers.get("Access-Control-Allow-Origin") is None
    finally:
        server.stop()


def test_mcp_liveness_and_readiness():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("ok")
    state.set_tool_registration("ok")
    port = _find_free_port()
    server = start_mcp_health_server("127.0.0.1", port, state)
    try:
        live_status, live_body = _request_json("127.0.0.1", port, "/healthz")
        ready_status, ready_body = _request_json("127.0.0.1", port, "/readyz")
        assert live_status == 200
        assert ready_status == 200
        assert live_body["service"] == "lifecycle-mcp"
        assert ready_body["checks"]["dataset"] == "ok"
        assert ready_body["checks"]["tool_registration"] == "ok"
    finally:
        server.stop()


def test_mcp_readiness_503_before_tool_registration():
    state = McpReadinessState()
    state.set_configuration("ok")
    state.set_dataset("ok")
    state.set_tool_registration("not_ready")
    port = _find_free_port()
    server = start_mcp_health_server("127.0.0.1", port, state)
    try:
        status, body = _request_json("127.0.0.1", port, "/readyz")
        assert status == 503
        assert body["checks"]["tool_registration"] == "not_ready"
    finally:
        server.stop()


def test_worker_readiness_503_when_draining():
    state = WorkerReadinessState()
    state.set_configuration("ok")
    state.set_lifecycle_mcp("skipped")
    state.set_socket_mode("ok")
    state.set_draining(True)
    port = _find_free_port()
    server = start_worker_health_server("127.0.0.1", port, state)
    try:
        ready_status, ready_body = _request_json("127.0.0.1", port, "/readyz")
        live_status, _ = _request_json("127.0.0.1", port, "/healthz")
        assert live_status == 200
        assert ready_status == 503
        assert ready_body["checks"]["draining"] == "yes"
    finally:
        server.stop()


def test_worker_draining_immediately_unready():
    state = WorkerReadinessState()
    state.set_configuration("ok")
    state.set_lifecycle_mcp("ok")
    state.set_socket_mode("ok")
    assert state.is_ready() is True
    state.set_draining(True)
    assert state.is_ready() is False


def test_structural_check_exits_zero_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)
    assert run_structural_check() == 0


def test_app_main_check_flag_exits_zero(monkeypatch: pytest.MonkeyPatch):
    import app as app_module

    monkeypatch.setattr(app_module, "parse_cli_args", lambda: True)
    monkeypatch.setattr(app_module, "run_structural_check", lambda: 0)
    with pytest.raises(SystemExit) as exc_info:
        app_module.main()
    assert exc_info.value.code == 0
