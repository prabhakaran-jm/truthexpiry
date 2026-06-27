"""Synthetic TruthExpiry fixtures.

All identifiers, channels, permalinks, and ticket IDs below are invented for
offline testing. They must never resemble credentials or real workspace content.
"""

from datetime import date

from truthexpiry.models.claim import EvidenceRef
from truthexpiry.models.evidence import LifecycleRecord, LifecycleState
from truthexpiry.ports.rts import RtsHitRef
from truthexpiry.services.claim_key import build_claim_key

SYNTHETIC_TEAM_ID = "T000SYNTHETIC"
SYNTHETIC_CHANNEL_ID = "C000SYNTHETIC_PUBLIC"
SYNTHETIC_MESSAGE_TS = "1700000000.000001"
SYNTHETIC_PERMALINK = "https://example.invalid/synthetic/truthexpiry/C000SYNTHETIC_PUBLIC/p1700000000000001"
SYNTHETIC_TICKET_REF = "PROD-482"

REPORT_EXPORT_KEY = build_claim_key(
    "report_export",
    "availability",
    {"plan": "starter", "region": "global"},
)
API_RATE_LIMIT_KEY = build_claim_key(
    "api_rate_limit",
    "max_requests",
    {"plan": "starter", "region": "global"},
)
BILLING_REFUND_KEY = build_claim_key(
    "billing_refund",
    "policy",
    {"plan": "enterprise", "region": "global"},
)

DEFAULT_EVIDENCE_REF = EvidenceRef(
    ref_type="slack_permalink",
    value=SYNTHETIC_PERMALINK,
    channel_id=SYNTHETIC_CHANNEL_ID,
    message_ts=SYNTHETIC_MESSAGE_TS,
)
TICKET_EVIDENCE_REF = EvidenceRef(ref_type="ticket_id", value=SYNTHETIC_TICKET_REF)

DEFAULT_RTS_HIT = RtsHitRef(
    channel_id=SYNTHETIC_CHANNEL_ID,
    message_ts=SYNTHETIC_MESSAGE_TS,
    permalink=SYNTHETIC_PERMALINK,
    ticket_ref=SYNTHETIC_TICKET_REF,
)

LIFECYCLE_RECORDS: dict[str, list[LifecycleRecord]] = {
    REPORT_EXPORT_KEY.canonical(): [
        LifecycleRecord(
            record_id="LC-SYNTH-001",
            key=REPORT_EXPORT_KEY,
            state=LifecycleState.SHIPPED,
            value="self_serve",
            effective_date=date(2024, 1, 1),
        )
    ],
    API_RATE_LIMIT_KEY.canonical(): [
        LifecycleRecord(
            record_id="LC-SYNTH-010",
            key=API_RATE_LIMIT_KEY,
            state=LifecycleState.EFFECTIVE,
            value="100",
            effective_date=date(2023, 6, 1),
        ),
        LifecycleRecord(
            record_id="LC-SYNTH-011",
            key=API_RATE_LIMIT_KEY,
            state=LifecycleState.SHIPPED,
            value="50",
            effective_date=date(2024, 6, 1),
            supersedes_record_id="LC-SYNTH-010",
        ),
    ],
    BILLING_REFUND_KEY.canonical(): [
        LifecycleRecord(
            record_id="LC-SYNTH-020-A",
            key=BILLING_REFUND_KEY,
            state=LifecycleState.EFFECTIVE,
            value="30_days",
            effective_date=date(2024, 3, 1),
        ),
        LifecycleRecord(
            record_id="LC-SYNTH-020-B",
            key=BILLING_REFUND_KEY,
            state=LifecycleState.SHIPPED,
            value="60_days",
            effective_date=date(2024, 3, 1),
        ),
    ],
}

PLANNED_ONLY_KEY = build_claim_key(
    "mobile_push",
    "delivery",
    {"plan": "starter", "region": "global"},
)
LIFECYCLE_RECORDS[PLANNED_ONLY_KEY.canonical()] = [
    LifecycleRecord(
        record_id="LC-SYNTH-030",
        key=PLANNED_ONLY_KEY,
        state=LifecycleState.PLANNED,
        value="enabled",
        effective_date=date(2025, 12, 1),
    )
]
