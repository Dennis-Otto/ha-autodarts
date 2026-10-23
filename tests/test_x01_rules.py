"""The X01 rules of play.autodarts.io: the In and Out mode straight, double or
master, the bull mode 25/50 or 50/50, and a round limit after which the lowest
score wins the leg."""

import pytest

from custom_components.homedarts.bot import aim, play_leg, x01_aim
from custom_components.homedarts.practice import (
    DEFAULT_RULES,
    X01_RULES,
    PracticeGame,
    VisitRefused,
    unwinnable_rules,
    valid_rule,
    valid_settings,
)
from custom_components.homedarts.scoring import (
    BULL_25_50,
    BULL_50_50,
    DOUBLE,
    MASTER,
    STRAIGHT,
    evaluate_visit,
    fits,
    score,
    visit_darts,
)

from .local_helpers import dart, playing, throw
from .test_bot import RecordingBot


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def names(visit: list[dict] | None) -> list[str] | None:
    return None if visit is None else [item["name"] for item in visit]


def match(players: int = 2, **rules) -> PracticeGame:
    """A match of 501 with these rules, for players with names."""
    game = PracticeGame()
    game.restore(rules)
    game.names[:players] = [f"Player {index + 1}" for index in range(players)]
    game.set_players(players)
    game.play(501)
    return game


def rounds(game: PracticeGame, count: int, *visits: tuple[str, ...]) -> list:
    """Every player throws their visit, round by round; the events."""
    events = []
    for _ in range(count):
        for visit in visits:
            events += throw(game, *visit)
    return events


FIFTEEN = ("S5", "S5", "S5")
THREE = ("S1", "S1", "S1")


# -- scoring -------------------------------------------------------------------


def test_a_dart_fits_the_in_or_out_mode():
    for name, straight, double, master in (
        ("S20", True, False, False),
        ("D20", True, True, True),
        ("T20", True, False, True),
        ("BULL", True, True, True),
        ("25", True, False, False),
        ("MISS", True, False, False),
    ):
        assert fits(dart(name), STRAIGHT) is straight
        assert fits(dart(name), DOUBLE) is double, name
        assert fits(dart(name), MASTER) is master, name
    assert fits({"number": 0, "multiplier": 3}, MASTER) is False


def test_the_bull_mode_50_50_scores_the_outer_bull_50():
    assert score(dart("25")) == 25 and score(dart("25"), BULL_50_50) == 50
    assert score(dart("BULL"), BULL_50_50) == 50
    assert evaluate_visit(75, darts("25", "25"), DOUBLE, BULL_50_50) == (75, "bust", 2)
    assert evaluate_visit(100, darts("25", "BULL"), DOUBLE, BULL_50_50) == (
        0,
        "won",
        2,
    )
    assert evaluate_visit(50, darts("25"), STRAIGHT, BULL_50_50) == (0, "won", 1)


def test_master_out_ends_on_a_double_or_a_treble_and_busts_on_1():
    assert evaluate_visit(60, darts("T20"), MASTER) == (0, "won", 1)
    assert evaluate_visit(60, darts("S20", "S20", "S20"), MASTER) == (60, "bust", 3)
    assert evaluate_visit(61, darts("T20"), MASTER) == (61, "bust", 1)
    assert evaluate_visit(60, darts("T20"), DOUBLE) == (60, "bust", 1)


def test_a_visit_entered_as_its_score_follows_the_modes():
    assert names(visit_darts(60, 60, 1, MASTER)) == ["T20"]
    # With double out, the treble busts.
    assert evaluate_visit(60, visit_darts(60, 60, 1, DOUBLE), DOUBLE)[1] == "bust"
    assert visit_darts(61, 60, 3, MASTER) is not None
    assert evaluate_visit(61, visit_darts(61, 60, 3, MASTER), MASTER)[1] == "bust"
    # With master in, a treble opens: 60 is one dart, 1 no visit at all.
    assert names(visit_darts(501, 60, 1, MASTER, opening=MASTER)) == ["T20"]
    assert visit_darts(501, 60, 1, MASTER, opening=DOUBLE) is None
    assert visit_darts(501, 1, 3, STRAIGHT, opening=MASTER) is None
    # With the bull mode 50/50, no dart scores 25, and 50 is the bull.
    assert visit_darts(25, 25, 1, STRAIGHT, bull_mode=BULL_50_50) is None
    assert names(visit_darts(25, 25, 1, STRAIGHT)) == ["25"]
    assert names(visit_darts(100, 100, 2, DOUBLE, bull_mode=BULL_50_50)) == [
        "T20",
        "D20",
    ]


