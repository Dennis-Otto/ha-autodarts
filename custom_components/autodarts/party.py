"""Party games for one to four players and the bull-off.

Shanghai, Halve-It and Killer, and Golf, Baseball and Count-Up, which play a
fixed number of rounds and settle a tie at the top in extra rounds.

A party game follows the darts of the visit for the player at the board and
books the visit when the darts are pulled, like X01. It knows its own rules:
who throws next, when a player wins at once, and who wins at the end.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .scoring import score
from .training import hit_key

PARTY_GAMES = ("shanghai", "halve_it", "killer", "golf", "baseball", "count_up")
SHANGHAI_ROUNDS = 7
# Halve-It: a number, any double (D), any treble (T) or the bull (25) per round.
HALVE_IT_TARGETS = ("15", "16", "D", "17", "18", "T", "19", "20", "25")
HALVE_IT_START = 40
KILLER_LIVES = 3
# Board Manager positions are relative to the outer edge of the double ring.
BOARD_RADIUS_MM = 170
# The bullseye beats the outer bull, which beats every other bed.
BULL_BEDS = {"BULL": 2, "25": 1}
GOLF_HOLES = (9, 18)
BASEBALL_INNINGS = 9
COUNT_UP_ROUNDS = 8
MAX_ROUNDS = 20
# Golf strokes of a dart at the hole: treble, double, inner and outer single.
GOLF_STROKES = {3: 1, 2: 2}
GOLF_INNER, GOLF_OUTER, GOLF_MISS = 3, 4, 5
# Singles closer to the centre than the middle of the treble ring (97 to
# 107 mm) are inner singles.
INNER_SINGLE = 102 / BOARD_RADIUS_MM


def distance_mm(position: tuple[float, float] | None) -> float | None:
    """How far a dart landed from the centre of the board, in millimetres."""
    if position is None:
        return None
    return round(math.hypot(*position) * BOARD_RADIUS_MM, 1)


def inner_single(position: tuple[float, float] | None) -> bool | None:
    """Whether a single landed inside the treble ring; None without a position."""
    return None if position is None else math.hypot(*position) < INNER_SINGLE


class BullOff:
    """Every player throws one dart at the bull; the closest starts the match.

    As the WDF and PDC rules want, the bullseye beats the outer bull, which
    beats every other bed, and two darts in the same bull bed throw again, in
    reverse order. Outside the bull, the measured distance decides; so it does
    inside, if players want. Darts the board did not measure cannot be told
    apart, so their players throw again as well.
    """

    def __init__(self, order: list[int]) -> None:
        self.order = list(order)
        self.index = 0
        # The bed each player hit, as BULL, 25 or S20, and how far from the
        # centre, where the board measured it.
        self.hits: dict[int, str] = {}
        self.distances: dict[int, float | None] = {}
        self.rethrow = False

    @property
    def thrower(self) -> int:
        return self.order[self.index]

    def book(
        self,
        dart: dict[str, Any],
        position: tuple[float, float] | None,
        by_distance: bool = False,
    ) -> int | None:
        """The first dart of the visit counts; the winner once everybody threw."""
        self.hits[self.thrower] = hit_key(dart)
        self.distances[self.thrower] = distance_mm(position)
        self.index += 1
        if self.index < len(self.order):
            return None
        closest = self._closest(by_distance)
        if len(closest) == 1:
            return closest[0]
        # A tie throws again among the tied players, the last one first.
        self.order, self.index = closest[::-1], 0
        self.hits, self.distances, self.rethrow = {}, {}, True
        return None

    def _closest(self, by_distance: bool) -> list[int]:
        """The players whose darts nothing beats."""
        beds = {player: BULL_BEDS.get(self.hits[player], 0) for player in self.order}
        best = max(beds.values())
        closest = [player for player in self.order if beds[player] == best]
        if len(closest) == 1 or (best and not by_distance):
            return closest
        measured = [
            distance
            for player in closest
            if (distance := self.distances[player]) is not None
        ]
        if len(measured) < len(closest):
            return closest
        nearest = min(measured)
        return [player for player in closest if self.distances[player] == nearest]

    def stored(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "index": self.index,
            "hits": self.hits,
            "distances": self.distances,
            "rethrow": self.rethrow,
        }

    @classmethod
    def restored(cls, saved: object, players: int) -> BullOff | None:
        if not isinstance(saved, dict):
            return None
        order = saved.get("order")
        if (
            not isinstance(order, list)
            or not order
            or not all(
                type(player) is int and 0 <= player < players for player in order
            )
            or len(set(order)) != len(order)
        ):
            return None
        bull_off = cls(order)
        bull_off.rethrow = saved.get("rethrow") is True
        index = saved.get("index")
        bull_off.index = index if type(index) is int and 0 <= index < len(order) else 0
        thrown = order[: bull_off.index]
        hits, distances = saved.get("hits"), saved.get("distances")
        for key, value in (hits if isinstance(hits, dict) else {}).items():
            player = int(key) if str(key).isdigit() else -1
            if player in thrown and isinstance(value, str):
                bull_off.hits[player] = value
        for key, value in (distances if isinstance(distances, dict) else {}).items():
            player = int(key) if str(key).isdigit() else -1
            number = isinstance(value, int | float) and not isinstance(value, bool)
            if player in thrown and (number or value is None):
                bull_off.distances[player] = None if value is None else float(value)
        # Up to version 1.5, only distances were kept: that round starts again.
        if not len(bull_off.hits) == len(bull_off.distances) == bull_off.index:
            bull_off.index, bull_off.hits, bull_off.distances = 0, {}, {}
        return bull_off


@dataclass
class Visit:
    """What a visit changes, worked out without booking it."""

    points: list[int]
    won: int | None = None
    lives: list[int] = field(default_factory=list)
    killers: list[bool] = field(default_factory=list)
    numbers: list[int | None] = field(default_factory=list)
    hits: int = 0
    # Darts that count: all of the visit, or up to the dart that won the leg.
    darts: int = 0


class PartyGame(ABC):
    """The rules of one party game for the players at the board."""

    kind = ""
    start = 0
    # Rounds of a leg, where the game has a fixed number.
    rounds: int | None = None

    def __init__(self, players: int) -> None:
        self.players = players
        self.new_leg(players, 0)

    def new_leg(self, players: int, starter: int) -> None:
        self.players = players
        self.starter = starter
        self.points = [self.start] * players
        self.hits = [0] * players
        self.turns = 0

    @property
    def round(self) -> int:
        return self.turns // self.players + 1

    @property
    def shown_round(self) -> int | None:
        """The round the card shows, which never passes the last one."""
        return min(self.round, self.rounds) if self.rounds else None

    def playoff(self) -> list[int] | None:
        """The players of extra rounds after a tie, while they play them."""
        return None

    @abstractmethod
    def target(self, player: int) -> str | None:
        """What the player aims at next, if the game names one."""

    @abstractmethod
    def visit(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        """What the darts of the visit change, without booking them."""

    def book(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        """Keep the visit; the winner when it decides the leg."""
        result = self.visit(player, darts)
        self.points = result.points
        self.hits[player] += result.hits
        self.turns += 1
        if result.won is None:
            result.won = self._decided()
        return result

    def _decided(self) -> int | None:
        return None

    def next(self, player: int) -> int:
        return (player + 1) % self.players

    def _best(self) -> int | None:
        """The most points win; more hits break a tie, otherwise nobody wins."""
        ranking = sorted(
            range(self.players),
            key=lambda index: (self.points[index], self.hits[index]),
            reverse=True,
        )
        first = ranking[0]
        if len(ranking) > 1 and (self.points[first], self.hits[first]) == (
            self.points[ranking[1]],
            self.hits[ranking[1]],
        ):
            return -1
        return first

    def details(self, player: int) -> dict[str, Any]:
        return {}

    def stored(self) -> dict[str, Any]:
        return {
            "starter": self.starter,
            "points": list(self.points),
            "hits": list(self.hits),
            "turns": self.turns,
        }

    def restore(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        size = self.players

        def counts(key: str, low: int = 0) -> list[int] | None:
            values = saved.get(key)
            if (
                isinstance(values, list)
                and len(values) == size
                and all(type(value) is int and value >= low for value in values)
            ):
                return list(values)
            return None

        starter = saved.get("starter")
        self.starter = starter if type(starter) is int and 0 <= starter < size else 0
        self.points = counts("points") or self.points
        self.hits = counts("hits") or self.hits
        turns = saved.get("turns")
        self.turns = turns if type(turns) is int and turns >= 0 else 0


class Shanghai(PartyGame):
    """Seven rounds at 1 to 7; a single, double and treble in one visit wins."""

    kind = "shanghai"
    rounds = SHANGHAI_ROUNDS

    def target(self, player: int) -> str | None:
        return str(min(self.round, SHANGHAI_ROUNDS))

    def visit(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        number = min(self.round, SHANGHAI_ROUNDS)
        points = list(self.points)
        hits: list[int] = []
        for count, dart in enumerate(darts, 1):
            # A miss next to the number is no hit.
            if dart["number"] != number or dart["multiplier"] == 0:
                continue
            points[player] += score(dart)
            hits.append(dart["multiplier"])
            if set(hits) >= {1, 2, 3}:
                return Visit(points, player, hits=len(hits), darts=count)
        return Visit(points, hits=len(hits), darts=len(darts))

    def _decided(self) -> int | None:
        return self._best() if self.turns >= SHANGHAI_ROUNDS * self.players else None


class HalveIt(PartyGame):
    """Nine targets from 40 points; a visit without a hit halves the score."""

    kind = "halve_it"
    start = HALVE_IT_START
    rounds = len(HALVE_IT_TARGETS)

    def target(self, player: int) -> str | None:
        return HALVE_IT_TARGETS[min(self.round, len(HALVE_IT_TARGETS)) - 1]

    @staticmethod
    def hit(dart: dict[str, Any], target: str) -> bool:
        """Any bed of the number counts; D and T mean any double or treble,
        the bullseye included, and 25 the outer bull or the bullseye."""
        number, multiplier = dart["number"], dart["multiplier"]
        if number == 0 or multiplier == 0:
            return False
        if target == "D":
            return bool(multiplier == 2)
        if target == "T":
            return bool(multiplier == 3)
        return bool(number == int(target))

    def visit(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        target = self.target(player) or ""
        hits = [dart for dart in darts if self.hit(dart, target)]
        points = list(self.points)
        points[player] += sum(score(dart) for dart in hits)
        if not hits and len(darts) >= 3:
            # Halving rounds down.
            points[player] //= 2
        return Visit(points, hits=len(hits), darts=len(darts))

    def book(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        # A visit ends with fewer than three darts when darts miss the board.
        thrown = len(darts)
        if not any(self.hit(dart, self.target(player) or "") for dart in darts):
            darts = [*darts, *[{"number": 0, "multiplier": 0}] * 3][:3]
        result = super().book(player, darts)
        result.darts = thrown
        return result

    def _decided(self) -> int | None:
        done = self.turns >= len(HALVE_IT_TARGETS) * self.players
        return self._best() if done else None


class Killer(PartyGame):
    """Everybody picks a number; hit your double to become a killer, then
    take the lives of the others with their doubles. The last one alive wins.
    """

    kind = "killer"

    def new_leg(self, players: int, starter: int) -> None:
        super().new_leg(players, starter)
        self.numbers: list[int | None] = [None] * players
        self.lives = [KILLER_LIVES] * players
        self.killers = [False] * players

    @property
    def choosing(self) -> bool:
        return None in self.numbers

    def target(self, player: int) -> str | None:
        number = self.numbers[player]
        if number is None:
            return None
        return None if self.killers[player] else f"D{number}"

    def visit(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        numbers, lives, killers = (
            list(self.numbers),
            list(self.lives),
            list(self.killers),
        )
        if self.choosing:
            # One dart in any bed of a number that nobody has yet picks it.
            dart = darts[0] if darts else None
            if (
                dart
                and dart["multiplier"] > 0
                and 1 <= dart["number"] <= 20
                and dart["number"] not in numbers
            ):
                numbers[player] = dart["number"]
            return Visit(
                list(self.points), None, lives, killers, numbers, darts=len(darts)
            )
        won, counted = None, len(darts)
        for count, dart in enumerate(darts, 1):
            if lives[player] == 0:
                # Out of the game: the rest of the visit does nothing.
                break
            if dart["multiplier"] != 2 or dart["number"] not in numbers:
                continue
            owner = numbers.index(dart["number"])
            if owner == player and not killers[player]:
                killers[player] = True
            elif killers[player] and lives[owner] > 0:
                # A killer hitting their own double loses a life, too.
                lives[owner] -= 1
                if lives[player] == 0:
                    killers[player] = False
            alive = [index for index, left in enumerate(lives) if left > 0]
            if len(alive) == 1:
                won, counted = alive[0], count
                break
        return Visit(list(self.points), won, lives, killers, numbers, darts=counted)

    def book(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        # Only a dart decides a Killer leg, never the end of a round.
        result = super().book(player, darts)
        self.numbers, self.lives, self.killers = (
            result.numbers,
            result.lives,
            result.killers,
        )
        return result

    def next(self, player: int) -> int:
        if self.choosing and self.numbers[player] is None:
            # A dart that picked no number is thrown again.
            return player
        following = player
        for _ in range(self.players):
            following = (following + 1) % self.players
            if self.choosing:
                if self.numbers[following] is None:
                    return following
            elif self.lives[following] > 0:
                return following
        return player

    def details(self, player: int) -> dict[str, Any]:
        return {
            "number": self.numbers[player],
            "lives": self.lives[player],
            "killer": self.killers[player],
        }

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "numbers": list(self.numbers),
            "lives": list(self.lives),
            "killers": list(self.killers),
        }

    def restore(self, saved: object) -> None:
        super().restore(saved)
        if not isinstance(saved, dict):
            return
        numbers, lives, killers = (
            saved.get("numbers"),
            saved.get("lives"),
            saved.get("killers"),
        )
        size = self.players
        if (
            isinstance(numbers, list)
            and len(numbers) == size
            and all(
                number is None or (type(number) is int and 1 <= number <= 20)
                for number in numbers
            )
            and len({number for number in numbers if number is not None})
            == len([number for number in numbers if number is not None])
        ):
            self.numbers = list(numbers)
        if (
            isinstance(lives, list)
            and len(lives) == size
            and all(type(left) is int and 0 <= left <= KILLER_LIVES for left in lives)
        ):
            self.lives = list(lives)
        if isinstance(killers, list) and len(killers) == size:
            self.killers = [killer is True for killer in killers]


class RoundsGame(PartyGame):
    """A fixed number of rounds for everybody; the best total wins.

    A tie at the top after the last round plays extra rounds among the tied
    players, in their throwing order, until one of them is ahead after a
    round. Round n aims at the number n, and extra rounds carry on from
    there, after 20 from 1 again.
    """

    default_rounds = 9
    lowest_wins = False

    def __init__(self, players: int, rounds: int | None = None) -> None:
        self.length = rounds or self.default_rounds
        self.rounds = self.length
        super().__init__(players)

    def new_leg(self, players: int, starter: int) -> None:
        super().new_leg(players, starter)
        self.current_round = 1
        # The players of the round in throwing order, and how many have thrown.
        self.lineup = [(starter + offset) % players for offset in range(players)]
        self.thrown = 0
        # The score of every round, per player.
        self.scorecard: list[list[int]] = [[] for _ in range(players)]

    @property
    def round(self) -> int:
        return self.current_round

    @property
    def shown_round(self) -> int | None:
        return self.current_round

    def playoff(self) -> list[int] | None:
        return list(self.lineup) if self.current_round > self.length else None

    def number(self) -> int:
        return (self.current_round - 1) % MAX_ROUNDS + 1

    def target(self, player: int) -> str | None:
        return str(self.number())

    @abstractmethod
    def score(self, darts: list[dict[str, Any]]) -> tuple[int, int]:
        """The points and the hits of a visit in the current round."""

    def visit(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        points = list(self.points)
        scored, hits = self.score(darts)
        points[player] += scored
        return Visit(points, hits=hits, darts=len(darts))

    def book(self, player: int, darts: list[dict[str, Any]]) -> Visit:
        result = self.visit(player, darts)
        self.scorecard[player].append(result.points[player] - self.points[player])
        self.points = result.points
        self.hits[player] += result.hits
        self.turns += 1
        self.thrown += 1
        if self.thrown == len(self.lineup):
            result.won = self._round_played()
        return result

    def _round_played(self) -> int | None:
        """The winner once the last round decides the leg; otherwise the next round."""
        if self.current_round >= self.length:
            pick = min if self.lowest_wins else max
            best = pick(self.points[player] for player in self.lineup)
            leaders = [player for player in self.lineup if self.points[player] == best]
            if len(leaders) == 1:
                return leaders[0]
            self.lineup = leaders
        self.current_round += 1
        self.thrown = 0
        return None

    def next(self, player: int) -> int:
        return self.lineup[self.thrown]

    def details(self, player: int) -> dict[str, Any]:
        return {"scorecard": list(self.scorecard[player])}

    def stored(self) -> dict[str, Any]:
        return {
            **super().stored(),
            "round": self.current_round,
            "lineup": list(self.lineup),
            "thrown": self.thrown,
            "scorecard": [list(scores) for scores in self.scorecard],
        }

    def restore(self, saved: object) -> None:
        super().restore(saved)
        if not isinstance(saved, dict):
            return
        size = self.players
        current, lineup = saved.get("round"), saved.get("lineup")
        thrown, scorecard = saved.get("thrown"), saved.get("scorecard")
        if type(current) is int and current >= 1:
            self.current_round = current
        if (
            isinstance(lineup, list)
            and lineup
            and all(type(player) is int and 0 <= player < size for player in lineup)
            and len(set(lineup)) == len(lineup)
        ):
            self.lineup = list(lineup)
        # Everybody has thrown once the last round decided the leg.
        if type(thrown) is int and 0 <= thrown <= len(self.lineup):
            self.thrown = thrown
        if (
            isinstance(scorecard, list)
            and len(scorecard) == size
            and all(
                isinstance(scores, list)
                and all(type(value) is int and value >= 0 for value in scores)
                for scores in scorecard
            )
        ):
            self.scorecard = [list(scores) for scores in scorecard]


def golf_strokes(dart: dict[str, Any], hole: int) -> int:
    """Strokes of a dart at the hole: treble 1, double 2, inner single 3,
    outer single 4, anything else 5. A single without a position counts as
    an outer single."""
    if dart["number"] != hole or dart["multiplier"] == 0:
        return GOLF_MISS
    if dart["multiplier"] in GOLF_STROKES:
        return GOLF_STROKES[dart["multiplier"]]
    return GOLF_INNER if dart.get("inner") else GOLF_OUTER


class Golf(RoundsGame):
    """Nine or 18 holes, hole n at the number n; the last dart of the visit
    counts, so players stop by pulling their darts. The fewest strokes win."""

    kind = "golf"
    lowest_wins = True

    def score(self, darts: list[dict[str, Any]]) -> tuple[int, int]:
        if not darts:
            return 0, 0
        strokes = golf_strokes(darts[-1], self.number())
        return strokes, int(strokes < GOLF_MISS)


class Baseball(RoundsGame):
    """Nine innings, inning n at the number n: a single scores one run, a
    double two, a treble three. The most runs win."""

    kind = "baseball"

    def score(self, darts: list[dict[str, Any]]) -> tuple[int, int]:
        number = self.number()
        hits = [
            dart["multiplier"]
            for dart in darts
            if dart["number"] == number and dart["multiplier"] > 0
        ]
        return sum(hits), len(hits)


class CountUp(RoundsGame):
    """Every dart scores its value for a number of rounds; the most points win."""

    kind = "count_up"
    default_rounds = COUNT_UP_ROUNDS

    def target(self, player: int) -> str | None:
        return None

    def score(self, darts: list[dict[str, Any]]) -> tuple[int, int]:
        return sum(score(dart) for dart in darts), sum(
            score(dart) > 0 for dart in darts
        )


GAME_RULES: dict[str, type[PartyGame]] = {
    "shanghai": Shanghai,
    "halve_it": HalveIt,
    "killer": Killer,
    "golf": Golf,
    "baseball": Baseball,
    "count_up": CountUp,
}


def make_party(kind: str, players: int, rounds: int | None = None) -> PartyGame:
    """The rules of a party game; Golf and Count-Up take their number of rounds."""
    rules = GAME_RULES[kind]
    if issubclass(rules, RoundsGame):
        return rules(players, rounds)
    return rules(players)
