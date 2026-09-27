"""Rules of the practice game: the bull-off dart, teams with the bot, an
aborted leg, the Cricket target, Cut-Throat, Killer, the bot's level and
routes, and player names."""

import json

import pytest

from custom_components.autodarts.checkout import checkout
from custom_components.autodarts.cricket import (
    CRICKET_NUMBERS,
    next_target,
    play_visit,
)
from custom_components.autodarts.practice import PracticeGame
from custom_components.autodarts.profiles import clean_name, valid_name

from .test_party import game_of, kinds
from .test_practice import dart, throw

CLOSED = [3] * 7
NAMES = ["Alex", "Sam", "Kim", "Lea"]


def bulling(kind: int | str = 501, start: int = 0) -> PracticeGame:
    game = PracticeGame()
    game.bull_off = True
    game.set_players(2)
    game.set_start(0, start)
    game.play(kind)
    return game


# -- the bull-off -------------------------------------------------------------


# A bullseye would win from 50 and bust from 40, were it a scoring dart.
@pytest.mark.parametrize("start", [0, 50, 40])
def test_the_bull_off_dart_scores_nothing_in_x01(start):
    game = bulling(start=start)
    game.track([dart("BULL")], [(0.0, 0.0)])
    snapshot = game.snapshot()
    begin = start or 501
    assert (
        snapshot["remaining"] == begin and snapshot["scores"][0]["remaining"] == begin
    )
    assert not snapshot["won"] and not snapshot["bust"]
    assert snapshot["visit"] == [] and snapshot["darts"] == 0
    assert snapshot["average"] is None and snapshot["scores"][0]["average"] is None
    assert snapshot["checkout"] is None and snapshot["setup"] is None
    # The bull-off itself shows the dart.
    assert snapshot["bull_off"]["throws"][0]["hit"] == "BULL"
    game.finish_visit()
    game.track([])
    # Player 2's dart at the bull is no dart of player 1's either.
    game.track([dart("T20")], [(0.0, 0.6)])
    snapshot = game.snapshot()
    assert snapshot["remaining"] == begin and snapshot["visit"] == []


def test_the_bull_off_dart_marks_nothing_in_cricket_or_a_party_game():
    game = bulling("cricket")
    game.track([dart("T20")], [(0.0, 0.6)])
    snapshot = game.snapshot()
    assert snapshot["scores"][0]["marks"] == [0] * 7 and snapshot["points"] == 0
    assert snapshot["target"] is None and snapshot["visit"] == []
    assert snapshot["mpr"] is None
    party = bulling("shanghai")
    party.track([dart("S1")], [(0.0, 0.6)])
    assert party.snapshot()["visit"] == [] and party.snapshot()["points"] == 0


def test_the_bull_off_dart_does_not_begin_the_leg():
    game = bulling()
    game.track([dart("BULL")], [(0.0, 0.0)])
    # Double out still changes the leg at once.
    game.set_option("double_out", False)
    assert game.double_out is False and game.double_out_next is None


# -- teams ------------------------------------------------------------------------


def test_a_team_with_the_bot_has_no_name():
    game = PracticeGame()
    for index, name in enumerate(NAMES):
        game.set_name(index, name)
    game.teams = True
    game.set_players(3)
    game.set_bot(60)
    game.play(301)
    assert game.bot_seat == 3
    # Lea's name stays in the fourth seat, but the bot plays there.
    assert [team["name"] for team in game.snapshot()["teams"]] == [
        "Alex & Kim",
        None,
    ]
    ((kind, turn),) = throw(game, "T20")
    assert kind == "turn_changed" and turn["name"] == "Sam"
    assert turn["team"] == 2 and turn["team_name"] is None


# -- an aborted leg -------------------------------------------------------------------


def test_a_new_leg_takes_back_what_the_aborted_leg_added_to_the_match():
    game = PracticeGame()
    game.set_players(2)
    game.set_format(legs=2)
    game.play(301)
    throw(game, "T20", "T20", "T20")
    throw(game, "S1", "S1", "S1")
    game.new_leg()
    assert [player.match_darts for player in game.players] == [0, 0]
    assert [player.match_points for player in game.players] == [0, 0]
    assert game.tallies[0].scores_180 == 0 and game.players[0].scores_180 == 0
    # A booked leg stays in the match.
    throw(game, "T20", "T20", "T20")
    throw(game, "S1", "S1", "S1")
    throw(game, "T20", "T11", "D14")
    assert game.players[0].legs == 1 and game.tallies[0].scores_180 == 1
    # Player 2 starts leg 2; that leg is aborted after one visit.
    throw(game, "T20", "T20", "S20")
    assert game.tallies[1].scores_140 == 1
    game.new_leg()
    assert game.players[1].match_darts == 3 and game.players[1].match_points == 3
    assert game.tallies[1].scores_140 == 0
    assert game.players[0].match_darts == 6 and game.tallies[0].scores_180 == 1
    # Cricket takes the marks back.
    cricket = PracticeGame()
    cricket.play("cricket")
    throw(cricket, "T20", "T19")
    cricket.new_leg()
    assert cricket.players[0].match_marks == 0 and cricket.players[0].match_darts == 0