def test_the_rules_are_valid_only_with_their_values():
    assert all(valid_rule(rule, value) for rule, value in DEFAULT_RULES.items())
    assert valid_rule("in_mode", MASTER) and valid_rule("bull_mode", BULL_50_50)
    assert valid_rule("max_rounds", 50) and not valid_rule("max_rounds", 51)
    assert not valid_rule("max_rounds", True) and not valid_rule("max_rounds", -1)
    assert not valid_rule("out_mode", "50_50") and not valid_rule("bull_mode", DOUBLE)
    assert not valid_rule("double_out", DOUBLE) and not valid_rule("in_mode", 1)


# -- In and Out mode ---------------------------------------------------------------


def test_a_master_out_501_accepts_a_treble_finish():
    game = playing(501, 60, out_mode=MASTER)
    assert game.snapshot()["checkout"] == "T20"
    [(kind, won)] = throw(game, "T20")
    assert kind == "leg_won" and won["checkout"] == 60 and won["darts"] == 1
    assert won["out_mode"] == MASTER and won["in_mode"] == STRAIGHT
    assert won["bull_mode"] == BULL_25_50
    # Records and the checkout rate count double out alone.
    assert won["double_out"] is False and game.legs[0]["double_out"] is False
    assert game.leg_stats[0]["checkouts"] == 0
    # A single on zero and 1 left still bust.
    game = playing(501, 60, out_mode=MASTER)
    assert throw(game, "S20", "S20", "S20")[0][0] == "bust"
    game = playing(501, 61, out_mode=MASTER)
    assert throw(game, "T20")[0][0] == "bust"


def test_master_out_without_a_checkout_sets_up_the_next_visit():
    game = playing(501, 200, out_mode=MASTER)
    assert game.snapshot()["setup"] == {"route": "T20 T20 T16", "leave": 32}
    game = playing(501, 200, out_mode=STRAIGHT)
    assert game.snapshot()["setup"] is None


def test_master_in_opens_the_leg_with_a_double_or_a_treble():
    game = playing(501, in_mode=MASTER)
    assert game.snapshot()["opened"] is False and game.snapshot()["in_mode"] == MASTER
    throw(game, "S20", "T20", "S20")
    assert game.players[0].remaining == 421 and game.players[0].opened
    game = playing(501, in_mode=DOUBLE)
    throw(game, "T20", "D20", "S20")
    assert game.players[0].remaining == 441
    # Master in and master out win a start of 3 with the treble 1.
    game = playing(501, 3, in_mode=MASTER, out_mode=MASTER)
    assert throw(game, "T1")[0][0] == "leg_won"


@pytest.mark.parametrize(
    ("in_mode", "out_mode", "unwinnable"),
    [
        (DOUBLE, DOUBLE, True),
        (MASTER, DOUBLE, True),
        (DOUBLE, MASTER, True),
        (MASTER, MASTER, False),
        (STRAIGHT, DOUBLE, False),
        (DOUBLE, STRAIGHT, False),
        (STRAIGHT, MASTER, False),
    ],
)
def test_a_start_of_3_is_unwinnable_with_double_or_master_in_and_out_unless_both_are_master(
    in_mode, out_mode, unwinnable
):
    assert unwinnable_rules(in_mode, out_mode) is unwinnable
    game = PracticeGame()
    game.restore({"in_mode": in_mode, "out_mode": out_mode})
    game.play(501)
    assert game.unwinnable([3, 0, 0, 0]) is unwinnable
    assert (
        game.unwinnable([3, 0, 0, 0], {"in_mode": MASTER, "out_mode": MASTER}) is False
    )
    # Double in and double out stand for the modes double or straight.
    assert game.unwinnable([3, 0, 0, 0], {"double_in": True, "double_out": True})
    assert game.unwinnable([3, 0, 0, 0], {"double_in": False}) is False
    both = {"double_in": True, "in_mode": out_mode, "out_mode": out_mode}
    assert game.unwinnable([3, 0, 0, 0], both) is unwinnable_rules(out_mode, out_mode)


