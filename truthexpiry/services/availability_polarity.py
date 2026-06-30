"""Deterministic availability polarity from user query wording."""

from __future__ import annotations

import re

_DISABLED_AVAILABILITY_PHRASES = (
    "not available",
    "not enabled",
    "switched off",
    "turned off",
    "unavailable",
    "disabled",
)

_ENABLED_AVAILABILITY_PHRASES = (
    "switched on",
    "turned on",
    "enabled",
    "available",
)


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def infer_report_export_stated_value(normalized_query: str) -> str:
    """Infer enabled/disabled availability from report-export query wording."""
    for phrase in _DISABLED_AVAILABILITY_PHRASES:
        if phrase in normalized_query:
            return "disabled"
    if _contains_token(normalized_query, "off"):
        return "disabled"

    for phrase in _ENABLED_AVAILABILITY_PHRASES:
        if phrase in normalized_query:
            return "enabled"
    if _contains_token(normalized_query, "on"):
        return "enabled"

    return "enabled"
