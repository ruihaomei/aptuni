"""Partial ISO dates for valid time (``2025``, ``2025-03``, ``2025-03-14``)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

PARTIAL_DATE_RE = re.compile(r"^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$")


def partial_date_range(text: str) -> tuple[date, date]:
    """Return the half-open ``[start, end)`` date range covered by a partial ISO date."""
    if not PARTIAL_DATE_RE.match(text):
        raise ValueError(f"invalid partial date: {text!r}")
    parts = [int(p) for p in text.split("-")]
    if len(parts) == 1:
        return date(parts[0], 1, 1), date(parts[0] + 1, 1, 1)
    if len(parts) == 2:
        start = date(parts[0], parts[1], 1)
        return start, date(parts[0] + (parts[1] == 12), parts[1] % 12 + 1, 1)
    start = date(parts[0], parts[1], parts[2])
    return start, start + timedelta(days=1)


def utc_now() -> datetime:
    return datetime.now(UTC)