def test_double_in_and_double_out_set_the_modes_double_or_straight():
    game = PracticeGame()
    game.set_option("double_in", True)
    game.set_option("double_out", False)
    assert (game.in_mode, game.out_mode) == (DOUBLE, STRAIGHT)
    assert game.double_in and not game.double_out
    game.set_rule("out_mode", MASTER)
    assert not game.double_out and not game.setting("double_out")
    # The switch turns master out on to double out, and off to straight.
    game.set_option("double_out", True)
    assert game.out_mode == DOUBLE
    game.set_rule("in_mode", MASTER)
    game.set_option("double_in", False)
    assert game.in_mode == STRAIGHT and game.setting("double_in") is False


def test_the_out_mode_changes_a_leg_only_before_its_first_dart():
    game = playing(501)
    assert game.set_rule("out_mode", MASTER) and game.out_mode == MASTER
    throw(game, "T20")
    assert game.set_rule("out_mode", STRAIGHT)
    assert game.out_mode == MASTER and game.out_mode_next == STRAIGHT
    assert game.rule("out_mode") == STRAIGHT and game.snapshot()["out_mode"] == MASTER
    # Back to the mode of the leg, nothing waits.
    assert game.set_rule("out_mode", MASTER) and game.out_mode_next is None
    assert not game.set_rule("out_mode", MASTER)
    assert game.set_rule("out_mode", DOUBLE) and game.out_mode_next == DOUBLE
    game.new_leg()
    assert game.out_mode == DOUBLE and game.out_mode_next is None
    # Values that are no rule change nothing.
    assert not game.set_rule("out_mode", "triple") and not game.set_rule(
        "max_rounds", 99
    )
    assert not game.set_rule("double_out", DOUBLE) and game.out_mode == DOUBLE


def test_a_visit_entered_as_its_score_checks_out_with_master_out():
    game = playing(501, 57, out_mode=MASTER)
    visit = game.score_visit(57, 1, checkout=True)
    assert names(visit) == ["T19"]
    # Darts at a double count with double out alone.
    assert not any(item.get("at_double") for item in visit)
    visit = game.score_visit(57, 3, at_double=2)
    assert evaluate_visit(57, visit, MASTER)[1] == "won"
    game = playing(501, in_mode=MASTER)
    assert names(game.score_visit(60, 1)) == ["T20"]
    with pytest.raises(VisitRefused) as refused:
        game.score_visit(1)
    assert refused.value.key == "visit_impossible"
    game = playing(501, 25, out_mode=STRAIGHT, bull_mode=BULL_50_50)
    with pytest.raises(VisitRefused) as refused:
        game.score_visit(25, 1, checkout=True)
    assert refused.value.key == "checkout_impossible"


# -- bull mode ---------------------------------------------------------------------


def test_a_50_50_bull_game_routes_50_through_the_outer_bull_too():
    game = playing(501, 90, bull_mode=BULL_50_50)
    assert game.snapshot()["checkout"] == "BULL D20"
    assert game.snapshot()["bull_mode"] == BULL_50_50
    throw(game, "25")
    assert game.players[0].remaining == 40 and game.snapshot()["checkout"] == "D20"
    # Only the bullseye is a double.
    game = playing(501, 50, bull_mode=BULL_50_50)
    assert throw(game, "25")[0][0] == "bust"
    game = playing(501, 50, bull_mode=BULL_50_50, out_mode=STRAIGHT)
    assert throw(game, "25")[0][0] == "leg_won"
    # The darts at the bull count 50 in the average.
    game = playing(501, bull_mode=BULL_50_50)
    throw(game, "25", "25", "25")
    assert game.players[0].remaining == 351 and game.players[0].points == 150


