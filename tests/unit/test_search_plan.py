import pytest

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


def test_build_rts_search_request_defaults_to_semantic_enabled():
    request = build_rts_search_request(
        team_id="T000",
        query="Is report export available on starter?",
        action_token="action-token",
    )
    assert request.disable_semantic_search is False
    assert request.action_token == "action-token"
    assert "action-token" not in repr(request)


def test_build_rts_search_request_honors_explicit_disable_semantic():
    request = build_rts_search_request(
        team_id="T000",
        query="report export starter",
        action_token=None,
        disable_semantic_search=True,
    )
    assert request.disable_semantic_search is True


def test_extract_ticket_ref():
    assert extract_ticket_ref("See PROD-482 for details") == "PROD-482"
    assert extract_ticket_ref("no ticket here") is None
