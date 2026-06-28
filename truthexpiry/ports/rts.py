from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchCapabilities:
    is_ai_search_enabled: bool


@dataclass(frozen=True)
class RtsSearchRequest:
    team_id: str
    query: str
    action_token: str | None
    disable_semantic_search: bool


@dataclass(frozen=True)
class RtsHitRef:
    channel_id: str
    message_ts: str
    permalink: str
    ticket_ref: str | None = None


@dataclass(frozen=True)
class EphemeralRtsHits:
    """Request-scoped RTS metadata. Must not be persisted."""

    hits: tuple[RtsHitRef, ...]


class RtsPort(Protocol):
    def search_capabilities(self, team_id: str) -> SearchCapabilities: ...

    def search_context(self, request: RtsSearchRequest) -> EphemeralRtsHits: ...