def test_the_bulls_aim_where_the_route_goes():
    game = playing(501, 90, bull_mode=BULL_50_50)
    game.track(darts("25", "D20"))
    assert game.booking().booked_aims == ["BULL", "D20"]
    game = playing(501, 60, out_mode=MASTER)
    game.track(darts("S20", "S20", "S20"))
    assert game.booking().booked_aims == ["T20", "D20", "D10"]
    game = playing(501, 61, out_mode=MASTER)
    game.track(darts("T20", "S1"))
    assert game.booking().booked_aims == [None, None]
    game = playing(501, in_mode=MASTER)
    game.track(darts("S20", "T20", "T20"))
    assert game.booking().booked_aims == [None, None, "T20"]


# -- round limit -------------------------------------------------------------------


def test_a_10_round_leg_ends_after_round_10_with_the_lowest_score_as_winner():
    game = match(max_rounds=10, legs_to_win=2)
    assert game.snapshot()["round"] == 1 and game.snapshot()["max_rounds"] == 10
    events = rounds(game, 9, FIFTEEN, THREE)
    assert "leg_won" not in [kind for kind, _ in events]
    assert game.snapshot()["round"] == 10
    events = throw(game, *FIFTEEN) + throw(game, *THREE)
    won = [details for kind, details in events if kind == "leg_won"]
    assert won == [
        {
            "game": 501,
            "player": 1,
            "name": "Player 1",
            "players": 2,
            "darts": 30,
            "average": 15.0,
            "checkout": None,
            "remaining": 351,
            "rounds": 10,
            "start": 501,
            "double_out": True,
            "double_in": False,
            "out_mode": DOUBLE,
            "in_mode": STRAIGHT,
            "bull_mode": BULL_25_50,
            "legs": 1,
            "sets": 0,
            "match": False,
        }
    ]
    # The next leg starts, with the next player.
    assert events[-1][0] == "turn_changed" and events[-1][1]["player"] == 2
    assert game.players[0].legs == 1 and game.players[0].remaining == 501
    assert game.snapshot()["round"] == 1
    leg = game.legs[0]
    assert leg["rounds"] == 10 and leg["checkout"] is None and leg["average"] == 15.0
    # It was not checked out: no checkout, no best leg and no fewest darts.
    assert game.leg_stats[0]["checkouts"] == 0
    assert game.tallies[0].best_leg == 0 and game.tallies[0].checkouts == 0
    profile = game.profiles.players["player 1"]
    assert profile.legs_won == 1 and profile.fewest_darts == {}
    assert profile.checkouts == 0


def test_a_tie_after_the_last_round_plays_on_round_by_round():
    game = match(max_rounds=2)
    events = rounds(game, 2, FIFTEEN, FIFTEEN)
    assert "leg_won" not in [kind for kind, _ in events]
    assert game.snapshot()["round"] == 3
    assert [kind for kind, _ in throw(game, *THREE)] == ["turn_changed"]
    events = throw(game, *FIFTEEN)
    assert [kind for kind, _ in events] == ["leg_won", "match_won"]
    won = dict(events[0][1])
    assert (won["player"], won["rounds"], won["remaining"]) == (2, 3, 456)
    assert won["match"] is True
    match_won = events[1][1]
    assert match_won["player"] == 2 and match_won["average"] == 15.0
    assert match_won["summary"] == game.summary["players"]
    # The winner keeps what they had left, and the result stays.
    assert game.winner == 1 and game.players[1].remaining == 456
    assert game.summary["players"][1]["best_leg"] is None
    assert game.snapshot()["winner"] == 2


def test_a_checkout_before_the_limit_wins_as_ever():
    game = match(max_rounds=10)
    game.players[0].remaining = 40
    assert throw(game, "D20")[0][0] == "leg_won"
    assert "rounds" not in game.legs[0]


