from truthexpiry.models.claim import EvidenceRef
from truthexpiry.ports.rts import EphemeralRtsHits, RtsHitRef
from truthexpiry.services.rts_sanitizer import hit_to_evidence_ref, sanitize_rts_hits

from adapters.fakes.synthetic_data import DEFAULT_RTS_HIT, SYNTHETIC_PERMALINK


def test_hit_to_evidence_ref_metadata_only():
    refs = hit_to_evidence_ref(DEFAULT_RTS_HIT)
    assert len(refs) == 2
    assert refs[0].ref_type == "slack_permalink"
    assert refs[0].value == SYNTHETIC_PERMALINK
    assert refs[1].ref_type == "ticket_id"


def test_sanitize_rts_hits_preserves_permalinks_not_bodies():
    hits = EphemeralRtsHits(
        hits=(
            RtsHitRef(
                channel_id="C000",
                message_ts="1.0",
                permalink="https://example.invalid/p/1",
                ticket_ref=None,
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
