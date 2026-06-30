from unittest.mock import MagicMock

from listeners.truthexpiry_handler import run_truthexpiry_query
from truthexpiry.services.pipeline import TruthExpiryRequest, TruthExpiryResponse


def test_listener_forwards_action_token_to_pipeline(fixed_clock):
    pipeline = MagicMock()
    pipeline.handle.return_value = TruthExpiryResponse(
        markdown_text="ok",
        results=(),
    )
    event = {
        "ts": "1.0",
        "team": "T000",
        "channel": "C000",
        "user": "U000",
        "assistant_thread": {"action_token": "forwarded-token"},
    }
    context = MagicMock()
    context.team_id = "T000"
    context.channel_id = "C000"
    context.user_id = "U000"

    run_truthexpiry_query(
        pipeline=pipeline,
        context=context,
        event=event,
        query="report export",
        logger=MagicMock(),
        say=MagicMock(),
        say_stream=MagicMock(return_value=MagicMock()),
        set_status=MagicMock(),
    )

    request = pipeline.handle.call_args.args[0]
    assert isinstance(request, TruthExpiryRequest)
    assert request.action_token == "forwarded-token"
    assert "forwarded-token" not in repr(request)
