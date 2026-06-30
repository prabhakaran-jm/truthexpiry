import logging
import sys

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from adapters.composition import build_pipeline
from listeners import register_listeners
from truthexpiry.config import ConfigError, SlackWorkerSettings

load_dotenv(dotenv_path=".env", override=False)


def create_slack_application(
    settings: SlackWorkerSettings,
) -> tuple[App, SocketModeHandler]:
    """Construct Bolt App and SocketModeHandler from validated settings."""
    bot_token = settings.slack_bot_token.get_secret()  # type: ignore[union-attr]
    app_token = settings.slack_app_token.get_secret()  # type: ignore[union-attr]

    if settings.slack_api_url:
        client = WebClient(
            base_url=settings.slack_api_url,
            token=bot_token,
            timeout=settings.slack_timeout_seconds,
        )
        app = App(client=client)
    else:
        app = App(
            token=bot_token,
            client=WebClient(
                token=bot_token,
                timeout=settings.slack_timeout_seconds,
            ),
        )

    handler = SocketModeHandler(app, app_token)
    return app, handler


def main() -> None:
    settings = SlackWorkerSettings.from_env()
    try:
        settings.validate_runtime()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    logging.basicConfig(level=settings.log_level)

    app, handler = create_slack_application(settings)
    pipeline = build_pipeline(slack_client=app.client, settings=settings)
    register_listeners(app, pipeline)
    handler.start()


if __name__ == "__main__":
    main()
