from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedClaimDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    attribute: str
    scope: dict[str, str] = Field(default_factory=dict)
    stated_value: str
    evidence_ids: list[str]


class ClaimExtractionOutputDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: ExtractedClaimDto | None
