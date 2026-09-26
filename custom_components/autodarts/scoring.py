"""Scoring rules shared by the practice games."""

from __future__ import annotations

from typing import Any

BULL = 25
# A visit has three darts; darts beyond them, before a takeout, do not count.
VISIT_DARTS = 3


def score(dart: dict[str, Any]) -> int:
    return int(dart["number"] * dart["multiplier"])


def is_double(dart: dict[str, Any]) -> bool:
    """Double rings and the bullseye end a leg with double out."""
    return bool(dart["multiplier"] == 2 and dart["number"] != 0)


def average(points: int, darts: int) -> float | None:
    """Points per three darts, as darts players compare their level."""
    return round(points * 3 / darts, 2) if darts else None


def rate(hits: int, tries: int) -> float | None:
    """Hits per try in percent."""
    return round(hits * 100 / tries, 1) if tries else None


def evaluate_visit(
    start: int, darts: list[dict[str, Any]], double_out: bool
) -> tuple[int, str | None, int]:
    """Remaining score, outcome ("bust", "won" or None) and counted darts.

    A dart that goes below zero, leaves 1 with double out, or reaches zero
    without a double busts the visit; later darts of the visit do not count.
    """
    remaining = start
    for index, dart in enumerate(darts, 1):
        left = remaining - score(dart)
        if (
            left < 0
            or (double_out and left == 1)
            or (left == 0 and double_out and not is_double(dart))
        ):
            return start, "bust", index
        if left == 0:
            return 0, "won", index
        remaining = left
    return remaining, None, len(darts)
