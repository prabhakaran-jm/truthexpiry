import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from slack_bolt import Args

import listeners.events.app_mentioned as app_mentioned
import listeners.events.message as message_event
from listeners.events.app_mentioned import register_app_mentioned
from listeners.events.message import register_message
from truthexpiry.services.pipeline import TruthExpiryPipeline


class _RecordingApp:
    def __init__(self) -> None:
        self.listeners: dict[str, object] = {}

    def event(self, event_type: str):
        def decorator(listener):
            self.listeners[event_type] = listener
            return listener

        return decorator


def _args_for_event(event: dict) -> Args:
    return SimpleNamespace(
        client=MagicMock(name="client"),
        context=MagicMock(name="context"),
        event=event,
        logger=MagicMock(name="logger"),
        say=MagicMock(name="say"),
        say_stream=MagicMock(name="say_stream"),
        set_status=MagicMock(name="set_status"),
    )


def test_app_mention_registered_listener_has_bolt_compatible_signature():
    recording_app = _RecordingApp()
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    register_app_mentioned(recording_app, pipeline)

    listener = recording_app.listeners["app_mention"]
    signature = inspect.signature(listener)
    assert list(signature.parameters) == ["args"]
    assert signature.parameters["args"].annotation is Args


def test_app_mention_listener_invokes_handler_with_injected_values():
    recording_app = _RecordingApp()
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    register_app_mentioned(recording_app, pipeline)
    listener = recording_app.listeners["app_mention"]

    bolt_args = _args_for_event(
        {
            "type": "app_mention",
            "text": "<@UBOT> Is report export available on the Starter plan?",
            "ts": "1.0",
            "team": "T000",
            "channel": "C000",
            "user": "U000",
            "action_token": "forwarded-token",
        }
    )

    with patch.object(app_mentioned, "handle_app_mentioned") as handle_mock:
        listener(bolt_args)

    handle_mock.assert_called_once_with(
        pipeline=pipeline,
        client=bolt_args.client,
        context=bolt_args.context,
        event=bolt_args.event,
        logger=bolt_args.logger,
        say=bolt_args.say,
        say_stream=bolt_args.say_stream,
        set_status=bolt_args.set_status,
    )


def test_app_mention_listener_strips_mention_and_forwards_action_token():
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    pipeline.handle.return_value = MagicMock(markdown_text="ok", results=())

    event = {
        "type": "app_mention",
        "text": "<@UBOT> Is report export available on the Starter plan?",
        "ts": "1.0",
        "team": "T000",
        "channel": "C000",
        "user": "U000",
        "action_token": "forwarded-token",
    }
    context = MagicMock()
    context.team_id = "T000"
    context.channel_id = "C000"
    context.user_id = "U000"

    app_mentioned.handle_app_mentioned(
        pipeline=pipeline,
        client=MagicMock(),
        context=context,
        event=event,
        logger=MagicMock(),
        say=MagicMock(),
        say_stream=MagicMock(return_value=MagicMock()),
        set_status=MagicMock(),
    )

    request = pipeline.handle.call_args.args[0]
    assert request.action_token == "forwarded-token"
    assert request.query == "Is report export available on the Starter plan?"


def test_message_registered_listener_has_bolt_compatible_signature():
    recording_app = _RecordingApp()
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    register_message(recording_app, pipeline)

    listener = recording_app.listeners["message"]
    signature = inspect.signature(listener)
    assert list(signature.parameters) == ["args"]
    assert signature.parameters["args"].annotation is Args


def test_message_listener_invokes_handler_with_injected_values():
    recording_app = _RecordingApp()
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    register_message(recording_app, pipeline)
    listener = recording_app.listeners["message"]

    bolt_args = _args_for_event(
        {
            "type": "message",
            "channel_type": "im",
            "text": "report export",
            "ts": "1.0",
            "team": "T000",
            "channel": "D000",
            "user": "U000",
            "action_token": "dm-token",
        }
    )

    with patch.object(message_event, "handle_message") as handle_mock:
        listener(bolt_args)

    handle_mock.assert_called_once_with(
        pipeline=pipeline,
        client=bolt_args.client,
        context=bolt_args.context,
        event=bolt_args.event,
        logger=bolt_args.logger,
        say=bolt_args.say,
        say_stream=bolt_args.say_stream,
        set_status=bolt_args.set_status,
    )


@pytest.mark.parametrize(
    "event",
    [
        {"type": "message", "subtype": "message_changed", "channel_type": "im"},
        {"type": "message", "bot_id": "B000", "channel_type": "im", "text": "bot"},
        {"type": "message", "channel_type": "channel", "text": "public"},
        {"type": "message", "channel_type": "im", "text": "   "},
    ],
)
def test_message_handler_ignores_filtered_events(event):
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    message_event.handle_message(
        pipeline=pipeline,
        client=MagicMock(),
        context=MagicMock(),
        event=event,
        logger=MagicMock(),
        say=MagicMock(),
        say_stream=MagicMock(),
        set_status=MagicMock(),
    )
    pipeline.handle.assert_not_called()


def test_registration_wrappers_do_not_store_request_state_on_modules():
    before_app_mentioned = set(vars(app_mentioned).keys())
    before_message = set(vars(message_event).keys())

    recording_app = _RecordingApp()
    pipeline = MagicMock(spec=TruthExpiryPipeline)
    register_app_mentioned(recording_app, pipeline)
    register_message(recording_app, pipeline)

    bolt_args = _args_for_event(
        {
            "type": "app_mention",
            "text": "<@UBOT> hello",
            "ts": "1.0",
            "action_token": "secret-token",
        }
    )

    with patch.object(app_mentioned, "handle_app_mentioned"):
        recording_app.listeners["app_mention"](bolt_args)
        recording_app.listeners["message"](bolt_args)

    after_app_mentioned = set(vars(app_mentioned).keys())
    after_message = set(vars(message_event).keys())
    assert after_app_mentioned == before_app_mentioned
    assert after_message == before_message
    assert "secret-token" not in repr(vars(app_mentioned))
    assert "secret-token" not in repr(vars(message_event))


def test_app_source_uses_token_or_client_not_both():
    source = (Path(__file__).resolve().parents[2] / "app.py").read_text(
        encoding="utf-8"
    )
    assert "if _slack_api_url:" in source
    assert "App(client=WebClient(base_url=_slack_api_url, token=_bot_token))" in source
    assert "App(token=_bot_token)" in source
    assert source.count("App(") == 2


def test_app_startup_builds_pipeline_with_bolt_client(
    monkeypatch: pytest.MonkeyPatch,
):
    import importlib
    import sys

    monkeypatch.delenv("SLACK_API_URL", raising=False)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    sys.modules.pop("app", None)

    with (
        patch("slack_bolt.App") as app_cls,
        patch("adapters.composition.build_pipeline") as build_pipeline,
        patch("listeners.register_listeners"),
        patch("dotenv.load_dotenv"),
        patch("logging.basicConfig"),
    ):
        mock_app = MagicMock()
        mock_app.client = MagicMock(name="bolt_client")
        app_cls.return_value = mock_app

        app_module = importlib.import_module("app")

    app_cls.assert_called_once_with(token="xoxb-test")
    build_pipeline.assert_called_once_with(slack_client=mock_app.client)
    assert app_module.pipeline is build_pipeline.return_value
