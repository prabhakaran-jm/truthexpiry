from __future__ import annotations

import logging
import signal
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class ShutdownCoordinator:
    """Coordinate graceful shutdown with in-flight request draining."""

    def __init__(self, *, drain_timeout_seconds: float) -> None:
        self._drain_timeout_seconds = drain_timeout_seconds
        self._accepting = threading.Event()
        self._accepting.set()
        self._in_flight = 0
        self._lock = threading.Lock()
        self._shutdown_requested = threading.Event()

    @property
    def accepting_requests(self) -> bool:
        return self._accepting.is_set() and not self._shutdown_requested.is_set()

    def request_shutdown(self) -> None:
        self._shutdown_requested.set()
        self._accepting.clear()

    def begin_request(self) -> bool:
        if not self.accepting_requests:
            return False
        with self._lock:
            if not self.accepting_requests:
                return False
            self._in_flight += 1
            return True

    def end_request(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    def in_flight_count(self) -> int:
        with self._lock:
            return self._in_flight

    def wait_for_drain(self) -> bool:
        deadline = time.monotonic() + self._drain_timeout_seconds
        while time.monotonic() < deadline:
            if self.in_flight_count() == 0:
                return True
            time.sleep(0.05)
        logger.warning(
            "Shutdown drain timeout",
            extra={
                "event": "shutdown_drain_timeout",
                "outcome": "failure",
                "duration_ms": int(self._drain_timeout_seconds * 1000),
            },
        )
        return False

    def install_signal_handlers(self, on_shutdown: Callable[[], None]) -> None:
        def _handler(signum: int, _frame: object) -> None:
            logger.info("Received signal %s; initiating shutdown", signum)
            self.request_shutdown()
            on_shutdown()

        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)


_shutdown_coordinator: ShutdownCoordinator | None = None


def get_shutdown_coordinator() -> ShutdownCoordinator | None:
    return _shutdown_coordinator


def init_shutdown_coordinator(*, drain_timeout_seconds: float) -> ShutdownCoordinator:
    global _shutdown_coordinator
    coordinator = ShutdownCoordinator(drain_timeout_seconds=drain_timeout_seconds)
    _shutdown_coordinator = coordinator
    return coordinator


def reset_shutdown_coordinator() -> None:
    global _shutdown_coordinator
    _shutdown_coordinator = None
