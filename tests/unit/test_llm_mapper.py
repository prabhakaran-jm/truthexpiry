import pytest

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY
from adapters.llm.contracts import ExtractedClaimDto
from adapters.llm.errors import (
    DuplicateEvidenceIdError,
    EmptyEvidenceIdsError,
    InvalidScopeError,
    InvalidStatedValueError,
    ScopeKeyCollisionError,
    UnknownEvidenceIdError,
    UnsupportedClaimSchemaError,
)
from adapters.llm.mapper import map_extracted_claim_dto
from truthexpiry.ports.rts import EphemeralRtsHit


def _hit(content: str, *, ts: str, permalink: str) -> EphemeralRtsHit:
    return EphemeralRtsHit(
        team_id="T000",
        channel_id="C000",
        channel_name="demo",
        message_ts=ts,
        permalink=permalink,
        content=content,
    )


def _evidence_map():
    return {
        "evidence-1": _hit(
            "Report export enabled PROD-481",
            ts="1.0",
            permalink="https://example.invalid/p/1",
        ),
        "evidence-2": _hit(
            "Report export disabled PROD-482",
            ts="2.0",
            permalink="https://example.invalid/p/2",
        ),
    }


def _dto(**overrides) -> ExtractedClaimDto:
    base = {
        "entity": "report_export",
        "attribute": "availability",
        "scope": {"plan": "starter", "region": "global"},
        "stated_value": "enabled",
        "evidence_ids": ["evidence-2", "evidence-1"],
    }
    base.update(overrides)
    return ExtractedClaimDto.model_validate(base)


def test_normalize_entity_attribute_and_stated_value():
    claim = map_extracted_claim_dto(
        _dto(entity="Report Export", attribute="Availability", stated_value="Enabled"),
        evidence_map=_evidence_map(),
    )
    assert claim.key == REPORT_EXPORT_KEY
    assert claim.stated_value == "enabled"


def test_normalize_scope_keys_and_values():
    claim = map_extracted_claim_dto(
        _dto(scope={"Plan": "Starter", "Region": "Global"}),
        evidence_map=_evidence_map(),
    )
    assert claim.key.scope.fields["plan"] == "starter"
    assert claim.key.scope.fields["region"] == "global"


def test_scope_key_collision_rejected():
    with pytest.raises(ScopeKeyCollisionError):
        map_extracted_claim_dto(
            _dto(scope={"plan": "starter", "Plan": "enterprise"}),
            evidence_map=_evidence_map(),
        )


def test_unsupported_entity_attribute_rejected():
    with pytest.raises(UnsupportedClaimSchemaError):
        map_extracted_claim_dto(
            _dto(entity="unknown", attribute="feature"),
            evidence_map=_evidence_map(),
        )


def test_invalid_stated_value_rejected():
    with pytest.raises(InvalidStatedValueError):
        map_extracted_claim_dto(
            _dto(stated_value="maybe"),
            evidence_map=_evidence_map(),
        )


def test_availability_synonyms_normalize_to_catalog_values():
    claim = map_extracted_claim_dto(
        _dto(stated_value="available"),
        evidence_map=_evidence_map(),
    )
    assert claim.stated_value == "enabled"

    claim = map_extracted_claim_dto(
        _dto(stated_value="unavailable"),
        evidence_map=_evidence_map(),
    )
    assert claim.stated_value == "disabled"


def test_off_alias_normalizes_to_disabled():
    claim = map_extracted_claim_dto(
        _dto(stated_value="off"),
        evidence_map=_evidence_map(),
    )
    assert claim.stated_value == "disabled"


def test_unknown_scope_key_rejected():
    with pytest.raises(InvalidScopeError):
        map_extracted_claim_dto(
            _dto(scope={"plan": "starter", "region": "global", "env": "prod"}),
            evidence_map=_evidence_map(),
        )


def test_missing_required_scope_rejected():
    with pytest.raises(InvalidScopeError):
        map_extracted_claim_dto(
            _dto(scope={}),
            evidence_map=_evidence_map(),
        )


def test_required_scope_fields_come_from_catalog_not_model():
    claim = map_extracted_claim_dto(_dto(), evidence_map=_evidence_map())
    assert claim.required_scope_fields == ("plan", "region")


def test_empty_evidence_ids_rejected():
    with pytest.raises(EmptyEvidenceIdsError):
        map_extracted_claim_dto(_dto(evidence_ids=[]), evidence_map=_evidence_map())


def test_duplicate_evidence_ids_rejected():
    with pytest.raises(DuplicateEvidenceIdError):
        map_extracted_claim_dto(
            _dto(evidence_ids=["evidence-1", "evidence-1"]),
            evidence_map=_evidence_map(),
        )


def test_fabricated_evidence_id_rejected():
    with pytest.raises(UnknownEvidenceIdError):
        map_extracted_claim_dto(
            _dto(evidence_ids=["evidence-99"]),
            evidence_map=_evidence_map(),
        )


def test_rate_limit_attribute_alias_maps_to_max_requests():
    claim = map_extracted_claim_dto(
        _dto(
            entity="api_rate_limit",
            attribute="rate_limit",
            scope={"plan": "starter", "region": "global"},
            stated_value="100",
        ),
        evidence_map=_evidence_map(),
    )
    assert claim.key.attribute == "max_requests"
    assert claim.stated_value == "100"


def test_valid_ids_map_to_correct_refs_and_preserve_rts_order():
    claim = map_extracted_claim_dto(
        _dto(evidence_ids=["evidence-2", "evidence-1"]),
        evidence_map=_evidence_map(),
    )
    permalinks = [
        ref.value for ref in claim.evidence_refs if ref.ref_type == "slack_permalink"
    ]
    assert permalinks == [
        "https://example.invalid/p/1",
        "https://example.invalid/p/2",
    ]
