"""Bermuda, Round the World and Gotcha, the games of play.autodarts.io."""

import json
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from custom_components.homedarts.party import (
    BERMUDA_TARGETS,
    GOTCHA_TARGET,
    Bermuda,
    Gotcha,
    RoundTheWorld,
    make_party,
    valid_gotcha_target,
)
from custom_components.homedarts.practice import PracticeGame, valid_party_rule
from custom_components.homedarts.scoring import DOUBLE, MASTER, STRAIGHT

from .local_helpers import NOW, dart, throw


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def practice_of(kind: str, players: int = 2) -> PracticeGame:
    practice = PracticeGame()
    practice.set_players(players)
    practice.play(kind)
    return practice


def kinds(events: list[tuple[str, dict]]) -> list[str]:
    return [kind for kind, _ in events]


# -- Bermuda -------------------------------------------------------------------


def test_bermuda_plays_the_thirteen_targets_of_homedarts():
    game = Bermuda(1)
    assert game.rounds == 13 and game.points == [0]
    targets = []
    for _ in BERMUDA_TARGETS:
        targets.append(game.target(0))
        game.book(0, darts("MISS", "MISS", "MISS"))
    assert tuple(targets) == BERMUDA_TARGETS
    assert targets[3] == "D" and targets[7] == "T" and targets[-2:] == ["25", "50"]


@pytest.mark.parametrize(
    ("target", "hits", "misses"),
    [
        ("12", ["S12", "D12", "T12"], ["S13", "MISS"]),
        ("D", ["D1", "D20", "BULL"], ["S20", "T20", "25"]),
        ("T", ["T1", "T20"], ["D20", "BULL"]),
        ("25", ["25", "BULL"], ["S20"]),
        ("50", ["BULL"], ["25", "D20"]),
    ],
)
def test_bermuda_counts_the_beds_of_its_target(target, hits, misses):
    for name in hits:
        assert Bermuda.hit(dart(name), target), name
    for name in misses:
        assert not Bermuda.hit(dart(name), target), name


def test_bermuda_scores_the_beds_hit_and_halves_a_visit_without_a_hit():
    game = Bermuda(2)
    visit = game.book(0, darts("S12", "D12", "T12"))
    assert visit.points == [72, 0] and visit.hits == 3
    game.book(1, darts("S12", "MISS", "MISS"))
    # Round 2 at the 13: no hit halves, rounding down.
    game.book(0, darts("S20", "S20", "S20"))
    game.book(1, darts("S13", "MISS", "MISS"))
    assert game.points == [36, 25]
    # A visit cut short by darts off the board halves as well.
    game.book(0, darts("MISS"))
    assert game.points == [18, 25]


def test_bermuda_can_be_played_without_halving():
    game = make_party("bermuda", 1, halve=False)
    assert isinstance(game, Bermuda) and not game.halves
    game.book(0, darts("S12", "MISS", "MISS"))
    game.book(0, darts("MISS", "MISS", "MISS"))
    assert game.points == [12]


def test_bermuda_ends_after_the_bullseye_round_with_the_most_points():
    practice = practice_of("bermuda", 2)
    events: list[tuple[str, dict]] = []
    for _ in BERMUDA_TARGETS[:-1]:
        throw(practice, "MISS")
        throw(practice, "MISS")
    snapshot = practice.snapshot()
    assert snapshot["target"] == "50" and snapshot["round"] == 13
    throw(practice, "25")
    events = throw(practice, "BULL")
    assert kinds(events) == ["leg_won", "match_won"]
    assert dict(events)["leg_won"]["player"] == 2
    assert dict(events)["leg_won"]["points"] == 50


def test_the_halving_option_restarts_a_game_of_bermuda():
    practice = practice_of("bermuda", 1)
    throw(practice, "T12")
    practice.set_option("bermuda_halve_on_miss", False)
    assert practice.party.points == [0] and not practice.party.halves
    throw(practice, "T12")
    # The same setting again, or while another game is played, changes nothing.
    practice.set_option("bermuda_halve_on_miss", False)
    assert practice.party.points == [36]
    practice.play("halve_it")
    practice.set_option("bermuda_halve_on_miss", True)
    assert practice.party.kind == "halve_it" and practice.party.halves


