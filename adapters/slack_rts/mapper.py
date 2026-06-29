from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from adapters.slack_rts.contracts import (
    SlackRtsContextMessageDto,
    SlackRtsPrimaryMessageDto,
    parse_search_response,
)
from adapters.slack_rts.errors import SlackRtsResponseError
from truthexpiry.ports.rts import (
    EphemeralRtsHit,
    EphemeralRtsHits,
    RtsContextMessage,
)

logger = logging.getLogger(__name__)


def map_search_response(payload: dict[str, Any]) -> EphemeralRtsHits:
    if payload.get("ok") is not True:
        error_code = payload.get("error", "unknown_error")
        raise SlackRtsResponseError(f"Slack RTS returned ok=false ({error_code})")

    results = payload.get("results")
    if not isinstance(results, dict) or "messages" not in results:
        raise SlackRtsResponseError("Slack RTS response missing results.messages")

    try:
        response = parse_search_response(payload)
    except Exception as exc:  # noqa: BLE001 - surface as response error
        raise SlackRtsResponseError("Slack RTS response failed validation") from exc

    if not response.ok:
        error_code = response.error or "unknown_error"
        raise SlackRtsResponseError(f"Slack RTS returned ok=false ({error_code})")

    if response.results is None:
        raise SlackRtsResponseError("Slack RTS response missing results")

    hits = _map_primary_messages(response.results.messages)
    return EphemeralRtsHits(hits=tuple(hits))


def _map_primary_messages(
    messages: list[SlackRtsPrimaryMessageDto],
) -> list[EphemeralRtsHit]:
    seen: set[str] = set()
    hits: list[EphemeralRtsHit] = []

    for message in messages:
        identity = f"{message.team_id}|{message.channel_id}|{message.message_ts}"
        if identity in seen:
            continue
        seen.add(identity)
        hits.append(_map_primary_message(message))

    return hits


def _map_primary_message(message: SlackRtsPrimaryMessageDto) -> EphemeralRtsHit:
    context = message.context_messages
    before = tuple(_map_context_messages(context.before if context else []))
    after = tuple(_map_context_messages(context.after if context else []))
    return EphemeralRtsHit(
        team_id=message.team_id,
        channel_id=message.channel_id,
        channel_name=message.channel_name,
        message_ts=message.message_ts,
        permalink=message.permalink,
        content=message.content,
        context_before=before,
        context_after=after,
    )


def _map_context_messages(entries: list[Any]) -> list[RtsContextMessage]:
    mapped: list[RtsContextMessage] = []
    skipped = 0
    for entry in entries:
        try:
            message = SlackRtsContextMessageDto.model_validate(entry)
        except ValidationError:
            skipped += 1
            continue
        mapped.append(
            RtsContextMessage(
                message_ts=message.ts,
                content=message.text,
                author_user_id=message.user_id,
                author_name=message.author_name,
            )
        )
    if skipped:
        logger.warning(
            "Slack RTS context entries skipped component=mapper "
            "outcome=invalid_context skipped_count=%s",
            skipped,
        )
    return mapped
