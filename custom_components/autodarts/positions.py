"""Where darts land: board positions, the bed aimed at, and the grouping around it.

The Board Manager reports a position for most darts, relative to the outer
edge of the double ring (170 mm) with y pointing to the 20. A log keeps the
newest positions together with the bed the dart was aimed at, where the game
knows it; the grouping of the darts at one bed is worked out from them.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable, Iterable
from typing import Any

from .doubles import aimed_at
from .scoring import VISIT_DARTS, is_double, score

BOARD_RADIUS_MM = 170
# Board Manager geometry in millimetres, as the cards draw it.
TREBLE_MM = (97 + 107) / 2
DOUBLE_MM = (160 + 170) / 2
NUMBERS = (20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5)
# The beds a dart can be aimed at, as the log stores them by position; the
# singles are too wide to tell where a player aimed.
AIMS = (
    "BULL",
    *(f"T{number}" for number in range(1, 21)),
    *(f"D{number}" for number in range(1, 21)),
)
# X01 visits that no checkout can finish aim at the treble 20.
SCORING_AIM = "T20"
# Positions further out than this are no darts on the board.
MAX_DISTANCE = 3.0
# A grouping needs this many darts; the trend compares two halves of them.
MIN_GROUP = 10
GROUPS = 6


def aim_point(aim: str) -> tuple[float, float]:
    """The centre of a bed in millimetres, x to the right and y up."""
    if aim == "BULL":
        return 0.0, 0.0
    radius = TREBLE_MM if aim[0] == "T" else DOUBLE_MM
    angle = math.radians(NUMBERS.index(int(aim[1:])) * 18)
    return radius * math.sin(angle), radius * math.cos(angle)


def x01_aims(
    start: int,
    darts: list[dict[str, Any]],
    double_out: bool,
    opening: int | None,
    route: Callable[[int, int], tuple[str, ...]],
) -> list[str | None]:
    """The bed each dart of an X01 visit was aimed at, where it is known.

    A score one double finishes aims at that double; a score no checkout can
    finish with the darts left is a scoring visit at the treble 20; otherwise
    the first bed of the route. `opening` is the place of the double that
    opens the leg with double in, while the leg still needs one: darts up to
    it aim at any double. Darts at a single, and darts after a bust or the
    finish, have no aim either.
    """
    aims: list[str | None] = []
    remaining: int | None = start
    for index, dart in enumerate(darts[:VISIT_DARTS]):
        aim: str | None = None
        if remaining is not None and (opening is None or index > opening):
            finish = aimed_at(remaining) if double_out else None
            path = route(remaining, VISIT_DARTS - index)
            aim = finish or (path[0] if path else SCORING_AIM)
        aims.append(aim if aim in AIMS else None)
        if remaining is None or (opening is not None and index < opening):
            continue
        left = remaining - score(dart)
        busted = left < 0 or (
            double_out and (left == 1 or (left == 0 and not is_double(dart)))
        )
        remaining = None if busted or left == 0 else left
    return aims


def _percentile(distances: list[float], share: float) -> float:
    """The smallest radius that holds this share of the darts."""
    return distances[math.ceil(share * len(distances)) - 1]


def _grouping(offsets: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Mean offset and the radii around it holding 50 and 80 percent."""
    mean_x = sum(x for x, _ in offsets) / len(offsets)
    mean_y = sum(y for _, y in offsets) / len(offsets)
    distances = sorted(math.hypot(x - mean_x, y - mean_y) for x, y in offsets)
    return mean_x, mean_y, _percentile(distances, 0.5), _percentile(distances, 0.8)


def spread(darts: Iterable[tuple[float, float, str | None]]) -> list[dict[str, Any]]:
    """The grouping at every bed aimed at with enough darts, most darts first.

    Offsets are millimetres from the centre of the bed, x to the right and y
    up. The radii hold 50 and 80 percent of the darts around their mean
    point; `change` compares the radius of the newer half of the darts with
    the older half, negative when the grouping got tighter.
    """
    groups: dict[str, list[tuple[float, float]]] = {}
    for x, y, aim in darts:
        if aim in AIMS:
            target_x, target_y = aim_point(aim)
            groups.setdefault(aim, []).append(
                (x * BOARD_RADIUS_MM - target_x, y * BOARD_RADIUS_MM - target_y)
            )
    result: list[dict[str, Any]] = []
    for aim, offsets in groups.items():
        if len(offsets) < MIN_GROUP:
            continue
        mean_x, mean_y, r50, r80 = _grouping(offsets)
        change = None
        if len(offsets) >= 2 * MIN_GROUP:
            half = len(offsets) // 2
            change = round(
                _grouping(offsets[half:])[2] - _grouping(offsets[:half])[2], 1
            )
        result.append(
            {
                "target": aim,
                "darts": len(offsets),
                "offset_x": round(mean_x, 1),
                "offset_y": round(mean_y, 1),
                "r50": round(r50, 1),
                "r80": round(r80, 1),
                "change": change,
            }
        )
    result.sort(key=lambda group: (-group["darts"], AIMS.index(group["target"])))
    return result[:GROUPS]


class DartLog:
    """The newest dart positions with the bed aimed at, oldest first.

    Positions are stored in tenths of a millimetre and the aim by its place in
    AIMS, three numbers per dart, which keeps a thousand darts small.
    """

    def __init__(self, size: int) -> None:
        self.darts: deque[tuple[float, float, str | None]] = deque(maxlen=size)
        # The grouping changes only with a new dart; the sensors ask often.
        self._spread: list[dict[str, Any]] | None = None

    def __len__(self) -> int:
        return len(self.darts)

    def add(self, position: tuple[float, float] | None, aim: str | None) -> None:
        if position is None or math.hypot(*position) > MAX_DISTANCE:
            return
        x, y = position
        self.darts.append((x, y, aim if aim in AIMS else None))
        self._spread = None

    def clear(self) -> None:
        self.darts.clear()
        self._spread = None

    def positions(self) -> list[list[float]]:
        """Normalised positions like the visit sensor's, for the cards."""
        return [[round(x, 3), round(y, 3)] for x, y, _ in self.darts]

    def spread(self) -> list[dict[str, Any]]:
        if self._spread is None:
            self._spread = spread(self.darts)
        return [dict(group) for group in self._spread]

    def stored(self) -> list[int]:
        scale = BOARD_RADIUS_MM * 10
        flat: list[int] = []
        for x, y, aim in self.darts:
            flat.extend(
                (round(x * scale), round(y * scale), AIMS.index(aim) + 1 if aim else 0)
            )
        return flat

    def restore(self, saved: object) -> None:
        self.clear()
        if not isinstance(saved, list) or len(saved) % 3:
            return
        scale = BOARD_RADIUS_MM * 10
        limit = MAX_DISTANCE * scale
        for index in range(0, len(saved), 3):
            x, y, aim = saved[index : index + 3]
            if not all(type(value) is int for value in (x, y, aim)):
                continue
            if abs(x) > limit or abs(y) > limit or not 0 <= aim <= len(AIMS):
                continue
            self.add((x / scale, y / scale), AIMS[aim - 1] if aim else None)
