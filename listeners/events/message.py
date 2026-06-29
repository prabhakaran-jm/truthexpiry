from functools import partial
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from listeners.truthexpiry_handler import run_truthexpiry_query
from truthexpiry.services.pipeline import TruthExpiryPipeline


def handle_message(
    pipeline: TruthExpiryPipeline,
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
        pipeline=pipeline,
        context=context,
        event=event,
        query=text,
        logger=logger,
        say=say,
        say_stream=say_stream,
        set_status=set_status,
    )


def register_message(app, pipeline: TruthExpiryPipeline) -> None:
    app.event("message")(partial(handle_message, pipeline=pipeline))
