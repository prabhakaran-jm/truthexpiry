import pytest

from truthexpiry.ports.rts import SearchCapabilities
from truthexpiry.services.search_plan import (
    build_rts_search_request,
    extract_ticket_ref,
    is_natural_language_question,
    should_use_semantic_search,
)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Is report export available?", True),
        ("what is the rate limit", True),
        ("report export starter", False),
        ("", False),
    ],
)
def test_is_natural_language_question(query: str, expected: bool):
    assert is_natural_language_question(query) is expected


@pytest.mark.parametrize(
    ("enabled", "query", "expected"),
    [
        (True, "Is report export available?", True),
        (True, "report export starter", False),
        (False, "Is report export available?", False),
    ],
)
def test_should_use_semantic_search(enabled: bool, query: str, expected: bool):
    assert should_use_semantic_search(enabled, query) is expected


def test_build_rts_search_request_uses_semantic_when_enabled():
    request = build_rts_search_request(
        team_id="T000",
        query="Is report export available on starter?",
        action_token="action-token",
        capabilities=SearchCapabilities(is_ai_search_enabled=True),
    )
    assert request.disable_semantic_search is False
    assert request.action_token == "action-token"


def test_build_rts_search_request_falls_back_to_keyword():
    request = build_rts_search_request(
        team_id="T000",
        query="report export starter",
        action_token=None,
        capabilities=SearchCapabilities(is_ai_search_enabled=True),
    )
    assert request.disable_semantic_search is True


def test_extract_ticket_ref():
    assert extract_ticket_ref("See PROD-482 for details") == "PROD-482"
    assert extract_ticket_ref("no ticket here") is None
