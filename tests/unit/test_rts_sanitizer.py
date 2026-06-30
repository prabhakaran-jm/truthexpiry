from truthexpiry.models.claim import EvidenceRef
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits, RtsHitRef
from truthexpiry.services.rts_sanitizer import (
    ephemeral_hit_to_evidence_refs,
    hit_to_evidence_ref,
    sanitize_rts_hits,
)

from adapters.fakes.synthetic_data import (
    DEFAULT_RTS_HIT,
    SYNTHETIC_PERMALINK,
    SYNTHETIC_TICKET_REF,
)


def test_hit_to_evidence_ref_metadata_only():
    refs = hit_to_evidence_ref(
        RtsHitRef(
            channel_id=DEFAULT_RTS_HIT.channel_id,
            message_ts=DEFAULT_RTS_HIT.message_ts,
            permalink=DEFAULT_RTS_HIT.permalink,
            ticket_ref=SYNTHETIC_TICKET_REF,
        )
    )
    assert len(refs) == 2
    assert refs[0].ref_type == "slack_permalink"
    assert refs[0].value == SYNTHETIC_PERMALINK
    assert refs[1].ref_type == "ticket_id"


def test_ephemeral_hit_to_evidence_refs_extracts_ticket_from_content():
    refs = ephemeral_hit_to_evidence_refs(DEFAULT_RTS_HIT)
    assert refs[0].ref_type == "slack_permalink"
    assert refs[1].ref_type == "ticket_id"
    assert refs[1].value == "PROD-481"


def test_sanitize_rts_hits_preserves_permalinks_not_bodies():
    hits = EphemeralRtsHits(
        hits=(
            EphemeralRtsHit(
                team_id="T000",
                channel_id="C000",
                channel_name="demo",
                message_ts="1.0",
                permalink="https://example.invalid/p/1",
                content="No ticket in this body.",
            ),
        )
    )
    refs = sanitize_rts_hits(hits)
    assert refs == (
        EvidenceRef(
            ref_type="slack_permalink",
            value="https://example.invalid/p/1",
            channel_id="C000",
            message_ts="1.0",
        ),
    )
    for ref in refs:
        assert ref.ref_type in {"slack_permalink", "ticket_id"}
        assert "message_text" not in ref.__dict__