def test_the_lowest_team_wins_on_the_round_limit():
    game = match(4, max_rounds=1, teams=True)
    events = rounds(game, 1, FIFTEEN, THREE, FIFTEEN, THREE)
    won = next(details for kind, details in events if kind == "leg_won")
    assert (won["player"], won["team"], won["remaining"]) == (1, 1, 471)
    assert game.players[2].remaining == 471
    # Both teams on the same score play on.
    game = match(4, max_rounds=1, teams=True)
    events = rounds(game, 1, FIFTEEN, FIFTEEN, THREE, THREE)
    assert "leg_won" not in [kind for kind, _ in events]


def test_a_pass_and_a_bust_count_for_the_round_limit():
    game = match(max_rounds=1)
    game.players[0].remaining = 40
    throw(game, "T20")
    assert game.finish_visit(empty=True)[0][0] == "leg_won"
    assert game.winner == 0 and game.players[1].remaining == 501


def test_a_restored_or_rewound_leg_keeps_its_rounds():
    game = match(max_rounds=3)
    rounds(game, 1, FIFTEEN, THREE)
    throw(game, *FIFTEEN)
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.leg_visits == 3 and restored.snapshot()["round"] == 2
    saved = restored.checkpoint()
    throw(restored, *THREE)
    restored.rewind(saved, [], [])
    assert restored.leg_visits == 3
    broken = {**game.stored(), "leg_visits": -1}
    restored.restore(broken)
    assert restored.leg_visits == 0


# -- storage, settings and tournaments ----------------------------------------------


def test_stored_games_with_double_in_and_double_out_load_with_the_modes():
    game = PracticeGame()
    game.restore(
        {"game": 501, "double_out": False, "double_in": True, "double_out_next": True}
    )
    assert (game.in_mode, game.out_mode, game.out_mode_next) == (
        DOUBLE,
        STRAIGHT,
        DOUBLE,
    )
    saved = game.stored()
    assert {rule: saved[rule] for rule in X01_RULES} == {
        "in_mode": DOUBLE,
        "out_mode": STRAIGHT,
        "bull_mode": BULL_25_50,
        "max_rounds": 0,
    }
    assert saved["out_mode_next"] == DOUBLE and "double_out_next" not in saved
    # The modes win over the old switches; broken values are left out.
    fresh = PracticeGame()
    fresh.restore(
        {
            **saved,
            "out_mode": MASTER,
            "in_mode": "sometimes",
            "bull_mode": BULL_50_50,
            "max_rounds": 51,
            "out_mode_next": "never",
        }
    )
    assert (fresh.in_mode, fresh.out_mode, fresh.bull_mode) == (
        DOUBLE,
        MASTER,
        BULL_50_50,
    )
    assert fresh.max_rounds == 0 and fresh.out_mode_next is None
    old = {key: value for key, value in saved.items() if key != "out_mode_next"}
    fresh.restore(old | {"double_out_next": False})
    assert fresh.out_mode_next == STRAIGHT


def test_the_settings_to_come_back_to_keep_the_rules():
    game = match(in_mode=MASTER, out_mode=MASTER, bull_mode=BULL_50_50, max_rounds=8)
    settings = game.settings()
    assert {rule: settings[rule] for rule in X01_RULES} == {
        "in_mode": MASTER,
        "out_mode": MASTER,
        "bull_mode": BULL_50_50,
        "max_rounds": 8,
    }
    assert settings["double_out"] is False
    assert valid_settings(settings) == settings
    # Settings from before the modes have double in and double out.
    old = {key: value for key, value in settings.items() if key not in X01_RULES}
    old |= {"double_in": True, "double_out": False}
    assert {rule: valid_settings(old)[rule] for rule in X01_RULES} == {
        "in_mode": DOUBLE,
        "out_mode": STRAIGHT,
        "bull_mode": BULL_25_50,
        "max_rounds": 0,
    }
    # They come back with the next match.
    other = PracticeGame()
    other.resume = valid_settings(settings)
    other.new_match()
    assert (other.in_mode, other.out_mode, other.bull_mode, other.max_rounds) == (
        MASTER,
        MASTER,
        BULL_50_50,
        8,
    )


