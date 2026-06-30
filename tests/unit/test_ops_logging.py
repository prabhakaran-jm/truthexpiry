from __future__ import annotations

import json
import logging

import pytest

from truthexpiry.config.worker import SlackWorkerSettings
from truthexpiry.ops.context import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from truthexpiry.ops.logging import JsonLogFormatter, configure_logging


def test_correlation_id_is_not_derived_from_slack_ids():
    token = set_correlation_id(new_correlation_id())
    correlation_id = get_correlation_id()
    assert correlation_id is not None
    assert "U123" not in correlation_id
    assert "C123" not in correlation_id
    from truthexpiry.ops.context import reset_correlation_id

    reset_correlation_id(token)


def test_json_log_formatter_includes_structured_request_fields():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="TruthExpiry request completed",
        args=(),
        exc_info=None,
    )
    record.event = "truthexpiry_request"
    record.outcome = "success"
    record.duration_ms = 42
    record.query_length = 17
    record.claim_count = 2
    record.evidence_count = 3
    payload = json.loads(formatter.format(record))
    assert payload["event"] == "truthexpiry_request"
    assert payload["outcome"] == "success"
    assert payload["duration_ms"] == 42
    assert payload["query_length"] == 17
    assert payload["claim_count"] == 2
    assert payload["evidence_count"] == 3
    assert "TruthExpiry request completed" in payload["message"]


def test_json_log_formatter_includes_correlation_id(caplog: pytest.LogCaptureFixture):
    token = set_correlation_id("abc123correlation")
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="pipeline completed",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert payload["correlation_id"] == "abc123correlation"
    assert "pipeline completed" in payload["message"]
    from truthexpiry.ops.context import reset_correlation_id

    reset_correlation_id(token)


def test_configure_logging_json_mode():
    settings = SlackWorkerSettings.from_env(
        {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            "TRUTH_EXPIRY_LOG_FORMAT": "json",
            "TRUTH_EXPIRY_LOG_LEVEL": "WARNING",
        }
    )
    configure_logging(settings)
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert isinstance(root.handlers[0].formatter, JsonLogFormatter)
