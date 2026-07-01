"""Block Kit layout for TruthExpiry validation responses."""

from __future__ import annotations

from slack_sdk.models.blocks import (
    Block,
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    SectionBlock,
)
from slack_sdk.models.blocks.basic_components import TextObject

from truthexpiry.models.claim import ClaimKey, EvidenceRef
from truthexpiry.models.verdict import ClaimStatus, ValidationResult
from truthexpiry.services.lifecycle_timeline import format_timeline_markdown
from truthexpiry.services.pipeline import TruthExpiryResponse

AUTHORITY_FOOTNOTE = (
    "Statuses are assigned by deterministic rules. The LLM extracts claims only; "
    "it does not decide validity."
)

_STATUS_HEADER: dict[ClaimStatus, tuple[str, str]] = {
    ClaimStatus.CURRENT: (":large_green_circle:", "Current"),
    ClaimStatus.SUPERSEDED: (":warning:", "Superseded"),
    ClaimStatus.CONFLICTING: (":bangbang:", "Conflicting"),
    ClaimStatus.UNVERIFIED: (":grey_question:", "Unverified"),
}


def humanize_claim_key(key: ClaimKey) -> str:
    entity = key.entity.replace("_", " ").title()
    attribute = key.attribute.replace("_", " ")
    scope_parts: list[str] = []
    for field, value in sorted(key.scope.fields.items()):
        if field == "plan":
            scope_parts.append(f"{value.title()} plan")
        else:
            scope_parts.append(f"{field}: {value}")
    if scope_parts:
        return f"{entity} - {attribute} ({', '.join(scope_parts)})"
    return f"{entity} - {attribute}"


def _format_slack_evidence(refs: tuple[EvidenceRef, ...]) -> str | None:
    lines: list[str] = []
    index = 1
    for ref in refs:
        if ref.ref_type != "slack_permalink":
            continue
        lines.append(f"• <{ref.value}|Slack message {index}>")
        index += 1
    if not lines:
        return None
    return "*Slack evidence*\n" + "\n".join(lines)


def _format_lifecycle_timeline(result: ValidationResult) -> str | None:
    return format_timeline_markdown(
        result.lifecycle_timeline,
        highlight_record_ids=result.lifecycle_record_ids,
    )


def _format_claim_section(result: ValidationResult) -> str:
    lines = [f"*Claim:* {humanize_claim_key(result.key)}"]
    if result.stated_value:
        lines.append(f"*Stated in Slack:* `{result.stated_value}`")
    lines.append(result.explanation)
    return "\n".join(lines)


def _blocks_for_result(result: ValidationResult) -> list[Block]:
    emoji, label = _STATUS_HEADER[result.status]
    blocks: list[Block] = [
        HeaderBlock(text=f"{emoji} {label}"),
        SectionBlock(text=_format_claim_section(result)),
    ]

    slack_evidence = _format_slack_evidence(result.evidence_refs)
    if slack_evidence:
        blocks.append(SectionBlock(text=slack_evidence))

    timeline = _format_lifecycle_timeline(result)
    if timeline:
        blocks.append(SectionBlock(text=timeline))

    if result.user_confirmed:
        blocks.append(
            ContextBlock(
                elements=[
                    TextObject(
                        type="mrkdwn",
                        text=(
                            "_Owner confirmed (metadata only; does not override "
                            "shipped evidence)._"
                        ),
                    )
                ]
            )
        )
    return blocks


def build_verdict_blocks(
    query: str, results: tuple[ValidationResult, ...]
) -> list[Block]:
    """Build Block Kit sections for one or more validation results."""
    blocks: list[Block] = [
        SectionBlock(text=f'*Your question:* "{query}"'),
        DividerBlock(),
    ]
    for index, result in enumerate(results):
        blocks.extend(_blocks_for_result(result))
        if index + 1 < len(results):
            blocks.append(DividerBlock())
    blocks.append(
        ContextBlock(
            elements=[TextObject(type="mrkdwn", text=f"_{AUTHORITY_FOOTNOTE}_")]
        )
    )
    return blocks


def build_text_response_blocks(markdown_text: str) -> list[Block]:
    """Block Kit fallback for guidance and unavailable paths."""
    return [
        SectionBlock(text=markdown_text),
    ]


def build_response_blocks(*, query: str, response: TruthExpiryResponse) -> list[Block]:
    if response.results:
        return build_verdict_blocks(query, response.results)
    return build_text_response_blocks(response.markdown_text)
