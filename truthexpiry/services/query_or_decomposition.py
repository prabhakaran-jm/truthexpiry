"""Split exclusive OR phrasing into candidate single-claim queries."""

from __future__ import annotations

import re

_AVAILABILITY_OR = re.compile(
    r"^(?P<head>.*?)"
    r"(?P<alt1>available|enabled|turned on|switched on|unavailable|disabled|"
    r"turned off|switched off|off)"
    r"\s+or\s+"
    r"(?P<alt2>available|enabled|turned on|switched on|unavailable|disabled|"
    r"turned off|switched off|off)"
    r"(?P<tail>.*)$",
    re.IGNORECASE,
)

_NUMERIC_OR = re.compile(
    r"^(?P<head>.*?)(?P<alt1>\d+)\s+or\s+(?P<alt2>\d+)(?P<tail>.*)$",
    re.IGNORECASE,
)


def iter_query_candidates(query: str) -> tuple[str, ...]:
    """Return decomposed query variants for exclusive OR questions."""
    stripped = query.strip()
    if not stripped:
        return ()

    availability_match = _AVAILABILITY_OR.match(stripped)
    if availability_match is not None:
        groups = availability_match.groupdict()
        return (
            f"{groups['head']}{groups['alt1']}{groups['tail']}",
            f"{groups['head']}{groups['alt2']}{groups['tail']}",
        )

    numeric_match = _NUMERIC_OR.match(stripped)
    if numeric_match is not None:
        groups = numeric_match.groupdict()
        return (
            f"{groups['head']}{groups['alt1']}{groups['tail']}",
            f"{groups['head']}{groups['alt2']}{groups['tail']}",
        )

    return (stripped,)
