from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from listeners.truthexpiry_handler import run_truthexpiry_query


def handle_message(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle direct messages (`message.im`) including assistant panel threads."""
    del client

    if event.get("subtype"):
        return
    if event.get("bot_id"):
        return
    if event.get("channel_type") != "im":
        return

    text = event.get("text", "").strip()
    if not text:
        return

    run_truthexpiry_query(
        context=context,
        event=event,
        query=text,
        logger=logger,
        say=say,
        say_stream=say_stream,
        set_status=set_status,
    )
