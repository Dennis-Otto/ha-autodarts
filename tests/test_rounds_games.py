"""Golf, Baseball and Count-Up: rounds for everybody, extra rounds after a tie."""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from custom_components.autodarts.party import (
    Baseball,
    CountUp,
    Golf,
    golf_strokes,
    inner_single,
    make_party,
)
from custom_components.autodarts.practice import PracticeGame

from .test_practice import dart, throw


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def single(number: int, inner: bool | None) -> dict:
    return {**dart(f"S{number}"), "inner": inner}


def test_golf_strokes_by_bed():
    assert golf_strokes(dart("T3"), 3) == 1
    assert golf_strokes(dart("D3"), 3) == 2
    assert golf_strokes(single(3, True), 3) == 3
    assert golf_strokes(single(3, False), 3) == 4
    # Without a position the board saw, a single counts as an outer single.
    assert golf_strokes(single(3, None), 3) == 4
    assert golf_strokes(dart("T4"), 3) == 5
    assert golf_strokes(dart("MISS"), 3) == 5


def test_inner_singles_lie_inside_the_treble_ring():
    assert inner_single(None) is None
    assert inner_single((0.0, 0.3)) is True
    assert inner_single((0.4, 0.5)) is False


def test_the_last_dart_of_a_golf_visit_counts():
    golf = Golf(1)
    assert golf.target(0) == "1" and golf.rounds == 9
    assert golf.visit(0, []).points == [0]
    assert golf.visit(0, darts("T1", "MISS")).points == [5]
    # A player stops after a good dart by pulling the darts.
    result = golf.book(0, darts("MISS", "T1"))
    assert result.points == [1] and result.hits == 1 and result.won is None
    assert golf.round == 2 and golf.details(0) == {"scorecard": [1]}


def test_golf_is_won_with_the_fewest_strokes_after_the_last_hole():
    golf = make_party("golf", 2, 18)
    assert isinstance(golf, Golf) and golf.rounds == 18
    golf = make_party("golf", 2, 9)
    for hole in range(1, 9):
        golf.book(0, darts(f"T{hole}"))
        golf.book(1, darts(f"D{hole}"))
    assert golf.book(0, darts("D9")).won is None
    result = golf.book(1, darts("T9"))
    assert result.won == 0 and golf.points == [10, 17]


def test_a_tie_plays_extra_holes_among_the_tied_players():
    golf = Golf(3, 1)
    golf.new_leg(3, 1)
    # Player 2 starts; players 2 and 3 tie at the top with a double each.
    assert golf.next(0) == 1
    golf.book(1, darts("D1"))
    golf.book(2, darts("D1"))
    assert golf.book(0, darts("S2")).won is None
    assert golf.playoff() == [1, 2] and golf.round == 2
    assert golf.target(1) == "2" and golf.next(0) == 1
    golf.book(1, darts("T2"))
    assert golf.next(1) == 2
    result = golf.book(2, darts("T2"))
    assert result.won is None and golf.round == 3
    golf.book(1, darts("D3"))
    assert golf.book(2, darts("T3")).won == 2


def test_extra_rounds_go_on_from_one_after_twenty():
    golf = Golf(2, 20)
    for _ in range(19):
        golf.book(0, darts("MISS"))
        golf.book(1, darts("MISS"))
    assert golf.target(0) == "20"
    golf.book(0, darts("MISS"))
    golf.book(1, darts("MISS"))
    assert golf.target(0) == "1" and golf.playoff() == [0, 1]


def test_baseball_scores_runs_on_the_number_of_the_inning():
    baseball = Baseball(2)
    assert baseball.rounds == 9
    result = baseball.book(0, darts("T1", "S1", "D2"))
    assert result.points == [4, 0] and result.hits == 2
    # The bull scores no runs.
    assert baseball.book(1, darts("BULL", "D1")).points == [4, 2]
    assert baseball.round == 2 and baseball.details(1) == {"scorecard": [2]}


def test_a_tied_baseball_game_plays_extra_innings():
    baseball = Baseball(2)
    for _ in range(9):
        baseball.book(0, darts("MISS"))
        baseball.book(1, darts("MISS"))
    assert baseball.playoff() == [0, 1] and baseball.target(0) == "10"
    baseball.book(0, darts("S10"))
    assert baseball.book(1, darts("T10")).won == 1


def test_count_up_adds_every_dart_for_its_rounds():
    count_up = make_party("count_up", 1, 2)
    assert isinstance(count_up, CountUp) and count_up.rounds == 2
    assert count_up.target(0) is None
    assert count_up.book(0, darts("T20", "MISS", "25")).hits == 2
    assert count_up.book(0, darts("S1")).won == 0 and count_up.points == [86]
    assert make_party("count_up", 2).rounds == 8


