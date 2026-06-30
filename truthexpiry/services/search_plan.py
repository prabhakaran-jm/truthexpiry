import re
from dataclasses import dataclass

from truthexpiry.ports.rts import RtsSearchRequest

QUESTION_PREFIXES = (
    "what ",
    "where ",
    "when ",
    "why ",
    "how ",
    "who ",
    "which ",
    "is ",
    "are ",
    "do ",
    "does ",
    "did ",
    "can ",
    "could ",
    "should ",
    "would ",
)


@dataclass(frozen=True)
class SearchCapabilities:
    """Legacy capability shape retained for unit tests only."""

    is_ai_search_enabled: bool


def is_natural_language_question(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    if normalized.endswith("?"):
        return True
    return normalized.startswith(QUESTION_PREFIXES)


def should_use_semantic_search(is_ai_search_enabled: bool, query: str) -> bool:
    if not is_ai_search_enabled:
        return False
    return is_natural_language_question(query)


def build_rts_search_request(
    *,
    team_id: str | None,
    query: str,
    action_token: str | None,
    disable_semantic_search: bool = False,
) -> RtsSearchRequest:
    """Build a single RTS search request without a capabilities lookup."""

    return RtsSearchRequest(
        query=query,
        action_token=action_token,
        team_id=team_id,
        disable_semantic_search=disable_semantic_search,
    )


def extract_ticket_ref(text: str) -> str | None:
    match = re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", text)
    if match is None:
        return None
    return match.group(0)
