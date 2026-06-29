import json
from pathlib import Path

import pytest

from adapters.slack_rts.mapper import map_search_response
from adapters.slack_rts.errors import SlackRtsResponseError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_contract_maps_primary_and_context_messages():
    payload = _load("slack_rts_success_primary_context.json")
    hits = map_search_response(payload)
    assert len(hits.hits) == 1
    hit = hits.hits[0]
    assert hit.team_id == "T000DEMO01"
    assert hit.channel_id == "C000PUBLIC1"
    assert hit.permalink.startswith("https://example.invalid/")
    assert len(hit.context_before) == 1
    assert hit.context_before[0].author_name == "Planner"
    assert hit.context_after == ()


def test_contract_deduplicates_primary_messages_preserving_order():
    payload = _load("slack_rts_success_duplicate_primary.json")
    hits = map_search_response(payload)
    assert [hit.message_ts for hit in hits.hits] == [
        "1710000000.000100",
        "1710000001.000101",
    ]
    assert hits.hits[0].content == "First duplicate."


def test_contract_maps_empty_success():
    payload = _load("slack_rts_success_empty.json")
    hits = map_search_response(payload)
    assert hits.hits == ()


def test_contract_rejects_ok_false():
    payload = _load("slack_rts_error_ok_false.json")
    with pytest.raises(SlackRtsResponseError, match="ok=false"):
        map_search_response(payload)


def test_contract_rejects_missing_messages():
    payload = _load("slack_rts_malformed_missing_messages.json")
    with pytest.raises(SlackRtsResponseError):
        map_search_response(payload)


def test_contract_skips_malformed_context_without_failing_primary():
    payload = _load("slack_rts_success_malformed_context.json")
    hits = map_search_response(payload)
    assert len(hits.hits) == 1
    hit = hits.hits[0]
    assert hit.channel_id == "C000PUBLIC1"
    assert [message.author_name for message in hit.context_before] == ["Planner"]
    assert hit.context_after == ()
