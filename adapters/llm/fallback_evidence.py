from __future__ import annotations

from truthexpiry.ports.rts import EphemeralRtsHit

MAX_FALLBACK_EVIDENCE_IDS = 3


def select_fallback_evidence_ids(
    evidence_map: dict[str, EphemeralRtsHit],
) -> list[str]:
    """Select opaque evidence IDs in RTS order without inspecting message content."""
    if not evidence_map:
        return []
    sorted_ids = sorted(
        evidence_map.keys(),
        key=lambda item: int(item.split("-", 1)[1]),
    )
    return sorted_ids[:MAX_FALLBACK_EVIDENCE_IDS]
