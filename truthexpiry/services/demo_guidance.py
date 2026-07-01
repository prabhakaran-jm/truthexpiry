"""Shared demo queries and workspace seed content for hackathon sandbox prep."""

from __future__ import annotations

from dataclasses import dataclass

from truthexpiry.services.catalog_topics import format_supported_topics_markdown


@dataclass(frozen=True)
class DemoExampleQuery:
    """A verified example question judges can ask in the demo workspace."""

    title: str
    message: str


# Public-channel evidence posts (RTS searches real messages).
DEMO_SEED_MESSAGES: tuple[str, ...] = (
    "Report export on the Starter plan is enabled. Tracked in PROD-481.",
    "Report export on the Starter plan is disabled. Tracked in PROD-482.",
    "Starter API rate limit is 100 requests. Tracked in PROD-510.",
    "Starter API rate limit is 50 requests. Tracked in PROD-511.",
    "Analytics export on the Starter plan is enabled. Tracked in PROD-550.",
    "Analytics export on the Starter plan is disabled. Tracked in PROD-551.",
    "Starter refund policy is 30 days. Tracked in PROD-560.",
    "Starter refund policy is 60 days. Tracked in PROD-561.",
    "Mobile push on the Starter plan is enabled. Tracked in PROD-570.",
    "Legacy API on the Starter plan is deprecated. Tracked in PROD-571.",
    "Enterprise feature rollout is enabled. Tracked in PROD-530.",
)

# Queries verified against lifecycle_records.json and demo acceptance matrix.
DEMO_EXAMPLE_QUERIES: tuple[DemoExampleQuery, ...] = (
    DemoExampleQuery(
        title="Stale report export",
        message="Is report export available on the Starter plan?",
    ),
    DemoExampleQuery(
        title="Current report export",
        message="Is report export disabled on the Starter plan?",
    ),
    DemoExampleQuery(
        title="Stale rate limit",
        message="Is the API rate limit 100 requests for Starter?",
    ),
    DemoExampleQuery(
        title="Current rate limit",
        message="Is the API rate limit 50 requests for Starter?",
    ),
    DemoExampleQuery(
        title="Stale analytics export",
        message="Is analytics export available on the Starter plan?",
    ),
    DemoExampleQuery(
        title="Starter refund policy",
        message="Is the Starter refund policy 30 days?",
    ),
    DemoExampleQuery(
        title="Mobile push delivery",
        message="Is mobile push enabled on the Starter plan?",
    ),
    DemoExampleQuery(
        title="Legacy API sunset",
        message="Is the legacy API deprecated on Starter?",
    ),
)


def suggested_prompt_payloads() -> list[dict[str, str]]:
    """Bolt `set_suggested_prompts` payload entries."""
    return [
        {"title": query.title, "message": query.message}
        for query in DEMO_EXAMPLE_QUERIES
    ]


def format_example_questions_markdown() -> str:
    lines = ["*Try one of these example questions:*"]
    for query in DEMO_EXAMPLE_QUERIES:
        lines.append(f"• {query.message}")
    return "\n".join(lines)


def format_no_claim_guidance(query: str) -> str:
    """Friendly guidance when no structured claim can be validated."""
    return "\n".join(
        (
            f'*Query:* "{query}"',
            "",
            "TruthExpiry validates **explicit claims** against lifecycle records "
            "using **public Slack evidence**. This question did not yield a "
            "structured claim to check — it may be informational, name multiple "
            "topics at once, or lack an explicit value to verify.",
            "",
            format_supported_topics_markdown(),
            "",
            format_example_questions_markdown(),
            "",
            "_The model extracts claims only. Deterministic code assigns validity._",
        )
    )


def format_empty_mention_guidance() -> str:
    """Short help when a user @mentions the app without a question."""
    return (
        "Ask whether a specific claim is still *current* in your workspace. "
        "I search *public channels* and compare against lifecycle records.\n\n"
        f"{format_example_questions_markdown()}"
    )
