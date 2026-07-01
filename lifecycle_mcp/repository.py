from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path

from truthexpiry.config.common import parse_bool
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
    """Transport-free repository backed by canonical lifecycle JSON."""

    def __init__(
        self,
        dataset_path: Path | None = None,
        *,
        hot_reload: bool = False,
    ) -> None:
        self._dataset_path = dataset_path
        self._hot_reload = hot_reload and dataset_path is not None
        self._loaded_mtime: float | None = None
        self._dataset_version = ""
        self._records_by_key: dict[str, list[LifecycleRecordDto]] = {}
        self._reload_from_source()

    def _reload_from_source(self) -> None:
        raw = json.loads(_read_dataset_text(self._dataset_path))
        dataset = LifecycleDatasetFile.model_validate(raw)
        self._dataset_version = dataset.dataset_version
        self._records_by_key = {}
        for record in dataset.records:
            key = _canonical_key(record.entity, record.attribute, record.scope)
            self._records_by_key.setdefault(key, []).append(record)
        if self._dataset_path is not None:
            self._loaded_mtime = self._dataset_path.stat().st_mtime

    def _maybe_reload(self) -> None:
        if not self._hot_reload or self._dataset_path is None:
            return
        mtime = self._dataset_path.stat().st_mtime
        if self._loaded_mtime != mtime:
            self._reload_from_source()

    @property
    def dataset_version(self) -> str:
        return self._dataset_version

    def find_dtos(
        self, entity: str, attribute: str, scope: dict[str, str]
    ) -> list[LifecycleRecordDto]:
        self._maybe_reload()
        key = _canonical_key(entity, attribute, scope)
        matches = self._records_by_key.get(key, [])
        return list(matches)

    def find_domain_records(self, key: ClaimKey) -> list[LifecycleRecord]:
        self._maybe_reload()
        dtos = self._records_by_key.get(key.canonical(), [])
        return [_dto_to_domain(dto, key) for dto in dtos]

    def records_by_canonical(self) -> dict[str, list[LifecycleRecord]]:
        self._maybe_reload()
        grouped: dict[str, list[LifecycleRecord]] = {}
        for canonical, dtos in self._records_by_key.items():
            if not dtos:
                continue
            sample = dtos[0]
            claim_key = build_claim_key(sample.entity, sample.attribute, sample.scope)
            grouped[canonical] = [_dto_to_domain(dto, claim_key) for dto in dtos]
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
    path_str = os.environ.get("TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_PATH")
    hot_reload = parse_bool(
        os.environ,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_HOT_RELOAD",
        default=False,
    )
    dataset_path = Path(path_str) if path_str else None
    return LifecycleRecordRepository(dataset_path, hot_reload=hot_reload)
