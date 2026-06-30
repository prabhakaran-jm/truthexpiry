from __future__ import annotations

import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

Outcome = Literal["success", "failure", "unavailable"]

_SERVICE_LABEL = {"service": "slack-worker"}


class MetricsRegistry:
    """Bounded in-memory metrics with Prometheus text exposition."""

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
        millis = max(0, int(seconds * 1000))
        self.increment(
            name,
            labels={"outcome": "success"},
            amount=millis,
        )

    def observe_stage_duration(self, name: str, seconds: float) -> None:
        millis = max(0, int(seconds * 1000))
        self.increment(name, labels=_SERVICE_LABEL, amount=millis)

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

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counter_names = sorted({name for name, _ in self._counters})
            for counter_name in counter_names:
                lines.append(f"# HELP {counter_name} TruthExpiry counter")
                lines.append(f"# TYPE {counter_name} counter")
                for (name, labels), value in sorted(self._counters.items()):
                    if name != counter_name:
                        continue
                    label_text = self._prometheus_labels(labels)
                    lines.append(f"{name}{label_text} {value}")
            lines.append("# HELP ready Service readiness gauge")
            lines.append("# TYPE ready gauge")
            for service, value in sorted(self._ready.items()):
                lines.append(f'ready{{service="{service}"}} {value}')
        return "\n".join(lines) + "\n"

    def _normalize_labels(
        self, labels: Mapping[str, str]
    ) -> tuple[tuple[str, str], ...]:
        merged = dict(_SERVICE_LABEL)
        merged.update(labels)
        for key in merged:
            if key not in self._ALLOWED_LABELS:
                raise ValueError(f"Disallowed metric label: {key}")
        return tuple(sorted(merged.items()))

    @staticmethod
    def _format_key(name: str, labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return name
        parts = ",".join(f"{key}={value}" for key, value in labels)
        return f"{name}{{{parts}}}"

    @staticmethod
    def _prometheus_labels(labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        parts = ",".join(f'{key}="{value}"' for key, value in labels)
        return f"{{{parts}}}"


_metrics: MetricsRegistry | None = None
_metrics_server: MetricsHttpServer | None = None


class MetricsHttpServer:
    """Background HTTP server exposing Prometheus text on ``/metrics``."""

    def __init__(self, host: str, port: int, registry: MetricsRegistry) -> None:
        self._host = host
        self._port = port
        self._registry = registry
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._httpd is not None:
            return
        registry = self._registry

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                if self.path.split("?", 1)[0] != "/metrics":
                    self.send_error(404)
                    return
                body = registry.render_prometheus().encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._httpd = ThreadingHTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="metrics-http",
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


def init_metrics(*, enabled: bool) -> MetricsRegistry | None:
    global _metrics
    if not enabled:
        _metrics = None
        return None
    _metrics = MetricsRegistry()
    return _metrics


def start_metrics_server(
    host: str, port: int, registry: MetricsRegistry | None = None
) -> MetricsHttpServer | None:
    global _metrics_server
    resolved = registry or _metrics
    if resolved is None:
        return None
    server = MetricsHttpServer(host, port, resolved)
    server.start()
    _metrics_server = server
    return server


def stop_metrics_server() -> None:
    global _metrics_server
    if _metrics_server is not None:
        _metrics_server.stop()
        _metrics_server = None


def get_metrics() -> MetricsRegistry | None:
    return _metrics


def reset_metrics() -> None:
    global _metrics, _metrics_server
    stop_metrics_server()
    _metrics = None


class _NoOpMetrics:
    def increment(self, *args: object, **kwargs: object) -> None:
        return

    def observe_duration(self, *args: object, **kwargs: object) -> None:
        return

    def observe_stage_duration(self, *args: object, **kwargs: object) -> None:
        return

    def set_ready(self, *args: object, **kwargs: object) -> None:
        return


NO_OP_METRICS = _NoOpMetrics()


def metrics_or_noop() -> MetricsRegistry | _NoOpMetrics:
    return get_metrics() or NO_OP_METRICS
