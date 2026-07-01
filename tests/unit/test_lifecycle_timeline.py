"""Tests for lifecycle timeline formatting."""

from __future__ import annotations

from datetime import date

from truthexpiry.models.verdict import LifecycleTimelineEntry
from truthexpiry.services.lifecycle_timeline import (
    build_timeline_entries,
    format_timeline_markdown,
)

from adapters.fakes.synthetic_data import LIFECYCLE_RECORDS, REPORT_EXPORT_KEY


def test_build_timeline_entries_orders_by_effective_date():
    records = LIFECYCLE_RECORDS[REPORT_EXPORT_KEY.canonical()]
    entries = build_timeline_entries(records)
    assert [entry.record_id for entry in entries] == ["PROD-481", "PROD-482"]


def test_format_timeline_markdown_includes_values_dates_and_highlights():
    records = LIFECYCLE_RECORDS[REPORT_EXPORT_KEY.canonical()]
    entries = build_timeline_entries(records)
    markdown = format_timeline_markdown(
        entries,
        highlight_record_ids=("PROD-482",),
    )
    assert markdown is not None
    assert "Enabled" in markdown
    assert "Jan 01, 2024" in markdown
    assert "Disabled" in markdown
    assert "May 12, 2026" in markdown
    assert "PROD-482" in markdown
    assert "authoritative" in markdown


def test_format_timeline_markdown_returns_none_for_empty_entries():
    assert format_timeline_markdown(()) is None


def test_format_timeline_markdown_renders_arrow_between_entries():
    entries = (
        LifecycleTimelineEntry(
            record_id="A",
            value="enabled",
            effective_date=date(2024, 1, 1),
            state="SHIPPED",
        ),
        LifecycleTimelineEntry(
            record_id="B",
            value="disabled",
            effective_date=date(2026, 5, 12),
            state="SHIPPED",
            supersedes_record_id="A",
        ),
    )
    markdown = format_timeline_markdown(entries)
    assert markdown is not None
    assert "• Enabled" in markdown
    assert "→ Disabled" in markdown
