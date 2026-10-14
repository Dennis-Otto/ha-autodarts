"""Where a player scores the most points per dart, from their own spread.

Tibshirani, Price and Taylor ("A statistician plays darts", Journal of the Royal
Statistical Society, Series A 174, 2011) model a dart as the point aimed at plus
an error from a bivariate normal distribution, the same wherever on the board the
player aims. The points a dart scores on average at an aim point are then the
points of the board around it, weighted by that distribution, and the best aim is
the point where they are highest: the treble 20 for a tight spread, then the
treble 19, and for a wide spread a point left of the bull, the closer to it the
wider the spread.

The error model comes from the darts a player aimed at a treble, see
`positions.aim_model`. The points per dart at an aim point are the mean score of
1,000 fixed draws of that error, spread evenly over the normal distribution by a
Fibonacci lattice, each landing point rounded to the millimetre. Home Assistant
searches the best point on a 2 mm grid, from a coarse grid and the centres of the
trebles to the points around the best of them, so that a new model costs some 20
milliseconds; the training card computes the same numbers for every point of the
grid, in a Web Worker of the browser, and shows the best point Home Assistant found.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache
from typing import Any

from .bot import BOARD_MM, SECTORS, TREBLE_MM, bed_name, segment_at

# The aim map needs this many darts aimed at a treble.
MIN_DARTS = 30
# Draws of the error for the points per dart, and the grid of aim points in mm.
DRAWS = 1000
GRID_MM = 2
# The search of Home Assistant: a coarse grid with fewer draws, then the 2 mm
# grid within a few millimetres of the best coarse points.
SEARCH_MM = 10
SEARCH_DRAWS = 144
SEARCH_STARTS = 4
SEARCH_REACH_MM = 4
# A landing point further than this from an aim point on the board misses the
# board, wherever on it the aim point lies; the board of points reaches that far.
REACH_MM = 2 * BOARD_MM
EDGE_MM = BOARD_MM + REACH_MM
WIDTH = 2 * EDGE_MM + 1
GOLDEN = (math.sqrt(5) - 1) / 2
# The beds the best aim is compared with, and the beds whose centres it beats.
COMPARED = ("T20", "T19", "BULL")
NAMED = (*(f"T{number}" for number in SECTORS), "BULL")


@dataclass(frozen=True)
class ErrorModel:
    """Where a player's darts land around the point aimed at, in millimetres:
    the mean offset, x to the right and y up, and the bivariate normal spread
    around it."""

    offset_x: float
    offset_y: float
    sd_x: float
    sd_y: float
    correlation: float


def points(x: float, y: float) -> int:
    """The points of a dart at a point in millimetres, 0 off the board."""
    number, multiplier = segment_at(x, y)
    return number * multiplier


@cache
def _board() -> bytes:
    """The points of every millimetre around the board, row by row from the bottom."""
    cells = bytearray(WIDTH * WIDTH)
    for y in range(-BOARD_MM, BOARD_MM + 1):
        row = (y + EDGE_MM) * WIDTH + EDGE_MM
        for x in range(-BOARD_MM, BOARD_MM + 1):
            cells[row + x] = points(x, y)
    return bytes(cells)


@cache
def draws(count: int) -> tuple[tuple[float, float], ...]:
    """Draws of a pair of standard normal numbers, spread evenly: a Fibonacci
    lattice of the unit square, mapped by the Box-Muller transform."""
    result = []
    for index in range(count):
        radius = math.sqrt(-2 * math.log((index + 0.5) / count))
        angle = 2 * math.pi * (index * GOLDEN % 1)
        result.append((radius * math.cos(angle), radius * math.sin(angle)))
    return tuple(result)


def _offsets(model: ErrorModel, count: int) -> list[int]:
    """Where the draws land from an aim point, as offsets in the board of points.

    A draw beyond the reach misses the board from every aim point on it, so it
    scores nothing and needs no offset; the mean still counts it.
    """
    spread = math.sqrt(1 - model.correlation * model.correlation)
    offsets = []
    for first, second in draws(count):
        x = math.floor(model.offset_x + model.sd_x * first + 0.5)
        y = math.floor(
            model.offset_y
            + model.sd_y * (model.correlation * first + spread * second)
            + 0.5
        )
        if abs(x) <= REACH_MM and abs(y) <= REACH_MM:
            offsets.append(y * WIDTH + x)
    return offsets


def _total(offsets: list[int], x: int, y: int) -> int:
    """The points of all draws from an aim point in whole millimetres."""
    board = _board()
    base = (y + EDGE_MM) * WIDTH + x + EDGE_MM
    return sum(map(board.__getitem__, map(base.__add__, offsets)))


def expected(model: ErrorModel, x: int, y: int) -> float:
    """The points per dart of a player with this error at an aim point in mm."""
    return _total(_offsets(model, DRAWS), x, y) / DRAWS


def _on_board(x: int, y: int) -> bool:
    return x * x + y * y <= BOARD_MM * BOARD_MM


def centre(bed: str) -> tuple[int, int]:
    """The centre of a treble or the bullseye, at its nearest point of the grid."""
    if bed == "BULL":
        return 0, 0
    angle = math.radians(SECTORS.index(int(bed[1:])) * 18)
    radius = sum(TREBLE_MM) / 2
    return (
        GRID_MM * round(radius * math.sin(angle) / GRID_MM),
        GRID_MM * round(radius * math.cos(angle) / GRID_MM),
    )


def best_aim(model: ErrorModel) -> dict[str, Any]:
    """The aim point with the most points per dart, its bed and those points,
    and the points per dart at the centres of the beds it is compared with.

    The search starts from the best points of a coarse grid, with fewer draws,
    and from the best centre of a treble or the bullseye, and takes the best
    point of the grid near them; it beats every treble and the bullseye. Ties
    go to the point nearest to the middle of the board, then to the right and up.
    """
    fine = _offsets(model, DRAWS)
    rough = _offsets(model, SEARCH_DRAWS)
    coarse = [
        (x, y)
        for y in range(-BOARD_MM, BOARD_MM + 1, SEARCH_MM)
        for x in range(-BOARD_MM, BOARD_MM + 1, SEARCH_MM)
        if _on_board(x, y)
    ]
    coarse.sort(key=lambda point: -_total(rough, *point))
    named = [centre(bed) for bed in NAMED]
    starts = [
        *coarse[:SEARCH_STARTS],
        max(named, key=lambda point: _total(fine, *point)),
    ]
    near = range(-SEARCH_REACH_MM, SEARCH_REACH_MM + 1, GRID_MM)
    candidates = {
        (x + dx, y + dy)
        for x, y in starts
        for dx in near
        for dy in near
        if _on_board(x + dx, y + dy)
    }
    total, _, x, y = max(
        (_total(fine, x, y), -(x * x + y * y), x, y) for x, y in {*candidates, *named}
    )
    return {
        "bed": bed_name(*segment_at(x, y)),
        "x": x,
        "y": y,
        "expected": total / DRAWS,
        "compared": {bed: _total(fine, *centre(bed)) / DRAWS for bed in COMPARED},
    }
