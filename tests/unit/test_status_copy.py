"""Tests for assistant loading and status copy."""

from listeners.status_copy import ASSISTANT_LOADING_MESSAGES, ASSISTANT_STATUS


def test_assistant_status_describes_validation_work():
    assert "lifecycle" in ASSISTANT_STATUS.lower()


def test_assistant_loading_messages_reflect_pipeline_stages():
    joined = " ".join(ASSISTANT_LOADING_MESSAGES).lower()
    assert "slack" in joined
    assert "extract" in joined
    assert "lifecycle" in joined
    assert "deterministic" in joined
    assert "hamster" not in joined
    assert "goldfish" not in joined
