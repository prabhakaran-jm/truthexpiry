from typing import Protocol

from truthexpiry.models.claim import ExtractedClaim
from truthexpiry.ports.rts import EphemeralRtsHits


class ClaimExtractionPort(Protocol):
    def extract_claims(
        self, query: str, hits: EphemeralRtsHits
    ) -> list[ExtractedClaim]: ...
