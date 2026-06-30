from __future__ import annotations

import threading
import time

from truthexpiry.ops.shutdown import ShutdownCoordinator


def test_shutdown_rejects_new_requests_after_request_shutdown():
    coordinator = ShutdownCoordinator(drain_timeout_seconds=1.0)
    coordinator.request_shutdown()
    assert coordinator.begin_request() is False


def test_in_flight_drain_waits_for_completion():
    coordinator = ShutdownCoordinator(drain_timeout_seconds=2.0)
    assert coordinator.begin_request() is True

    def _complete_later() -> None:
        time.sleep(0.1)
        coordinator.end_request()

    thread = threading.Thread(target=_complete_later)
    thread.start()
    drained = coordinator.wait_for_drain()
    thread.join()
    assert drained is True
    assert coordinator.in_flight_count() == 0


def test_drain_timeout_when_requests_remain():
    coordinator = ShutdownCoordinator(drain_timeout_seconds=0.05)
    assert coordinator.begin_request() is True
    assert coordinator.wait_for_drain() is False
