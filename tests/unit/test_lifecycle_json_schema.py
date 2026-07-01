import json
from importlib import resources

from lifecycle_mcp.contracts import LifecycleDatasetFile, LifecycleRecordDto
from lifecycle_mcp.repository import LifecycleRecordRepository


def test_canonical_dataset_file_validates_against_schema():
    raw = json.loads(
        (resources.files("lifecycle_mcp.data") / "lifecycle_records.json").read_text(
            encoding="utf-8"
        )
    )
    dataset = LifecycleDatasetFile.model_validate(raw)
    assert dataset.dataset_version == "2"
    assert len(dataset.records) >= 20


def test_repository_loads_dataset_once_and_indexes_by_claim_key():
    repository = LifecycleRecordRepository()
    key_records = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "starter", "region": "global"},
    )
    record_ids = {record.record_id for record in key_records}
    assert record_ids == {"PROD-481", "PROD-482"}


def test_repository_returns_enterprise_report_export_record():
    repository = LifecycleRecordRepository()
    records = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "enterprise", "region": "global"},
    )
    assert {record.record_id for record in records} == {"PROD-580"}


def test_repository_dto_fields_match_expected_prod_482():
    repository = LifecycleRecordRepository()
    records = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "starter", "region": "global"},
    )
    prod_482 = next(record for record in records if record.record_id == "PROD-482")
    assert prod_482 == LifecycleRecordDto(
        record_id="PROD-482",
        entity="report_export",
        attribute="availability",
        scope={"plan": "starter", "region": "global"},
        value="disabled",
        state="SHIPPED",
        effective_date=prod_482.effective_date,
        supersedes_record_id="PROD-481",
    )
    assert str(prod_482.effective_date) == "2026-05-12"
