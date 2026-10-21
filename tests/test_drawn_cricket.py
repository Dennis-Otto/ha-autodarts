"""Random and Hidden Cricket: six numbers of 1 to 20 drawn for every leg and
the bull, which Hidden Cricket shows only once a dart has marked them."""

import json
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from custom_components.homedarts.bot import Bot, aim, hidden_cricket_aim
from custom_components.homedarts.const import DOMAIN
from custom_components.homedarts.cricket import (
    BULL,
    CRICKET_NUMBERS,
    DRAWN_GAMES,
    MARKS_TO_CLOSE,
    by_value,
    draw_numbers,
    hidden_target,
    shown,
    valid_draw,
)
from custom_components.homedarts.practice import PracticeGame

from .local_helpers import board, dart, setup_local, state, throw

# A draw as Random Cricket shows it, highest first, and one in the order of a
# Hidden Cricket draw.
DRAWN = (18, 14, 11, 7, 5, 2, 25)
HIDDEN = (7, 18, 2, 14, 5, 11, 25)
OPEN = [0] * 7


def drawn_game(
    kind: str, players: int = 2, numbers: tuple[int, ...] | None = None
) -> PracticeGame:
    """A match of a drawn game with a seeded draw, or with these numbers."""
    practice = PracticeGame()
    practice.rng = random.Random(1)
    practice.set_players(players)
    practice.play(kind)
    if numbers:
        practice.drawn = numbers
    return practice


def name_of(thrown: dict) -> str:
    """The name of a dart the bot threw, as the tests name darts."""
    number, multiplier = thrown["number"], thrown["multiplier"]
    if number == BULL:
        return "BULL" if multiplier == 2 else "25"
    return f"{'SDT'[multiplier - 1]}{number}" if number else "MISS"


@given(st.integers(0, 2**32), st.booleans())
def test_a_draw_is_six_numbers_of_one_to_twenty_and_the_bull(seed, hidden):
    numbers = draw_numbers(random.Random(seed), hidden)
    assert valid_draw(numbers) and valid_draw(list(numbers))
    assert numbers[-1] == BULL and len(set(numbers)) == 7
    drawn = random.Random(seed).sample(range(1, 21), 6)
    # Random Cricket shows them highest first; Hidden Cricket as they were drawn.
    assert list(numbers[:-1]) == (drawn if hidden else sorted(drawn, reverse=True))


@pytest.mark.parametrize(
    "numbers",
    [
        None,
        "18 14 11 7 5 2 25",
        [18, 14, 11, 7, 5, 2],
        [18, 14, 11, 7, 5, 2, 25, 25],
        [18, 18, 11, 7, 5, 2, 25],
        [18, 14, 11, 7, 5, 0, 25],
        [21, 14, 11, 7, 5, 2, 25],
        [18, 14, 11, 7, 5, 2, 20],
        [18, 14, 11, 7, 5, 2.0, 25],
        [18, 14, 11, 7, 5, True, 25],
        [18, 14, 11, 7, 5, 2, 25.0],
        [18, 14, 11, 7, 5, "2", 25],
    ],
)
def test_a_stored_draw_must_be_one(numbers):
    assert not valid_draw(numbers)


def test_hidden_numbers_show_once_a_dart_marked_them():
    assert shown(HIDDEN, [OPEN, OPEN]) == [False] * 6 + [True]
    marked = [[0, 0, 1, 0, 0, 0, 0], [0, 3, 0, 0, 0, 0, 0]]
    assert shown(HIDDEN, marked) == [False, True, True, False, False, False, True]
    numbers = [None, 18, 2, None, None, None, 25]
    # Highest first, the bull last, hidden numbers left out.
    assert by_value(numbers) == [1, 2, 6]
    assert by_value(HIDDEN) == [1, 3, 5, 0, 4, 2, 6]


def test_hidden_cricket_aims_only_at_the_numbers_that_show():
    numbers = [None, 18, 2, None, None, None, 25]
    assert hidden_target(OPEN, numbers, [OPEN]) == "T18"
    assert hidden_target([0, 3, 0, 0, 0, 0, 0], numbers, [OPEN]) == "T2"
    # Every number that shows but the bull is closed while others hide: the
    # players search, as the bot does, so nothing is the target.
    assert hidden_target([0, 3, 3, 0, 0, 0, 0], numbers, [OPEN]) is None
    closed = [0, 3, 3, 0, 0, 0, 3]
    assert hidden_target(closed, numbers, [[0, 2, 3, 0, 0, 0, 3]]) is None
    # Once every number shows, the bull is the target, then one to score on.
    found = [20, 18, 2, 7, 5, 3, 25]
    assert hidden_target([3, 3, 3, 3, 3, 3, 0], found, [OPEN]) == "BULL"
    assert hidden_target([3] * 7, found, [[3, 2, 3, 3, 3, 3, 3]]) == "T18"
    assert hidden_target([3] * 7, found, [[3] * 7]) is None


