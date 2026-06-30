from truthexpiry.ports.rts import EphemeralRtsHits, RtsSearchRequest

from adapters.fakes.synthetic_data import DEFAULT_RTS_HIT


class FakeRtsPort:
    """Synthetic RTS adapter for offline Milestone 0 testing."""

    def __init__(self, *, return_empty: bool = False) -> None:
        self.return_empty = return_empty
        self.search_calls: list[RtsSearchRequest] = []

    def search_context(self, request: RtsSearchRequest) -> EphemeralRtsHits:
        self.search_calls.append(request)
        if self.return_empty:
            return EphemeralRtsHits(hits=())
        return EphemeralRtsHits(hits=(DEFAULT_RTS_HIT,))
