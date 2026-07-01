"""Build and format lifecycle evidence timelines for validation results."""

from __future__ import annotations

from datetime import date

from truthexpiry.models.evidence import LifecycleRecord
from truthexpiry.models.verdict import LifecycleTimelineEntry


def build_timeline_entries(
    records: list[LifecycleRecord],
) -> tuple[LifecycleTimelineEntry, ...]:
    if not records:
        return ()
    ordered = sorted(records, key=lambda record: (record.effective_date, record.record_id))
    return tuple(
        LifecycleTimelineEntry(
            record_id=record.record_id,
            value=record.value,
            effective_date=record.effective_date,
            state=record.state.value,
            supersedes_record_id=record.supersedes_record_id,
        )
        for record in ordered
    )


def format_timeline_value(value: str) -> str:
    if value in {"enabled", "disabled"}:
        return value.title()
    if value.endswith("_days"):
        return value.replace("_", " ")
    return value


def format_timeline_date(on_date: date) -> str:
    return on_date.strftime("%b %d, %Y")


def format_timeline_markdown(
    entries: tuple[LifecycleTimelineEntry, ...],
    *,
    highlight_record_ids: tuple[str, ...] = (),
) -> str | None:
    if not entries:
        return None
    highlights = set(highlight_record_ids)
    lines = ["*Lifecycle timeline*"]
    for index, entry in enumerate(entries):
        prefix = "→ " if index > 0 else "• "
        value_label = format_timeline_value(entry.value)
        date_label = format_timeline_date(entry.effective_date)
        line = f"{prefix}{value_label} — {date_label} (`{entry.record_id}`)"
        if entry.record_id in highlights:
            line += " ← authoritative"
        lines.append(line)
    return "\n".join(lines)
