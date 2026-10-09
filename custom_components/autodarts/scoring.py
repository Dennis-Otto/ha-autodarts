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


def _bed(number: int, multiplier: int) -> dict[str, Any]:
    """A dart in a bed, named as the actions name the beds."""
    if not number:
        name = "MISS"
    elif number == BULL:
        name = "BULL" if multiplier == 2 else "25"
    else:
        name = f"{'SDT'[multiplier - 1]}{number}"
    return {"number": number, "multiplier": multiplier, "name": name}


# The beds of a visit entered as its score, in the order its darts are looked for:
# the treble and single of every number from the 20 down, the doubles, the bulls
# and a miss, so that 140 is T20 T20 S20 and 100 is T20 S20 S20.
SCORE_BEDS: tuple[dict[str, Any], ...] = (
    *(_bed(number, multiplier) for number in range(20, 0, -1) for multiplier in (3, 1)),
    *(_bed(number, 2) for number in range(20, 0, -1)),
    _bed(BULL, 2),
    _bed(BULL, 1),
    _bed(0, 0),
)
_BEDS_BY_SCORE: dict[int, list[dict[str, Any]]] = {}
for _dart in SCORE_BEDS:
    _BEDS_BY_SCORE.setdefault(score(_dart), []).append(_dart)


def visit_darts(
    start: int, points: int, darts: int, double_out: bool, opening: bool = False
) -> list[dict[str, Any]] | None:
    """Darts that make an X01 visit of `points` from `start`, or None.

    The visit checks out when the points are what is left, busts when they are
    more or leave 1 with double out, and otherwise leaves the rest; it has
    `darts` darts, and a checkout or a bust ends with its last one. With
    `opening`, the leg still needs a double to open, and the first dart that
    scores is one. The beds are made up: only the score of the visit is known.
    """
    if points == start:
        wanted = "won"
    elif points > start or (double_out and start - points == 1):
        wanted = "bust"
    else:
        wanted = None

    def fits(visit: list[dict[str, Any]]) -> bool:
        first = next((dart for dart in visit if score(dart)), None)
        if opening and first is not None and not is_double(first):
            return False
        return evaluate_visit(start, visit, double_out)[1:] == (wanted, darts)

    def search(chosen: list[dict[str, Any]], left: int) -> list[dict[str, Any]] | None:
        if len(chosen) == darts - 1:
            return next(
                (
                    [*chosen, dart]
                    for dart in _BEDS_BY_SCORE.get(left, [])
                    if fits([*chosen, dart])
                ),
                None,
            )
        for dart in SCORE_BEDS:
            if score(dart) <= left and (
                found := search([*chosen, dart], left - score(dart))
            ):
                return found
        return None

    return search([], points)
