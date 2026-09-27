"""Double out switched during a leg: the leg keeps its rules, so none becomes unwinnable."""

import json

from custom_components.autodarts.practice import PracticeGame

from .test_practice import PLAYER_1, dart, match, playing, throw


def test_double_out_switched_on_while_a_player_stands_on_1_waits_for_the_next_leg():
    game = playing(301, 21, double_out=False)
    throw(game, "S20")
    assert game.snapshot()["remaining"] == 1
    game.set_option("double_out", True)
    # The switch shows the new rule; the leg in progress keeps single out.
    assert game.setting("double_out") is True
    assert game.double_out is False and game.snapshot()["double_out"] is False
    events = throw(game, "S1")
    assert events[0][0] == "leg_won" and events[0][1]["double_out"] is False
    # The next leg is played with double out.
    assert game.double_out is True and game.double_out_next is None
    assert game.snapshot()["double_out"] is True
    game.players[0].remaining = 21
    assert throw(game, "S20") == [("bust", {**PLAYER_1, "remaining": 21})]


def test_double_out_switched_off_during_a_leg_also_waits():
    game = playing(301)
    throw(game, "T20")
    game.set_option("double_out", False)
    assert game.setting("double_out") is False and game.double_out is True
    # Switching back before the leg ends leaves nothing to change.
    game.set_option("double_out", True)
    assert game.double_out_next is None and game.setting("double_out") is True
    game.set_option("double_out", False)
    game.new_leg()
    assert game.double_out is False and game.double_out_next is None


def test_double_out_applies_at_once_before_the_first_dart_and_between_matches():
    game = playing(301)
    game.set_option("double_out", False)
    assert game.double_out is False and game.double_out_next is None
    # A dart on the board before it counts starts the leg as well.
    game.track([dart("S5")])
    game.set_option("double_out", True)
    assert game.double_out is False and game.double_out_next is True
    game.play(301)
    assert game.double_out is True
    # A finished match, Cricket and the training games have no leg to keep.
    two = match(2)
    two.players[0].remaining = 40
    throw(two, "D20")
    assert two.winner == 0
    two.set_option("double_out", False)
    assert two.double_out is False
    two.play("cricket")
    two.set_option("double_out", True)
    assert two.double_out is True


def test_the_waiting_rule_survives_a_restart():
    game = playing(301)
    throw(game, "T20")
    game.set_option("double_out", False)
    restored = PracticeGame()
    restored.restore(json.loads(json.dumps(game.stored())))
    assert restored.double_out is True and restored.setting("double_out") is False
    restored.new_leg()
    assert restored.double_out is False


def test_other_rules_apply_at_once():
    game = playing(301)
    throw(game, "T20")
    game.set_option("personal_routes", True)
    game.set_option("bull_off_distance", True)
    assert game.personal_routes is True and game.setting("bull_off_distance") is True
