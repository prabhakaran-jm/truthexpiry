from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1"
SOURCE_NAME = "truth-expiry-lifecycle-mcp"
TOOL_NAME = "get_lifecycle_evidence"

LifecycleStateName = Literal[
    "PROPOSED",
    "PLANNED",
    "SHIPPED",
    "EFFECTIVE",
    "CANCELLED",
    "REJECTED",
    "DRAFT",
]


class LifecycleRecordDto(BaseModel):
    record_id: str
    entity: str
    attribute: str
    scope: dict[str, str]
    value: str
    state: LifecycleStateName
    effective_date: date
    supersedes_record_id: str | None = None


class GetLifecycleEvidenceOutput(BaseModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    source: Literal["truth-expiry-lifecycle-mcp"] = SOURCE_NAME
    records: list[LifecycleRecordDto] = Field(default_factory=list)


class LifecycleDatasetFile(BaseModel):
    dataset_version: str
    description: str
    records: list[LifecycleRecordDto]
