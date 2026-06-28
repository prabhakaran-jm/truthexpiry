import re
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from listeners.truthexpiry_handler import run_truthexpiry_query


def handle_app_mentioned(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle @mentions in public channels."""
    del (
        client
    )  # TruthExpiry uses the pipeline; WebClient reserved for future thread fetch.

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
        context=context,
        event=event,
        query=cleaned_text,
        logger=logger,
        say=say,
        say_stream=say_stream,
        set_status=set_status,
    )
