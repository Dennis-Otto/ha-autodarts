"""The practice game with the bot in the last seat, passes and undone visits."""

import json

from custom_components.autodarts.bot import DEFAULT_DELAY
from custom_components.autodarts.practice import PracticeGame, valid_delay

from .test_practice import dart, throw


def against_the_bot(game: int | str = 301, level: int = 60, humans: int = 1):
    practice = PracticeGame()
    practice.set_name(0, "Alex")
    practice.set_name(1, "Lea")
    practice.set_players(humans)
    practice.set_bot(level)
    practice.play(game)
    return practice


def test_the_bot_takes_the_seat_after_the_players():
    game = against_the_bot()
    assert len(game.players) == 2 and game.humans == 1 and game.bot_seat == 1
    snapshot = game.snapshot()
    assert snapshot["bot"] == {"player": 2, "level": 60}
    # The bot's seat has no name, even when the seat had one before.
    assert [score["name"] for score in snapshot["scores"]] == ["Alex", None]
    assert [score.get("bot") for score in snapshot["scores"]] == [None, True]
    assert not game.bot_up
    ((kind, turn),) = throw(game, "T20")
    assert kind == "turn_changed" and turn["bot"] is True and turn["name"] is None
    assert game.bot_up and game.thrower is None
    # Everybody else takes turns as before.
    game.set_players(2)
    assert len(game.players) == 3 and game.bot_seat == 2
    # With the bot, three players at most.
    game.set_players(4)
    assert game.humans == 3 and len(game.players) == 4


def test_the_bot_plays_x01_and_the_cricket_games_only():
    game = against_the_bot("cricket")
    assert game.bot_seat == 1
    game.play("shanghai")
    assert game.bot_seat is None and len(game.players) == 1
    game.play("around_the_clock")
    assert game.bot_seat is None
    game.play(501)
    assert game.bot_seat == 1 and game.snapshot()["bot"]["player"] == 2
    # Level 0 sends the bot home; an impossible level changes nothing.
    game.set_bot(0)
    assert game.bot_seat is None and len(game.players) == 1
    game.set_bot(19)
    assert game.bot_level == 0
    game.play(0)
    assert game.snapshot()["bot"] is None


def test_the_bot_throws_its_dart_of_the_bull_off():
    game = PracticeGame()
    game.bull_off = True
    game.set_bot(80)
    game.play(501)
    assert game.bulling is not None and not game.bot_up
    game.track([dart("S20")], [(0.0, 0.5)])
    game.finish_visit()
    assert game.bot_up
    throws = game.snapshot()["bull_off"]["throws"]
    assert [item.get("bot") for item in throws] == [None, True]


def test_the_bots_darts_count_for_nobody():
    game = against_the_bot(301, humans=1)
    game.players[1].remaining = 40
    # The bot checks out, and its darts at the double count for nobody.
    throw(game, "S1", "S1", "S1")
    throw(game, "S20", "D10")
    assert game.leg_stats[0]["checkouts"] == 0
    assert game.leg_stats[0]["at_double"] == 0
    assert game.doubles.snapshot()["attempts"] == 0
    assert game.legs[0]["bot"] is True and game.legs[0]["name"] is None
    # No profile for the bot, and the match result for the player.
    assert list(game.profiles.players) == ["alex"]
    assert game.profiles.players["alex"].matches_played == 1
    match = game.profiles.matches[0]
    assert match["players"][1] == {
        "name": None,
        "legs": 1,
        "sets": 1,
        "match_legs": 1,
        "bot": True,
        "average": 60.0,
    }
    assert game.profiles.head_to_head == {}


def test_the_player_checks_out_against_the_bot():
    game = against_the_bot(301)
    game.players[0].remaining = 40
    throw(game, "S20", "D10")
    assert game.leg_stats[0] == {
        "first9_points": 40,
        "first9_darts": 2,
        "at_double": 2,
        "checkouts": 1,
    }


