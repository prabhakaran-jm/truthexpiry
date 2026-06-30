from dataclasses import dataclass, field
from typing import Protocol


class RtsSearchUnavailableError(RuntimeError):
    """Raised when live Slack RTS cannot be performed for this request."""


@dataclass(frozen=True)
class RtsSearchRequest:
    query: str
    action_token: str | None = field(default=None, repr=False)
    team_id: str | None = None
    disable_semantic_search: bool = False


@dataclass(frozen=True)
class RtsContextMessage:
    message_ts: str
    content: str = field(repr=False)
    author_user_id: str | None = None
    author_name: str | None = None


@dataclass(frozen=True)
class RtsHitRef:
    """Metadata-only evidence reference. Must not contain message bodies."""

    channel_id: str
    message_ts: str
    permalink: str
    ticket_ref: str | None = None


@dataclass(frozen=True)
class EphemeralRtsHit:
    """Request-scoped RTS hit with ephemeral Slack content. Must not be persisted."""

    team_id: str
    channel_id: str
    channel_name: str | None
    message_ts: str
    permalink: str
    content: str = field(repr=False)
    context_before: tuple[RtsContextMessage, ...] = field(default=(), repr=False)
    context_after: tuple[RtsContextMessage, ...] = field(default=(), repr=False)


@dataclass(frozen=True)
class EphemeralRtsHits:
    """Request-scoped RTS results. Must not be persisted."""

    hits: tuple[EphemeralRtsHit, ...]


class RtsPort(Protocol):
    def search_context(self, request: RtsSearchRequest) -> EphemeralRtsHits: ...