def test_plain_rules_are_the_rules_a_tournament_knows():
    game = match()
    assert game.plain_rules()
    for rule, value in (
        ("in_mode", MASTER),
        ("out_mode", MASTER),
        ("bull_mode", BULL_50_50),
        ("max_rounds", 5),
    ):
        game = match()
        game.set_rule(rule, value)
        assert not game.plain_rules(), rule


# -- the bot -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("remaining", "darts", "out_mode", "opening", "bull_mode", "bed"),
    [
        # Master out finishes on a treble where that saves a dart.
        (60, 1, MASTER, STRAIGHT, BULL_25_50, "T20"),
        (117, 3, MASTER, STRAIGHT, BULL_25_50, "T20"),
        (200, 3, MASTER, STRAIGHT, BULL_25_50, "T20"),
        # The bull mode 50/50 aims at the bull for 50.
        (90, 3, DOUBLE, STRAIGHT, BULL_50_50, "BULL"),
        (82, 1, DOUBLE, STRAIGHT, BULL_50_50, "BULL"),
        (51, 1, STRAIGHT, STRAIGHT, BULL_50_50, "T17"),
        (29, 1, STRAIGHT, STRAIGHT, BULL_50_50, "D14"),
        # Master in opens on the treble 20 where it does not bust ...
        (501, 3, DOUBLE, MASTER, BULL_25_50, "T20"),
        (62, 3, DOUBLE, MASTER, BULL_25_50, "T20"),
        # ... unless a double or, with master out, a treble wins at once ...
        (40, 3, DOUBLE, MASTER, BULL_25_50, "D20"),
        (57, 3, MASTER, MASTER, BULL_25_50, "T19"),
        (57, 3, STRAIGHT, MASTER, BULL_25_50, "T19"),
        # ... or it busts: then a double as with double in.
        (60, 3, DOUBLE, MASTER, BULL_25_50, "D20"),
        (61, 2, DOUBLE, MASTER, BULL_25_50, "D20"),
    ],
)
def test_where_the_bot_aims_with_the_modes(
    remaining, darts, out_mode, opening, bull_mode, bed
):
    assert x01_aim(remaining, darts, out_mode, opening, bull_mode) == bed


def test_the_bot_plays_the_rules_of_the_game():
    game = PracticeGame()
    game.restore({"in_mode": MASTER, "out_mode": MASTER})
    game.set_bot(60)
    game.set_players(1)
    game.play(501)
    game.current = 1
    assert aim(game.snapshot()) == "T20"
    game.players[1].opened = True
    game.players[1].remaining = 57
    assert aim(game.snapshot()) == "T19"
    game.bull_mode = BULL_50_50
    game.out_mode = DOUBLE
    game.players[1].remaining = 90
    assert aim(game.snapshot()) == "BULL"


@pytest.mark.parametrize(
    ("out_mode", "bull_mode", "ends"),
    [(MASTER, BULL_25_50, {2, 3}), (DOUBLE, BULL_50_50, {2})],
)
def test_a_leg_of_the_bot_ends_as_the_out_mode_says(out_mode, bull_mode, ends):
    bot = RecordingBot(5)
    finishes = set()
    for _ in range(25):
        bot.darts.clear()
        assert play_leg(bot, 90, 301, out_mode, bull_mode) == len(bot.darts)
        finishes.add(bot.darts[-1]["multiplier"])
    assert finishes <= ends and 2 in finishes


def test_a_leg_the_round_limit_decides_after_passes_survives_a_restart():
    game = match(max_rounds=1)
    game.set_start(1, 301)
    game.finish_visit(empty=True)
    events = game.finish_visit(empty=True)
    won = next(details for kind, details in events if kind == "leg_won")
    assert (won["player"], won["darts"], won["average"]) == (2, 0, None)
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.legs == game.legs and restored.legs[0]["rounds"] == 1
