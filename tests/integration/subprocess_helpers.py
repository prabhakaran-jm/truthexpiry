from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

_RUNTIME_ENV_PREFIXES = ("TRUTH_EXPIRY_",)
_RUNTIME_ENV_EXACT = frozenset(
    {
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "SLACK_API_URL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    }
)

_READINESS_TIMEOUT_SECONDS = 15.0
_SHUTDOWN_TIMEOUT_SECONDS = 5.0


def clean_runtime_env() -> dict[str, str]:
    """Return a copy of the environment without TruthExpiry runtime variables."""
    return {
        key: value
        for key, value in os.environ.items()
        if key not in _RUNTIME_ENV_EXACT
        and not any(key.startswith(prefix) for prefix in _RUNTIME_ENV_PREFIXES)
    }


def reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(
    host: str, port: int, path: str, *, timeout: float = 2.0
) -> tuple[int, dict]:
    url = f"http://{host}:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body


def wait_for_health_endpoint(
    host: str,
    port: int,
    path: str,
    *,
    expected_status: int,
    timeout_seconds: float = _READINESS_TIMEOUT_SECONDS,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    backoff = 0.05
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, body = request_json(host, port, path)
            if status == expected_status:
                return body
        except Exception as exc:  # noqa: BLE001 - readiness polling
            last_error = exc
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 1.0)
    raise TimeoutError(
        f"Endpoint {path} on {host}:{port} did not return {expected_status}"
    ) from last_error


def force_kill_process_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def shutdown_server_subprocess(proc: subprocess.Popen[bytes]) -> None:
    root_pid = proc.pid
    proc.terminate()
    if sys.platform == "win32":
        force_kill_process_tree(root_pid)
    try:
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        force_kill_process_tree(root_pid)
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
