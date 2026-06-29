import re
from functools import partial
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from listeners.truthexpiry_handler import run_truthexpiry_query
from truthexpiry.services.pipeline import TruthExpiryPipeline


def handle_app_mentioned(
    pipeline: TruthExpiryPipeline,
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle @mentions in public channels."""
    del client

    thread_ts = event.get("thread_ts") or event["ts"]
    text = event.get("text", "")
    cleaned_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not cleaned_text:
        say(
            text=(
                "Ask me whether a claim is still current. "
                "MVP search covers *public channels* in your workspace."
            ),
            thread_ts=thread_ts,
        )
        return

    run_truthexpiry_query(
        pipeline=pipeline,
        context=context,
        event=event,
        query=cleaned_text,
        logger=logger,
        say=say,
        say_stream=say_stream,
        set_status=set_status,
    )


def register_app_mentioned(app, pipeline: TruthExpiryPipeline) -> None:
    app.event("app_mention")(
        partial(handle_app_mentioned, pipeline=pipeline),
    )
