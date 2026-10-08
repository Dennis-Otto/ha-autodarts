"""Cricket: marks, points on numbers others need, winning and whole matches."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.cricket import (
    CRICKET_NUMBERS,
    marks_per_round,
    next_target,
    play_visit,
)
from custom_components.autodarts.practice import MAX_PLAYERS, PracticeGame

from .local_helpers import dart, throw

OPEN = [0] * 7
CLOSED = [3] * 7


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def test_marks_close_a_number_and_extra_marks_score_while_others_need_it():
    marks, points, count, won, counted, *_ = play_visit(
        OPEN, 0, darts("T20", "T20"), [OPEN], [0]
    )
    assert marks == [3, 0, 0, 0, 0, 0, 0] and points == 60
    assert (count, won, counted) == (2, False, 6)
    # Nobody else needs the 20 any more: extra marks neither score nor count.
    marks, points, _, _, counted, *_ = play_visit(
        OPEN, 0, darts("T20", "T20"), [[3, 0, 0, 0, 0, 0, 0]], [0]
    )
    assert points == 0 and counted == 3


def test_the_bull_counts_two_marks_and_other_beds_none():
    marks, points, _, _, counted, *_ = play_visit(
        [0, 0, 0, 0, 0, 0, 2], 0, darts("BULL", "25", "S14", "MISS"), [OPEN], [0]
    )
    assert marks[6] == 3 and points == 50 and counted == 3


def test_closing_everything_wins_only_without_fewer_points():
    almost = [3, 3, 3, 3, 3, 3, 2]
    assert play_visit(almost, 0, darts("25"), [OPEN], [40])[3] is False
    # Scoring on the 20, which the other player still needs, catches up.
    marks, points, count, won, *_ = play_visit(
        almost, 0, darts("S20", "T20", "25", "S19"), [OPEN], [40]
    )
    assert (points, count, won) == (80, 3, True) and marks == CLOSED
    # Playing alone, closing everything wins.
    assert play_visit(almost, 0, darts("MISS", "25"), [], [])[1:4] == (0, 2, True)


def test_marks_per_round_and_the_next_target():
    assert marks_per_round(9, 3) == 9.0 and marks_per_round(7, 6) == 3.5
    assert marks_per_round(0, 0) is None
    assert next_target(OPEN) == "T20"
    assert next_target([3, 3, 1, 0, 0, 0, 0]) == "T18"
    assert next_target([3, 3, 3, 3, 3, 3, 0]) == "BULL"
    assert next_target(CLOSED) is None


def cricket(players: int = 1, legs: int = 1, sets: int = 1) -> PracticeGame:
    game = PracticeGame()
    game.play("cricket")
    game.set_players(players)
    game.set_format(legs, sets)
    return game


DENNIS = {"game": "cricket", "player": 1, "name": "Dennis", "players": 2}
LEA = {"game": "cricket", "player": 2, "name": "Lea", "players": 2}


def test_players_take_turns_and_score_on_open_numbers():
    game = cricket(2)
    game.set_name(0, "Dennis")
    game.set_name(1, "Lea")
    game.track(darts("T20", "T20"))
    snapshot = game.snapshot()
    assert snapshot["game"] == "cricket" and snapshot["remaining"] is None
    assert snapshot["points"] == 60 and snapshot["target"] == "T19"
    assert snapshot["mpr"] == 9.0 and snapshot["numbers"] == list(CRICKET_NUMBERS)
    assert snapshot["scores"][0]["marks"] == [3, 0, 0, 0, 0, 0, 0]
    assert throw(game, "T20", "T20", "S19") == [
        (
            "turn_changed",
            {**LEA, "remaining": None, "checkout": None, "setup": None, "points": 0},
        )
    ]
    assert throw(game, "T20") == [
        (
            "turn_changed",
            {
                **DENNIS,
                "remaining": None,
                "checkout": None,
                "setup": None,
                "points": 60,
            },
        )
    ]
    scores = game.snapshot()["scores"]
    assert [(score["marks"][:2], score["points"]) for score in scores] == [
        ([3, 1], 60),
        ([3, 0], 0),
    ]
    # Marks per round of the match: 7 in 3 darts, and 3 in Lea's only dart.
    assert scores[0]["mpr"] == 7.0 and scores[1]["mpr"] == 9.0
    # Lea has closed the 20: Dennis scores no more on it.
    throw(game, "T20")
    assert game.snapshot()["scores"][0]["points"] == 60


def test_the_last_mark_wins_the_leg_and_the_match():
    game = cricket(2)
    game.players[0].marks = [3, 3, 3, 3, 3, 3, 1]
    game.players[0].points = 45
    game.players[0].darts = 21
    game.players[0].marks_hit = 19
    game.players[1].points = 40
    events = throw(game, "BULL", "T20")
    assert [kind for kind, _ in events] == ["leg_won", "match_won"]
    won = dict(events)
    assert won["leg_won"]["darts"] == 22 and won["leg_won"]["points"] == 45
    assert won["leg_won"]["mpr"] == round(21 * 3 / 22, 2)
    assert won["leg_won"]["match"] is True and won["match_won"]["sets"] == 1
    assert won["match_won"]["legs"] == 1 and won["match_won"]["scores"] == [
        {"player": 1, "name": None, "legs": 1, "sets": 1},
        {"player": 2, "name": None, "legs": 0, "sets": 0},
    ]
    snapshot = game.snapshot()
    assert snapshot["winner"] == 1 and snapshot["target"] is None
    assert game.legs[0]["game"] == "cricket" and game.legs[0]["points"] == 45
    # Cricket legs count as legs played, but leave the X01 statistics alone.
    assert game.legs_total == 1 and game.leg_stats == []
    # The next dart starts a new match.
    game.track(darts("S20"))
    assert game.snapshot()["winner"] is None
    assert game.snapshot()["scores"][0]["marks"][0] == 1


def test_a_corrected_winning_dart_takes_the_win_back():
    game = cricket()
    game.players[0].marks = [3, 3, 3, 3, 3, 3, 2]
    assert [kind for kind, _ in game.track(darts("25"))] == ["leg_won"]
    # The board corrects the dart to a 5: no win, and nothing to announce.
    assert game.track(darts("S5")) == []
    assert game.snapshot()["won"] is False and game.snapshot()["target"] == "BULL"
    assert [kind for kind, _ in game.track(darts("S5", "25"))] == ["leg_won"]


def test_fewer_points_keep_the_leg_open():
    game = cricket(2)
    game.players[0].marks = [3, 3, 3, 3, 3, 3, 2]
    game.players[1].points = 40
    assert throw(game, "25", "S20")[0][0] == "turn_changed"
    assert game.players[0].points == 20 and game.winner is None


def test_playing_alone_closing_everything_wins_and_starts_the_next_leg():
    game = cricket()
    game.players[0].marks = [3, 3, 3, 3, 3, 0, 3]
    game.track(darts("T15"))
    assert game.snapshot()["won"] is True and game.snapshot()["target"] is None
    assert game.finish_visit() == [
        (
            "turn_changed",
            {
                "game": "cricket",
                "player": 1,
                "name": None,
                "players": 1,
                "remaining": None,
                "checkout": None,
                "setup": None,
                "points": 0,
            },
        )
    ]
    assert game.snapshot()["target"] == "T20" and len(game.legs) == 1
    assert game.legs[0]["mpr"] == 9.0


def test_cricket_survives_a_restart_and_invalid_marks_are_dropped():
    game = cricket(2)
    throw(game, "T20", "S19")
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.cricket and restored.stored() == game.stored()
    assert restored.snapshot()["scores"][0]["marks"][:2] == [3, 1]
    saved = game.stored()
    saved["players"][0]["marks"] = [9, "x", -1, 0, 0, 0, 0]
    saved["players"][1]["marks"] = [1, 2]
    restored.restore(saved)
    assert restored.players[0].marks == [0] * 7
    assert restored.players[1].marks == [0] * 7
    restored.play(301)
    assert not restored.cricket and restored.snapshot()["remaining"] == 301


BEDS = ["T20", "D19", "S18", "T17", "S16", "D15", "BULL", "25", "S5", "MISS"]


@given(
    st.integers(1, MAX_PLAYERS),
    st.lists(st.lists(st.sampled_from(BEDS), min_size=1, max_size=3), max_size=80),
)
def test_any_cricket_match_keeps_marks_and_points_consistent(players, visits):
    game = cricket(players)
    for visit in visits:
        before = game.snapshot()
        won = any(kind == "leg_won" for kind, _ in throw(game, *visit))
        snapshot = game.snapshot()
        for score in snapshot["scores"]:
            assert all(0 <= mark <= 3 for mark in score["marks"])
            assert score["points"] >= 0
            if snapshot["winner"] == score["player"]:
                assert score["marks"] == CLOSED
                assert all(
                    score["points"] >= other["points"] for other in snapshot["scores"]
                )
        if players > 1 and before["winner"] is None and not won:
            # Every visit passes the turn, unless it won a leg.
            assert snapshot["player"] == before["player"] % players + 1


def test_every_dart_says_what_it_counted_for():
    # The second T20 hits a number nobody needs any more, the S14 no number at all.
    visit = play_visit(
        OPEN, 0, darts("T20", "S14", "T20"), [[3, 0, 0, 0, 0, 0, 0]], [0]
    )
    assert visit.targets == ("20", None, None)
    assert play_visit(OPEN, 0, darts("T20", "T20"), [OPEN], [0]).targets == ("20", "20")
    # Points given away in Cut-Throat count, and a win ends the list.
    almost = [3, 3, 3, 3, 3, 3, 2]
    visit = play_visit(
        almost, 0, darts("T20", "25", "T19"), [OPEN], [0], cut_throat=True
    )
    assert visit.won and visit.targets == ("20", "25")
