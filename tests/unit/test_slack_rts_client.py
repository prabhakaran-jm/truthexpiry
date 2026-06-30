from unittest.mock import MagicMock

import pytest
from slack_sdk import WebClient
from slack_sdk.web import SlackResponse

from adapters.slack_rts.adapter import SlackRtsAdapter
from adapters.slack_rts.client import (
    API_METHOD,
    HTTP_VERB,
    _response_payload,
    build_search_payload,
    call_search_context,
)
from adapters.slack_rts.contracts import API_METHOD as CONTRACT_API_METHOD
from truthexpiry.ports.rts import RtsSearchRequest, RtsSearchUnavailableError


def test_build_search_payload_matches_m2_contract():
    request = RtsSearchRequest(
        query="Is report export available?",
        action_token="action-token-value",
        team_id="T000",
    )
    payload = build_search_payload(request)
    assert payload == {
        "query": "Is report export available?",
        "action_token": "action-token-value",
        "channel_types": ["public_channel"],
        "content_types": ["messages"],
        "include_context_messages": True,
        "include_bots": False,
        "include_archived_channels": False,
        "limit": 20,
        "sort": "score",
        "sort_dir": "desc",
        "highlight": False,
        "disable_semantic_search": False,
    }


def test_response_payload_accepts_slack_response_wrapper():
    payload = {"ok": True, "results": {"messages": []}}
    wrapped = SlackResponse(
        client=None,
        http_verb=HTTP_VERB,
        api_url="https://slack.com/api/assistant.search.context",
        req_args={},
        data=payload,
        headers={},
        status_code=200,
    )
    assert _response_payload(wrapped) == payload


def test_call_search_context_unwraps_slack_response():
    client = MagicMock(spec=WebClient)
    payload = {"ok": True, "results": {"messages": []}}
    client.api_call.return_value = SlackResponse(
        client=client,
        http_verb=HTTP_VERB,
        api_url="https://slack.com/api/assistant.search.context",
        req_args={},
        data=payload,
        headers={},
        status_code=200,
    )
    assert call_search_context(client, {"query": "demo"}) == payload


def test_adapter_uses_exact_api_call_method_and_body():
    client = MagicMock(spec=WebClient)
    client.api_call.return_value = {
        "ok": True,
        "results": {"messages": []},
    }
    adapter = SlackRtsAdapter(client)
    request = RtsSearchRequest(
        query="starter rate limit",
        action_token="token-123",
        team_id="T000",
    )
    adapter.search_context(request)
    client.api_call.assert_called_once_with(
        api_method=API_METHOD,
        http_verb=HTTP_VERB,
        json=build_search_payload(request),
    )
    assert API_METHOD == CONTRACT_API_METHOD == "assistant.search.context"


@pytest.mark.parametrize("action_token", [None, "", "   "])
def test_adapter_rejects_missing_or_blank_action_token(action_token):
    adapter = SlackRtsAdapter(MagicMock(spec=WebClient))
    with pytest.raises(RtsSearchUnavailableError):
        adapter.search_context(
            RtsSearchRequest(
                query="demo",
                action_token=action_token,
                team_id="T000",
            )
        )
