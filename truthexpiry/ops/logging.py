from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from truthexpiry.config.worker import SlackWorkerSettings
from truthexpiry.ops.context import get_correlation_id

_STRUCTURED_LOG_FIELDS = frozenset(
    {
        "event",
        "outcome",
        "duration_ms",
        "query_length",
        "claim_count",
        "evidence_count",
        "failure_category",
        "exception_category",
    }
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": "slack-worker",
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = get_correlation_id()
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
        for field in _STRUCTURED_LOG_FIELDS:
            if field == "exception_category" and record.exc_info:
                payload["exception_category"] = (
                    record.exc_info[0].__name__ if record.exc_info[0] else None
                )
                continue
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=True)


_THIRD_PARTY_LOGGERS = (
    "httpx",
    "httpcore",
    "slack_sdk",
    "slack_bolt",
    "pydantic_ai",
    "openai",
)


def configure_logging(settings: SlackWorkerSettings) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    if settings.log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root.addHandler(handler)
    root.setLevel(settings.log_level)
    for logger_name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
