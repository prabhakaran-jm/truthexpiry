import asyncio
from datetime import date

import pytest

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY
from lifecycle_mcp.contracts import (
    SCHEMA_VERSION,
    SOURCE_NAME,
    TOOL_NAME,
    GetLifecycleEvidenceOutput,
)
from lifecycle_mcp.repository import default_repository
from lifecycle_mcp.server import create_mcp


@pytest.fixture
def mcp_server():
    return create_mcp()


def test_tool_contract_exposes_exact_tool_name(mcp_server):
    tools = asyncio.run(mcp_server.list_tools())
    assert [tool.name for tool in tools] == [TOOL_NAME]


def test_tool_contract_uses_flat_input_schema(mcp_server):
    tools = asyncio.run(mcp_server.list_tools())
    schema = tools[0].inputSchema
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"entity", "attribute", "scope"}
    assert schema["properties"]["entity"]["type"] == "string"
    assert schema["properties"]["attribute"]["type"] == "string"
    assert schema["properties"]["scope"]["type"] == "object"
    assert schema["properties"]["scope"]["additionalProperties"]["type"] == "string"
    assert "request" not in schema["properties"]
    assert "evaluation_date" not in schema["properties"]


def test_tool_contract_structured_output_schema(mcp_server):
    tools = asyncio.run(mcp_server.list_tools())
    output_schema = tools[0].outputSchema
    assert output_schema is not None
    assert output_schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert output_schema["properties"]["source"]["const"] == SOURCE_NAME
    record_schema = output_schema["$defs"]["LifecycleRecordDto"]
    assert record_schema["properties"]["state"]["enum"] == [
        "PROPOSED",
        "PLANNED",
        "SHIPPED",
        "EFFECTIVE",
        "CANCELLED",
        "REJECTED",
        "DRAFT",
    ]
    assert record_schema["properties"]["effective_date"]["format"] == "date"


def test_repository_returns_prod_482_for_exact_claim_key():
    repository = default_repository()
    records = repository.find_dtos(
        REPORT_EXPORT_KEY.entity,
        REPORT_EXPORT_KEY.attribute,
        dict(REPORT_EXPORT_KEY.scope.fields),
    )
    prod_482 = next(record for record in records if record.record_id == "PROD-482")
    assert prod_482.value == "disabled"
    assert prod_482.state == "SHIPPED"
    assert prod_482.effective_date == date(2026, 5, 12)


def test_repository_returns_enterprise_report_export_record():
    repository = default_repository()
    records = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "enterprise", "region": "global"},
    )
    assert {record.record_id for record in records} == {"PROD-580"}


def test_structured_output_serializes_enums_and_iso_dates():
    repository = default_repository()
    dtos = repository.find_dtos(
        REPORT_EXPORT_KEY.entity,
        REPORT_EXPORT_KEY.attribute,
        dict(REPORT_EXPORT_KEY.scope.fields),
    )
    payload = GetLifecycleEvidenceOutput(records=dtos).model_dump(mode="json")
    prod_482 = next(
        record for record in payload["records"] if record["record_id"] == "PROD-482"
    )
    assert prod_482["state"] == "SHIPPED"
    assert prod_482["effective_date"] == "2026-05-12"
