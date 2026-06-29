from slack_bolt import App

from truthexpiry.services.pipeline import TruthExpiryPipeline

from .app_home_opened import handle_app_home_opened
from .app_mentioned import register_app_mentioned
from .assistant_thread_started import handle_assistant_thread_started
from .message import register_message


def register(app: App, pipeline: TruthExpiryPipeline) -> None:
    app.event("app_home_opened")(handle_app_home_opened)
    register_app_mentioned(app, pipeline)
    app.event("assistant_thread_started")(handle_assistant_thread_started)
    register_message(app, pipeline)
