import re
from logging import Logger

from slack_bolt import Args, BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from listeners.slack_events import slack_event_id
from listeners.truthexpiry_handler import run_truthexpiry_query
from truthexpiry.services.demo_guidance import format_empty_mention_guidance
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
    *,
    event_id: str | None = None,
):
    """Handle @mentions in public channels."""
    del client

    thread_ts = event.get("thread_ts") or event["ts"]
    text = event.get("text", "")
    cleaned_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not cleaned_text:
        say(
            text=format_empty_mention_guidance(),
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
        event_id=event_id,
    )


def register_app_mentioned(app, pipeline: TruthExpiryPipeline) -> None:
    def app_mention_listener(args: Args) -> None:
        event = args.event
        if event is None:
            args.logger.warning("app_mention event missing from request body")
            return
        if args.say_stream is None or args.set_status is None:
            args.logger.warning("app_mention missing assistant utilities")
            return

        handle_app_mentioned(
            pipeline=pipeline,
            client=args.client,
            context=args.context,
            event=event,
            logger=args.logger,
            say=args.say,
            say_stream=args.say_stream,
            set_status=args.set_status,
            event_id=slack_event_id(
                args.body if isinstance(getattr(args, "body", None), dict) else {}
            ),
        )

    app.event("app_mention")(app_mention_listener)
