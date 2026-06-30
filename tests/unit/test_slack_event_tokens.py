from listeners.slack_events import action_token_from_event


def test_action_token_from_event_reads_top_level_token():
    assert action_token_from_event({"action_token": " top-level "}) == "top-level"


def test_action_token_from_event_reads_assistant_thread_token():
    event = {
        "assistant_thread": {
            "action_token": "nested-token-value",
        }
    }
    assert action_token_from_event(event) == "nested-token-value"


def test_action_token_from_event_prefers_top_level_when_present():
    event = {
        "action_token": "top-level",
        "assistant_thread": {"action_token": "nested"},
    }
    assert action_token_from_event(event) == "top-level"


def test_action_token_from_event_returns_none_when_missing():
    assert action_token_from_event({}) is None
    assert action_token_from_event({"assistant_thread": {}}) is None