def test_random_cricket_draws_new_numbers_for_every_leg():
    practice = drawn_game("random_cricket")
    expected = draw_numbers(random.Random(1))
    assert practice.drawn == expected
    snapshot = practice.snapshot()
    assert snapshot["game"] == "random_cricket"
    assert snapshot["numbers"] == list(expected)
    assert snapshot["target"] == f"T{expected[0]}"
    # A dart on a number that was not drawn counts nothing.
    unused = next(number for number in range(20, 0, -1) if number not in expected)
    practice.track([dart(f"T{unused}"), dart(f"T{expected[0]}")])
    assert practice.snapshot()["counted"] == [None, str(expected[0])]
    practice.finish_visit()
    practice.track([])
    assert practice.players[0].marks[0] == MARKS_TO_CLOSE
    practice.new_leg()
    assert valid_draw(practice.drawn) and practice.drawn != expected
    assert practice.players[0].marks == OPEN
    # Another game plays its own numbers again.
    practice.play("cricket")
    assert practice.snapshot()["numbers"] == list(CRICKET_NUMBERS)
    assert practice.stored()["drawn"] is None


def test_random_cricket_plays_to_a_winner_by_the_cricket_rules():
    practice = drawn_game("random_cricket", numbers=DRAWN)
    # Marks beyond three score the number while the other has it open.
    throw(practice, "T18", "T18", "S14")
    assert practice.players[0].points == 54
    assert practice.players[0].marks[:2] == [3, 1]
    throw(practice, "T20", "MISS", "MISS")
    assert practice.players[1].marks == OPEN
    practice.players[0].marks = [3, 3, 3, 3, 3, 3, 2]
    events = throw(practice, "25")
    assert events[0][0] == "leg_won" and events[0][1]["game"] == "random_cricket"
    assert events[0][1]["points"] == 54 and practice.winner == 0
    assert practice.legs[0]["game"] == "random_cricket"


def test_a_restart_and_an_undone_visit_keep_the_numbers():
    practice = drawn_game("hidden_cricket", numbers=HIDDEN)
    checkpoint = practice.checkpoint()
    throw(practice, "T7")
    stored = json.loads(json.dumps(practice.stored()))
    assert stored["drawn"] == list(HIDDEN)
    restored = PracticeGame()
    restored.restore(stored)
    assert restored.drawn == HIDDEN and restored.stored() == stored
    assert restored.snapshot()["numbers"] == [7, None, None, None, None, None, 25]
    # The undone visit comes back on the same numbers, thrown again.
    practice.rewind(checkpoint, [dart("S18")], [None])
    assert practice.drawn == HIDDEN
    assert practice.snapshot()["numbers"] == [None, 18, None, None, None, None, 25]


@pytest.mark.parametrize("drawn", [None, [20, 19, 18], [18, 14, 11, 7, 5, 5, 25]])
def test_a_store_without_its_draw_starts_the_leg_with_new_numbers(drawn):
    practice = drawn_game("random_cricket", numbers=DRAWN)
    throw(practice, "T18")
    saved = practice.stored()
    saved["drawn"] = drawn
    restored = PracticeGame()
    restored.rng = random.Random(2)
    restored.restore(saved)
    assert restored.drawn == draw_numbers(random.Random(2))
    assert restored.players[0].marks == OPEN and restored.players[0].darts == 0
    assert restored.players[0].match_darts == 1


