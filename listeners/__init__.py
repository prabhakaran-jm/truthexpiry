from slack_bolt import App

from truthexpiry.services.pipeline import TruthExpiryPipeline

from listeners import actions, events, views


def register_listeners(app: App, pipeline: TruthExpiryPipeline) -> None:
    actions.register(app)
    events.register(app, pipeline)
    views.register(app)
