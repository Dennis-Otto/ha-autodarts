"""Aimed beds, dart positions and the grouping around a bed, with synthetic scatter."""

import math
import random

import pytest

from custom_components.autodarts.checkout import checkout
from custom_components.autodarts.positions import (
    AIMS,
    BOARD_RADIUS_MM,
    GROUPS,
    MIN_GROUP,
    DartLog,
    aim_point,
    spread,
    x01_aims,
)

from .test_practice import dart


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def routes(remaining: int, left: int) -> tuple[str, ...]:
    return checkout(remaining, left)


def single_out(remaining: int, left: int) -> tuple[str, ...]:
    return checkout(remaining, left, False)


def around(aim: str, dx: float, dy: float) -> tuple[float, float, str]:
    """A dart that landed dx and dy millimetres from the centre of a bed."""
    x, y = aim_point(aim)
    return (x + dx) / BOARD_RADIUS_MM, (y + dy) / BOARD_RADIUS_MM, aim


def ring(aim: str, radius: float, count: int, centre=(0.0, 0.0)):
    """Darts evenly around a circle, so their mean is the circle's centre."""
    return [
        around(
            aim,
            centre[0] + radius * math.cos(2 * math.pi * index / count),
            centre[1] + radius * math.sin(2 * math.pi * index / count),
        )
        for index in range(count)
    ]


def test_aim_points_follow_the_board():
    assert aim_point("BULL") == (0.0, 0.0)
    x, y = aim_point("T20")
    assert (round(x, 6), y) == (0.0, 102.0)
    # The 6 is on the right, the 3 at the bottom and the 19 next to it.
    x, y = aim_point("D6")
    assert (x, round(y, 6)) == (165.0, 0.0)
    x, y = aim_point("T3")
    assert (round(x, 6), y) == (0.0, -102.0)
    x, y = aim_point("T19")
    assert x < 0 and y < -95
    assert len(AIMS) == 41 and "S20" not in AIMS


def test_x01_scoring_visits_aim_at_the_treble_20():
    assert x01_aims(501, darts("T20", "S20", "S1"), True, None, routes) == [
        "T20",
        "T20",
        "T20",
    ]


def test_x01_finishes_aim_at_the_double_or_the_route():
    # 100: T20 D20; after a single 20, 80 is T20 D10 with two darts.
    assert x01_aims(100, darts("S20", "T20", "D10"), True, None, routes) == [
        "T20",
        "T20",
        "D10",
    ]
    # One dart at 40 is thrown at D20; a miss leaves 40, a single 20 leaves D10.
    assert x01_aims(40, darts("MISS", "S20", "D10"), True, None, routes) == [
        "D20",
        "D20",
        "D10",
    ]
    assert x01_aims(50, darts("BULL"), True, None, routes) == ["BULL"]
    # 60 is S20 D20: a single has no aim. Two darts cannot finish 140.
    assert x01_aims(60, darts("S20"), True, None, routes) == [None]
    assert x01_aims(200, darts("T20", "T20", "T20"), True, None, routes) == [
        "T20",
        "T20",
        "T20",
    ]


def test_x01_darts_after_the_finish_or_a_bust_have_no_aim():
    assert x01_aims(40, darts("D20", "S1", "S1"), True, None, routes) == [
        "D20",
        None,
        None,
    ]
    # 20 minus a treble 20 busts: the rest of the visit does not count.
    assert x01_aims(20, darts("T20", "S1", "S1"), True, None, routes) == [
        "D10",
        None,
        None,
    ]
    # Leaving one busts with double out, as does a finish on a single.
    assert x01_aims(21, darts("S20", "S1"), True, None, routes)[1] is None
    assert x01_aims(20, darts("S20", "S1"), True, None, routes)[1] is None


def test_without_double_out_the_route_can_end_on_a_single():
    assert x01_aims(20, darts("S20"), False, None, single_out) == [None]
    assert x01_aims(501, darts("T20"), False, None, single_out) == ["T20"]
    assert x01_aims(20, darts("S19", "S1"), False, None, single_out) == [None, None]


def test_double_in_aims_after_the_opening_double():
    # Before the opening double, any double will do.
    assert x01_aims(501, darts("S20", "D5", "T20"), True, 1, routes) == [
        None,
        None,
        "T20",
    ]
    assert x01_aims(501, darts("S20", "S5", "T20"), True, 3, routes) == [
        None,
        None,
        None,
    ]
    assert x01_aims(501, darts("D20", "T20"), True, 0, routes) == [None, "T20"]


