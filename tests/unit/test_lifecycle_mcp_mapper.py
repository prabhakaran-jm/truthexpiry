from datetime import date

import pytest
from mcp.types import CallToolResult

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY
from adapters.lifecycle_mcp.errors import LifecycleMcpResponseError
from adapters.lifecycle_mcp.mapper import map_output_dtos, map_structured_content
from lifecycle_mcp.contracts import GetLifecycleEvidenceOutput, LifecycleRecordDto
from truthexpiry.models.evidence import LifecycleState


def _valid_output(*records: LifecycleRecordDto) -> GetLifecycleEvidenceOutput:
    return GetLifecycleEvidenceOutput(records=list(records))


def test_mapper_maps_dto_to_domain_record():
    dto = LifecycleRecordDto(
        record_id="PROD-482",
        entity="report_export",
        attribute="availability",
        scope={"plan": "starter", "region": "global"},
        value="disabled",
        state="SHIPPED",
        effective_date=date(2026, 5, 12),
        supersedes_record_id="PROD-481",
    )
    records = map_output_dtos(_valid_output(dto), REPORT_EXPORT_KEY)
    assert len(records) == 1
    record = records[0]
    assert record.record_id == "PROD-482"
    assert record.state is LifecycleState.SHIPPED
    assert record.value == "disabled"
    assert record.key.canonical() == REPORT_EXPORT_KEY.canonical()


def test_mapper_rejects_missing_structured_content():
    result = CallToolResult(content=[], structuredContent=None, isError=False)
    with pytest.raises(LifecycleMcpResponseError, match="missing structuredContent"):
        map_structured_content(result, REPORT_EXPORT_KEY)


def test_mapper_rejects_tool_error_result():
    result = CallToolResult(content=[], structuredContent={}, isError=True)
    with pytest.raises(LifecycleMcpResponseError, match="isError=True"):
        map_structured_content(result, REPORT_EXPORT_KEY)


def test_mapper_rejects_unsupported_schema_version():
    output = GetLifecycleEvidenceOutput.model_construct(
        schema_version="2",
        source="truth-expiry-lifecycle-mcp",
        records=[],
    )
    with pytest.raises(
        LifecycleMcpResponseError, match="Unsupported lifecycle MCP schema"
    ):
        map_output_dtos(output, REPORT_EXPORT_KEY)


def test_mapper_rejects_malformed_effective_date():
    payload = {
        "schema_version": "1",
        "source": "truth-expiry-lifecycle-mcp",
        "records": [
            {
                "record_id": "PROD-482",
                "entity": "report_export",
                "attribute": "availability",
                "scope": {"plan": "starter", "region": "global"},
                "value": "disabled",
                "state": "SHIPPED",
                "effective_date": "not-a-date",
            }
        ],
    }
    result = CallToolResult(content=[], structuredContent=payload, isError=False)
    with pytest.raises(LifecycleMcpResponseError, match="failed validation"):
        map_structured_content(result, REPORT_EXPORT_KEY)


def test_mapper_rejects_unknown_state():
    dto = LifecycleRecordDto(
        record_id="PROD-999",
        entity="report_export",
        attribute="availability",
        scope={"plan": "starter", "region": "global"},
        value="disabled",
        state="SHIPPED",
        effective_date=date(2026, 5, 12),
    )
    payload = _valid_output(dto).model_dump(mode="json")
    payload["records"][0]["state"] = "UNKNOWN"
    result = CallToolResult(content=[], structuredContent=payload, isError=False)
    with pytest.raises(LifecycleMcpResponseError, match="failed validation"):
        map_structured_content(result, REPORT_EXPORT_KEY)


def test_mapper_rejects_claim_key_mismatch():
    dto = LifecycleRecordDto(
        record_id="PROD-482",
        entity="analytics_export",
        attribute="availability",
        scope={"plan": "enterprise", "region": "global"},
        value="enabled",
        state="SHIPPED",
        effective_date=date(2024, 1, 1),
    )
    with pytest.raises(LifecycleMcpResponseError, match="does not match request"):
        map_output_dtos(_valid_output(dto), REPORT_EXPORT_KEY)
