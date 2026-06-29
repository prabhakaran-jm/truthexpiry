import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from adapters.composition import build_pipeline
from listeners import register_listeners

load_dotenv(dotenv_path=".env", override=False)

logging.basicConfig(level=os.environ.get("TRUTH_EXPIRY_LOG_LEVEL", "INFO"))

_bot_token = os.environ.get("SLACK_BOT_TOKEN")
_slack_api_url = os.environ.get("SLACK_API_URL")

if _slack_api_url:
    app = App(client=WebClient(base_url=_slack_api_url, token=_bot_token))
else:
    app = App(token=_bot_token)

pipeline = build_pipeline(slack_client=app.client)
register_listeners(app, pipeline)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
