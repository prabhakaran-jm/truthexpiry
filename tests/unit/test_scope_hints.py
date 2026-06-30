from adapters.llm.scope_hints import apply_scope_hints_from_query
from adapters.llm.contracts import ExtractedClaimDto


def _claim(**overrides) -> ExtractedClaimDto:
    base = {
        "entity": "report_export",
        "attribute": "availability",
        "scope": {},
        "stated_value": "enabled",
        "evidence_ids": ["evidence-1"],
    }
    base.update(overrides)
    return ExtractedClaimDto.model_validate(base)


def test_starter_plan_hint_fills_missing_plan():
    claim = apply_scope_hints_from_query(
        "Is report export available on the Starter plan?",
        _claim(),
    )
    assert claim.scope == {"plan": "starter", "region": "global"}


def test_existing_scope_is_not_overwritten():
    claim = apply_scope_hints_from_query(
        "Starter plan question",
        _claim(scope={"plan": "enterprise", "region": "eu"}),
    )
    assert claim.scope == {"plan": "enterprise", "region": "eu"}
