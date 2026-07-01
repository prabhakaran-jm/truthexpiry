"""Tests for shared demo guidance and workspace seeding."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.seed_demo_workspace import seed_channel
from truthexpiry.services.demo_guidance import (
    DEMO_EXAMPLE_QUERIES,
    DEMO_SEED_MESSAGES,
    format_empty_mention_guidance,
    format_no_claim_guidance,
    suggested_prompt_payloads,
)


def test_demo_seed_messages_match_acceptance_matrix():
    assert len(DEMO_SEED_MESSAGES) == 4
    assert "PROD-481" in DEMO_SEED_MESSAGES[0]
    assert "PROD-482" in DEMO_SEED_MESSAGES[1]
    assert "PROD-510" in DEMO_SEED_MESSAGES[2]
    assert "PROD-511" in DEMO_SEED_MESSAGES[3]


def test_demo_example_queries_cover_report_export_and_rate_limit():
    messages = {query.message for query in DEMO_EXAMPLE_QUERIES}
    assert "Is report export available on the Starter plan?" in messages
    assert "Is report export disabled on the Starter plan?" in messages
    assert "Is the API rate limit 100 requests for Starter?" in messages
    assert "Is the API rate limit 50 requests for Starter?" in messages


def test_suggested_prompt_payloads_align_with_example_queries():
    payloads = suggested_prompt_payloads()
    assert len(payloads) == len(DEMO_EXAMPLE_QUERIES)
    for payload, query in zip(payloads, DEMO_EXAMPLE_QUERIES, strict=True):
        assert payload == {"title": query.title, "message": query.message}


def test_format_no_claim_guidance_lists_working_examples():
    text = format_no_claim_guidance("What is the API rate limit for Starter?")
    assert "Try one of these example questions" in text
    assert "Is the API rate limit 50 requests for Starter?" in text
    assert "deterministic code assigns validity" in text.lower()


def test_format_empty_mention_guidance_lists_examples():
    text = format_empty_mention_guidance()
    assert "Try one of these example questions" in text
    assert "public channels" in text


def test_seed_channel_dry_run_does_not_call_slack():
    client = MagicMock()
    timestamps = seed_channel(
        client=client,
        channel_id="C01234567",
        dry_run=True,
    )
    assert len(timestamps) == len(DEMO_SEED_MESSAGES)
    client.chat_postMessage.assert_not_called()


def test_seed_channel_posts_each_message():
    client = MagicMock()
    client.chat_postMessage.side_effect = [
        {"ts": "1.0"},
        {"ts": "2.0"},
        {"ts": "3.0"},
        {"ts": "4.0"},
    ]
    timestamps = seed_channel(
        client=client,
        channel_id="C01234567",
        delay_seconds=0,
    )
    assert timestamps == ["1.0", "2.0", "3.0", "4.0"]
    assert client.chat_postMessage.call_count == 4
    for call, message in zip(
        client.chat_postMessage.call_args_list,
        DEMO_SEED_MESSAGES,
        strict=True,
    ):
        assert call.kwargs == {"channel": "C01234567", "text": message}


def test_seed_channel_rejects_invalid_channel_id():
    with pytest.raises(ValueError, match="public channel ID"):
        seed_channel(client=MagicMock(), channel_id="D01234567", delay_seconds=0)
