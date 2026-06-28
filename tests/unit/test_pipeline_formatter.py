from truthexpiry.models.verdict import ClaimStatus, ValidationResult
from truthexpiry.services.claim_key import build_claim_key
from truthexpiry.services.pipeline import format_validation_results

from adapters.fakes.synthetic_data import BILLING_REFUND_KEY, REPORT_EXPORT_KEY


def _result(
    *,
    key,
    status: ClaimStatus,
    explanation: str,
    lifecycle_record_ids: tuple[str, ...] = (),
) -> ValidationResult:
    return ValidationResult(
        key=key,
        status=status,
        explanation=explanation,
        lifecycle_record_ids=lifecycle_record_ids,
    )


def test_formatter_renders_conflicting_lifecycle_record_ids():
    markdown = format_validation_results(
        "refund policy",
        (
            _result(
                key=BILLING_REFUND_KEY,
                status=ClaimStatus.CONFLICTING,
                explanation="Multiple active authoritative lifecycle records disagree for this claim key.",
                lifecycle_record_ids=("PROD-520-A", "PROD-520-B"),
            ),
        ),
    )
    assert "Lifecycle evidence:" in markdown
    assert "- PROD-520-A" in markdown
    assert "- PROD-520-B" in markdown


def test_formatter_renders_superseded_lifecycle_record_ids():
    markdown = format_validation_results(
        "rate limit",
        (
            _result(
                key=build_claim_key(
                    "api_rate_limit", "max_requests", {"plan": "starter"}
                ),
                status=ClaimStatus.SUPERSEDED,
                explanation="The claim conflicts with the current authoritative lifecycle state.",
                lifecycle_record_ids=("PROD-511",),
            ),
        ),
    )
    assert "Lifecycle evidence:" in markdown
    assert "- PROD-511" in markdown


def test_formatter_renders_current_lifecycle_record_ids():
    markdown = format_validation_results(
        "report export",
        (
            _result(
                key=REPORT_EXPORT_KEY,
                status=ClaimStatus.CURRENT,
                explanation="An authoritative lifecycle record matches this claim's value and scope.",
                lifecycle_record_ids=("PROD-501",),
            ),
        ),
    )
    assert "Lifecycle evidence:" in markdown
    assert "- PROD-501" in markdown