# -- Cricket and Cut-Throat ---------------------------------------------------------


def test_the_cricket_target_is_a_number_to_score_on_once_everything_is_closed():
    game = PracticeGame()
    game.set_players(2)
    game.play("cricket")
    game.players[0].marks = list(CLOSED)
    game.players[1].marks = [3, 0, 3, 3, 0, 3, 3]
    game.players[1].points = 60
    # Behind with everything closed: the highest number the opponent needs.
    assert game.snapshot()["target"] == "T19"
    # Cut-Throat: a number the player with the fewest points still has open.
    game = PracticeGame()
    game.set_players(3)
    game.play("cut_throat")
    game.players[0].marks, game.players[0].points = list(CLOSED), 50
    game.players[1].marks, game.players[1].points = [3, 3, 0, 3, 3, 3, 3], 40
    game.players[2].marks, game.players[2].points = [0] * 7, 70
    assert game.snapshot()["target"] == "T18"
    # Nothing open anywhere: no target.
    assert next_target(CLOSED, CRICKET_NUMBERS, [CLOSED], [0]) is None
    assert next_target(CLOSED) is None


def test_points_given_in_cut_throat_can_win_the_leg_for_another_player():
    visit = play_visit(
        [3, 0, 0, 0, 0, 0, 0],
        70,
        [dart("S1"), dart("D20"), dart("S5")],
        [list(CLOSED), [0, 3, 3, 3, 3, 3, 3]],
        [50, 40],
        cut_throat=True,
    )
    # The D20 gives the second player 40: the first, closed with 50, wins.
    assert visit.other_won == 0 and not visit.won and visit.darts == 2
    assert visit.others == [50, 80]
    # In Cricket, the points of a dart go to the thrower: nobody else wins.
    cricket = play_visit([3, 0, 0, 0, 0, 0, 0], 0, [dart("D20")], [list(CLOSED)], [50])
    assert cricket.other_won is None


def test_a_cut_throat_leg_goes_to_the_player_the_visit_leaves_lowest():
    game = PracticeGame()
    for index, name in enumerate(NAMES[:3]):
        game.set_name(index, name)
    game.set_players(3)
    game.set_format(legs=2)
    game.play("cut_throat")
    alex, sam, kim = game.players
    alex.marks, alex.points, alex.darts, alex.marks_hit = list(CLOSED), 50, 30, 21
    sam.marks, sam.points = [0, 3, 3, 3, 3, 3, 3], 40
    kim.marks, kim.points = [3, 0, 0, 0, 0, 0, 0], 70
    game.current = 2
    events = game.track([dart("D20")])
    ((kind, won),) = events
    assert kind == "leg_won" and won["name"] == "Alex" and won["player"] == 1
    assert won["darts"] == 30 and won["points"] == 50 and won["mpr"] == 2.1
    assert game.snapshot()["target"] is None
    # Kim's later darts change nothing: the leg is decided.
    assert game.track([dart("D20"), dart("S15")]) == []
    game.finish_visit()
    assert game.legs[0]["name"] == "Alex" and game.legs[0]["darts"] == 30
    assert game.players[0].legs == 1 and game.players[2].match_darts == 1
    assert game.current == 1


# -- Killer --------------------------------------------------------------------------


def test_killer_announces_lives_instead_of_points():
    game = game_of("killer", 2, p1="Alex", p2="Sam")
    game.party.numbers = [7, 12]
    game.party.killers = [True, False]
    game.party.lives = [3, 2]
    ((kind, turn),) = throw(game, "D12")
    assert kind == "turn_changed" and turn["player"] == 2
    assert turn["lives"] == 1 and turn["killer"] is False and "points" not in turn
    throw(game, "S1")
    events = throw(game, "D12")
    assert kinds(events) == ["leg_won", "match_won"]
    won = events[0][1]
    assert won["lives"] == 3 and won["killer"] is True and "points" not in won