# -- Round the World -----------------------------------------------------------


def test_round_the_world_goes_round_and_adds_the_points_of_its_targets():
    game = RoundTheWorld(1)
    assert game.sequence == [*range(1, 21), 25] and game.target(0) == "1"
    # Any bed completes the target, and the next dart aims at the next one.
    visit = game.book(0, darts("S1", "D2", "T3"))
    assert visit.progress == [3] and visit.points == [14] and visit.hits == 3
    assert game.target(0) == "4" and game.details(0) == {"progress": 3}
    # A dart at a later number does not count.
    game.book(0, darts("S5", "MISS", "S4"))
    assert game.progress == [4] and game.points == [18]


def test_round_the_world_goes_down_or_in_a_random_order():
    assert RoundTheWorld(1, "descending").sequence == [*range(20, 0, -1), 25]
    random.seed(7)
    shuffled = RoundTheWorld(1, "random").sequence
    assert shuffled[-1] == 25 and sorted(shuffled[:-1]) == list(range(1, 21))
    assert shuffled[:-1] != list(range(1, 21))
    # An unknown order goes up.
    assert RoundTheWorld(1, "sideways").order == "ascending"


def test_round_the_world_is_won_with_the_bull_after_the_last_number():
    practice = practice_of("round_the_world", 2)
    practice.party.progress = [20, 0]
    assert practice.snapshot()["target"] == "25"
    practice.track(darts("S20"), now=NOW)
    snapshot = practice.snapshot()
    assert snapshot["target"] == "25" and snapshot["scored"] == 0
    events = practice.track(darts("S20", "BULL"), now=NOW)
    assert kinds(events) == ["leg_won", "match_won"]
    assert dict(events)["leg_won"]["darts"] == 2
    assert dict(events)["leg_won"]["points"] == 50
    assert practice.snapshot()["won"] is True


def test_round_the_world_shows_the_target_of_every_dart_while_it_is_thrown():
    practice = practice_of("round_the_world", 2)
    practice.track(darts("S1"), now=NOW)
    snapshot = practice.snapshot()
    assert snapshot["target"] == "2" and snapshot["scored"] == 1
    assert snapshot["scores"][0]["progress"] == 1
    assert snapshot["scores"][1]["progress"] == 0
    practice.track(darts("S1", "T2"), now=NOW)
    assert practice.snapshot()["target"] == "3"
    assert practice.snapshot()["scored"] == 7
    events = practice.finish_visit(now=NOW)
    assert events[-1][1]["target"] == "1" and events[-1][1]["player"] == 2
    practice.track([], now=NOW)
    assert practice.snapshot()["scores"][0]["progress"] == 2


def test_the_order_of_round_the_world_is_a_rule_that_restarts_the_game():
    practice = practice_of("round_the_world", 1)
    throw(practice, "S1")
    practice.set_party_rule("round_the_world_order", "descending")
    assert practice.party.progress == [0] and practice.party.target(0) == "20"
    throw(practice, "S20")
    # An unknown or unchanged order changes nothing.
    practice.set_party_rule("round_the_world_order", "sideways")
    practice.set_party_rule("round_the_world_order", "descending")
    assert practice.party.progress == [1]
    restored = PracticeGame()
    restored.restore(json.loads(json.dumps(practice.stored())))
    assert restored.round_the_world_order == "descending"
    assert restored.party.sequence == practice.party.sequence
    assert restored.party.progress == [1] and restored.party.points == [20]


def test_round_the_world_restores_its_state_and_ignores_nonsense():
    game = RoundTheWorld(2, "random")
    game.book(0, darts(f"S{game.sequence[0]}"))
    restored = RoundTheWorld(2)
    restored.restore(json.loads(json.dumps(game.stored())))
    assert restored.sequence == game.sequence and restored.progress == [1, 0]
    for nonsense in (
        {"sequence": [*range(1, 21), 20], "progress": [22, 0]},
        {"sequence": [1, 2, 25], "progress": [1]},
        {"sequence": [25], "progress": "1"},
        {"sequence": [*range(1, 20), 1, 25], "progress": [-1, 0]},
        {"sequence": [*map(str, range(1, 21)), 25], "progress": [1.5, 0]},
        {"sequence": [], "progress": [0, 0, 0]},
    ):
        fresh = RoundTheWorld(2)
        fresh.restore(nonsense)
        assert fresh.sequence == [*range(1, 21), 25] and fresh.progress == [0, 0]
    fresh.restore(None)
    assert fresh.progress == [0, 0]


