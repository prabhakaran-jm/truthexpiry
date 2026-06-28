from __future__ import annotations

from typing import Any

from mcp.types import CallToolResult

from adapters.lifecycle_mcp.errors import LifecycleMcpResponseError
from lifecycle_mcp.contracts import (
    SCHEMA_VERSION,
    SOURCE_NAME,
    GetLifecycleEvidenceOutput,
    LifecycleRecordDto,
)
from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord, LifecycleState
from truthexpiry.services.claim_key import build_claim_key


def map_structured_content(
    result: CallToolResult, requested_key: ClaimKey
) -> list[LifecycleRecord]:
    if result.isError:
        raise LifecycleMcpResponseError("MCP tool returned isError=True")
    if result.structuredContent is None:
        raise LifecycleMcpResponseError("MCP tool response missing structuredContent")

    try:
        output = GetLifecycleEvidenceOutput.model_validate(result.structuredContent)
    except Exception as exc:  # noqa: BLE001 - surface as response error
        raise LifecycleMcpResponseError(
            "MCP tool structuredContent failed validation"
        ) from exc

    if output.schema_version != SCHEMA_VERSION:
        raise LifecycleMcpResponseError(
            f"Unsupported lifecycle MCP schema version: {output.schema_version!r}"
        )
    if output.source != SOURCE_NAME:
        raise LifecycleMcpResponseError(
            f"Unexpected lifecycle MCP source: {output.source!r}"
        )

    records: list[LifecycleRecord] = []
    for dto in output.records:
        records.append(_dto_to_domain(dto, requested_key))
    return records


def map_output_dtos(
    output: GetLifecycleEvidenceOutput, requested_key: ClaimKey
) -> list[LifecycleRecord]:
    if output.schema_version != SCHEMA_VERSION:
        raise LifecycleMcpResponseError(
            f"Unsupported lifecycle MCP schema version: {output.schema_version!r}"
        )
    if output.source != SOURCE_NAME:
        raise LifecycleMcpResponseError(
            f"Unexpected lifecycle MCP source: {output.source!r}"
        )
    return [_dto_to_domain(dto, requested_key) for dto in output.records]


def _dto_to_domain(dto: LifecycleRecordDto, requested_key: ClaimKey) -> LifecycleRecord:
    record_key = build_claim_key(dto.entity, dto.attribute, dto.scope)
    if record_key.canonical() != requested_key.canonical():
        raise LifecycleMcpResponseError(
            "Lifecycle MCP record claim key does not match request"
        )
    try:
        state = LifecycleState(dto.state)
    except ValueError as exc:
        raise LifecycleMcpResponseError(
            f"Unknown lifecycle state: {dto.state!r}"
        ) from exc

    return LifecycleRecord(
        record_id=dto.record_id,
        key=record_key,
        state=state,
        value=dto.value,
        effective_date=dto.effective_date,
        supersedes_record_id=dto.supersedes_record_id,
    )


def structured_content_to_output(payload: dict[str, Any]) -> GetLifecycleEvidenceOutput:
    return GetLifecycleEvidenceOutput.model_validate(payload)
