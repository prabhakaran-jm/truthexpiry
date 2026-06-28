from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

from truthexpiry.models.claim import ClaimKey
from truthexpiry.models.evidence import LifecycleRecord, LifecycleState
from truthexpiry.services.claim_key import build_claim_key

from lifecycle_mcp.contracts import LifecycleDatasetFile, LifecycleRecordDto


def _read_dataset_text(dataset_path: Path | None = None) -> str:
    if dataset_path is not None:
        return dataset_path.read_text(encoding="utf-8")
    resource = resources.files("lifecycle_mcp.data") / "lifecycle_records.json"
    return resource.read_text(encoding="utf-8")


def _canonical_key(entity: str, attribute: str, scope: dict[str, str]) -> str:
    return build_claim_key(entity, attribute, scope).canonical()


class LifecycleRecordRepository:
    """Transport-free repository that loads canonical JSON once at construction."""

    def __init__(self, dataset_path: Path | None = None) -> None:
        raw = json.loads(_read_dataset_text(dataset_path))
        dataset = LifecycleDatasetFile.model_validate(raw)
        self._dataset_version = dataset.dataset_version
        self._records_by_key: dict[str, list[LifecycleRecordDto]] = {}
        for record in dataset.records:
            key = _canonical_key(record.entity, record.attribute, record.scope)
            self._records_by_key.setdefault(key, []).append(record)

    @property
    def dataset_version(self) -> str:
        return self._dataset_version

    def find_dtos(
        self, entity: str, attribute: str, scope: dict[str, str]
    ) -> list[LifecycleRecordDto]:
        key = _canonical_key(entity, attribute, scope)
        matches = self._records_by_key.get(key, [])
        return list(matches)

    def find_domain_records(self, key: ClaimKey) -> list[LifecycleRecord]:
        dtos = self._records_by_key.get(key.canonical(), [])
        return [_dto_to_domain(dto, key) for dto in dtos]

    def records_by_canonical(self) -> dict[str, list[LifecycleRecord]]:
        grouped: dict[str, list[LifecycleRecord]] = {}
        for canonical, dtos in self._records_by_key.items():
            if not dtos:
                continue
            sample = dtos[0]
            claim_key = build_claim_key(
                sample.entity, sample.attribute, sample.scope
            )
            grouped[canonical] = [
                _dto_to_domain(dto, claim_key) for dto in dtos
            ]
        return grouped


def _dto_to_domain(dto: LifecycleRecordDto, key: ClaimKey) -> LifecycleRecord:
    return LifecycleRecord(
        record_id=dto.record_id,
        key=key,
        state=LifecycleState(dto.state),
        value=dto.value,
        effective_date=dto.effective_date,
        supersedes_record_id=dto.supersedes_record_id,
    )


@lru_cache(maxsize=1)
def default_repository() -> LifecycleRecordRepository:
    return LifecycleRecordRepository()