def test_rounds_games_restore_their_state_and_ignore_nonsense():
    golf = Golf(3, 9)
    golf.book(0, darts("T1"))
    saved = json.loads(json.dumps(golf.stored()))
    restored = Golf(3, 9)
    restored.restore(saved)
    assert restored.stored() == golf.stored()
    restored.restore(
        {
            **saved,
            "round": 0,
            "lineup": [0, 0],
            "thrown": 5,
            "scorecard": [[1], [-1], []],
        }
    )
    assert restored.stored() == golf.stored()
    restored.restore({**saved, "lineup": [], "scorecard": [[1]]})
    assert restored.lineup == [0, 1, 2] and restored.scorecard == [[1], [], []]
    restored.restore(None)
    assert restored.stored() == golf.stored()


def rounds_game(kind: str, players: int = 2) -> PracticeGame:
    practice = PracticeGame()
    practice.set_players(players)
    practice.play(kind)
    return practice


def test_a_golf_leg_in_the_practice_game_uses_the_dart_positions():
    practice = rounds_game("golf")
    snapshot = practice.snapshot()
    assert snapshot["game"] == "golf" and snapshot["rounds"] == 9
    practice.set_rounds(golf_holes=18)
    snapshot = practice.snapshot()
    assert snapshot["rounds"] == 18 and snapshot["round"] == 1
    assert snapshot["target"] == "1" and snapshot["playoff"] is None
    # An inner single: three strokes, as the board's position tells.
    practice.track([dart("S1")], [(0.0, 0.3)])
    assert practice.snapshot()["points"] == 3
    events = practice.finish_visit()
    assert events == [
        (
            "turn_changed",
            {
                "game": "golf",
                "player": 2,
                "name": None,
                "players": 2,
                "remaining": None,
                "checkout": None,
                "points": 0,
                "target": "1",
            },
        )
    ]
    practice.track([dart("S1")], [(0.0, 0.8)])
    practice.finish_visit()
    practice.track([])
    scores = practice.snapshot()["scores"]
    assert [score["scorecard"] for score in scores] == [[3], [4]]
    assert practice.snapshot()["round"] == 2


def test_a_golf_leg_ends_with_leg_won_after_the_last_hole():
    practice = rounds_game("golf", 1)
    practice.set_rounds(golf_holes=9)
    for hole in range(1, 9):
        throw(practice, f"T{hole}")
    events = throw(practice, "D9")
    assert events == [
        (
            "leg_won",
            {
                "game": "golf",
                "player": 1,
                "name": None,
                "players": 1,
                "darts": 9,
                "points": 10,
                "legs": 1,
                "sets": 0,
                "match": False,
            },
        )
    ]
    assert practice.legs[0]["points"] == 10 and practice.legs_total == 1


def test_count_up_rounds_are_an_option_and_restart_the_game():
    practice = rounds_game("count_up", 1)
    practice.set_rounds(count_up_rounds=3)
    assert practice.snapshot()["rounds"] == 3 and practice.party.rounds == 3
    practice.set_rounds(count_up_rounds=99)
    assert practice.count_up_rounds == 3
    throw(practice, "T20")
    throw(practice, "T20")
    events = throw(practice, "T20")
    assert events[0][0] == "leg_won" and events[0][1]["points"] == 180
    # Another game keeps the options; the stored game brings them back.
    practice.play("baseball")
    restored = PracticeGame()
    restored.restore(json.loads(json.dumps(practice.stored())))
    assert restored.count_up_rounds == 3 and restored.golf_holes == 9
    assert restored.party.kind == "baseball" and restored.party.rounds == 9
    restored.restore({"game": "count_up", "count_up_rounds": 0, "golf_holes": 10})
    assert restored.count_up_rounds == 8 and restored.golf_holes == 9


@settings(max_examples=60, deadline=None)
@given(
    kind=st.sampled_from(["golf", "baseball", "count_up"]),
    players=st.integers(1, 4),
    visits=st.lists(
        st.lists(st.sampled_from(["T1", "D2", "S3", "S20", "T20", "MISS"]), max_size=3),
        max_size=120,
    ),
)
def test_rounds_games_always_end_with_one_winner(kind, players, visits):
    practice = rounds_game(kind, players)
    for visit in visits:
        before = practice.legs_total
        events = throw(practice, *visit) if visit else []
        won = [event for event in events if event[0] == "leg_won"]
        assert len(won) == practice.legs_total - before <= 1
        snapshot = practice.snapshot()
        assert all(score["points"] >= 0 for score in snapshot["scores"])
        assert snapshot["round"] >= 1
