from truthexpiry.ports.rts import EphemeralRtsHits, RtsSearchRequest, SearchCapabilities

from adapters.fakes.synthetic_data import DEFAULT_RTS_HIT


class FakeRtsPort:
    """Synthetic RTS adapter for offline Milestone 0 testing."""

    def __init__(self, *, is_ai_search_enabled: bool = True) -> None:
        self.is_ai_search_enabled = is_ai_search_enabled
        self.capability_calls: list[str] = []
        self.search_calls: list[RtsSearchRequest] = []

    def search_capabilities(self, team_id: str) -> SearchCapabilities:
        self.capability_calls.append(team_id)
        return SearchCapabilities(is_ai_search_enabled=self.is_ai_search_enabled)

    def search_context(self, request: RtsSearchRequest) -> EphemeralRtsHits:
        self.search_calls.append(request)
        return EphemeralRtsHits(hits=(DEFAULT_RTS_HIT,))
