from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from truthexpiry.ops.mcp_health import probe_mcp_health_readyz

if TYPE_CHECKING:
    from truthexpiry.ops.health import CheckValue, WorkerReadinessState

logger = logging.getLogger(__name__)

ProbeFn = Callable[[], bool]

_DEFAULT_POLL_INTERVAL_SECONDS = 0.5
_MAX_BACKOFF_SECONDS = 2.0
_JOIN_GRACE_SECONDS = 2.0


class McpReadinessMonitor:
    """Background GET /readyz poller that updates worker lifecycle MCP readiness.

    Timing is fixed internally: one immediate probe on start, then bounded polling
    with backoff from the initial poll interval up to two seconds. Per-request
    timeout comes from the worker MCP client-timeout setting. There is no total
    startup deadline and temporary MCP outage never terminates the worker.
    """

    def __init__(
        self,
        readiness: WorkerReadinessState,
        *,
        health_readyz_url: str,
        timeout_seconds: float,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
        join_timeout_seconds: float | None = None,
        probe: ProbeFn | None = None,
    ) -> None:
        self._readiness = readiness
        self._health_readyz_url = health_readyz_url
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._join_timeout_seconds = join_timeout_seconds
        self._probe = probe
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_reported: str | None = None
        self._stop_timeout_logged = False

    @property
    def health_readyz_url(self) -> str:
        return self._health_readyz_url

    @property
    def has_live_thread(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def probe_once(self) -> bool:
        if self._probe is not None:
            return self._probe()
        return probe_mcp_health_readyz(
            health_readyz_url=self._health_readyz_url,
            timeout_seconds=self._timeout_seconds,
        )

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if self._thread is not None and not self._thread.is_alive():
                self._thread = None
                self._stop_timeout_logged = False

        ready = self.probe_once()
        self._apply_probe_result(ready)

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            thread = threading.Thread(
                target=self._run,
                name="mcp-readiness-monitor",
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._join_thread()

    def _join_timeout(self) -> float:
        if self._join_timeout_seconds is not None:
            return self._join_timeout_seconds
        return self._timeout_seconds + self._poll_interval_seconds + _JOIN_GRACE_SECONDS

    def _join_thread(self) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            if not thread.is_alive():
                self._thread = None
                self._stop_timeout_logged = False
                return

        thread.join(timeout=self._join_timeout())

        with self._lock:
            if self._thread is not thread:
                return
            if thread.is_alive():
                if not self._stop_timeout_logged:
                    logger.warning(
                        "MCP readiness monitor stop timed out",
                        extra={
                            "event": "mcp_readiness_monitor_stop_timeout",
                            "outcome": "warning",
                        },
                    )
                    self._stop_timeout_logged = True
            else:
                self._thread = None
                self._stop_timeout_logged = False

    def _run(self) -> None:
        backoff = self._poll_interval_seconds
        while not self._stop.is_set():
            if self._stop.wait(backoff):
                break
            ready = self.probe_once()
            self._apply_probe_result(ready)
            if ready:
                backoff = self._poll_interval_seconds
            else:
                backoff = min(backoff * 1.5, _MAX_BACKOFF_SECONDS)

    def _apply_probe_result(self, ready: bool) -> None:
        status: CheckValue = "ok" if ready else "unavailable"
        if status != self._last_reported:
            logger.info(
                "Lifecycle MCP readiness state changed",
                extra={
                    "event": "mcp_readiness_transition",
                    "outcome": status,
                },
            )
            self._last_reported = status
        self._readiness.set_lifecycle_mcp(status)
