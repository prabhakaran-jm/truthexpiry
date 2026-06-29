"""Thin wrapper for assistant.search.context.

The official Slack method reference documents WebClient.assistant_search_context,
but slack-sdk 3.42.0 does not yet ship a generated helper for this method.
"""

from __future__ import annotations

from typing import Any

from slack_sdk import WebClient

from adapters.slack_rts.contracts import API_METHOD, HTTP_VERB
from adapters.slack_rts.errors import SlackRtsResponseError
from truthexpiry.ports.rts import RtsSearchRequest


def build_search_payload(request: RtsSearchRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "action_token": request.action_token,
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


def call_search_context(client: WebClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.api_call(
        api_method=API_METHOD,
        http_verb=HTTP_VERB,
        json=payload,
    )
    if not isinstance(response, dict):
        raise SlackRtsResponseError("Unexpected non-object Slack RTS response")
    return response
