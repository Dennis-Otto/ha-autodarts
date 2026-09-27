"""Practice games under any mix of darts, corrections, settings and restarts."""

import json

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

from custom_components.autodarts.cricket import CRICKET_GAMES
from custom_components.autodarts.party import KILLER_LIVES
from custom_components.autodarts.practice import (
    GAMES,
    MAX_LEGS,
    MAX_PLAYERS,
    MAX_SETS,
    OPTIONS,
    PracticeGame,
)

from .test_practice import dart

KINDS = [
    *(101, 301, "cricket", "cut_throat", "tactics"),
    *("shanghai", "halve_it", "killer", "golf", "baseball", "count_up"),
]
STARTS = [0, 0, 2, 40, 101, 301, 501, 1001]
BEDS = [
    *("T20", "T19", "T15", "T3", "T1", "S20", "S19", "S15", "S3", "S2", "S1"),
    *("D20", "D19", "D16", "D8", "D7", "D3", "D2", "D1", "BULL", "25", "MISS"),
]
POSITIONS = st.one_of(
    st.none(),
    st.tuples(st.floats(-0.1, 0.1), st.floats(-0.1, 0.1)),
)


def stored_as_json(game: PracticeGame) -> dict:
    """What Home Assistant's store keeps: JSON, with text keys."""
    return json.loads(json.dumps(game.stored()))


