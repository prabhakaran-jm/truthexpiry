"""Tests for TruthExpiry Block Kit verdict rendering."""

from __future__ import annotations

from truthexpiry.models.claim import EvidenceRef
from truthexpiry.models.verdict import ClaimStatus, ValidationResult
from truthexpiry.services.pipeline import TruthExpiryResponse, format_validation_results

from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY, SYNTHETIC_PERMALINK
from listeners.views.verdict_builder import (
    AUTHORITY_FOOTNOTE,
    build_response_blocks,
    build_verdict_blocks,
    humanize_claim_key,
)


def _result(
    *,
    status: ClaimStatus,
    lifecycle_record_ids: tuple[str, ...] = ("PROD-482",),
    stated_value: str = "enabled",
) -> ValidationResult:
    return ValidationResult(
        key=REPORT_EXPORT_KEY,
        status=status,
        explanation="Example explanation for judges.",
        stated_value=stated_value,
        evidence_refs=(
            EvidenceRef(
                ref_type="slack_permalink",
                value=SYNTHETIC_PERMALINK,
                channel_id="C000",
                message_ts="1.0",
            ),
        ),
        lifecycle_record_ids=lifecycle_record_ids,
    )


def test_humanize_claim_key_includes_scope():
    label = humanize_claim_key(REPORT_EXPORT_KEY)
    assert "Report Export" in label
    assert "Starter plan" in label


def test_build_verdict_blocks_include_status_claim_timeline_and_footnote():
    blocks = build_verdict_blocks(
        "Is report export available on the Starter plan?",
        (_result(status=ClaimStatus.SUPERSEDED),),
    )
    payload = [block.to_dict() for block in blocks]

    assert payload[0]["type"] == "section"
    assert "Your question" in payload[0]["text"]["text"]
    assert any(
        block["type"] == "header"
        and "Superseded" in block["text"]["text"]
        for block in payload
    )
    body_text = " ".join(
        block["text"]["text"]
        for block in payload
        if block.get("text") and isinstance(block["text"], dict)
    )
    context_text = " ".join(
        element["text"]
        for block in payload
        if block["type"] == "context"
        for element in block.get("elements", [])
    )
    assert "Stated in Slack" in body_text
    assert "PROD-482" in body_text
    assert SYNTHETIC_PERMALINK in body_text
    assert AUTHORITY_FOOTNOTE in context_text


def test_build_response_blocks_use_guidance_fallback_without_results():
    response = TruthExpiryResponse(
        markdown_text="Try one of these example questions",
        results=(),
    )
    blocks = build_response_blocks(
        query="Tell me about report export",
        response=response,
    )
    assert len(blocks) == 1
    assert blocks[0].to_dict()["type"] == "section"


def test_format_validation_results_includes_stated_value():
    markdown = format_validation_results(
        "report export",
        (_result(status=ClaimStatus.CURRENT),),
    )
    assert "Stated in Slack" in markdown
    assert "`enabled`" in markdown