def test_other_party_games_announce_points():
    game = game_of("shanghai", 2)
    ((_, turn),) = throw(game, "S1")
    assert turn["points"] == 0 and "lives" not in turn


# -- the bot -------------------------------------------------------------------------


def test_a_new_bot_level_keeps_the_match_and_the_training_game():
    game = PracticeGame()
    game.set_bot(60)
    game.play(501)
    assert game.bot_seat == 1
    throw(game, "T20", "T20", "T20")
    game.set_bot(60)
    game.set_bot(80)
    # The bot stays in its seat: the same match, at the new level.
    assert game.players[0].remaining == 321 and game.bot_level == 80
    # The bot leaving starts a new match.
    game.set_bot(0)
    assert len(game.players) == 1 and game.players[0].remaining == 501
    game.play("doubles")
    throw(game, "D1")
    game.set_bot(60)
    assert game.drills["doubles"].index == 1
    game.set_players(2)
    game.play("shanghai")
    throw(game, "S1")
    game.set_bot(0)
    assert game.party.points == [1, 0]


def test_the_bot_seat_shows_the_usual_checkout_route():
    game = PracticeGame()
    game.personal_routes = True
    game.set_name(0, "Alex")
    game.doubles.record([("D8", True)] * 10)
    game.set_bot(60)
    game.play(501)
    game.players[0].remaining = game.players[1].remaining = 41
    # Alex's route goes over the strongest double at the board ...
    assert game.snapshot()["checkout"] == "25 D8"
    # ... but the bot aims at the usual route, and the cards show it.
    ((_, turn),) = throw(game, "S1", "S1", "S1")
    assert turn["bot"] and turn["checkout"] == " ".join(checkout(41)) == "S1 D20"
    assert game.snapshot()["checkout"] == "S1 D20"


# -- names and storage ---------------------------------------------------------------


def test_player_names_lose_template_and_control_characters():
    assert valid_name("Alex") and valid_name("Zoë-Marie O'Neil")
    for name in ("{{ x }}", "50%", "#1", "A\x07", "Tab\tbed", "\x85"):
        assert not valid_name(name), name
    assert clean_name("  {{ Alex }}\t ") == "Alex"
    assert clean_name("A" * 30 + "{") == "A" * 20
    game = PracticeGame()
    game.set_name(0, "Kim{{x}}")
    assert game.names[0] == "Kimx"
    game.restore({"game": 501, "names": ["{%Lea%}", 5, "#"]})
    assert game.names == ["Lea", "", "", ""]


@pytest.mark.parametrize("kind", [["cricket"], {"cricket": 1}, 5.5, None])
def test_a_stored_game_of_the_wrong_type_is_no_game(kind):
    game = PracticeGame()
    game.restore(json.loads(json.dumps({"game": kind, "drill": ["doubles"]})))
    assert game.kind is None and game.cricket is None and game.drill is None


def test_a_party_leg_passed_to_its_end_survives_a_restart():
    game = PracticeGame()
    game.set_rounds(count_up_rounds=1)
    game.play("count_up")
    events = game.finish_visit(empty=True)
    assert events[0][0] == "leg_won" and events[0][1]["darts"] == 0
    restored = PracticeGame()
    restored.restore(json.loads(json.dumps(game.stored())))
    assert restored.legs == game.legs and len(restored.legs) == 1
    # Any other leg without darts is no leg.
    restored.restore(
        {
            "game": 501,
            "legs": [
                {"game": 501, "darts": 0},
                {"game": "count_up", "darts": -1},
            ],
        }
    )
    assert restored.legs == []


@pytest.mark.parametrize(
    ("kind", "on_board", "counted"),
    [
        (101, "T20", lambda game: game.snapshot()["remaining"] == 101),
        (
            "around_the_clock",
            "S1",
            lambda game: game.snapshot()["drill"]["progress"] == 0,
        ),
    ],
)
def test_darts_on_the_board_at_a_new_leg_count_after_an_undo_neither(
    kind, on_board, counted
):
    """Darts that were on the board when a leg or a drill began count for no
    visit, also when that visit is undone and booked again."""
    game = PracticeGame()
    game.play(kind)
    game.track([dart(on_board)])
    game.new_leg()
    saved = game.checkpoint()
    game.finish_visit()
    assert counted(game)
    game.rewind(saved, [dart(on_board)], [None])
    game.finish_visit()
    assert counted(game)
