"""Human-readable descriptions of claims TruthExpiry can validate in the demo sandbox."""

from __future__ import annotations

from truthexpiry.services.claim_schema import CLAIM_SCHEMA_CATALOG

_TOPIC_LABELS: dict[tuple[str, str], str] = {
    ("report_export", "availability"): "Report export on Starter (enabled/disabled)",
    ("api_rate_limit", "max_requests"): "Starter API rate limit (50 or 100 requests)",
    ("analytics_export", "availability"): "Analytics export availability",
    ("billing_refund", "policy"): "Enterprise refund policy (30- or 60-day)",
    ("mobile_push", "delivery"): "Mobile push delivery on Starter",
    ("feature_flag", "rollout"): "Feature-flag rollout on Enterprise",
    ("legacy_api", "sunset"): "Legacy API sunset on Starter",
}


def supported_catalog_topics() -> tuple[str, ...]:
    """Ordered list of supported claim families for judge-facing guidance."""
    topics: list[str] = []
    for entity, attribute in CLAIM_SCHEMA_CATALOG:
        label = _TOPIC_LABELS.get((entity, attribute))
        if label is None:
            label = f"{entity.replace('_', ' ')} — {attribute.replace('_', ' ')}"
        topics.append(label)
    return tuple(topics)


def format_supported_topics_markdown() -> str:
    lines = ["*Supported claim families in this sandbox:*"]
    for topic in supported_catalog_topics():
        lines.append(f"• {topic}")
    lines.extend(
        [
            "",
            "_Ask one explicit claim at a time - for example, "
            '"Is report export available on the Starter plan?" '
            'or "Is the API rate limit 50 requests for Starter?"_',
        ]
    )
    return "\n".join(lines)
