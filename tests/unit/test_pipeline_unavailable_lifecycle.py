from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.models.verdict import ClaimStatus
from truthexpiry.ports.lifecycle import LifecycleEvidenceUnavailableError
from truthexpiry.services.pipeline import TruthExpiryPipeline, TruthExpiryRequest

from adapters.fakes.llm import FakeClaimExtractionPort
from adapters.fakes.rts import FakeRtsPort
from adapters.fakes.synthetic_data import REPORT_EXPORT_KEY


class _UnavailableLifecycle:
    def fetch_records(self, key):
        raise LifecycleEvidenceUnavailableError(
            "Authoritative lifecycle evidence is currently unavailable."
        )


def test_pipeline_returns_unverified_when_lifecycle_unavailable(fixed_clock):
    llm = FakeClaimExtractionPort(
        claims_by_query={
            "report export": [
                ExtractedClaim(
                    key=REPORT_EXPORT_KEY,
                    stated_value="enabled",
                    required_scope_fields=("plan", "region"),
                )
            ]
        }
    )
    pipeline = TruthExpiryPipeline(
        rts=FakeRtsPort(),
        lifecycle=_UnavailableLifecycle(),
        llm=llm,
        clock=fixed_clock,
    )
    response = pipeline.handle(
        TruthExpiryRequest(
            team_id="T000SYNTHETIC",
            user_id="U000",
            channel_id="C000",
            thread_ts="1.0",
            query="Is report export available on the starter plan?",
        )
    )
    assert response.results[0].status is ClaimStatus.UNVERIFIED
    assert (
        "authoritative lifecycle evidence is currently unavailable"
        in response.results[0].explanation.lower()
    )
    assert "UNVERIFIED" in response.markdown_text
