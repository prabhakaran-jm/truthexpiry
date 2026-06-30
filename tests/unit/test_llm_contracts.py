import pytest
from pydantic import ValidationError

from adapters.llm.contracts import ClaimExtractionOutputDto, ExtractedClaimDto


def _claim_payload(**overrides):
    base = {
        "entity": "report_export",
        "attribute": "availability",
        "scope": {"plan": "starter", "region": "global"},
        "stated_value": "enabled",
        "evidence_ids": ["evidence-1"],
    }
    base.update(overrides)
    return base


def test_explicit_null_claim_accepted():
    output = ClaimExtractionOutputDto.model_validate({"claim": None})
    assert output.claim is None


def test_omitted_claim_rejected():
    with pytest.raises(ValidationError):
        ClaimExtractionOutputDto.model_validate({})


def test_empty_object_rejected():
    with pytest.raises(ValidationError):
        ClaimExtractionOutputDto.model_validate({})


def test_extra_top_level_field_rejected():
    with pytest.raises(ValidationError):
        ClaimExtractionOutputDto.model_validate({"claim": None, "status": "CURRENT"})


def test_claims_array_rejected():
    with pytest.raises(ValidationError):
        ClaimExtractionOutputDto.model_validate(
            {"claims": [_claim_payload()], "claim": None}
        )


def test_status_field_on_claim_rejected():
    with pytest.raises(ValidationError):
        ExtractedClaimDto.model_validate({**_claim_payload(), "status": "CURRENT"})


def test_omitted_evidence_ids_rejected():
    payload = _claim_payload()
    del payload["evidence_ids"]
    with pytest.raises(ValidationError):
        ExtractedClaimDto.model_validate(payload)