def test_hidden_cricket_shows_a_number_once_a_dart_marks_it():
    practice = drawn_game("hidden_cricket", numbers=HIDDEN)
    snapshot = practice.snapshot()
    assert snapshot["numbers"] == [None] * 6 + [25]
    # Nothing but the bull shows: the players search, so there is no target.
    assert snapshot["target"] is None
    # A dart on a number that was not drawn shows nothing.
    practice.track([dart("T20")])
    assert practice.snapshot()["numbers"] == [None] * 6 + [25]
    # The dart on the 14 shows it at once, in the row of its draw.
    practice.track([dart("T20"), dart("S14")])
    snapshot = practice.snapshot()
    assert snapshot["numbers"] == [None, None, None, 14, None, None, 25]
    assert snapshot["counted"] == [None, "14"] and snapshot["target"] == "T14"
    practice.finish_visit()
    practice.track([])
    # It shows for the other player too, who aims at it.
    snapshot = practice.snapshot()
    assert snapshot["player"] == 2 and snapshot["numbers"][3] == 14
    assert snapshot["target"] == "T14"
    assert snapshot["scores"][0]["marks"][3] == 1


def test_hidden_cricket_plays_to_a_winner_by_the_cricket_rules():
    practice = drawn_game("hidden_cricket", numbers=HIDDEN)
    practice.players[0].marks = [3, 3, 3, 3, 3, 0, 3]
    practice.players[0].points = 36
    practice.players[1].points = 50
    # Everything closed with fewer points does not win yet.
    events = throw(practice, "T11", "S11")
    assert practice.players[0].points == 47 and practice.winner is None
    assert events[-1][0] == "turn_changed"
    practice.players[1].marks = [3, 3, 3, 3, 3, 3, 2]
    events = throw(practice, "25")
    # Everything closed with no fewer points wins.
    assert events[0][0] == "leg_won" and events[0][1]["player"] == 2
    assert events[0][1]["game"] == "hidden_cricket"


def test_the_bot_searches_the_hidden_numbers():
    numbers = [None, 18, None, None, None, None, 25]
    # A number that shows comes first.
    assert hidden_cricket_aim(OPEN, 0, [OPEN], [0], numbers, 0) == "T18"
    # With it closed, the bot searches, another number with every dart.
    closed = [0, 3, 0, 0, 0, 0, 0]
    beds = [
        hidden_cricket_aim(closed, 0, [OPEN], [0], numbers, darts)
        for darts in range(20)
    ]
    assert beds[:3] == ["T20", "T19", "T17"] and beds[19] == "T20"
    assert sorted(beds[:19]) == sorted(f"T{n}" for n in range(1, 21) if n != 18)
    # Everything shows: Cricket as usual, on the numbers by value.
    everything = list(HIDDEN)
    assert hidden_cricket_aim(OPEN, 0, [OPEN], [0], everything, 5) == "T18"
    assert hidden_cricket_aim([3] * 6 + [0], 0, [OPEN], [0], everything, 5) == "BULL"


def test_the_bot_plays_hidden_and_random_cricket_from_the_snapshot():
    practice = PracticeGame()
    practice.bot_level = 60
    practice.set_players(1)
    practice.play("hidden_cricket")
    practice.drawn = HIDDEN
    assert practice.bot_seat == 1
    practice.current = 1
    # Nothing shows but the bull: the bot searches.
    assert aim(practice.snapshot()) == "T20"
    practice.players[0].marks = [0, 2, 0, 0, 0, 0, 0]
    assert aim(practice.snapshot()) == "T18"
    # Random Cricket plays its numbers as Cricket does.
    practice.play("random_cricket")
    practice.drawn = DRAWN
    practice.current = 1
    assert aim(practice.snapshot()) == "T18"