def test_round_the_world_restored_round_the_board_takes_darts_without_a_crash():
    game = RoundTheWorld(2)
    game.restore({"progress": [21, 0]})
    assert game.progress == [21, 0] and game.target(0) is None
    result = game.visit(0, darts("BULL", "S1"))
    assert result.won is None and result.progress == [21, 0] and result.hits == 0


# -- Gotcha --------------------------------------------------------------------


def test_gotcha_counts_up_and_sends_a_player_on_the_same_score_back_to_zero():
    game = Gotcha(3)
    assert game.goal == GOTCHA_TARGET and game.out_mode == STRAIGHT
    game.book(0, darts("T20", "S20"))
    game.book(1, darts("S20"))
    assert game.points == [80, 20, 0]
    # The second dart reaches 80: gotcha, player 1 goes back to 0.
    visit = game.book(2, darts("T20", "S20", "S1"))
    assert visit.points == [0, 20, 81] and game.points == [0, 20, 81]
    assert game.details(2) == {"left": 220} and game.target(2) is None


def test_a_gotcha_visit_that_overshoots_is_denied_with_its_gotchas():
    game = Gotcha(2, 101)
    game.points = [70, 80]
    # Reaching 80 would send player 2 back, but the visit busts after it.
    visit = game.visit(0, darts("S10", "T20", "S1"))
    assert visit.points == [70, 80] and visit.bust and visit.darts == 2
    visit = game.visit(0, darts("MISS", "S10", "S1"))
    assert visit.points == [81, 0] and not visit.bust and visit.won is None
    visit = game.visit(1, darts("S20", "S1"))
    assert visit.won == 1 and visit.points[1] == 101 and visit.darts == 2


@pytest.mark.parametrize(
    ("mode", "finish", "outcome"),
    [
        (DOUBLE, ["D1"], "won"),
        (DOUBLE, ["S2"], "bust"),
        (DOUBLE, ["S1"], "bust"),
        (MASTER, ["T1"], "bust"),
        (MASTER, ["D1"], "won"),
        (STRAIGHT, ["S1", "S1"], "won"),
    ],
)
def test_gotcha_ends_as_the_out_mode_asks(mode, finish, outcome):
    game = Gotcha(1, 101, mode)
    game.points = [99]
    visit = game.visit(0, darts(*finish))
    assert ("won" if visit.won == 0 else "bust" if visit.bust else None) == outcome


def test_gotcha_master_out_finishes_on_a_treble():
    game = Gotcha(1, 101, MASTER)
    game.points = [98]
    assert game.visit(0, darts("T1")).won == 0


def test_gotcha_takes_target_scores_from_101_to_1001():
    assert valid_gotcha_target(101) and valid_gotcha_target(1001)
    assert not valid_gotcha_target(100) and not valid_gotcha_target(1002)
    assert not valid_gotcha_target(301.0) and not valid_gotcha_target(True)
    assert Gotcha(1, 5000).goal == GOTCHA_TARGET
    assert Gotcha(1, out_mode="sideways").out_mode == STRAIGHT
    assert valid_party_rule("gotcha_target", 501)
    assert valid_party_rule("round_the_world_order", "random")
    assert not valid_party_rule("round_the_world_order", 501)
    assert not valid_party_rule("golf_holes", "random")


def test_gotcha_restores_its_points_within_the_target():
    game = Gotcha(2, 101)
    game.book(0, darts("T20"))
    restored = Gotcha(2, 101)
    restored.restore(json.loads(json.dumps(game.stored())))
    assert restored.points == [60, 0]
    restored.restore({"points": [150, 0], "turns": 1})
    assert restored.points == [0, 0]


