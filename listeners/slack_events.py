def slack_event_id(body: dict) -> str | None:
    """Return the Slack envelope ``event_id`` when present."""
    event_id = body.get("event_id")
    if isinstance(event_id, str) and event_id.strip():
        return event_id.strip()
    return None


def action_token_from_event(event: dict) -> str | None:
    """Return the request-scoped RTS action token from a Slack event payload."""

    token = event.get("action_token")
    if isinstance(token, str) and token.strip():
        return token.strip()

    assistant_thread = event.get("assistant_thread")
    if isinstance(assistant_thread, dict):
        nested = assistant_thread.get("action_token")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    return None
