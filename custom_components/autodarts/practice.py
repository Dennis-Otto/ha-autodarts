"""Practice games on the local board for up to four players, and training games.

X01, Cricket and the party games Shanghai, Halve-It and Killer; with several
players, a bull-off can decide who starts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.util import dt as dt_util

from .checkout import checkout
from .cricket import CRICKET_NUMBERS, marks_per_round, next_target, play_visit
from .doubles import DoubleStats, aimed_at, hits
from .drills import DRILLS, Drill, make_drill
from .party import (
    HALVE_IT_TARGETS,
    PARTY_GAMES,
    SHANGHAI_ROUNDS,
    BullOff,
    PartyGame,
    Visit,
    distance_mm,
    make_party,
)
from .profiles import Profiles
from .scoring import average as _average
from .scoring import evaluate_visit, is_double, rate, score
from .training import hit_key

GAMES = (101, 301, 501, 701, 901, 1001)
CRICKET = "cricket"
LEG_HISTORY = 10
# The statistics cover the last ten legs.
STATS_LEGS = 10
STATS_KEYS = ("first9_points", "first9_darts", "at_double", "checkouts")
MAX_PLAYERS = 4
MAX_LEGS = 11
MAX_SETS = 7
NAME_LENGTH = 20


def _count(value: object, low: int, high: int, default: int) -> int:
    return value if type(value) is int and low <= value <= high else default


@dataclass
class Player:
    """Scores of one player; remaining, darts and points restart every leg."""

    remaining: int = 0
    darts: int = 0
    points: int = 0
    legs: int = 0
    sets: int = 0
    match_darts: int = 0
    match_points: int = 0
    # Points of the first nine darts and darts thrown at a double, per leg.
    first9_points: int = 0
    first9_darts: int = 0
    at_double: int = 0
    # Cricket: marks per number, and the marks that counted per leg and match.
    marks: list[int] = field(default_factory=lambda: [0] * len(CRICKET_NUMBERS))
    marks_hit: int = 0
    match_marks: int = 0
    # Double in: scoring starts with the first double of the leg.
    opened: bool = False

    def new_leg(self, game: int) -> None:
        self.remaining, self.darts, self.points = game, 0, 0
        self.first9_points, self.first9_darts, self.at_double = 0, 0, 0
        self.marks, self.marks_hit = [0] * len(CRICKET_NUMBERS), 0
        self.opened = False

    @classmethod
    def restored(cls, saved: object, game: int) -> Player:
        data = saved if isinstance(saved, dict) else {}
        numbers = {
            key: _count(data.get(key), 0, 10**6, 0)
            for key, value in asdict(cls()).items()
            if type(value) is int
        }
        marks = data.get("marks")
        valid = isinstance(marks, list) and len(marks) == len(CRICKET_NUMBERS)
        player = cls(
            **numbers,
            marks=[_count(mark, 0, 3, 0) for mark in marks]
            if valid and isinstance(marks, list)
            else [0] * len(CRICKET_NUMBERS),
            opened=data.get("opened") is True,
        )
        if player.remaining > game:
            player.new_leg(game)
        return player


class PracticeGame:
    """X01 legs played with the darts the board detects.

    The training session reports the darts of the current visit; a visit
    ends when the darts are pulled, and then the next player throws. A bust
    keeps the score of the visit start. With several players, legs make sets
    and sets make the match; the result stays until the next dart.
    """

    def __init__(self) -> None:
        # The X01 start score; 0 while no X01 game is played.
        self.game = 0
        self.cricket = False
        self.party: PartyGame | None = None
        self.double_out = True
        self.double_in = False
        self.bull_off = False
        # Checkout routes over the strongest doubles of the player at the board.
        self.personal_routes = False
        # The bull-off before a match of several players, while it runs.
        self.bulling: BullOff | None = None
        self.legs_to_win = 1
        self.sets_to_win = 1
        self.names = [""] * MAX_PLAYERS
        self.players = [Player()]
        self.current = 0
        self.starter = 0
        self.winner: int | None = None
        self.legs: list[dict[str, Any]] = []
        self.leg_stats: list[dict[str, int]] = []
        self.legs_total = 0
        # The training game played instead of X01, if any.
        self.drill: str | None = None
        self.drills: dict[str, Drill] = {kind: make_drill(kind) for kind in DRILLS}
        self.profiles = Profiles()
        self.doubles = DoubleStats()
        self._visit: list[dict[str, Any]] = []
        # Board positions of the visit's darts, where the board reports them.
        self._positions: list[tuple[float, float] | None] = []
        # Darts of the current visit thrown before the leg began.
        self._skip = 0
        self._announced: str | None = None

    # -- storage ---------------------------------------------------------------

    def restore(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        if saved.get("game") in GAMES:
            self.game = saved["game"]
        self.cricket = saved.get("game") == CRICKET
        for option in ("double_out", "double_in", "bull_off", "personal_routes"):
            if isinstance(saved.get(option), bool):
                setattr(self, option, saved[option])
        self.legs_to_win = _count(saved.get("legs_to_win"), 1, MAX_LEGS, 1)
        self.sets_to_win = _count(saved.get("sets_to_win"), 1, MAX_SETS, 1)
        names = saved.get("names")
        if isinstance(names, list):
            self.names = [
                name.strip()[:NAME_LENGTH] if isinstance(name, str) else ""
                for name in [*names, *[""] * MAX_PLAYERS][:MAX_PLAYERS]
            ]
        players = saved.get("players")
        if isinstance(players, list) and 0 < len(players) <= MAX_PLAYERS:
            self.players = [Player.restored(player, self.game) for player in players]
        else:
            # Version 1.2 stored a single player at the top level.
            self.players = [
                Player.restored(
                    {"remaining": saved.get("remaining"), "darts": saved.get("darts")},
                    self.game,
                )
            ]
        last = len(self.players) - 1
        self.current = _count(saved.get("current"), 0, last, 0)
        self.starter = _count(saved.get("starter"), 0, last, 0)
        winner = saved.get("winner")
        self.winner = winner if type(winner) is int and 0 <= winner <= last else None
        for index, player in enumerate(self.players):
            # Only the winner of a finished match has nothing left to score.
            if self.game and not player.remaining and index != self.winner:
                player.new_leg(self.game)
        kind = saved.get("game")
        self.party = (
            make_party(kind, len(self.players)) if kind in PARTY_GAMES else None
        )
        if self.party:
            self.party.restore(saved.get("party"))
        self.bulling = BullOff.restored(saved.get("bulling"), len(self.players))
        stats = saved.get("leg_stats")
        self.leg_stats = [
            {key: record[key] for key in STATS_KEYS}
            for record in (stats if isinstance(stats, list) else [])
            if isinstance(record, dict)
            and all(
                type(record.get(key)) is int and record[key] >= 0 for key in STATS_KEYS
            )
        ][:STATS_LEGS]
        total = saved.get("legs_total")
        self.legs_total = total if type(total) is int and total >= 0 else 0
        self.profiles.restore(saved.get("profiles"))
        self.doubles.restore(saved.get("doubles"))
        drills = saved.get("drills")
        for kind, drill in self.drills.items():
            state = drills.get(kind) if isinstance(drills, dict) else None
            if isinstance(state, dict):
                drill.restore(state)
        self.drill = saved["drill"] if saved.get("drill") in DRILLS else None
        if self.drill:
            self.game, self.cricket, self.party, self.bulling = 0, False, None, None
        legs = saved.get("legs")
        self.legs = [
            dict(leg)
            for leg in (legs if isinstance(legs, list) else [])
            if isinstance(leg, dict)
            and leg.get("game") in (*GAMES, CRICKET, *PARTY_GAMES)
            and type(leg.get("darts")) is int
            and leg["darts"] > 0
        ][:LEG_HISTORY]

    def stored(self) -> dict[str, Any]:
        return {
            "game": self._kind(),
            "double_out": self.double_out,
            "double_in": self.double_in,
            "bull_off": self.bull_off,
            "personal_routes": self.personal_routes,
            "doubles": self.doubles.stored(),
            "party": self.party.stored() if self.party else None,
            "bulling": self.bulling.stored() if self.bulling else None,
            "legs_to_win": self.legs_to_win,
            "sets_to_win": self.sets_to_win,
            "names": list(self.names),
            "players": [asdict(player) for player in self.players],
            "current": self.current,
            "starter": self.starter,
            "winner": self.winner,
            "legs": [dict(leg) for leg in self.legs],
            "leg_stats": [dict(record) for record in self.leg_stats],
            "legs_total": self.legs_total,
            "drill": self.drill,
            "drills": {kind: drill.stored() for kind, drill in self.drills.items()},
            "profiles": self.profiles.stored(),
        }

    # -- settings --------------------------------------------------------------

    def play(self, game: int | str) -> None:
        """Start a match of X01, Cricket or a party game, or a training game.

        0 stops playing.
        """
        self.drill = game if isinstance(game, str) and game in DRILLS else None
        self.cricket = game == CRICKET
        self.game = game if not self.drill and game in GAMES else 0
        self.party = (
            make_party(game, len(self.players))
            if isinstance(game, str) and game in PARTY_GAMES
            else None
        )
        self.new_match()

    def set_players(self, count: int) -> None:
        self.players = [Player() for _ in range(_count(count, 1, MAX_PLAYERS, 1))]
        self.new_match()

    def set_format(self, legs: int | None = None, sets: int | None = None) -> None:
        if legs is not None:
            self.legs_to_win = _count(legs, 1, MAX_LEGS, self.legs_to_win)
        if sets is not None:
            self.sets_to_win = _count(sets, 1, MAX_SETS, self.sets_to_win)
        self.new_match()

    def set_name(self, index: int, name: str) -> None:
        if 0 <= index < MAX_PLAYERS:
            self.names[index] = name.strip()[:NAME_LENGTH]

    def new_match(self) -> None:
        """Everybody starts from zero legs and sets; player 1 throws first,
        unless a bull-off decides it."""
        self.players = [Player() for _ in self.players]
        self.starter, self.winner = 0, None
        self.bulling = (
            BullOff(list(range(len(self.players))))
            if self.bull_off and len(self.players) > 1 and self._playing()
            else None
        )
        self.new_leg()

    def new_leg(self) -> None:
        """Start the leg from the full score; darts already thrown do not count."""
        if self.drill:
            self.drills[self.drill].reset(len(self._visit))
        for player in self.players:
            player.new_leg(self.game)
        if self.party:
            self.party.new_leg(len(self.players), self.starter)
        self.current = self.starter
        self._skip = len(self._visit)
        self._announced = None

    # -- play ------------------------------------------------------------------

    def _name(self, index: int) -> str | None:
        return self.names[index] or None

    def _kind(self) -> int | str:
        """The game as events and storage name it: 501, cricket or killer."""
        if self.cricket:
            return CRICKET
        return self.party.kind if self.party else self.game

    def _playing(self) -> bool:
        return bool(self.game or self.cricket or self.party)

    @property
    def kind(self) -> int | str | None:
        """The X01, Cricket or party game being played; None otherwise."""
        return self._kind() if self._playing() else None

    def _who(self, index: int) -> dict[str, Any]:
        return {
            "game": self._kind(),
            "player": index + 1,
            "name": self._name(index),
            "players": len(self.players),
        }

    def _thrown(self) -> list[dict[str, Any]]:
        return self._visit[self._skip :]

    def _opening(self) -> int:
        """Darts of the visit before the double that opens the leg with double in."""
        player = self.players[self.current]
        thrown = self._thrown()
        if not self.double_in or player.opened:
            return 0
        return next(
            (index for index, dart in enumerate(thrown) if is_double(dart)), len(thrown)
        )

    def _evaluate(self) -> tuple[int, str | None, int]:
        """Remaining score, outcome and counted darts of the current visit."""
        start = self.players[self.current].remaining
        opening = self._opening()
        remaining, outcome, darts = evaluate_visit(
            start, self._thrown()[opening:], self.double_out
        )
        return remaining, outcome, opening + darts

    def _route(self, remaining: int, darts: int) -> tuple[str, ...]:
        """The checkout route, over the player's strongest doubles if wanted."""
        preferred: tuple[str, ...] = ()
        if self.personal_routes and self.double_out:
            preferred = (
                self.profiles.preferred(self._name(self.current))
                or self.doubles.preferred()
            )
        return checkout(remaining, darts, self.double_out, preferred)

    def _record_doubles(self, attempts: list[tuple[str, bool]], player: int) -> None:
        self.doubles.record(attempts)
        self.profiles.doubles(self._name(player), attempts)

    def _position(self, index: int) -> tuple[float, float] | None:
        """Where the board saw the dart at this index of the thrown darts."""
        index += self._skip
        return self._positions[index] if index < len(self._positions) else None

    def _result(self, index: int) -> tuple[int, int, bool]:
        """Legs, sets and the match decision after the player wins this leg."""
        player = self.players[index]
        legs, sets = player.legs + 1, player.sets
        if len(self.players) == 1:
            return legs, sets, False
        if legs >= self.legs_to_win:
            legs, sets = 0, sets + 1
        return legs, sets, sets >= self.sets_to_win

    def track(
        self,
        visit: list[dict[str, Any]],
        positions: list[tuple[float, float] | None] | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Follow the darts of the current visit, announcing a bust or a win."""
        self._visit = list(visit)
        self._positions = list(positions or [])
        self._skip = min(self._skip, len(self._visit))
        if self.drill:
            return self.drills[self.drill].track(visit)
        if not self._playing():
            return []
        if self.winner is not None and self._thrown():
            # The first dart after a finished match starts the next one.
            self.new_match()
            self._skip = 0
        if self.bulling:
            return []
        if self.cricket:
            return self._track_cricket()
        if self.party:
            return self._track_party()
        remaining, outcome, darts = self._evaluate()
        if outcome == self._announced:
            return []
        self._announced = outcome
        player = self.players[self.current]
        if outcome == "bust":
            return [
                ("bust", {**self._who(self.current), "remaining": player.remaining})
            ]
        if outcome != "won":
            return []
        leg_darts = player.darts + darts
        legs, sets, match = self._result(self.current)
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "leg_won",
                {
                    **self._who(self.current),
                    "darts": leg_darts,
                    "average": _average(self.game, leg_darts),
                    "checkout": player.remaining,
                    "legs": legs,
                    "sets": sets,
                    "match": match,
                },
            )
        ]
        if match:
            events.append(
                (
                    "match_won",
                    {
                        **self._who(self.current),
                        "sets": sets,
                        "average": _average(
                            player.match_points + player.remaining,
                            player.match_darts + darts,
                        ),
                    },
                )
            )
        return events

    def finish_visit(self) -> list[tuple[str, dict[str, Any]]]:
        """Book the visit whose darts were pulled; then the next player throws."""
        events: list[tuple[str, dict[str, Any]]] = []
        if self.drill:
            self._record_doubles(self.drills[self.drill].double_attempts(), 0)
            events = self.drills[self.drill].finish_visit()
        elif not self._playing() or self.winner is not None or not self._thrown():
            pass
        elif self.bulling:
            events = self._book_bull_off()
        elif self.cricket:
            events = self._book_cricket()
        elif self.party:
            events = self._book_party()
        else:
            opening = self._opening()
            remaining, outcome, darts = self._evaluate()
            player = self.players[self.current]
            self._record_doubles(
                self._count_visit(player, outcome, darts, opening), self.current
            )
            scored = player.remaining - remaining
            player.darts += darts
            player.points += scored
            player.match_darts += darts
            player.match_points += scored
            if self.double_in and opening < darts and outcome != "bust":
                player.opened = True
            self.profiles.visit(self._name(self.current), scored)
            if outcome == "won":
                self._book_leg()
            else:
                player.remaining = remaining
                self.current = (self.current + 1) % len(self.players)
            if self.winner is None:
                # Also when playing alone: the next visit is up, for callers.
                events.append(self._turn())
        self._visit, self._skip, self._announced = [], 0, None
        return events

    def _turn(self) -> tuple[str, dict[str, Any]]:
        """The player at the board next, with what callers need to announce."""
        if self.bulling:
            return (
                "turn_changed",
                {
                    **self._who(self.bulling.thrower),
                    "remaining": None,
                    "checkout": None,
                    "bull_off": True,
                },
            )
        up = self.players[self.current]
        details: dict[str, Any] = {"remaining": None, "checkout": None}
        if self.cricket:
            details["points"] = up.points
        elif self.party:
            details["points"] = self.party.points[self.current]
            details["target"] = self.party.target(self.current)
        else:
            opened = up.opened or not self.double_in
            route = self._route(up.remaining, 3) if opened else ()
            details = {"remaining": up.remaining, "checkout": " ".join(route) or None}
        return "turn_changed", {**self._who(self.current), **details}

    # -- bull-off ----------------------------------------------------------------

    def _book_bull_off(self) -> list[tuple[str, dict[str, Any]]]:
        """The first dart of the visit counts; the closest dart starts the match."""
        bulling = self.bulling
        assert bulling is not None
        winner = bulling.book(self._thrown()[0], self._position(0))
        if winner is None:
            return [self._turn()]
        distance = bulling.distances[winner]
        self.bulling = None
        self.starter = winner
        self.new_leg()
        return [
            ("bull_off_won", {**self._who(winner), "distance": distance}),
            self._turn(),
        ]

    def _bull_off_snapshot(self) -> dict[str, Any] | None:
        bulling = self.bulling
        if bulling is None:
            return None
        thrown = self._thrown()
        live = round(distance_mm(thrown[0], self._position(0)), 1) if thrown else None
        return {
            "player": bulling.thrower + 1,
            "name": self._name(bulling.thrower),
            "throws": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "distance": live
                    if index == bulling.thrower
                    else bulling.distances.get(index),
                }
                for index in bulling.order
            ],
        }

    def _count_visit(
        self, player: Player, outcome: str | None, darts: int, opening: int = 0
    ) -> list[tuple[str, bool]]:
        """First nine darts and darts at a double of the visit being booked.

        With double in, darts before the opening double score nothing. Returns
        every dart thrown at the double that finishes, and whether it hit.
        """
        attempts: list[tuple[str, bool]] = []
        running = player.remaining
        for index, dart in enumerate(self._thrown()[:darts]):
            points = score(dart) if index >= opening else 0
            # A dart is thrown at a double when that double alone finishes.
            double = aimed_at(running) if self.double_out and index >= opening else None
            if double:
                player.at_double += 1
                attempts.append((double, hits(dart, double)))
            if player.first9_darts < 9:
                player.first9_darts += 1
                # A bust visit scores nothing, not even its early darts.
                player.first9_points += 0 if outcome == "bust" else points
            running -= points
        return attempts

    def _book_stats(self) -> None:
        """One record per leg for everybody at the board, then a fresh count."""
        self.leg_stats.insert(
            0,
            {
                "first9_points": sum(player.first9_points for player in self.players),
                "first9_darts": sum(player.first9_darts for player in self.players),
                "at_double": sum(player.at_double for player in self.players),
                "checkouts": int(self.double_out),
            },
        )
        del self.leg_stats[STATS_LEGS:]
        self.legs_total += 1
        for player in self.players:
            player.first9_points, player.first9_darts, player.at_double = 0, 0, 0

    def statistics(self) -> dict[str, Any]:
        """Averages and rates of the last ten legs and the double drills."""
        totals = {
            key: sum(record[key] for record in self.leg_stats) for key in STATS_KEYS
        }
        drill_darts, drill_hits = 0, 0
        for kind in ("doubles", "bobs_27"):
            for result in self.drills[kind].results:
                darts, hits = result.get("darts"), result.get("hits")
                if type(darts) is int and type(hits) is int and 0 <= hits <= darts:
                    drill_darts += darts
                    drill_hits += hits
        return {
            "first_9_average": _average(
                totals["first9_points"], totals["first9_darts"]
            ),
            "checkout_rate": rate(totals["checkouts"], totals["at_double"]),
            "doubles_rate": rate(
                totals["checkouts"] + drill_hits, totals["at_double"] + drill_darts
            ),
            "legs_played": self.legs_total,
            "legs_counted": len(self.leg_stats),
            "darts_at_double": totals["at_double"] + drill_darts,
        }

    # -- cricket -----------------------------------------------------------------

    def _cricket_visit(self) -> tuple[list[int], int, int, bool, int]:
        player = self.players[self.current]
        others = [
            item for index, item in enumerate(self.players) if index != self.current
        ]
        return play_visit(
            player.marks,
            player.points,
            self._thrown(),
            [item.marks for item in others],
            [item.points for item in others],
        )

    def _track_cricket(self) -> list[tuple[str, dict[str, Any]]]:
        _, points, darts, won, counted = self._cricket_visit()
        outcome = "won" if won else None
        if outcome == self._announced:
            return []
        self._announced = outcome
        if not won:
            return []
        player = self.players[self.current]
        legs, sets, match = self._result(self.current)
        leg_darts = player.darts + darts
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "leg_won",
                {
                    **self._who(self.current),
                    "darts": leg_darts,
                    "points": points,
                    "mpr": marks_per_round(player.marks_hit + counted, leg_darts),
                    "legs": legs,
                    "sets": sets,
                    "match": match,
                },
            )
        ]
        if match:
            events.append(
                (
                    "match_won",
                    {
                        **self._who(self.current),
                        "sets": sets,
                        "mpr": marks_per_round(
                            player.match_marks + counted, player.match_darts + darts
                        ),
                    },
                )
            )
        return events

    def _book_cricket(self) -> list[tuple[str, dict[str, Any]]]:
        marks, points, darts, won, counted = self._cricket_visit()
        player = self.players[self.current]
        player.marks, player.points = marks, points
        player.darts += darts
        player.match_darts += darts
        player.marks_hit += counted
        player.match_marks += counted
        if won:
            self._book_leg()
        else:
            self.current = (self.current + 1) % len(self.players)
        return [] if self.winner is not None else [self._turn()]

    def _cricket_snapshot(self, common: dict[str, Any]) -> dict[str, Any]:
        marks, points, darts, won, counted = self._cricket_visit()
        player = self.players[self.current]
        done = won or self.winner is not None
        return {
            "game": CRICKET,
            **common,
            "player": self.current + 1,
            "name": self._name(self.current),
            "winner": None if self.winner is None else self.winner + 1,
            "remaining": None,
            "checkout": None,
            "target": None if done else next_target(marks),
            "bust": False,
            "won": won,
            "visit": [hit_key(dart) for dart in self._thrown()],
            "darts": player.darts + darts,
            "average": None,
            "points": points,
            "mpr": marks_per_round(player.marks_hit + counted, player.darts + darts),
            "numbers": list(CRICKET_NUMBERS),
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "marks": marks if index == self.current else list(item.marks),
                    "points": points if index == self.current else item.points,
                    "legs": item.legs,
                    "sets": item.sets,
                    "mpr": marks_per_round(
                        item.match_marks + (counted if index == self.current else 0),
                        item.match_darts + (darts if index == self.current else 0),
                    ),
                }
                for index, item in enumerate(self.players)
            ],
        }

    # -- party games ---------------------------------------------------------------

    def _party_ready(self) -> bool:
        """Killer needs at least two players."""
        return not (
            self.party and self.party.kind == "killer" and len(self.players) < 2
        )

    def _party_won(
        self, winner: int, darts: int, points: int
    ) -> list[tuple[str, dict[str, Any]]]:
        legs, sets, match = self._result(winner)
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "leg_won",
                {
                    **self._who(winner),
                    "darts": self.players[winner].darts + darts,
                    "points": points,
                    "legs": legs,
                    "sets": sets,
                    "match": match,
                },
            )
        ]
        if match:
            events.append(("match_won", {**self._who(winner), "sets": sets}))
        return events

    def _party_visit(self) -> Visit:
        assert self.party is not None
        return self.party.visit(self.current, self._thrown())

    def _track_party(self) -> list[tuple[str, dict[str, Any]]]:
        """Shanghai and Killer can be won with a single dart."""
        if not self._party_ready():
            return []
        result = self._party_visit()
        won = result.won
        outcome = "won" if won is not None else None
        if outcome == self._announced:
            return []
        self._announced = outcome
        if won is None:
            return []
        darts = len(self._thrown()) if won == self.current else 0
        return self._party_won(won, darts, result.points[won])

    def _book_party(self) -> list[tuple[str, dict[str, Any]]]:
        assert self.party is not None
        if not self._party_ready():
            return []
        thrown = self._thrown()
        announced = self._announced == "won"
        result = self.party.book(self.current, thrown)
        events: list[tuple[str, dict[str, Any]]] = []
        if result.won is not None and result.won >= 0 and not announced:
            # A win at the end of the last round is known only now.
            darts = len(thrown) if result.won == self.current else 0
            events = self._party_won(result.won, darts, result.points[result.won])
        player = self.players[self.current]
        player.darts += len(thrown)
        player.match_darts += len(thrown)
        if result.won is not None and result.won >= 0:
            self.current = result.won
            self._book_leg()
        elif result.won is not None:
            # A tie in points and hits: the leg is played again.
            self.starter = (self.starter + 1) % len(self.players)
            self.new_leg()
        else:
            self.current = self.party.next(self.current)
        if self.winner is None:
            events.append(self._turn())
        return events

    def _party_snapshot(self, common: dict[str, Any]) -> dict[str, Any]:
        assert self.party is not None
        party = self.party
        ready = self._party_ready()
        live = ready and self.winner is None and self.bulling is None
        result = self._party_visit() if live else None
        points = result.points if result else list(party.points)
        details = [party.details(index) for index in range(len(self.players))]
        if result and party.kind == "killer":
            details = [
                {
                    "number": result.numbers[index],
                    "lives": result.lives[index],
                    "killer": result.killers[index],
                }
                for index in range(len(self.players))
            ]
        won = bool(result and result.won is not None and result.won >= 0)
        target = party.target(self.current) if live and not won else None
        if result and party.kind == "killer" and not won:
            # A killer made in this visit hunts the others from the next dart.
            number = result.numbers[self.current]
            killer = result.killers[self.current]
            target = None if number is None or killer else f"D{number}"
        rounds = {"shanghai": SHANGHAI_ROUNDS, "halve_it": len(HALVE_IT_TARGETS)}
        choosing = party.kind == "killer" and None in getattr(party, "numbers", [])
        player = self.players[self.current]
        return {
            "game": party.kind,
            **common,
            "player": self.current + 1,
            "name": self._name(self.current),
            "winner": None if self.winner is None else self.winner + 1,
            "remaining": None,
            "checkout": None,
            "target": target,
            "bust": False,
            "won": won,
            "visit": [hit_key(dart) for dart in self._thrown()],
            "darts": player.darts + len(self._thrown()),
            "average": None,
            "points": points[self.current],
            "round": min(party.round, rounds[party.kind])
            if party.kind in rounds
            else None,
            "rounds": rounds.get(party.kind),
            "phase": "choose" if choosing else "play",
            "needs_players": None if ready else 2,
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "points": points[index],
                    "legs": item.legs,
                    "sets": item.sets,
                    **details[index],
                }
                for index, item in enumerate(self.players)
            ],
        }

    def _leg_entries(self) -> list[dict[str, Any]]:
        """Every player's numbers of the leg that just ended, for the profiles."""
        entries = []
        for index, player in enumerate(self.players):
            entry: dict[str, Any] = {
                "name": self._name(index),
                "won": index == self.current,
                "darts": player.darts,
            }
            if self.cricket:
                entry["marks"] = player.marks_hit
            elif not self.party:
                entry.update(
                    points=player.points,
                    first9_points=player.first9_points,
                    first9_darts=player.first9_darts,
                    at_double=player.at_double,
                    double_out=self.double_out,
                    checkout=player.remaining if index == self.current else 0,
                )
            entries.append(entry)
        return entries

    def _match_entries(self) -> list[dict[str, Any]]:
        """Every player's result of the match that just ended, for the history."""
        entries = []
        for index, player in enumerate(self.players):
            entry: dict[str, Any] = {
                "name": self._name(index),
                "legs": player.legs,
                "sets": player.sets,
            }
            if self.cricket:
                entry["mpr"] = marks_per_round(player.match_marks, player.match_darts)
            elif self.party:
                entry["points"] = self.party.points[index]
            else:
                entry["average"] = _average(player.match_points, player.match_darts)
            entries.append(entry)
        return entries

    def _book_leg(self) -> None:
        self.profiles.leg(self._kind(), self._leg_entries())
        winner = self.players[self.current]
        if self.cricket:
            record = {
                "darts": winner.darts,
                "points": winner.points,
                "mpr": marks_per_round(winner.marks_hit, winner.darts),
            }
        elif self.party:
            record = {"darts": winner.darts, "points": self.party.points[self.current]}
        else:
            self._book_stats()
            record = {
                "darts": winner.darts,
                "average": _average(self.game, winner.darts),
                "checkout": winner.remaining,
            }
        self.legs.insert(
            0,
            {
                **self._who(self.current),
                **record,
                "ended": dt_util.utcnow().isoformat(),
            },
        )
        del self.legs[LEG_HISTORY:]
        winner.legs, winner.sets, match = self._result(self.current)
        if match:
            winner.remaining = 0
            self.winner = self.current
            self.profiles.match(
                self._kind(),
                self._match_entries(),
                self.current,
                self.legs_to_win,
                self.sets_to_win,
            )
            return
        if winner.legs == 0:
            # A won set starts the next one from zero legs for everybody.
            for player in self.players:
                player.legs = 0
        self.starter = (self.starter + 1) % len(self.players)
        self.new_leg()

    # -- state -----------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        common = {
            "double_out": self.double_out,
            "players": len(self.players),
            "legs_to_win": self.legs_to_win,
            "sets_to_win": self.sets_to_win,
            "legs": self.legs,
            "drill": self.drills[self.drill].snapshot() if self.drill else None,
            "double_in": self.double_in,
            "bull_off": self._bull_off_snapshot(),
        }
        if self.cricket:
            return self._cricket_snapshot(common)
        if self.party:
            return self._party_snapshot(common)
        if not self.game:
            return {"game": None, **common}
        remaining, outcome, darts = self._evaluate()
        thrown = len(self._thrown())
        player = self.players[self.current]
        opened = not self.double_in or player.opened or self._opening() < thrown
        if outcome == "won" or self.winner is not None or not opened:
            route: tuple[str, ...] = ()
        elif outcome == "bust" or thrown >= 3:
            # The visit is over; the next one starts with three darts.
            route = self._route(remaining, 3)
        else:
            route = self._route(remaining, 3 - thrown)
        scored = player.remaining - remaining
        leg_darts = player.darts + darts
        return {
            "game": self.game,
            **common,
            "player": self.current + 1,
            "name": self._name(self.current),
            "winner": None if self.winner is None else self.winner + 1,
            "remaining": remaining,
            "checkout": " ".join(route) or None,
            "bust": outcome == "bust",
            "won": outcome == "won",
            "visit": [hit_key(dart) for dart in self._thrown()],
            "darts": leg_darts,
            "average": _average(player.points + scored, leg_darts),
            "opened": opened,
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "remaining": remaining if index == self.current else item.remaining,
                    "opened": opened
                    if index == self.current
                    else item.opened or not self.double_in,
                    "legs": item.legs,
                    "sets": item.sets,
                    "average": _average(
                        item.match_points + (scored if index == self.current else 0),
                        item.match_darts + (darts if index == self.current else 0),
                    ),
                }
                for index, item in enumerate(self.players)
            ],
        }
