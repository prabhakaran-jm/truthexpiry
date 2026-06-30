from __future__ import annotations

from truthexpiry.models.claim import EvidenceRef
from truthexpiry.ports.rts import EphemeralRtsHit
from truthexpiry.services.rts_sanitizer import ephemeral_hit_to_evidence_refs

MAX_FALLBACK_EVIDENCE_REFS = 3


def _evidence_ref_identity(ref: EvidenceRef) -> tuple[str, str, str | None, str | None]:
    return (ref.ref_type, ref.value, ref.channel_id, ref.message_ts)


def _sorted_evidence_ids(evidence_map: dict[str, EphemeralRtsHit]) -> list[str]:
    return sorted(
        evidence_map.keys(),
        key=lambda item: int(item.split("-", 1)[1]),
    )


def build_fallback_evidence_refs(
    evidence_map: dict[str, EphemeralRtsHit],
) -> tuple[EvidenceRef, ...]:
    """Sanitize RTS hits in order, deduplicate references, then cap at three."""
    if not evidence_map:
        return ()

    seen: set[tuple[str, str, str | None, str | None]] = set()
    refs: list[EvidenceRef] = []
    for evidence_id in _sorted_evidence_ids(evidence_map):
        hit = evidence_map[evidence_id]
        for ref in ephemeral_hit_to_evidence_refs(hit):
            identity = _evidence_ref_identity(ref)
            if identity in seen:
                continue
            seen.add(identity)
            refs.append(ref)
            if len(refs) >= MAX_FALLBACK_EVIDENCE_REFS:
                return tuple(refs)
    return tuple(refs)


def select_fallback_evidence_ids(
    evidence_map: dict[str, EphemeralRtsHit],
) -> list[str]:
    """Select opaque evidence IDs in RTS order without inspecting message content."""
    return _sorted_evidence_ids(evidence_map)[:MAX_FALLBACK_EVIDENCE_REFS]
