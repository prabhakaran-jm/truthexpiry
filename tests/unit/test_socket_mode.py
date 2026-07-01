from __future__ import annotations

import time
from unittest.mock import MagicMock

from truthexpiry.ops.health import WorkerReadinessState
from truthexpiry.ops.metrics import init_metrics, metrics_or_noop, reset_metrics
from truthexpiry.ops.socket_mode import SocketModeConnectionMonitor


def _monitor(*, connected_sequence: list[bool], poll_interval: float = 0.05):
    readiness = WorkerReadinessState()
    handler = MagicMock()
    states = iter(connected_sequence)

    def _is_connected() -> bool:
        try:
            return next(states)
        except StopIteration:
            return connected_sequence[-1]

    handler.client.is_connected.side_effect = _is_connected
    monitor = SocketModeConnectionMonitor(
        handler,
        readiness,
        poll_interval_seconds=poll_interval,
    )
    return monitor, readiness, handler


def test_socket_mode_starts_connecting():
    monitor, readiness, _handler = _monitor(connected_sequence=[False])
    assert readiness.checks()["socket_mode"] == "connecting"


def test_socket_mode_initial_connection_becomes_ok():
    monitor, readiness, _handler = _monitor(connected_sequence=[False, True])
    monitor.start()
    try:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if readiness.checks()["socket_mode"] == "ok":
                break
            time.sleep(0.02)
        assert readiness.checks()["socket_mode"] == "ok"
    finally:
        monitor.stop()


def test_socket_mode_initial_connection_is_not_reconnect():
    reset_metrics()
    init_metrics(enabled=True)
    monitor, readiness, _handler = _monitor(connected_sequence=[False, True, True])
    monitor.start()
    try:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if readiness.checks()["socket_mode"] == "ok":
                break
            time.sleep(0.02)
        assert (
            metrics_or_noop()
            .snapshot()["counters"]
            .get("socket_mode_reconnects_total{service=slack-worker}")
            is None
        )
    finally:
        monitor.stop()
        reset_metrics()


def test_socket_mode_lost_connection_becomes_disconnected():
    monitor, readiness, _handler = _monitor(connected_sequence=[True, False, False])
    monitor.start()
    try:
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if readiness.checks()["socket_mode"] == "disconnected":
                break
            time.sleep(0.02)
        assert readiness.checks()["socket_mode"] == "disconnected"
        assert readiness.is_ready() is False
    finally:
        monitor.stop()


def test_socket_mode_recovery_increments_reconnect_once():
    reset_metrics()
    init_metrics(enabled=True)
    monitor, readiness, _handler = _monitor(
        connected_sequence=[True, False, False, True, True]
    )
    monitor.start()
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            snapshot = metrics_or_noop().snapshot()["counters"]
            if snapshot.get("socket_mode_reconnects_total{service=slack-worker}") == 1:
                break
            time.sleep(0.02)
        assert (
            metrics_or_noop().snapshot()["counters"][
                "socket_mode_reconnects_total{service=slack-worker}"
            ]
            == 1
        )
    finally:
        monitor.stop()
        reset_metrics()


def test_socket_mode_stop_leaves_disconnected():
    monitor, readiness, _handler = _monitor(connected_sequence=[True])
    monitor.start()
    time.sleep(0.1)
    monitor.stop()
    assert readiness.checks()["socket_mode"] == "disconnected"


def test_socket_mode_start_is_idempotent():
    monitor, readiness, _handler = _monitor(connected_sequence=[False])
    monitor.start()
    first = monitor._thread
    monitor.start()
    assert monitor._thread is first
    monitor.stop()
