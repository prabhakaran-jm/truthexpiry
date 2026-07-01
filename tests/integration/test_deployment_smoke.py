from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.subprocess_helpers import (
    clean_runtime_env,
    reserve_local_port,
    shutdown_server_subprocess,
    wait_for_health_endpoint,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SENSITIVE_HEALTH_KEYS = frozenset(
    {
        "token",
        "secret",
        "password",
        "authorization",
        "slack_bot_token",
        "slack_app_token",
        "openai_api_key",
        "auth_token",
    }
)


@pytest.mark.integration
def test_worker_structural_check_subprocess_exits_zero():
    env = clean_runtime_env()
    result = subprocess.run(
        [sys.executable, "app.py", "--check"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Configuration structure: OK" in result.stdout


@pytest.mark.integration
def test_mcp_structural_check_subprocess_exits_zero():
    env = clean_runtime_env()
    env["TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "lifecycle_mcp.server", "--check"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Configuration structure: OK" in result.stdout


@pytest.mark.integration
def test_mcp_subprocess_health_and_readiness_endpoints():
    mcp_port = reserve_local_port()
    health_port = reserve_local_port()
    env = {
        **os.environ,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST": "127.0.0.1",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT": str(mcp_port),
        "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT": str(health_port),
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "lifecycle_mcp.server"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        live_body = wait_for_health_endpoint(
            "127.0.0.1",
            health_port,
            "/healthz",
            expected_status=200,
        )
        ready_body = wait_for_health_endpoint(
            "127.0.0.1",
            health_port,
            "/readyz",
            expected_status=200,
        )
        assert live_body["status"] == "ok"
        assert live_body["service"] == "lifecycle-mcp"
        assert ready_body["status"] == "ok"
        assert ready_body["checks"]["dataset"] == "ok"
        assert ready_body["checks"]["tool_registration"] == "ok"

        serialized = f"{live_body}{ready_body}".lower()
        for key in _SENSITIVE_HEALTH_KEYS:
            assert key not in serialized
    finally:
        shutdown_server_subprocess(proc)
