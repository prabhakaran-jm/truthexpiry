"""Synthetic TruthExpiry fixtures.

All identifiers, channels, permalinks, and ticket IDs below are invented for
offline testing. They must never resemble credentials or real workspace content.
"""

from truthexpiry.models.claim import EvidenceRef
from truthexpiry.models.evidence import LifecycleRecord
from truthexpiry.ports.rts import RtsHitRef
from truthexpiry.services.claim_key import build_claim_key

from lifecycle_mcp.repository import default_repository

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
PLANNED_ONLY_KEY = build_claim_key(
    "mobile_push",
    "delivery",
    {"plan": "starter", "region": "global"},
)
ANALYTICS_EXPORT_KEY = build_claim_key(
    "analytics_export",
    "availability",
    {"plan": "enterprise", "region": "global"},
)
FEATURE_FLAG_KEY = build_claim_key(
    "feature_flag",
    "rollout",
    {"plan": "enterprise", "region": "global"},
)
LEGACY_API_KEY = build_claim_key(
    "legacy_api",
    "sunset",
    {"plan": "starter", "region": "global"},
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

LIFECYCLE_RECORDS: dict[str, list[LifecycleRecord]] = default_repository().records_by_canonical()
