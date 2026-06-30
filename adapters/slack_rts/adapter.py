from __future__ import annotations

import logging
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from adapters.slack_rts.client import build_search_payload, call_search_context
from adapters.slack_rts.contracts import API_METHOD
from adapters.slack_rts.errors import SlackRtsResponseError, SlackRtsTransportError
from adapters.slack_rts.mapper import map_search_response
from truthexpiry.ports.rts import (
    EphemeralRtsHits,
    RtsPort,
    RtsSearchRequest,
    RtsSearchUnavailableError,
)

logger = logging.getLogger(__name__)

_MISSING_ACTION_TOKEN_MESSAGE = (
    "Live Slack search requires a request-scoped action token."
)


class SlackRtsAdapter(RtsPort):
    """Live public-channel Slack RTS adapter."""

    def __init__(self, slack_client: WebClient) -> None:
        self._client = slack_client

    def search_context(self, request: RtsSearchRequest) -> EphemeralRtsHits:
        action_token = request.action_token
        if action_token is None or not action_token.strip():
            raise RtsSearchUnavailableError(_MISSING_ACTION_TOKEN_MESSAGE)

        payload = build_search_payload(request)
        started = time.perf_counter()
        try:
            response = call_search_context(self._client, payload)
        except SlackApiError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            error_code = "slack_api_error"
            if isinstance(exc.response, dict):
                error_code = str(exc.response.get("error", error_code))
            logger.warning(
                "Slack RTS transport failure method=%s outcome=transport error_code=%s duration_ms=%s",
                API_METHOD,
                error_code,
                duration_ms,
            )
            raise RtsSearchUnavailableError(
                "Live Slack search is currently unavailable for this request."
            ) from SlackRtsTransportError("Slack RTS API call failed")
        except SlackRtsResponseError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Slack RTS response failure method=%s outcome=response duration_ms=%s",
                API_METHOD,
                duration_ms,
            )
            raise RtsSearchUnavailableError(
                "Live Slack search is currently unavailable for this request."
            ) from exc

        try:
            hits = map_search_response(response)
        except SlackRtsResponseError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Slack RTS mapping failure method=%s outcome=response duration_ms=%s",
                API_METHOD,
                duration_ms,
            )
            raise RtsSearchUnavailableError(
                "Live Slack search is currently unavailable for this request."
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Slack RTS search completed method=%s outcome=success result_count=%s duration_ms=%s",
            API_METHOD,
            len(hits.hits),
            duration_ms,
        )
        return hits