class PracticeMachine(RuleBasedStateMachine):
    """A board where darts land, get corrected and pulled while players change
    the game, its rules and its format, and Home Assistant restarts."""

    def __init__(self) -> None:
        super().__init__()
        self.game = PracticeGame()
        self.darts: list[str] = []
        self.positions: list[tuple[float, float] | None] = []

    def _track(self) -> None:
        self.game.track([dart(name) for name in self.darts], list(self.positions))

    @initialize(
        kind=st.sampled_from(KINDS),
        players=st.integers(1, MAX_PLAYERS),
        legs=st.integers(1, 3),
        sets=st.integers(1, 2),
        bull_off=st.booleans(),
        teams=st.booleans(),
        starts=st.lists(st.sampled_from(STARTS), min_size=4, max_size=4),
    )
    def start(self, kind, players, legs, sets, bull_off, teams, starts) -> None:
        self.game.bull_off = bull_off
        self.game.teams = teams
        for index, start in enumerate(starts):
            self.game.set_start(index, start)
        self.game.set_players(players)
        self.game.set_format(legs, sets)
        self.game.play(kind)

    @rule(bed=st.sampled_from(BEDS), position=POSITIONS)
    def throw(self, bed, position) -> None:
        if len(self.darts) == 3:
            self.pull_darts()
        self.darts.append(bed)
        self.positions.append(position)
        self._track()

    def _aimed(self, choice: int) -> str:
        """The bed the game suggests: the checkout, the target or a double."""
        snapshot = self.game.snapshot()
        if self.game.bulling:
            return ("BULL", "25", "S20")[choice]
        if snapshot.get("checkout"):
            return str(snapshot["checkout"].split()[0])
        target = snapshot.get("target")
        if target:
            bed = {"D": "D20", "T": "T20", "25": "BULL"}.get(target, target)
            return f"{'SDT'[choice]}{bed}" if bed.isdigit() else str(bed)
        others = [
            score["number"]
            for score in snapshot.get("scores", [])
            if score["player"] != snapshot["player"] and score.get("lives")
        ]
        if snapshot["game"] == "killer" and snapshot["phase"] == "play" and others:
            return f"D{others[choice % len(others)]}"
        return f"T{20 - choice}"

    @rule(choices=st.lists(st.integers(0, 2), min_size=1, max_size=3))
    def aim(self, choices) -> None:
        """A visit at what the game suggests, so that legs and matches end."""
        for choice in choices:
            if len(self.darts) == 3:
                break
            self.darts.append(self._aimed(choice))
            self.positions.append(None if choice else (0.01 * len(self.darts), 0.0))
            self._track()
        self.pull_darts()

    @rule(index=st.integers(0, 2), bed=st.sampled_from(BEDS))
    def correct(self, index, bed) -> None:
        if self.darts:
            self.darts[index % len(self.darts)] = bed
            self._track()

    @rule()
    def pull_darts(self) -> None:
        self.game.finish_visit()
        self.darts, self.positions = [], []
        self._track()

    @rule(
        change=st.sampled_from(["option", "format", "game", "leg", "start", "rounds"]),
        option=st.sampled_from(OPTIONS),
        enabled=st.booleans(),
        kind=st.sampled_from(KINDS),
        legs=st.integers(0, MAX_LEGS + 1),
        sets=st.integers(0, MAX_SETS + 1),
        players=st.integers(0, MAX_PLAYERS + 1),
        start=st.sampled_from([*STARTS, 1, 1002]),
    )
    def change(self, change, option, enabled, kind, legs, sets, players, start) -> None:
        """A rule, the format, the game or a new leg, as the entities set them."""
        game = self.game
        if change == "option":
            # As the coordinator does: double in, the bull-off and teams start anew.
            game.set_option(option, enabled)
            if option in ("double_in", "bull_off", "teams"):
                game.new_match()
        elif change == "format":
            game.set_format(legs, sets)
            game.set_players(players)
        elif change == "start":
            game.set_start(players, start)
        elif change == "rounds":
            game.set_rounds(9 + 9 * enabled, legs)
        elif change == "game":
            game.play(kind)
        else:
            game.new_leg()

    @rule()
    def restart(self) -> None:
        """Home Assistant stops and starts; darts on the board do not count."""
        saved = stored_as_json(self.game)
        restored = PracticeGame()
        restored.restore(saved)
        assert stored_as_json(restored) == saved
        self.game = restored
        self.darts, self.positions = [], []
        self._track()

    @invariant()
    def the_snapshot_is_consistent(self) -> None:
        game = self.game
        snapshot = game.snapshot()
        json.dumps(snapshot)
        if snapshot["game"] is None:
            return
        players = snapshot["players"]
        assert players == len(game.players)
        assert 1 <= snapshot["player"] <= players
        winner = snapshot["winner"]
        teams = snapshot["teams"]
        assert teams is None or (
            players == 4 and snapshot["game"] in (*GAMES, *CRICKET_GAMES)
        )

        def partners(first: int | None, second: int) -> bool:
            """The same player, or partners in a team."""
            if first is None:
                return False
            return first == second or bool(teams and (first - second) % 2 == 0)

        for score in snapshot["scores"]:
            assert 0 <= score["legs"] <= score["match_legs"]
            if players > 1:
                assert score["legs"] <= game.legs_to_win
                assert score["sets"] <= game.sets_to_win
            won = partners(winner, score["player"])
            # Only the winners have a won match, with every set it needed.
            assert won == (players > 1 and score["sets"] == game.sets_to_win)
            if snapshot["game"] in GAMES:
                assert 0 <= score["remaining"] <= score["start"]
                # Every leg can still be won: nobody stands on 1 with double out.
                open_leg = winner is None and snapshot["double_out"]
                assert not (open_leg and score["remaining"] == 1)
                # Nothing is left for the winners, or for a checkout on the board.
                checkout = snapshot["won"] and partners(
                    snapshot["player"], score["player"]
                )
                assert (score["remaining"] == 0) == (won or checkout)
            elif snapshot["game"] in CRICKET_GAMES:
                assert len(score["marks"]) == len(snapshot["numbers"])
                assert all(0 <= mark <= 3 for mark in score["marks"])
            else:
                assert score["points"] >= 0
                if snapshot["game"] == "killer":
                    assert 0 <= score["lives"] <= KILLER_LIVES
        assert snapshot["darts"] >= 0

    @invariant()
    def the_bull_off_waits_for_everybody(self) -> None:
        bulling = self.game.bulling
        if bulling is not None:
            assert 0 <= bulling.index < len(bulling.order)
            assert set(bulling.hits) == set(bulling.distances)
            assert len(bulling.hits) == bulling.index


PracticeMachine.TestCase.settings = settings(
    max_examples=200, stateful_step_count=80, deadline=None
)
# 200 games take 10-25 s on a busy machine, and shrinking a failure takes longer:
# a generous limit lets a real failure show its example instead of a timeout.
TestPracticeMachine = pytest.mark.timeout(180)(PracticeMachine.TestCase)
