from truthexpiry.models.claim import EvidenceRef
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits, RtsHitRef
from truthexpiry.services.search_plan import extract_ticket_ref


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


def ephemeral_hit_to_evidence_refs(hit: EphemeralRtsHit) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = [
        EvidenceRef(
            ref_type="slack_permalink",
            value=hit.permalink,
            channel_id=hit.channel_id,
            message_ts=hit.message_ts,
        )
    ]
    ticket_ref = extract_ticket_ref(hit.content)
    if ticket_ref:
        refs.append(EvidenceRef(ref_type="ticket_id", value=ticket_ref))
    return tuple(refs)


def sanitize_rts_hits(hits: EphemeralRtsHits) -> tuple[EvidenceRef, ...]:
    """Map ephemeral RTS hits to evidence references without retaining message bodies."""

    evidence: list[EvidenceRef] = []
    for hit in hits.hits:
        evidence.extend(ephemeral_hit_to_evidence_refs(hit))
    return tuple(evidence)
