"""Tests for assistant suggested prompts on thread start."""

from __future__ import annotations

from unittest.mock import MagicMock

from listeners.events.assistant_thread_started import (
    SUGGESTED_PROMPTS_TITLE,
    handle_assistant_thread_started,
)
from truthexpiry.services.demo_guidance import suggested_prompt_payloads


def test_handle_assistant_thread_started_sets_demo_queries():
    set_suggested_prompts = MagicMock()
    logger = MagicMock()

    handle_assistant_thread_started(set_suggested_prompts, logger)

    set_suggested_prompts.assert_called_once_with(
        prompts=suggested_prompt_payloads(),
        title=SUGGESTED_PROMPTS_TITLE,
    )
    logger.exception.assert_not_called()
