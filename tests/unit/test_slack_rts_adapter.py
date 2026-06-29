import logging
from unittest.mock import MagicMock

import pytest
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from adapters.slack_rts.adapter import SlackRtsAdapter
from truthexpiry.ports.rts import RtsSearchRequest, RtsSearchUnavailableError

from adapters.fakes.rts import FakeRtsPort


def test_fake_adapter_ignores_missing_action_token():
    rts = FakeRtsPort()
    hits = rts.search_context(
        RtsSearchRequest(query="report export", action_token=None, team_id="T000")
    )
    assert len(hits.hits) == 1


def test_adapter_maps_slack_api_error_to_unavailable():
    client = MagicMock(spec=WebClient)
    response = MagicMock()
    response.get.return_value = "rate_limited"
    client.api_call.side_effect = SlackApiError(
        "rate limited",
        response={"ok": False, "error": "rate_limited"},
    )
    adapter = SlackRtsAdapter(client)
    with pytest.raises(RtsSearchUnavailableError):
        adapter.search_context(
            RtsSearchRequest(
                query="demo",
                action_token="token",
                team_id="T000",
            )
        )


def test_adapter_maps_malformed_response_to_unavailable():
    client = MagicMock(spec=WebClient)
    client.api_call.return_value = {"ok": True, "results": {}}
    adapter = SlackRtsAdapter(client)
    with pytest.raises(RtsSearchUnavailableError):
        adapter.search_context(
            RtsSearchRequest(
                query="demo",
                action_token="token",
                team_id="T000",
            )
        )


def test_adapter_returns_empty_hits_on_successful_empty_search():
    client = MagicMock(spec=WebClient)
    client.api_call.return_value = {"ok": True, "results": {"messages": []}}
    adapter = SlackRtsAdapter(client)
    hits = adapter.search_context(
        RtsSearchRequest(
            query="demo",
            action_token="token",
            team_id="T000",
        )
    )
    assert hits.hits == ()


def test_adapter_logging_excludes_sensitive_values(caplog: pytest.LogCaptureFixture):
    client = MagicMock(spec=WebClient)
    client.api_call.return_value = {
        "ok": True,
        "results": {
            "messages": [
                {
                    "team_id": "T000",
                    "channel_id": "C000",
                    "channel_name": "demo",
                    "message_ts": "1.0",
                    "content": "secret-body-text",
                    "permalink": "https://example.invalid/p/secret",
                    "author_name": "Secret User",
                }
            ]
        },
    }
    adapter = SlackRtsAdapter(client)
    with caplog.at_level(logging.INFO):
        adapter.search_context(
            RtsSearchRequest(
                query="secret query text",
                action_token="secret-action-token",
                team_id="T000",
            )
        )
    combined = caplog.text
    for sensitive in (
        "secret-action-token",
        "secret query text",
        "secret-body-text",
        "https://example.invalid/p/secret",
        "Secret User",
    ):
        assert sensitive not in combined
