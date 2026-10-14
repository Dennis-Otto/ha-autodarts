"""The aim map: the points of the board, the fixed draws, the points per dart at an
aim point and the best aim, with the results of Tibshirani, Price and Taylor."""

import math

import pytest

from custom_components.autodarts import aim
from custom_components.autodarts.aim import (
    COMPARED,
    DRAWS,
    GRID_MM,
    SEARCH_MM,
    ErrorModel,
    best_aim,
    centre,
    draws,
    expected,
    points,
)
from custom_components.autodarts.bot import segment_at
from custom_components.autodarts.positions import aim_point

# The same numbers as tests/frontend/training-aim.test.mjs, which the training card
# computes for its map: Home Assistant and the card agree to the last digit.
BOARD_SUM = 1_213_944
BOARD_MOMENTS = (-6_705_061, -1_380_490)
CIRCLE_20 = ErrorModel(0, 0, 20, 20, 0)
EXPECTED_20 = {"T20": 18.047, "T19": 18.507, "BULL": 16.353}


def circle(sd: float, offset_x: float = 0, offset_y: float = 0) -> ErrorModel:
    return ErrorModel(offset_x, offset_y, sd, sd, 0)


@pytest.mark.parametrize("number", range(1, 21))
def test_points_follow_the_board(number):
    """The middle of every bed scores its points."""
    for bed, times in (("T", 3), ("D", 2)):
        assert points(*aim_point(f"{bed}{number}")) == times * number
    x, y = aim_point(f"T{number}")
    # The outer single lies between the treble and the double, the inner one inside.
    assert points(x * 1.3, y * 1.3) == number
    assert points(x * 0.5, y * 0.5) == number


def test_the_rings_end_where_the_board_manager_draws_them():
    # From the middle up the 20: bull to 7 mm, outer bull to 17, the treble from
    # beyond 97 to 107, the double from beyond 160 to 170, then the board ends.
    ends = {7: 50, 8: 25, 17: 25, 18: 20, 97: 20, 98: 60, 107: 60, 108: 20}
    ends |= {160: 20, 161: 40, 170: 40, 171: 0}
    assert {y: points(0, y) for y in ends} == ends
    assert points(0, 0) == 50 and points(500, -500) == 0
    # A point exactly between two sectors lies in the even one, as Python rounds
    # halves; the card does the same.
    diagonals = [segment_at(*point) for point in ((50, 50), (-50, 50), (50, -50))]
    assert diagonals == [(18, 1), (12, 1), (2, 1)]
    assert segment_at(-50, -50) == (7, 1)


def test_the_board_of_points_is_the_board():
    """Every millimetre of the board, as the card has it; outside, nothing."""
    board = aim._board()
    assert len(board) == aim.WIDTH**2
    total, moment_x, moment_y = 0, 0, 0
    for y in range(-170, 171):
        for x in range(-170, 171):
            value = board[(y + aim.EDGE_MM) * aim.WIDTH + x + aim.EDGE_MM]
            assert value == points(x, y)
            total, moment_x, moment_y = (
                total + value,
                moment_x + x * value,
                moment_y + y * value,
            )
    assert total == sum(board) == BOARD_SUM
    assert (moment_x, moment_y) == BOARD_MOMENTS
    # Off the board, in the corner of the reach.
    assert board[0] == 0


def test_the_draws_are_standard_normal_and_fixed():
    pairs = draws(DRAWS)
    assert len(pairs) == DRAWS and draws(DRAWS) is pairs
    for axis in (0, 1):
        values = [pair[axis] for pair in pairs]
        assert sum(values) / DRAWS == pytest.approx(0, abs=0.01)
        assert sum(value**2 for value in values) / DRAWS == pytest.approx(1, abs=0.02)
    assert sum(x * y for x, y in pairs) / DRAWS == pytest.approx(0, abs=0.01)
    # Half of the pairs lie within the median radius of a standard normal pair.
    inside = sum(math.hypot(x, y) <= math.sqrt(2 * math.log(2)) for x, y in pairs)
    assert inside == DRAWS // 2
    first = pairs[0]
    assert first == pytest.approx((3.8989, 0), abs=1e-4)


def test_the_points_per_dart_are_those_of_the_card():
    assert {bed: expected(CIRCLE_20, *centre(bed)) for bed in COMPARED} == EXPECTED_20