def test_the_grouping_of_rings_is_exact():
    """20 darts 30 mm and 20 darts 10 mm around a point 6 mm left of T20."""
    older = ring("T20", 30, 20, centre=(-6, 2))
    newer = ring("T20", 10, 20, centre=(-6, 2))
    [group] = spread([*older, *newer])
    assert group == {
        "target": "T20",
        "darts": 40,
        "offset_x": -6.0,
        "offset_y": 2.0,
        "r50": 10.0,
        "r80": 30.0,
        # The newer half is 20 mm tighter than the older one.
        "change": -20.0,
    }


def test_a_normal_scatter_has_the_expected_radii():
    """Darts scattered normally: half lie within 1.18 and 80 % within 1.79 sigma."""
    generator = random.Random(27)
    sigma = 20
    scatter = [
        around("D16", generator.gauss(4, sigma), generator.gauss(-3, sigma))
        for _ in range(2000)
    ]
    [group] = spread(scatter)
    assert group["darts"] == 2000
    assert group["offset_x"] == pytest.approx(4, abs=2)
    assert group["offset_y"] == pytest.approx(-3, abs=2)
    assert group["r50"] == pytest.approx(1.1774 * sigma, rel=0.06)
    assert group["r80"] == pytest.approx(1.7941 * sigma, rel=0.06)
    assert group["change"] == pytest.approx(0, abs=3)


def test_groupings_need_enough_darts_and_an_aim():
    few = ring("BULL", 5, MIN_GROUP - 1)
    unaimed = [(x, y, None) for x, y, _ in ring("T19", 5, 30)]
    singles = [(x, y, "S20") for x, y, _ in ring("T20", 5, 30)]
    assert spread([*few, *unaimed, *singles]) == []
    [group] = spread(ring("BULL", 5, MIN_GROUP))
    # With fewer than two halves of enough darts, there is no trend.
    assert group["target"] == "BULL" and group["change"] is None


def test_groupings_come_most_darts_first():
    beds = [f"D{number}" for number in range(1, GROUPS + 3)]
    scatter = [
        dart for index, bed in enumerate(beds) for dart in ring(bed, 8, 10 + index)
    ]
    scatter += ring("T20", 8, 10 + len(beds))
    groups = spread(scatter)
    assert len(groups) == GROUPS
    assert [group["target"] for group in groups[:3]] == ["T20", beds[-1], beds[-2]]
    # Equal numbers of darts keep the order of the aims.
    tied = spread([*ring("D2", 8, 10), *ring("D1", 8, 10)])
    assert [group["target"] for group in tied] == ["D1", "D2"]


def test_the_log_keeps_the_newest_darts_compactly():
    log = DartLog(3)
    log.add(None, "T20")
    log.add((0.0, 4.0), "T20")
    assert len(log) == 0
    for step in range(4):
        log.add((0.1 * step, 0.6), "T20" if step else "S20")
    assert len(log) == 3
    assert log.positions() == [[0.1, 0.6], [0.2, 0.6], [0.3, 0.6]]
    stored = log.stored()
    assert stored == [170, 1020, 21, 340, 1020, 21, 510, 1020, 21]
    copy = DartLog(3)
    copy.restore(stored)
    assert copy.positions() == log.positions()
    assert list(copy.darts)[0][2] == "T20"
    log.clear()
    assert log.positions() == [] and log.spread() == []


def test_the_log_restores_only_valid_darts():
    log = DartLog(10)
    for saved in (None, {"x": 1}, [1, 2]):
        log.restore(saved)
        assert len(log) == 0
    log.restore(
        [
            *(170, 1020, 0),
            *(170.5, 1020, 21),
            *(9000, 0, 21),
            *(0, -9000, 21),
            *(0, 0, 42),
            *(0, 0, -1),
            *(0, 0, True),
            *(-170, 0, 1),
        ]
    )
    assert log.positions() == [[0.1, 0.6], [-0.1, 0.0]]
    assert [aim for _, _, aim in log.darts] == [None, "BULL"]


def test_the_log_works_out_its_grouping_once_per_dart():
    log = DartLog(100)
    for x, y, aim in ring("T20", 5, MIN_GROUP):
        log.add((x, y), aim)
    first = log.spread()
    first[0]["darts"] = 0
    assert log.spread()[0]["darts"] == MIN_GROUP
    log.add((0.0, 0.6), "T20")
    assert log.spread()[0]["darts"] == MIN_GROUP + 1
