"""Shared demo queries and workspace seed content for hackathon sandbox prep."""

from __future__ import annotations

from dataclasses import dataclass


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
            "TruthExpiry checks **explicit claims** against lifecycle records "
            "using **public Slack evidence**. This question did not produce a "
            "structured claim to validate — it may be informational, too broad, "
            "or outside the supported demo catalog.",
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