def test_the_centres_of_the_compared_beds():
    assert centre("T20") == (0, 102)
    # The centre of the treble 19, (-31.5, -97.0), on the grid.
    assert centre("T19") == (-32, -98)
    assert centre("BULL") == (0, 0)


def test_a_dart_that_never_misses_scores_its_bed():
    for x, y in ((0, 102), (0, 0), (-32, -97), (0, 140)):
        number, multiplier = segment_at(x, y)
        assert expected(circle(0.01), x, y) == number * multiplier
    # Far off the board, every draw misses it.
    assert expected(circle(5, offset_x=600), 0, 0) == 0


def test_a_tight_spread_aims_at_the_treble_20():
    best = best_aim(circle(5))
    assert best["bed"] == "T20"
    assert best["expected"] == pytest.approx(47.2, abs=0.1)
    assert best["compared"]["T20"] == pytest.approx(best["expected"], abs=0.1)
    assert best["compared"]["T20"] > best["compared"]["T19"] > best["compared"]["BULL"]


def test_a_wider_spread_moves_to_the_treble_19():
    """As in the paper: from about 17 mm, the treble 19 beats the treble 20."""
    assert best_aim(circle(15))["bed"] == "T20"
    best = best_aim(CIRCLE_20)
    assert best["bed"] == "T19"
    assert best["compared"] == EXPECTED_20
    assert best["expected"] >= EXPECTED_20["T19"] > EXPECTED_20["T20"]


def test_a_wide_spread_aims_towards_the_middle_left_of_the_bull():
    """The nine numbers on the left, from the 5 to the 19, add up to 101, those on
    the right, from the 1 to the 17, to 86."""
    best = best_aim(circle(60))
    assert best["x"] < 0
    assert math.hypot(best["x"], best["y"]) < 80
    # Near the middle, the bull scores more than the treble 20.
    assert best["compared"]["BULL"] > best["compared"]["T20"]


def test_the_points_per_dart_fall_as_the_spread_grows():
    values = [best_aim(circle(sd))["expected"] for sd in (3, 10, 20, 40, 80)]
    assert values == sorted(values, reverse=True)
    assert values[0] > 50 and values[-1] < 13


def test_the_best_aim_makes_up_for_the_offset():
    """Darts that land 8 mm low are best aimed 8 mm above the treble 20."""
    best = best_aim(circle(4, offset_y=-8))
    assert (best["x"], best["y"]) == (0, 110)
    # The point lies in the single above the treble; the darts land in the treble.
    assert best["bed"] == "S20"
    assert best["expected"] > best["compared"]["T20"] + 20


def test_a_spread_up_and_down_keeps_the_20():
    """The treble 20 suits a spread up and down more than one to the sides."""
    upright = best_aim(ErrorModel(0, 0, 8, 25, 0))
    sideways = best_aim(ErrorModel(0, 0, 25, 8, 0))
    assert segment_at(upright["x"], upright["y"])[0] == 20
    assert segment_at(sideways["x"], sideways["y"])[0] != 20


def test_ties_go_to_the_point_nearest_to_the_middle():
    """With a spread of half a millimetre, the treble 20 scores 60 from many points."""
    best = best_aim(circle(0.5))
    assert best == {
        "bed": "T20",
        "x": 0,
        "y": 100,
        "expected": 60,
        "compared": {"T20": 60, "T19": 57, "BULL": 50},
    }


@pytest.mark.parametrize(
    "model",
    [
        circle(12),
        circle(25),
        circle(45, offset_x=5, offset_y=-3),
        ErrorModel(2.5, -3, 30, 45, 0.3),
        ErrorModel(-6, 2, 21, 21, -0.4),
    ],
)
def test_the_search_beats_every_point_of_the_coarse_grid(model):
    offsets = aim._offsets(model, DRAWS)
    coarse = max(
        aim._total(offsets, x, y)
        for x in range(-170, 171, SEARCH_MM)
        for y in range(-170, 171, SEARCH_MM)
        if x * x + y * y <= 170 * 170
    )
    best = best_aim(model)
    assert best["expected"] * DRAWS >= coarse
    assert best["x"] % GRID_MM == 0 and best["y"] % GRID_MM == 0
    assert best["expected"] == expected(model, best["x"], best["y"])