def test_the_bot_survives_a_restart():
    game = against_the_bot(501, level=95)
    game.bot_delay = 1.5
    game.manual_entry = True
    saved = json.loads(json.dumps(game.stored()))
    restored = PracticeGame()
    restored.restore(saved)
    assert (restored.bot_level, restored.bot_delay) == (95, 1.5)
    assert restored.manual_entry is True and restored.bot_seat == 1
    assert restored.stored() == saved
    # Values of another kind fall back to the defaults.
    restored.restore({**saved, "bot_level": 19, "bot_delay": "slow"})
    assert (restored.bot_level, restored.bot_delay) == (0, DEFAULT_DELAY)
    restored.restore({**saved, "bot_level": True, "bot_delay": 11})
    assert (restored.bot_level, restored.bot_delay) == (0, DEFAULT_DELAY)
    # Stores of earlier versions know no bot.
    old = PracticeGame()
    old.restore({"game": 501})
    assert (old.bot_level, old.bot_delay, old.manual_entry) == (0, DEFAULT_DELAY, False)


def test_valid_delays():
    assert all(valid_delay(value) for value in (0, 0.5, 2, 10, 10.0))
    assert not any(valid_delay(value) for value in (-0.5, 10.5, True, "2", None))


def test_a_visit_without_darts_passes_in_x01_and_cricket():
    game = against_the_bot(301)
    assert game.passes()
    ((kind, turn),) = game.finish_visit(empty=True)
    assert kind == "turn_changed" and turn["player"] == 2
    assert game.players[0].darts == 0 and game.players[0].remaining == 301
    game = against_the_bot("cricket")
    assert game.finish_visit(empty=True)[0][1]["player"] == 2
    # Without the empty flag, nothing happens as before.
    assert game.finish_visit() == []


def test_no_pass_while_choosing_in_the_bull_off_training_games_or_after_the_match():
    game = PracticeGame()
    game.set_players(2)
    game.play("killer")
    # Killer passes only once every player has a number.
    assert not game.passes() and game.finish_visit(empty=True) == []
    game.party.numbers = [20, 3]
    assert game.passes()
    ((kind, turn),) = game.finish_visit(empty=True)
    assert kind == "turn_changed" and turn["player"] == 2
    assert turn["lives"] == 3 and turn["killer"] is False and "points" not in turn
    game.set_players(1)
    game.play("killer")
    assert not game.passes()
    game.play("around_the_clock")
    assert not game.passes()
    game.bull_off = True
    game.set_players(2)
    game.play(301)
    assert not game.passes() and game.finish_visit(empty=True) == []
    game.bull_off = False
    game.play(301)
    game.players[0].remaining = 40
    throw(game, "D20")
    assert game.winner == 0 and not game.passes()
    assert game.finish_visit(empty=True) == []


def test_a_checkpoint_brings_the_game_back_with_its_visit():
    game = against_the_bot(301)
    game.set_format(legs=2)
    game.players[0].remaining = 40
    checkpoint = game.checkpoint()
    visit = [dart("S20"), dart("D10")]
    for count in (1, 2):
        game.track(visit[:count])
    assert game.finish_visit()[0][0] == "turn_changed"
    assert game.players[0].legs == 1 and len(game.legs) == 1
    game.track([])
    game.rewind(checkpoint, visit, [None, (0.0, 0.97)])
    # Before the booking, with the darts thrown again and the win known.
    assert game.players[0].legs == 0 and game.legs == []
    snapshot = game.snapshot()
    assert snapshot["won"] is True and snapshot["visit"] == ["S20", "D10"]
    assert game.track(visit) == []
    # A correction that changes the outcome announces again.
    assert game.track([dart("S20"), dart("S10")]) == []
    assert game.track(visit)[0][0] == "leg_won"
    # A checkpoint is a copy: the game goes on independently.
    checkpoint["players"][0]["remaining"] = 7
    assert game.players[0].remaining == 40


def test_a_checkpoint_of_cricket_goes_back_from_any_game():
    game = against_the_bot("cricket")
    checkpoint = game.checkpoint()
    throw(game, "T20")
    game.play(301)
    game.rewind(checkpoint, [dart("T20")], [None])
    assert game.cricket == "cricket" and game.game == 0
    assert game.snapshot()["scores"][0]["marks"][0] == 3
