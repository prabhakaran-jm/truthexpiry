"""Tests for lifecycle dataset hot reload."""

from __future__ import annotations

import json
from pathlib import Path

from lifecycle_mcp.repository import LifecycleRecordRepository


def _write_dataset(path: Path, *, prod_482_value: str) -> None:
    payload = {
        "dataset_version": "test-hot-reload",
        "description": "Hot reload test fixture",
        "records": [
            {
                "record_id": "PROD-481",
                "entity": "report_export",
                "attribute": "availability",
                "scope": {"plan": "starter", "region": "global"},
                "value": "enabled",
                "state": "SHIPPED",
                "effective_date": "2024-01-01",
                "supersedes_record_id": None,
            },
            {
                "record_id": "PROD-482",
                "entity": "report_export",
                "attribute": "availability",
                "scope": {"plan": "starter", "region": "global"},
                "value": prod_482_value,
                "state": "SHIPPED",
                "effective_date": "2026-05-12",
                "supersedes_record_id": "PROD-481",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_repository_hot_reload_picks_up_file_changes(tmp_path: Path) -> None:
    dataset_path = tmp_path / "lifecycle_records.json"
    _write_dataset(dataset_path, prod_482_value="disabled")

    repository = LifecycleRecordRepository(dataset_path, hot_reload=True)
    records = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "starter", "region": "global"},
    )
    assert records[-1].value == "disabled"

    _write_dataset(dataset_path, prod_482_value="enabled")
    reloaded = repository.find_dtos(
        "report_export",
        "availability",
        {"plan": "starter", "region": "global"},
    )
    assert reloaded[-1].value == "enabled"
