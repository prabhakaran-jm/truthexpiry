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


def test_shutdown_close_before_drain_order():
    events: list[str] = []
    coordinator = ShutdownCoordinator(drain_timeout_seconds=1.0)
    assert coordinator.begin_request() is True

    def _close_intake() -> None:
        events.append("close")
        coordinator.request_shutdown()

    def _drain() -> None:
        events.append("drain")
        coordinator.wait_for_drain()
        coordinator.end_request()

    close_thread = threading.Thread(target=_close_intake)
    close_thread.start()
    time.sleep(0.05)
    _drain()
    close_thread.join()
    assert events.index("close") < events.index("drain")


def test_end_request_runs_on_exception_path():
    coordinator = ShutdownCoordinator(drain_timeout_seconds=1.0)
    assert coordinator.begin_request() is True
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        coordinator.end_request()
    assert coordinator.in_flight_count() == 0


def test_repeated_shutdown_callback_runs_once():
    calls = 0
    lock = threading.Lock()
    done = False

    def _shutdown() -> None:
        nonlocal done, calls
        with lock:
            if done:
                return
            done = True
            calls += 1

    _shutdown()
    _shutdown()
    assert calls == 1


def test_in_flight_counter_never_negative():
    coordinator = ShutdownCoordinator(drain_timeout_seconds=1.0)
    coordinator.end_request()
    coordinator.end_request()
    assert coordinator.in_flight_count() == 0
