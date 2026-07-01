from __future__ import annotations

import time
from logging import Logger
from unittest.mock import MagicMock

import pytest

from listeners.truthexpiry_handler import run_truthexpiry_query
from truthexpiry.ops.event_dedup import (
    BoundedEventIdCache,
    init_event_dedup_cache,
    reset_event_dedup_cache,
)
from truthexpiry.ops.shutdown import (
    init_shutdown_coordinator,
    reset_shutdown_coordinator,
)
from truthexpiry.services.pipeline import TruthExpiryResponse


def _pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.handle.return_value = TruthExpiryResponse(markdown_text="ok", results=())
    return pipeline


def _args(**overrides):
    defaults = {
        "pipeline": _pipeline(),
        "context": MagicMock(),
        "event": {"ts": "1.0", "team": "T", "channel": "C", "user": "U"},
        "query": "Is report export available?",
        "logger": MagicMock(spec=Logger),
        "say": MagicMock(),
        "say_stream": MagicMock(return_value=MagicMock()),
        "set_status": MagicMock(),
        "event_id": "Ev-test-001",
    }
    defaults.update(overrides)
    return defaults


@pytest.fixture(autouse=True)
def _reset_globals():
    reset_event_dedup_cache()
    reset_shutdown_coordinator()
    yield
    reset_event_dedup_cache()
    reset_shutdown_coordinator()


def test_enabled_first_event_id_accepted():
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-1"))
    pipeline.handle.assert_called_once()


def test_enabled_duplicate_event_id_suppressed():
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-dup"))
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-dup"))
    pipeline.handle.assert_called_once()


def test_enabled_different_event_id_accepted():
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-a"))
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-b"))
    assert pipeline.handle.call_count == 2


def test_missing_event_id_accepted_when_enabled():
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id=None))
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id=None))
    assert pipeline.handle.call_count == 2


def test_expired_event_id_accepted_again():
    cache = BoundedEventIdCache(ttl_seconds=0.05, max_size=10)
    init_event_dedup_cache(enabled=True)
    from truthexpiry.ops import event_dedup as dedup_module

    dedup_module._event_dedup_cache = cache
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-expire"))
    time.sleep(0.06)
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-expire"))
    assert pipeline.handle.call_count == 2


def test_max_size_eviction_allows_evicted_id_again():
    cache = BoundedEventIdCache(ttl_seconds=60.0, max_size=2)
    from truthexpiry.ops import event_dedup as dedup_module

    dedup_module._event_dedup_cache = cache
    assert cache.is_duplicate("EvA") is False
    assert cache.is_duplicate("EvB") is False
    assert cache.is_duplicate("EvC") is False
    assert cache.is_duplicate("EvA") is False


def test_disabled_mode_accepts_duplicate_ids():
    init_event_dedup_cache(enabled=False)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-dup"))
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-dup"))
    assert pipeline.handle.call_count == 2


def test_duplicate_suppressed_before_pipeline_work():
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-before"))
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-before"))
    pipeline.handle.assert_called_once()


def test_cache_does_not_store_query_payload():
    cache = BoundedEventIdCache()
    cache.is_duplicate("Ev-only")
    assert list(cache._entries.keys()) == ["Ev-only"]


def test_duplicate_suppression_log_has_no_payload(caplog: pytest.LogCaptureFixture):
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    secret_query = "super-secret-query-text"
    with caplog.at_level("INFO"):
        run_truthexpiry_query(
            **_args(pipeline=pipeline, event_id="Ev-log", query=secret_query)
        )
        run_truthexpiry_query(
            **_args(pipeline=pipeline, event_id="Ev-log", query=secret_query)
        )
    assert secret_query not in caplog.text


def test_shutdown_reset_clears_cache():
    init_event_dedup_cache(enabled=True)
    cache = init_event_dedup_cache(enabled=True)
    assert cache is not None
    cache.is_duplicate("Ev-reset")
    reset_event_dedup_cache()
    init_event_dedup_cache(enabled=True)
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-reset"))
    pipeline.handle.assert_called_once()


def test_shutdown_gate_rejects_after_draining():
    init_shutdown_coordinator(drain_timeout_seconds=1.0)
    from truthexpiry.ops.shutdown import get_shutdown_coordinator

    coordinator = get_shutdown_coordinator()
    assert coordinator is not None
    coordinator.request_shutdown()
    pipeline = _pipeline()
    run_truthexpiry_query(**_args(pipeline=pipeline, event_id="Ev-shutdown"))
    pipeline.handle.assert_not_called()
