"""Times as the games store them, as ISO 8601 text, without Home Assistant.

The games take the time of each step as a parameter, see BoardGames, and keep
it in UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime


def stamp(now: datetime) -> str:
    """The time of a step as the games store it: ISO 8601, in UTC."""
    return now.astimezone(UTC).isoformat()


def parse_moment(value: object) -> datetime | None:
    """A stored ISO 8601 time; None for anything else."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
