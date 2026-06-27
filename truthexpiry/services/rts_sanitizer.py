from truthexpiry.models.claim import EvidenceRef
from truthexpiry.ports.rts import EphemeralRtsHits, RtsHitRef


def hit_to_evidence_ref(hit: RtsHitRef) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = [
        EvidenceRef(
            ref_type="slack_permalink",
            value=hit.permalink,
            channel_id=hit.channel_id,
            message_ts=hit.message_ts,
        )
    ]
    if hit.ticket_ref:
        refs.append(EvidenceRef(ref_type="ticket_id", value=hit.ticket_ref))
    return tuple(refs)


def sanitize_rts_hits(hits: EphemeralRtsHits) -> tuple[EvidenceRef, ...]:
    """Map ephemeral RTS metadata to evidence references without retaining message bodies."""

    evidence: list[EvidenceRef] = []
    for hit in hits.hits:
        evidence.extend(hit_to_evidence_ref(hit))
    return tuple(evidence)