async def test_start_game_plays_random_and_hidden_cricket_by_name(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.games.practice
    for name, kind in (
        ("Random Cricket", "random_cricket"),
        ("hidden", "hidden_cricket"),
    ):
        await hass.services.async_call(
            DOMAIN,
            "start_game",
            {"game": name, "players": ["Alex", "Sam"]},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert practice.cricket == kind and valid_draw(practice.drawn)
        assert state(hass, "select", "practice_game") == kind
    # Hidden Cricket starts with only the bull showing: the players search, so
    # there is no target yet.
    assert state(hass, "sensor", "practice_target") == "unknown"


class DrawnCricketMachine(RuleBasedStateMachine):
    """Random and Hidden Cricket under darts, undone visits, new legs and
    restarts, with the bot: a leg keeps its numbers, and Hidden Cricket shows
    exactly the numbers a dart has marked."""

    def __init__(self) -> None:
        super().__init__()
        self.game = PracticeGame()
        self.checkpoint: tuple[dict, list[str]] | None = None
        self.numbers: tuple[int, ...] = ()

    @initialize(
        kind=st.sampled_from(DRAWN_GAMES),
        players=st.integers(1, 4),
        legs=st.integers(1, 3),
        seed=st.integers(0, 2**16),
        teams=st.booleans(),
    )
    def start(self, kind, players, legs, seed, teams) -> None:
        self.game.rng = random.Random(seed)
        self.game.teams = teams
        self.game.set_players(players)
        self.game.set_format(legs, 1)
        self.game.play(kind)
        self.numbers = self.game.drawn

    def _visit(self, names: list[str]) -> None:
        """A visit dart by dart, then the darts are pulled."""
        legs, won = self.game.legs_total, self.game.winner is not None
        self.checkpoint = (self.game.checkpoint(), names)
        for count in range(1, len(names) + 1):
            self.game.track([dart(name) for name in names[:count]])
        self.game.finish_visit()
        self.game.track([])
        if won or self.game.legs_total != legs:
            # A new match or the next leg plays numbers of its own.
            self.checkpoint = None
            self.numbers = self.game.drawn

    @rule(
        beds=st.lists(
            st.sampled_from(["T", "D", "S", "BULL", "25", "MISS", "T20", "S1"]),
            min_size=1,
            max_size=3,
        ),
        slot=st.integers(0, 5),
    )
    def throw(self, beds, slot) -> None:
        """Darts at a number of the leg, hidden or not, or anywhere else."""
        number = self.game.drawn[slot]
        self._visit([f"{bed}{number}" if len(bed) == 1 else bed for bed in beds])

    @rule(seed=st.integers(0, 2**16))
    def bot_visit(self, seed) -> None:
        """The bot throws where it aims while it is at the board."""
        game = self.game
        if game.bot_level != 60:
            # A bot that joins starts a new match: the last visit is gone.
            self.checkpoint = None
        game.set_bot(60)
        self.numbers = game.drawn
        if not game.bot_up:
            return
        bot, names = Bot(random.Random(seed)), []
        for _ in range(3):
            snapshot = game.snapshot()
            if snapshot["won"] or snapshot["bull_off"]:
                break
            thrown, _ = bot.throw(aim(snapshot), 60, cricket=True)
            names.append(name_of(thrown))
            game.track([dart(name) for name in names])
        self._visit(names)

    @rule()
    def undo(self) -> None:
        """The last visit comes back and is pulled again."""
        if self.checkpoint is None:
            return
        saved, names = self.checkpoint
        self.checkpoint = None
        self.game.rewind(saved, [dart(name) for name in names], [None] * len(names))
        self.game.finish_visit()
        self.game.track([])

    @rule()
    def new_leg(self) -> None:
        self.game.new_leg()
        self.checkpoint = None
        self.numbers = self.game.drawn

    @rule()
    def restart(self) -> None:
        """Home Assistant stops and starts: the store is JSON."""
        saved = json.loads(json.dumps(self.game.stored()))
        restored = PracticeGame()
        restored.restore(saved)
        assert json.loads(json.dumps(restored.stored())) == saved
        self.game = restored
        self.checkpoint = None

    @invariant()
    def a_leg_keeps_its_numbers(self) -> None:
        assert self.game.drawn == self.numbers and valid_draw(self.numbers)
        if self.game.cricket == "random_cricket":
            drawn = list(self.numbers[:-1])
            assert drawn == sorted(drawn, reverse=True)

    @invariant()
    def hidden_cricket_shows_what_a_dart_marked(self) -> None:
        snapshot = self.game.snapshot()
        marks = [score["marks"] for score in snapshot["scores"]]
        for slot, number in enumerate(snapshot["numbers"]):
            marked = any(player[slot] for player in marks)
            if snapshot["game"] == "random_cricket" or marked or slot == 6:
                assert number == self.game.drawn[slot]
            else:
                assert number is None
        visible = {f"T{number}" for number in snapshot["numbers"] if number}
        assert snapshot["target"] in {None, "BULL", *visible}

    @invariant()
    def the_marks_stay_on_the_chalkboard(self) -> None:
        for player in self.game.players:
            assert len(player.marks) == 7 and player.points >= 0
            assert all(0 <= mark <= MARKS_TO_CLOSE for mark in player.marks)


DrawnCricketMachine.TestCase.settings = settings(
    max_examples=80, stateful_step_count=40, deadline=None
)
TestDrawnCricketMachine = pytest.mark.timeout(180)(DrawnCricketMachine.TestCase)
