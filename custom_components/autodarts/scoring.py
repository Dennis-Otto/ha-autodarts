"""Scoring rules shared by the practice games."""

from __future__ import annotations

from typing import Any

BULL = 25
# A visit has three darts; darts beyond them, before a takeout, do not count.
VISIT_DARTS = 3
# How an X01 leg opens and ends, as the In and Out mode of play.autodarts.io:
# with any dart, with a double, or with a double or a treble (master).
STRAIGHT, DOUBLE, MASTER = "straight", "double", "master"
MODES = (STRAIGHT, DOUBLE, MASTER)
# What the bull scores: 25 for the outer bull and 50 for the bullseye, or 50 for both.
BULL_25_50, BULL_50_50 = "25_50", "50_50"
BULL_MODES = (BULL_25_50, BULL_50_50)


def score(dart: dict[str, Any], bull_mode: str = BULL_25_50) -> int:
    """The points of a dart; with the bull mode 50/50, the outer bull scores 50."""
    if bull_mode == BULL_50_50 and dart["number"] == BULL:
        return 2 * BULL
    return int(dart["number"] * dart["multiplier"])


def is_double(dart: dict[str, Any]) -> bool:
    """Double rings and the bullseye end a leg with double out."""
    return bool(dart["multiplier"] == 2 and dart["number"] != 0)


def fits(dart: dict[str, Any], mode: str) -> bool:
    """Whether a dart opens a leg with this In mode, or ends it with this Out
    mode: any dart straight, a double ring or the bullseye with double, and a
    treble as well with master. The outer bull is a single in both bull modes."""
    if mode == STRAIGHT:
        return True
    return is_double(dart) or (
        mode == MASTER and dart["multiplier"] == 3 and dart["number"] != 0
    )


def average(points: int, darts: int) -> float | None:
    """Points per three darts, as darts players compare their level."""
    return round(points * 3 / darts, 2) if darts else None


def rate(hits: int, tries: int) -> float | None:
    """Hits per try in percent."""
    return round(hits * 100 / tries, 1) if tries else None


def evaluate_visit(
    start: int,
    darts: list[dict[str, Any]],
    out_mode: str,
    bull_mode: str = BULL_25_50,
) -> tuple[int, str | None, int]:
    """Remaining score, outcome ("bust", "won" or None) and counted darts.

    A dart that goes below zero, leaves 1 with double or master out, or
    reaches zero with a dart that does not fit the Out mode busts the visit;
    later darts of the visit do not count.
    """
    remaining = start
    for index, dart in enumerate(darts, 1):
        left = remaining - score(dart, bull_mode)
        if (
            left < 0
            or (out_mode != STRAIGHT and left == 1)
            or (left == 0 and not fits(dart, out_mode))
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
# With the bull mode 50/50, the outer bull scores what the bullseye does: the
# made-up darts take the bullseye, which opens and finishes as well.
_SCORE_BEDS = {
    BULL_25_50: SCORE_BEDS,
    BULL_50_50: tuple(
        dart for dart in SCORE_BEDS if (dart["number"], dart["multiplier"]) != (BULL, 1)
    ),
}
_BEDS_BY_SCORE: dict[str, dict[int, list[dict[str, Any]]]] = {}
for _mode, _beds in _SCORE_BEDS.items():
    for _dart in _beds:
        _BEDS_BY_SCORE.setdefault(_mode, {}).setdefault(score(_dart), []).append(_dart)


def visit_darts(
    start: int,
    points: int,
    darts: int,
    out_mode: str,
    opening: str = STRAIGHT,
    bull_mode: str = BULL_25_50,
) -> list[dict[str, Any]] | None:
    """Darts that make an X01 visit of `points` from `start`, or None.

    The visit checks out when the points are what is left and a finish exists,
    busts when they are more, leave 1 with double or master out or are what is
    left without a finish, and otherwise leaves the rest. It has `darts` darts,
    and a checkout or a bust ends with its last one, so that every dart counts;
    a bust that can't, such as 100 from 32, comes as late as it can, and the
    darts after it do not count. `opening` is the In mode the leg still waits
    for, straight once it is open: the first dart that scores fits it. The beds
    are made up: only the score of the visit is known.
    """
    beds, by_score = _SCORE_BEDS[bull_mode], _BEDS_BY_SCORE[bull_mode]
    if points == start:
        wanted = "won"
    elif points > start or (out_mode != STRAIGHT and start - points == 1):
        wanted = "bust"
    else:
        wanted = None
    # The outcomes looked for, with the darts that count, the best first: what is
    # left without a finish busts, and a bust may come before the last dart.
    endings = [(wanted, darts)]
    if wanted is not None:
        endings += [("bust", counted) for counted in range(darts, 0, -1)]

    def matches(visit: list[dict[str, Any]], ending: tuple[str | None, int]) -> bool:
        first = next((dart for dart in visit if score(dart)), None)
        if first is not None and not fits(first, opening):
            return False
        return evaluate_visit(start, visit, out_mode, bull_mode)[1:] == ending

    def search(
        chosen: list[dict[str, Any]], left: int, ending: tuple[str | None, int]
    ) -> list[dict[str, Any]] | None:
        if len(chosen) == darts - 1:
            return next(
                (
                    [*chosen, dart]
                    for dart in by_score.get(left, [])
                    if matches([*chosen, dart], ending)
                ),
                None,
            )
        for dart in beds:
            if score(dart) <= left and (
                found := search([*chosen, dart], left - score(dart), ending)
            ):
                return found
        return None

    for ending in dict.fromkeys(endings):
        if found := search([], points, ending):
            return found
    return None
