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