def test_gotcha_in_the_practice_game_busts_wins_and_follows_the_out_mode():
    practice = practice_of("gotcha", 2)
    practice.set_party_rule("gotcha_target", 101)
    assert practice.party.goal == 101 and practice.party.out_mode == "double"
    throw(practice, "T20", "S20")
    snapshot = practice.snapshot()
    assert snapshot["scores"][0]["points"] == 80 and snapshot["scores"][0]["left"] == 21
    # The out mode changes a leg only before its first dart.
    practice.set_rule("out_mode", "straight")
    assert practice.party.out_mode == "double"
    events = practice.track(darts("T20", "T20"), now=NOW)
    assert events == [("bust", {**practice._who(1), "remaining": 101})]
    snapshot = practice.snapshot()
    assert snapshot["bust"] is True and snapshot["scored"] == 0
    practice.finish_visit(now=NOW)
    practice.track([], now=NOW)
    assert practice.party.points == [80, 0] and practice.players[1].darts == 2
    events = throw(practice, "S1", "D10")
    assert kinds(events) == ["leg_won", "match_won"]
    assert dict(events)["leg_won"]["points"] == 101
    # The next match plays the new out mode.
    practice.new_match()
    assert practice.party.out_mode == "straight" and practice.party.points == [0, 0]
    practice.set_rule("out_mode", "master")
    assert practice.party.out_mode == "master"


def test_a_gotcha_bust_is_announced_once_and_taken_back_with_a_correction():
    practice = practice_of("gotcha", 1)
    practice.set_party_rule("gotcha_target", 101)
    assert practice.track(darts("T20"), now=NOW) == []
    events = practice.track(darts("T20", "T20"), now=NOW)
    assert kinds(events) == ["bust"] and events[0][1]["remaining"] == 101
    # Later darts of the busted visit announce nothing again.
    assert practice.track(darts("T20", "T20", "S1"), now=NOW) == []
    # The dart corrected back below the target takes the bust away.
    assert practice.track(darts("T20", "S20"), now=NOW) == []
    assert practice.snapshot()["bust"] is False
    assert kinds(practice.track(darts("T20", "S20", "T20"), now=NOW)) == ["bust"]


def test_gotcha_rules_restart_the_game_and_come_back_after_a_restart():
    practice = practice_of("gotcha", 1)
    throw(practice, "T20")
    practice.set_party_rule("gotcha_target", 501)
    assert practice.party.points == [0] and practice.party.goal == 501
    practice.set_party_rule("gotcha_target", 99)
    assert practice.gotcha_target == 501
    practice.play("count_up")
    practice.set_party_rule("gotcha_target", 701)
    assert practice.party.kind == "count_up"
    restored = PracticeGame()
    restored.restore(json.loads(json.dumps(practice.stored())))
    assert restored.gotcha_target == 701 and restored.bermuda_halve_on_miss
    restored.restore({"gotcha_target": 5, "round_the_world_order": 1})
    assert restored.gotcha_target == 701
    assert restored.round_the_world_order == "ascending"


# -- every new game ------------------------------------------------------------


@settings(max_examples=60, deadline=None)
@given(
    kind=st.sampled_from(["bermuda", "round_the_world", "gotcha"]),
    players=st.integers(1, 8),
    visits=st.lists(
        st.lists(
            st.sampled_from(
                ["S1", "D2", "T3", "S12", "D12", "T20", "25", "BULL", "MISS"]
            ),
            max_size=3,
        ),
        max_size=150,
    ),
)
def test_the_new_games_keep_their_invariants(kind, players, visits):
    """Points never go below zero, a leg is won only once, the throw passes
    in turn, and Gotcha never overshoots its target."""
    practice = practice_of(kind, players)
    practice.set_party_rule("gotcha_target", 101)
    for visit in visits:
        before, legs = practice.current, practice.legs_total
        events = (
            throw(practice, *visit)
            if visit
            else practice.finish_visit(empty=True, now=NOW)
        )
        won = [event for event in events if event[0] == "leg_won"]
        assert len(won) == practice.legs_total - legs <= 1
        snapshot = practice.snapshot()
        assert all(score["points"] >= 0 for score in snapshot["scores"])
        if kind == "gotcha":
            assert all(score["points"] <= 101 for score in snapshot["scores"])
        if practice.winner is not None:
            assert [kind for kind, _ in won] == ["leg_won"]
            break
        # A tie after the last round of Bermuda plays the leg again.
        if not won and practice.party.turns:
            assert practice.current == (before + 1) % players
