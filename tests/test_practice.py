"""X01 practice games: counting down, busts, checkouts, corrections and matches."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.checkout import checkout
from custom_components.autodarts.practice import (
    GAMES,
    MAX_PLAYERS,
    PARTY_PLAYERS,
    PracticeGame,
)

from .local_helpers import PLAYER_1, dart, match, playing, throw, win_leg


def test_a_leg_counts_down_and_suggests_the_checkout():
    game = playing(501)
    assert throw(game, "T20", "T20", "T20") == []
    snapshot = game.snapshot()
    assert snapshot["remaining"] == 321 and snapshot["darts"] == 3
    assert snapshot["average"] == 180.0 and snapshot["checkout"] is None
    game.restore({"game": 501, "remaining": 100})
    assert game.snapshot()["checkout"] == "T20 D20"
    game.track([dart("S20")])
    snapshot = game.snapshot()
    assert snapshot["remaining"] == 80 and snapshot["visit"] == ["S20"]
    assert snapshot["checkout"] == " ".join(checkout(80, 2))


def test_a_bust_keeps_the_score_of_the_visit_start():
    game = playing(301, 32)
    events = throw(game, "S20", "S20", "S5")
    assert events == [("bust", {**PLAYER_1, "remaining": 32})]
    assert game.snapshot()["remaining"] == 32
    # One left, or zero without a double, is a bust with double out.
    assert throw(game, "S20", "S11") == [("bust", {**PLAYER_1, "remaining": 32})]
    assert throw(game, "S16", "S16") == [("bust", {**PLAYER_1, "remaining": 32})]
    # Darts after a bust are not part of the visit.
    snapshot = game.snapshot()
    assert snapshot["remaining"] == 32 and snapshot["darts"] == 6
    assert snapshot["checkout"] == "D16"


def test_the_bust_shows_until_the_darts_are_pulled():
    game = playing(301, 32)
    game.track([dart("T20")])
    snapshot = game.snapshot()
    assert snapshot["bust"] and snapshot["remaining"] == 32
    assert snapshot["checkout"] == "D16"


def test_a_double_wins_the_leg_and_the_next_leg_starts():
    game = playing(301, 40)
    events = throw(game, "S20", "D10", "T20")
    assert events == [
        (
            "leg_won",
            {
                **PLAYER_1,
                "darts": 2,
                "average": 451.5,
                "checkout": 40,
                "start": 301,
                "double_out": True,
                "double_in": False,
                "legs": 1,
                "sets": 0,
                "match": False,
            },
        )
    ]
    assert game.snapshot()["remaining"] == 301
    assert game.legs[0]["darts"] == 2 and game.legs[0]["checkout"] == 40
    assert throw(game, "BULL") == []
    assert game.snapshot()["remaining"] == 251


def test_without_double_out_any_bed_finishes():
    game = playing(301, 20, double_out=False)
    game.track([dart("S20")])
    assert game.snapshot()["won"] and game.snapshot()["checkout"] is None
    game.finish_visit()
    assert game.legs[0]["checkout"] == 20


def test_corrections_revise_the_visit():
    game = playing(301, 40)
    assert game.track([dart("D20")])[0][0] == "leg_won"
    assert game.track([dart("S20")]) == []
    assert game.snapshot()["remaining"] == 20
    assert game.track([dart("S20"), dart("D10")])[0][0] == "leg_won"


def test_darts_already_thrown_do_not_count_for_a_new_leg():
    game = PracticeGame()
    assert game.track([dart("T20")]) == []
    assert game.snapshot() == {
        "game": None,
        "double_out": True,
        "players": 1,
        "legs_to_win": 1,
        "sets_to_win": 1,
        "legs": [],
        "summary": None,
        "drill": None,
        "double_in": False,
        "bull_off": None,
        "teams": None,
        "bot": None,
    }
    game.play(501)
    game.track([dart("T20"), dart("T19")])
    assert game.snapshot()["remaining"] == 444
    game.new_leg()
    game.track([dart("T20"), dart("T19"), dart("S1")])
    assert game.snapshot()["remaining"] == 500
    game.play(0)
    assert game.snapshot()["game"] is None


def test_restore_keeps_valid_data_only():
    game = PracticeGame()
    game.restore({"game": 501, "remaining": 88, "darts": 21, "double_out": False})
    # Version 1.2 stored one player at the top level.
    stored = game.stored()
    assert stored["players"] == [
        {
            "remaining": 88,
            "darts": 21,
            "points": 0,
            "legs": 0,
            "sets": 0,
            "match_legs": 0,
            "match_darts": 0,
            "match_points": 0,
            "first9_points": 0,
            "first9_darts": 0,
            "at_double": 0,
            "marks": [0] * 7,
            "marks_hit": 0,
            "match_marks": 0,
            "opened": False,
            "scores_100": 0,
            "scores_140": 0,
            "scores_180": 0,
        }
    ]
    assert stored["double_out"] is False and stored["names"] == [""] * PARTY_PLAYERS
    game.restore({"game": 401, "remaining": 600, "legs": [{"game": 501, "darts": 0}]})
    assert game.game == 501 and game.snapshot()["remaining"] == 501
    assert game.legs == []
    game.restore("broken")
    assert game.game == 501


@given(
    st.sampled_from(GAMES),
    st.booleans(),
    st.lists(
        st.lists(
            st.sampled_from(
                ["T20", "T19", "S20", "S1", "D16", "D1", "BULL", "25", "MISS"]
            ),
            min_size=1,
            max_size=3,
        ),
        max_size=60,
    ),
)
def test_any_visits_keep_the_leg_consistent(start, double_out, visits):
    game = playing(start, double_out=double_out)
    for visit in visits:
        throw(game, *visit)
        remaining = game.snapshot()["remaining"]
        assert 0 < remaining <= start
        assert not double_out or remaining != 1
    for leg in game.legs:
        # Nobody finishes faster than three perfect visits per 180 points.
        assert leg["darts"] >= -(-start // 60)
        assert leg["average"] == round(start * 3 / leg["darts"], 2)


DENNIS = {"game": 301, "player": 1, "name": "Dennis", "players": 2}
LEA = {"game": 301, "player": 2, "name": "Lea", "players": 2}


def test_players_take_turns_and_a_bust_passes_the_turn():
    game = match(2, p1="Dennis", p2=" Lea ")
    assert throw(game, "T20", "T20", "T20") == [
        ("turn_changed", {**LEA, "remaining": 301, "checkout": None, "setup": None})
    ]
    throw(game, "S20")
    scores = game.snapshot()["scores"]
    assert [(score["name"], score["remaining"]) for score in scores] == [
        ("Dennis", 121),
        ("Lea", 281),
    ]
    assert scores[0]["average"] == 180.0 and scores[1]["average"] == 60.0
    # 121 - 120 leaves one: a bust, and the turn passes anyway.
    assert throw(game, "T20", "T20") == [
        ("bust", {**DENNIS, "remaining": 121}),
        ("turn_changed", {**LEA, "remaining": 281, "checkout": None, "setup": None}),
    ]
    assert game.snapshot()["player"] == 2


def test_legs_make_sets_and_sets_make_the_match():
    game = match(2, legs=2, sets=2)
    starters = []
    for leg in range(1, 5):
        starters.append(game.snapshot()["player"])
        events = win_leg(game, 1)
        kinds = [kind for kind, _ in events]
        if leg < 4:
            assert kinds == ["leg_won", "turn_changed"]
        else:
            assert kinds == ["leg_won", "match_won"]
    # The throw passes every leg, and the second set starts with player 2.
    assert starters == [1, 2, 2, 1]
    won = dict(events)
    assert won["leg_won"]["legs"] == 2 and won["leg_won"]["sets"] == 2
    assert won["match_won"]["player"] == 1 and won["match_won"]["sets"] == 2
    assert won["match_won"]["legs"] == 2
    assert won["leg_won"]["match"] is True
    snapshot = game.snapshot()
    assert snapshot["winner"] == 1 and snapshot["checkout"] is None
    assert [score["sets"] for score in snapshot["scores"]] == [2, 0]
    assert [score["legs"] for score in snapshot["scores"]] == [2, 0]
    assert [score["match_legs"] for score in snapshot["scores"]] == [4, 0]
    assert len(game.legs) == 4 and game.legs[0]["player"] == 1
    # The result stays until the next dart, which starts a new match.
    game.track([dart("S20")])
    snapshot = game.snapshot()
    assert snapshot["winner"] is None and snapshot["player"] == 1
    assert [score["remaining"] for score in snapshot["scores"]] == [281, 301]
    assert [score["sets"] for score in snapshot["scores"]] == [0, 0]


def test_a_set_won_resets_the_legs_of_everybody():
    game = match(2, legs=2, sets=3)
    game.players[1].legs = 1
    game.players[0].legs = 1
    game.players[0].remaining = 40
    events = throw(game, "D20")
    assert [kind for kind, _ in events] == ["leg_won", "turn_changed"]
    # The event tells the legs that won the set; the next set starts from zero.
    assert (events[0][1]["legs"], events[0][1]["sets"]) == (2, 1)
    assert [(player.legs, player.sets) for player in game.players] == [(0, 1), (0, 0)]


def test_the_throw_alternates_by_leg_within_a_set_and_by_set():
    game = match(2, legs=2, sets=2)
    starters = []
    for winner in (1, 1, 2, 1, 2, 1, 1):
        starters.append(game.snapshot()["player"])
        events = win_leg(game, winner)
    assert starters == [1, 2, 2, 1, 2, 1, 2]
    won = dict(events)["match_won"]
    assert (won["player"], won["legs"], won["sets"]) == (1, 2, 2)
    assert won["scores"] == [
        {"player": 1, "name": None, "legs": 2, "sets": 2},
        {"player": 2, "name": None, "legs": 0, "sets": 1},
    ]
    assert [player.match_legs for player in game.players] == [5, 2]

    three = match(3, legs=1, sets=3)
    starters = []
    for winner in (1, 1, 2, 3, 1):
        starters.append(three.snapshot()["player"])
        win_leg(three, winner)
    # One leg per set: every set starts with the next player.
    assert starters == [1, 2, 3, 1, 2]


def test_a_finished_match_keeps_the_legs_of_every_player():
    game = match(2, legs=3, p1="Alex", p2="Sam")
    for winner in (2, 1, 2, 1):
        win_leg(game, winner)
    events = dict(win_leg(game, 1))
    assert (events["leg_won"]["legs"], events["leg_won"]["sets"]) == (3, 1)
    assert events["match_won"]["scores"] == [
        {"player": 1, "name": "Alex", "legs": 3, "sets": 1},
        {"player": 2, "name": "Sam", "legs": 2, "sets": 0},
    ]
    scores = game.snapshot()["scores"]
    assert [(score["legs"], score["sets"]) for score in scores] == [(3, 1), (2, 0)]
    history = game.profiles.snapshot()["matches"][0]
    assert (history["legs_to_win"], history["sets_to_win"]) == (3, 1)
    assert [
        (player["name"], player["legs"], player["sets"], player["match_legs"])
        for player in history["players"]
    ] == [("Alex", 3, 1, 3), ("Sam", 2, 0, 2)]
    # The result survives a restart.
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.snapshot()["scores"] == scores


def test_a_store_without_the_set_starter_finds_it_from_the_legs():
    game = match(2, legs=3, sets=2)
    saved = game.stored()
    for key in ("set_starter", "bull_off_distance"):
        del saved[key]
    for player in saved["players"]:
        del player["match_legs"]
    # Player 2 throws first in the third leg of a set after two legs.
    saved["starter"] = 0
    saved["players"][0]["legs"], saved["players"][1]["legs"] = 1, 1
    game.restore(saved)
    assert game.set_starter == 0 and game.bull_off_distance is False
    saved["starter"] = 1
    saved["players"][1]["legs"] = 0
    game.restore(saved)
    assert game.set_starter == 0
    assert game.stored()["players"][0]["match_legs"] == 0


VERSION_1_5 = {
    "game": 501,
    "double_out": True,
    "double_in": False,
    "bull_off": True,
    "personal_routes": False,
    "doubles": {"D20": [3, 1]},
    "party": None,
    "bulling": {"order": [0, 1], "index": 1, "distances": {"0": 11.0}},
    "legs_to_win": 2,
    "sets_to_win": 2,
    "names": ["Alex", "Sam", "", ""],
    "players": [
        {"remaining": 501, "darts": 0, "points": 0, "legs": 1, "sets": 1},
        {"remaining": 501, "darts": 0, "points": 0, "legs": 0, "sets": 0},
    ],
    "current": 1,
    "starter": 1,
    "winner": None,
    "legs": [
        {"game": 501, "player": 1, "name": "Alex", "darts": 18, "checkout": 40},
    ],
    "leg_stats": [],
    "legs_total": 3,
    "drill": None,
    "drills": {},
    "profiles": {},
}


def test_a_store_of_version_1_5_restores_cleanly():
    game = PracticeGame()
    game.restore(VERSION_1_5)
    # The bull-off round starts again: the old store kept no beds.
    assert game.bulling is not None and game.bulling.index == 0
    assert game.bull_off_distance is False
    # Player 2 started the second leg of the second set, so player 1 the set.
    assert (game.starter, game.set_starter) == (1, 0)
    assert [player.match_legs for player in game.players] == [0, 0]
    stored = game.stored()
    assert stored["legs"] == VERSION_1_5["legs"] and stored["set_starter"] == 0
    # The match goes on under the new rules.
    game.bulling = None
    events = dict(win_leg(game, 2))
    assert (events["leg_won"]["legs"], events["leg_won"]["sets"]) == (1, 0)
    assert game.snapshot()["player"] == 1


def test_darts_beyond_the_third_do_not_count():
    game = playing(301)
    game.track([dart("T20"), dart("T20"), dart("T20"), dart("T20")])
    snapshot = game.snapshot()
    assert snapshot["remaining"] == 121 and snapshot["visit"] == ["T20"] * 3


def test_settings_start_a_new_match_and_survive_a_restart():
    game = match(3, legs=3, sets=2, p1="Dennis", p3="Max")
    throw(game, "T20")
    assert game.snapshot()["player"] == 2
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.stored() == game.stored()
    assert restored.snapshot()["scores"][0]["remaining"] == 241
    game.set_players(9)
    assert len(game.players) == 1 and game.snapshot()["remaining"] == 301
    game.set_format(legs=0, sets=99)
    assert (game.legs_to_win, game.sets_to_win) == (3, 2)
    game.set_name(7, "nobody")
    game.set_name(0, "A very long name that is cut")
    assert game.names[0] == "A very long name tha"


@given(
    st.integers(1, MAX_PLAYERS),
    st.integers(1, 3),
    st.integers(1, 2),
    st.lists(
        st.lists(
            st.sampled_from(["T20", "T19", "S20", "D20", "D16", "BULL", "MISS"]),
            min_size=1,
            max_size=3,
        ),
        max_size=80,
    ),
)
def test_any_match_keeps_turns_and_scores_consistent(players, legs, sets, visits):
    game = match(players, legs, sets)
    for visit in visits:
        before = game.snapshot()
        won = any(kind == "leg_won" for kind, _ in throw(game, *visit))
        snapshot = game.snapshot()
        assert 1 <= snapshot["player"] <= players
        if players > 1 and before["winner"] is None and not won:
            # Every visit passes the turn, unless it won a leg.
            assert snapshot["player"] == before["player"] % players + 1
        for score in snapshot["scores"]:
            if snapshot["winner"] == score["player"]:
                assert score["remaining"] == 0 and score["sets"] == sets
            else:
                assert 0 < score["remaining"] <= 301
                assert score["legs"] < legs or players == 1
                assert score["sets"] < sets or players == 1


def test_playing_alone_the_next_visit_is_announced_with_its_checkout():
    game = playing(301, 141)
    game.track([dart("T20")])
    assert game.finish_visit() == [
        (
            "turn_changed",
            {**PLAYER_1, "remaining": 81, "checkout": "T19 D12", "setup": None},
        )
    ]
    game.players[0].remaining = 40
    game.track([dart("D20")])
    # A won leg starts the next one.
    assert game.finish_visit() == [
        (
            "turn_changed",
            {**PLAYER_1, "remaining": 301, "checkout": None, "setup": None},
        )
    ]
