from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from truthexpiry.ops.metrics import metrics_or_noop

if TYPE_CHECKING:
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    from truthexpiry.ops.health import WorkerReadinessState

logger = logging.getLogger(__name__)


class SocketModeConnectionMonitor:
    """Poll ``SocketModeClient.is_connected()`` and update readiness state."""

    def __init__(
        self,
        handler: SocketModeHandler,
        readiness: WorkerReadinessState,
        *,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._handler = handler
        self._readiness = readiness
        self._poll_interval_seconds = poll_interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ever_connected = False
        self._last_connected = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._readiness.set_socket_mode("connecting")
        self._thread = threading.Thread(
            target=self._run,
            name="socket-mode-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval_seconds + 1.0)
            self._thread = None
        self._readiness.set_socket_mode("disconnected")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                connected = self._handler.client.is_connected()
            except Exception:
                logger.debug("Socket Mode connection check failed", exc_info=True)
                connected = False
            if connected:
                if self._ever_connected and not self._last_connected:
                    metrics_or_noop().increment(
                        "socket_mode_reconnects_total", labels={}
                    )
                    logger.warning(
                        "Socket Mode reconnect detected",
                        extra={
                            "event": "socket_mode_reconnect",
                            "outcome": "warning",
                        },
                    )
                self._ever_connected = True
                self._last_connected = True
                self._readiness.set_socket_mode("ok")
            else:
                self._last_connected = False
                self._readiness.set_socket_mode("connecting")
            if self._stop.wait(self._poll_interval_seconds):
                break
