"""Setup hints: where to aim when the darts in hand cannot check out."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.checkout import (
    BEDS,
    FINISHING,
    LEAVE_ORDER,
    PREFERRED_LEAVES,
    checkout,
    setup,
)
from custom_components.autodarts.practice import PracticeGame

from .local_helpers import dart, playing

SCORES = {bed.name: bed.score for bed in BEDS}

# Remaining score and darts in hand -> the setup darts and the score they leave.
SETUPS = {
    # The bogey numbers leave 32 with two trebles 20 and a single.
    (169, 3): ("T20 T20 S17", 32),
    (168, 3): ("T20 T20 S16", 32),
    (166, 3): ("T20 T20 S14", 32),
    (165, 3): ("T20 T20 S13", 32),
    (163, 3): ("T20 T20 S11", 32),
    (162, 3): ("T20 T20 S10", 32),
    (159, 3): ("T20 T20 S7", 32),
    # Above 170, only a double is worth setting up.
    (171, 3): ("T20 T20 S19", 32),
    (180, 3): ("T20 T20 S20", 40),
    (200, 3): ("T20 T20 T16", 32),
    (220, 3): ("T20 T20 T20", 40),
    # With fewer darts: a preferred double, then any double, then the
    # smallest finish of two darts.
    (100, 1): ("T20", 40),
    (80, 1): ("T16", 32),
    (60, 1): ("S20", 40),
    (51, 1): ("S19", 32),
    (41, 1): ("S9", 32),
    (35, 1): ("S3", 32),
    (21, 1): ("S5", 16),
    (3, 1): ("S1", 2),
    (99, 1): ("T20", 39),
    (101, 1): ("T20", 41),
    (150, 1): ("T20", 90),
    (110, 1): ("T20", 50),
    (111, 2): ("T20 S19", 32),
    (121, 2): ("T20 T7", 40),
    (170, 2): ("T20 T20", 50),
}


@pytest.mark.parametrize(("remaining", "darts"), SETUPS)
def test_setup_shots(remaining, darts):
    route, leave = SETUPS[remaining, darts]
    plan = setup(remaining, darts)
    assert plan is not None
    assert (" ".join(plan.route), plan.leave) == (route, leave)


@pytest.mark.parametrize(
    ("remaining", "darts"),
    [
        # A checkout exists: no setup.
        (170, 3),
        (100, 2),
        (40, 1),
        # Nothing worth setting up: above 170 a double is out of reach.
        (224, 3),
        (230, 3),
        (301, 3),
        (501, 3),
        # Scores and darts that make no sense.
        (1, 1),
        (0, 3),
        (100, 0),
        (100, 4),
    ],
)
def test_no_setup(remaining, darts):
    assert setup(remaining, darts) is None


def test_the_leaves_start_with_32_40_36_and_16_and_end_with_the_bull():
    assert LEAVE_ORDER[:4] == PREFERRED_LEAVES == (32, 40, 36, 16)
    assert LEAVE_ORDER[-1] == 50
    assert sorted(LEAVE_ORDER) == sorted(FINISHING)


def test_a_players_strongest_doubles_come_first():
    assert setup(80, 1) == (("T16",), 32)
    assert setup(80, 1, ("D10",)) == (("T20",), 20)
    # The strongest double counts only where no small bed is needed for it.
    assert setup(169, 3, ("D10",)) == (("T20", "T20", "S17"), 32)
    # A preferred double beyond the bull and the doubles is ignored.
    assert setup(100, 1, ("S20",)) == (("T20",), 40)


@given(remaining=st.integers(2, 400), darts=st.integers(1, 3))
def test_a_setup_adds_up_and_leaves_a_finish_for_the_next_visit(remaining, darts):
    plan = setup(remaining, darts)
    if checkout(remaining, darts) or plan is None:
        return
    assert len(plan.route) == darts
    assert remaining - sum(SCORES[bed] for bed in plan.route) == plan.leave
    # Never a double to set up, and the next visit finishes in two darts.
    assert not any(bed.startswith("D") or bed == "BULL" for bed in plan.route)
    assert checkout(plan.leave, 2)
    if darts == 3 and remaining > 170:
        assert plan.leave in FINISHING


def test_the_practice_game_shows_the_setup_instead_of_an_empty_checkout():
    game = playing(501, 169)
    snapshot = game.snapshot()
    assert snapshot["checkout"] is None
    assert snapshot["setup"] == {"route": "T20 T20 S17", "leave": 32}
    game.track([dart("T20")])
    assert game.snapshot()["setup"] == {"route": "T20 S17", "leave": 32}
    # A single 20 instead of the treble: the last dart still leaves 32.
    game.track([dart("T20"), dart("S20")])
    assert game.snapshot()["setup"] == {"route": "T19", "leave": 32}
    # 32 is left: the next visit finishes on D16.
    game.track([dart("T20"), dart("S20"), dart("T19")])
    snapshot = game.snapshot()
    assert snapshot["checkout"] == "D16" and snapshot["setup"] is None


def test_no_setup_without_double_out_before_double_in_or_after_the_leg():
    assert playing(501, 169, double_out=False).snapshot()["setup"] is None
    game = playing(501, 169, double_in=True)
    assert game.snapshot()["setup"] is None
    game = playing(301, 40)
    game.track([dart("D20")])
    assert game.snapshot()["setup"] is None


def test_the_next_player_hears_the_setup_with_the_turn():
    game = PracticeGame()
    game.set_players(2)
    game.play(301)
    game.players[1].remaining = 169
    game.track([dart("S1")])
    ((kind, turn),) = game.finish_visit()
    assert kind == "turn_changed" and turn["checkout"] is None
    assert turn["setup"] == {"route": "T20 T20 S17", "leave": 32}


def test_personal_routes_set_up_the_players_strongest_double():
    game = playing(501, 82, personal_routes=True)
    game.set_name(0, "Alex")
    game.track([dart("S1"), dart("S1")])
    assert game.snapshot()["setup"] == {"route": "T16", "leave": 32}
    game.profiles.doubles("Alex", [("D10", True)] * 10)
    assert game.snapshot()["setup"] == {"route": "T20", "leave": 20}
