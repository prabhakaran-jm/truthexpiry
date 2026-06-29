from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

API_METHOD = "assistant.search.context"
HTTP_VERB = "POST"


class SlackRtsContextMessageDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    user_id: str | None = None
    author_name: str | None = None
    ts: str


class SlackRtsContextMessagesDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    before: list[SlackRtsContextMessageDto] = Field(default_factory=list)
    after: list[SlackRtsContextMessageDto] = Field(default_factory=list)


class SlackRtsPrimaryMessageDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    team_id: str
    channel_id: str
    channel_name: str | None = None
    message_ts: str
    content: str
    author_user_id: str | None = None
    author_name: str | None = None
    is_author_bot: bool | None = None
    permalink: str
    context_messages: SlackRtsContextMessagesDto | None = None


class SlackRtsResultsDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: list[SlackRtsPrimaryMessageDto] = Field(default_factory=list)


class SlackRtsResponseMetadataDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    next_cursor: str | None = None


class SlackRtsSearchResponseDto(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    error: str | None = None
    results: SlackRtsResultsDto | None = None
    response_metadata: SlackRtsResponseMetadataDto | None = None


def parse_search_response(payload: dict[str, Any]) -> SlackRtsSearchResponseDto:
    return SlackRtsSearchResponseDto.model_validate(payload)
