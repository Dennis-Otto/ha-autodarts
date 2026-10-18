"""The dartboard: its rings and numbers, the names of its beds, and points on it.

Every module that places a dart on the board or names its bed uses this one
geometry: the bot where it aims and where its darts land, the dart log where
players aimed, the aim map, the party games for distances and inner singles,
and the actions that enter a dart by its position. It is the Board Manager's
geometry, as the cards draw the board (`R` in `autodarts-card.js`, which a
test keeps equal to it). Positions are in millimetres, x to the right and y
up to the 20; the Board Manager reports them relative to the outer edge of
the double ring.
"""

from __future__ import annotations

import math

# The outer edge of the double ring, to which the Board Manager scales positions.
RADIUS_MM = 170
# The outer edges of the bullseye and of the outer bull, and each ring as the
# distances of its inner and its outer edge from the centre.
BULL_MM = 7
OUTER_BULL_MM = 17
TREBLE_MM = (97, 107)
DOUBLE_MM = (160, RADIUS_MM)
# The numbers clockwise from the 20 at the top, 18 degrees each.
SECTORS = (20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5)
SECTOR_DEGREES = 360 / len(SECTORS)
# Where a dart is aimed inside a bed: the middle of its ring, and for a single
# the big outer part of the bed between the treble and the double ring.
AIM_MM = {
    "T": sum(TREBLE_MM) / 2,
    "D": sum(DOUBLE_MM) / 2,
    "S": (TREBLE_MM[1] + DOUBLE_MM[0]) / 2,
}
OUTER_BULL_AIM_MM = (BULL_MM + OUTER_BULL_MM) / 2


def bed_name(number: int, multiplier: int) -> str:
    """S20, D16, T19, 25 (outer bull), BULL or MISS: the name of a bed
    everywhere, in the actions, the statistics and the games."""
    if number == 0 or multiplier == 0:
        return "MISS"
    if number == 25:
        return "BULL" if multiplier >= 2 else "25"
    return f"{'SDT'[multiplier - 1]}{number}"


def top_bed(number: int) -> str:
    """The bed of a number worth the most marks: its treble, or the bullseye."""
    return "BULL" if number == 25 else f"T{number}"


def segment_at(x: float, y: float) -> tuple[int, int]:
    """The number and multiplier of the bed at a point, in millimetres."""
    radius = math.hypot(x, y)
    if radius <= BULL_MM:
        return 25, 2
    if radius <= OUTER_BULL_MM:
        return 25, 1
    if radius > RADIUS_MM:
        return 0, 0
    degrees = math.degrees(math.atan2(x, y))
    number = SECTORS[round(degrees / SECTOR_DEGREES) % len(SECTORS)]
    if TREBLE_MM[0] < radius <= TREBLE_MM[1]:
        return number, 3
    if DOUBLE_MM[0] < radius <= DOUBLE_MM[1]:
        return number, 2
    return number, 1


def aim_point(bed: str) -> tuple[float, float]:
    """The point in millimetres a dart at a bed is aimed at: T20, S5, D16, 25 or BULL."""
    if bed == "BULL":
        return 0.0, 0.0
    if bed == "25":
        return 0.0, OUTER_BULL_AIM_MM
    angle = math.radians(SECTORS.index(int(bed[1:])) * SECTOR_DEGREES)
    radius = AIM_MM[bed[0]]
    return radius * math.sin(angle), radius * math.cos(angle)


def distance_mm(position: tuple[float, float] | None) -> float | None:
    """How far a dart landed from the centre of the board, in millimetres, from
    a position relative to the double ring; None without a position."""
    if position is None:
        return None
    return round(math.hypot(*position) * RADIUS_MM, 1)
