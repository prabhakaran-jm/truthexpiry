import logging

import pytest

from adapters.slack_rts.errors import SlackRtsResponseError
from adapters.slack_rts.mapper import map_search_response
from truthexpiry.services.search_plan import extract_ticket_ref


def test_mapper_does_not_extract_ticket_refs():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "channel_name": "demo",
                    "message_ts": "1.0",
                    "content": "Tracked in PROD-481.",
                    "permalink": "https://example.invalid/p/1",
                }
            ]
        },
    }
    hits = map_search_response(payload)
    assert extract_ticket_ref(hits.hits[0].content) == "PROD-481"
    assert not hasattr(hits.hits[0], "ticket_ref")


def test_mapper_allows_optional_context_author_name():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "message_ts": "1.0",
                    "content": "Primary",
                    "permalink": "https://example.invalid/p/1",
                    "context_messages": {
                        "before": [
                            {
                                "text": "Context without author name",
                                "user_id": "U000",
                                "ts": "0.9",
                            }
                        ],
                        "after": [],
                    },
                }
            ]
        },
    }
    hits = map_search_response(payload)
    assert hits.hits[0].context_before[0].author_name is None


def test_mapper_rejects_missing_primary_content():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "message_ts": "1.0",
                    "permalink": "https://example.invalid/p/1",
                }
            ]
        },
    }
    with pytest.raises(SlackRtsResponseError):
        map_search_response(payload)


def test_mapper_rejects_missing_primary_message_ts():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "content": "Primary without ts",
                    "permalink": "https://example.invalid/p/1",
                }
            ]
        },
    }
    with pytest.raises(SlackRtsResponseError):
        map_search_response(payload)


def test_mapper_skips_malformed_before_context_keeps_valid_primary():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "message_ts": "1.0",
                    "content": "Primary",
                    "permalink": "https://example.invalid/p/1",
                    "context_messages": {
                        "before": [
                            {
                                "text": "Valid before context",
                                "user_id": "U000",
                                "ts": "0.9",
                            },
                            {
                                "text": "Missing ts is malformed",
                                "user_id": "U001",
                            },
                        ],
                        "after": [],
                    },
                }
            ]
        },
    }
    hits = map_search_response(payload)
    assert len(hits.hits) == 1
    hit = hits.hits[0]
    assert hit.content == "Primary"
    assert len(hit.context_before) == 1
    assert hit.context_before[0].content == "Valid before context"


def test_mapper_skips_malformed_after_context_keeps_valid_primary():
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "message_ts": "1.0",
                    "content": "Primary",
                    "permalink": "https://example.invalid/p/1",
                    "context_messages": {
                        "before": [],
                        "after": [
                            {
                                "user_id": "U002",
                                "ts": "1.1",
                            }
                        ],
                    },
                }
            ]
        },
    }
    hits = map_search_response(payload)
    assert len(hits.hits) == 1
    assert hits.hits[0].context_after == ()


def test_mapper_does_not_log_skipped_context_content(
    caplog: pytest.LogCaptureFixture,
):
    payload = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "message_ts": "1.0",
                    "content": "Primary",
                    "permalink": "https://example.invalid/p/1",
                    "context_messages": {
                        "before": [
                            {
                                "text": "secret-context-body-text",
                                "user_id": "U003",
                            }
                        ],
                        "after": [],
                    },
                }
            ]
        },
    }
    with caplog.at_level(logging.WARNING):
        hits = map_search_response(payload)
    assert hits.hits[0].context_before == ()
    assert "secret-context-body-text" not in caplog.text
