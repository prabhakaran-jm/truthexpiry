from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections.abc import Callable
from typing import Any, Literal

CheckValue = Literal[
    "ok",
    "unavailable",
    "skipped",
    "connecting",
    "disconnected",
    "not_ready",
]

SERVICE_SLACK_WORKER = "slack-worker"
SERVICE_LIFECYCLE_MCP = "lifecycle-mcp"


@dataclass
class WorkerReadinessState:
    """Thread-safe readiness snapshot for the Slack worker."""

    configuration: CheckValue = "ok"
    lifecycle_mcp: CheckValue = "skipped"
    socket_mode: CheckValue = "connecting"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_configuration(self, status: CheckValue) -> None:
        with self._lock:
            self.configuration = status

    def set_lifecycle_mcp(self, status: CheckValue) -> None:
        with self._lock:
            self.lifecycle_mcp = status

    def set_socket_mode(self, status: CheckValue) -> None:
        with self._lock:
            self.socket_mode = status

    def checks(self) -> dict[str, str]:
        with self._lock:
            return {
                "configuration": self.configuration,
                "lifecycle_mcp": self.lifecycle_mcp,
                "socket_mode": self.socket_mode,
            }

    def is_ready(self) -> bool:
        checks = self.checks()
        return all(value in {"ok", "skipped"} for value in checks.values())

    def readiness_body(self) -> dict[str, Any]:
        ready = self.is_ready()
        return {
            "status": "ok" if ready else "not_ready",
            "service": SERVICE_SLACK_WORKER,
            "checks": self.checks(),
        }

    def liveness_body(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": SERVICE_SLACK_WORKER,
            "checks": {"process": "ok"},
        }


@dataclass
class McpReadinessState:
    """Thread-safe readiness snapshot for the lifecycle MCP server."""

    configuration: CheckValue = "ok"
    dataset: CheckValue = "not_ready"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_configuration(self, status: CheckValue) -> None:
        with self._lock:
            self.configuration = status

    def set_dataset(self, status: CheckValue) -> None:
        with self._lock:
            self.dataset = status

    def checks(self) -> dict[str, str]:
        with self._lock:
            return {
                "configuration": self.configuration,
                "dataset": self.dataset,
            }

    def is_ready(self) -> bool:
        checks = self.checks()
        return all(value == "ok" for value in checks.values())

    def readiness_body(self) -> dict[str, Any]:
        ready = self.is_ready()
        return {
            "status": "ok" if ready else "not_ready",
            "service": SERVICE_LIFECYCLE_MCP,
            "checks": self.checks(),
        }

    def liveness_body(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": SERVICE_LIFECYCLE_MCP,
            "checks": {"process": "ok"},
        }


class HealthProbeServer:
    """Background HTTP server exposing /healthz and /readyz."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        liveness_body: Callable[[], dict[str, Any]],
        readiness_body: Callable[[], dict[str, Any]],
        is_ready: Callable[[], bool],
    ) -> None:
        self._host = host
        self._port = port
        self._liveness_body = liveness_body
        self._readiness_body = readiness_body
        self._is_ready = is_ready
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        if self._httpd is not None:
            return

        liveness_body = self._liveness_body
        readiness_body = self._readiness_body
        is_ready = self._is_ready

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_OPTIONS(self) -> None:
                self.send_response(405)
                self.send_header("Allow", "GET, HEAD")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_HEAD(self) -> None:
                self._handle_probe(include_body=False)

            def do_GET(self) -> None:
                self._handle_probe(include_body=True)

            def _handle_probe(self, *, include_body: bool) -> None:
                path = self.path.split("?", 1)[0]
                if path == "/healthz":
                    body = liveness_body()
                    status = 200
                elif path == "/readyz":
                    body = readiness_body()
                    status = 200 if is_ready() else 503
                else:
                    self.send_error(404)
                    return
                payload = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                if include_body:
                    self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if include_body:
                    self.wfile.write(payload)

        self._httpd = ThreadingHTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="health-probe",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None


def start_worker_health_server(
    host: str,
    port: int,
    state: WorkerReadinessState,
) -> HealthProbeServer:
    server = HealthProbeServer(
        host,
        port,
        liveness_body=state.liveness_body,
        readiness_body=state.readiness_body,
        is_ready=state.is_ready,
    )
    server.start()
    return server


def start_mcp_health_server(
    host: str,
    port: int,
    state: McpReadinessState,
) -> HealthProbeServer:
    server = HealthProbeServer(
        host,
        port,
        liveness_body=state.liveness_body,
        readiness_body=state.readiness_body,
        is_ready=state.is_ready,
    )
    server.start()
    return server
