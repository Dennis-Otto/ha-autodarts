"""Practice games on the local board for up to four players, and training games.

X01 with a start score of its own for every player, Cricket, Cut-Throat and
Tactics, the party games, and the training games; X01 and the Cricket games
also as two teams of two. With several players, a bull-off can decide who
starts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.util import dt as dt_util

from .checkout import checkout
from .cricket import (
    CRICKET_GAMES,
    CRICKET_NUMBERS,
    CricketVisit,
    marks_per_round,
    next_target,
    play_visit,
)
from .doubles import DoubleStats, aimed_at, hits
from .drills import DRILLS, CheckoutDrill, Drill, make_drill
from .party import (
    COUNT_UP_ROUNDS,
    GOLF_HOLES,
    MAX_ROUNDS,
    PARTY_GAMES,
    BullOff,
    PartyGame,
    Visit,
    distance_mm,
    inner_single,
    make_party,
)
from .positions import x01_aims
from .profiles import NAME_LENGTH, Profiles
from .scoring import VISIT_DARTS, evaluate_visit, is_double, rate, score
from .scoring import average as _average
from .training import hit_key

GAMES = (101, 301, 501, 701, 901, 1001)
LEG_HISTORY = 10
# The statistics cover the last ten legs.
STATS_LEGS = 10
STATS_KEYS = ("first9_points", "first9_darts", "at_double", "checkouts")
MAX_PLAYERS = 4
MAX_LEGS = 11
MAX_SETS = 7
# A start score of its own: 0 plays the game's, otherwise 2 to 1001.
MAX_START = 1001
# Two teams of two: players 1 and 3 against players 2 and 4.
TEAM_PLAYERS = 4
# The rules of the practice game that players switch on and off.
OPTIONS = (
    "double_out",
    "double_in",
    "bull_off",
    "bull_off_distance",
    "personal_routes",
    "teams",
)
# The games to choose from, as the practice game select and start_game offer them.
GAME_OPTIONS = (*(str(game) for game in GAMES), *CRICKET_GAMES, *PARTY_GAMES, *DRILLS)


def _count(value: object, low: int, high: int, default: int) -> int:
    return value if type(value) is int and low <= value <= high else default


def valid_start(value: object) -> bool:
    """0 for the game's start score, or a start score of 2 to 1001."""
    return type(value) is int and (value == 0 or 2 <= value <= MAX_START)


@dataclass
class Player:
    """Scores of one player; remaining, darts and points restart every leg."""

    remaining: int = 0
    darts: int = 0
    points: int = 0
    # Legs won in the current set, or in the final set of a finished match.
    legs: int = 0
    sets: int = 0
    match_legs: int = 0
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

    def new_leg(self, start: int, slots: int = len(CRICKET_NUMBERS)) -> None:
        self.remaining, self.darts, self.points = start, 0, 0
        self.first9_points, self.first9_darts, self.at_double = 0, 0, 0
        self.marks, self.marks_hit = [0] * slots, 0
        self.opened = False

    @classmethod
    def restored(cls, saved: object, slots: int = len(CRICKET_NUMBERS)) -> Player:
        data = saved if isinstance(saved, dict) else {}
        numbers = {
            key: _count(data.get(key), 0, 10**6, 0)
            for key, value in asdict(cls()).items()
            if type(value) is int
        }
        marks = data.get("marks")
        valid = isinstance(marks, list) and len(marks) == slots
        return cls(
            **numbers,
            marks=[_count(mark, 0, 3, 0) for mark in marks]
            if valid and isinstance(marks, list)
            else [0] * slots,
            opened=data.get("opened") is True,
        )


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
        # The Cricket game being played: cricket, cut_throat or tactics.
        self.cricket: str | None = None
        self.party: PartyGame | None = None
        self.double_out = True
        self.double_in = False
        self.bull_off = False
        # Two darts in the same bull bed: the measured distance decides instead
        # of a rethrow, as the official rules want.
        self.bull_off_distance = False
        # Checkout routes over the strongest doubles of the player at the board.
        self.personal_routes = False
        # Four players of X01 or Cricket play as two teams of two.
        self.teams = False
        # A start score of their own per player; 0 plays the game's.
        self.starts = [0] * MAX_PLAYERS
        self.golf_holes = GOLF_HOLES[0]
        self.count_up_rounds = COUNT_UP_ROUNDS
        # The bull-off before a match of several players, while it runs.
        self.bulling: BullOff | None = None
        self.legs_to_win = 1
        self.sets_to_win = 1
        self.names = [""] * MAX_PLAYERS
        self.players = [Player()]
        self.current = 0
        # Who throws first in the current leg, and in the current set: the
        # throw passes on every leg within a set and every set within the match.
        self.starter = 0
        self.set_starter = 0
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
        kind = saved.get("game")
        if kind in GAMES:
            self.game = kind
        self.cricket = kind if kind in CRICKET_GAMES else None
        for option in OPTIONS:
            if isinstance(saved.get(option), bool):
                setattr(self, option, saved[option])
        starts = saved.get("starts")
        if isinstance(starts, list) and len(starts) == MAX_PLAYERS:
            self.starts = [start if valid_start(start) else 0 for start in starts]
        if saved.get("golf_holes") in GOLF_HOLES:
            self.golf_holes = saved["golf_holes"]
        self.count_up_rounds = _count(
            saved.get("count_up_rounds"), 1, MAX_ROUNDS, COUNT_UP_ROUNDS
        )
        self.legs_to_win = _count(saved.get("legs_to_win"), 1, MAX_LEGS, 1)
        self.sets_to_win = _count(saved.get("sets_to_win"), 1, MAX_SETS, 1)
        names = saved.get("names")
        if isinstance(names, list):
            self.names = [
                name.strip()[:NAME_LENGTH] if isinstance(name, str) else ""
                for name in [*names, *[""] * MAX_PLAYERS][:MAX_PLAYERS]
            ]
        slots = len(self._numbers())
        players = saved.get("players")
        if isinstance(players, list) and 0 < len(players) <= MAX_PLAYERS:
            self.players = [Player.restored(player, slots) for player in players]
        else:
            # Version 1.2 stored a single player at the top level.
            self.players = [
                Player.restored(
                    {"remaining": saved.get("remaining"), "darts": saved.get("darts")},
                    slots,
                )
            ]
        last = len(self.players) - 1
        self.current = _count(saved.get("current"), 0, last, 0)
        self.starter = _count(saved.get("starter"), 0, last, 0)
        # Up to version 1.5, the starter passed on every leg; the legs of the
        # current set tell who started it.
        played = sum(player.legs for player in self.players)
        self.set_starter = _count(
            saved.get("set_starter"),
            0,
            last,
            (self.starter - played) % len(self.players),
        )
        winner = saved.get("winner")
        self.winner = winner if type(winner) is int and 0 <= winner <= last else None
        for index, player in enumerate(self.players):
            start = self._start(index)
            # Only the winners of a finished match have nothing left to score.
            left = player.remaining or index in self._winners()
            if self.game and (player.remaining > start or not left):
                player.new_leg(start, slots)
        self.party = (
            make_party(kind, len(self.players), self._rounds(kind))
            if kind in PARTY_GAMES
            else None
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
        for drill_kind, drill in self.drills.items():
            state = drills.get(drill_kind) if isinstance(drills, dict) else None
            if isinstance(state, dict):
                drill.restore(state)
        self.drill = saved["drill"] if saved.get("drill") in DRILLS else None
        if self.drill:
            self.game, self.cricket, self.party, self.bulling = 0, None, None, None
        legs = saved.get("legs")
        self.legs = [
            dict(leg)
            for leg in (legs if isinstance(legs, list) else [])
            if isinstance(leg, dict)
            and leg.get("game") in (*GAMES, *CRICKET_GAMES, *PARTY_GAMES)
            and type(leg.get("darts")) is int
            and leg["darts"] > 0
        ][:LEG_HISTORY]

    def stored(self) -> dict[str, Any]:
        return {
            "game": self._kind(),
            "double_out": self.double_out,
            "double_in": self.double_in,
            "bull_off": self.bull_off,
            "bull_off_distance": self.bull_off_distance,
            "personal_routes": self.personal_routes,
            "teams": self.teams,
            "starts": list(self.starts),
            "golf_holes": self.golf_holes,
            "count_up_rounds": self.count_up_rounds,
            "doubles": self.doubles.stored(),
            "party": self.party.stored() if self.party else None,
            "bulling": self.bulling.stored() if self.bulling else None,
            "legs_to_win": self.legs_to_win,
            "sets_to_win": self.sets_to_win,
            "names": list(self.names),
            "players": [asdict(player) for player in self.players],
            "current": self.current,
            "starter": self.starter,
            "set_starter": self.set_starter,
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
        """Start a match of X01, a Cricket or party game, or a training game.

        0 stops playing.
        """
        self.drill = game if isinstance(game, str) and game in DRILLS else None
        self.cricket = game if isinstance(game, str) and game in CRICKET_GAMES else None
        self.game = game if not self.drill and game in GAMES else 0
        self.party = (
            make_party(game, len(self.players), self._rounds(game))
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

    def set_start(self, index: int, start: int) -> None:
        """A start score of the player's own, or 0 for the game's; a new match."""
        if 0 <= index < MAX_PLAYERS and valid_start(start):
            self.starts[index] = start
        self.new_match()

    def set_rounds(
        self, golf_holes: int | None = None, count_up_rounds: int | None = None
    ) -> None:
        """Holes of Golf and rounds of Count-Up; a change starts the game anew
        while it is played."""
        before = {"golf": self.golf_holes, "count_up": self.count_up_rounds}
        if golf_holes in GOLF_HOLES:
            self.golf_holes = golf_holes
        if count_up_rounds is not None:
            self.count_up_rounds = _count(
                count_up_rounds, 1, MAX_ROUNDS, self.count_up_rounds
            )
        kind = self.party.kind if self.party else None
        if kind in before and before[kind] != self._rounds(kind):
            self.play(str(kind))

    def set_name(self, index: int, name: str) -> None:
        if 0 <= index < MAX_PLAYERS:
            self.names[index] = name.strip()[:NAME_LENGTH]

    def forget(self, name: str) -> None:
        """Clear the player slots with this name, in any upper and lower case."""
        key = name.strip().casefold()
        self.names = ["" if slot.casefold() == key else slot for slot in self.names]

    def new_match(self) -> None:
        """Everybody starts from zero legs and sets; player 1 throws first,
        unless a bull-off decides it."""
        self.players = [Player() for _ in self.players]
        self.starter, self.set_starter, self.winner = 0, 0, None
        self.bulling = (
            BullOff(list(range(len(self.players))))
            if self.bull_off and len(self.players) > 1 and self._playing()
            else None
        )
        self.new_leg()

    def new_leg(self) -> None:
        """Start the leg from the full score; darts already thrown do not count.

        After a finished match, the next match starts.
        """
        if self.winner is not None:
            self.new_match()
            return
        if self.drill:
            self.drills[self.drill].reset(len(self._visit))
        slots = len(self._numbers())
        for index, player in enumerate(self.players):
            player.new_leg(self._start(index), slots)
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
            return self.cricket
        return self.party.kind if self.party else self.game

    def _playing(self) -> bool:
        return bool(self.game or self.cricket or self.party)

    def _numbers(self) -> tuple[int, ...]:
        """The numbers of the Cricket game: 20 to 15 and the bull, or Tactics'."""
        return CRICKET_GAMES[self.cricket] if self.cricket else CRICKET_NUMBERS

    def _rounds(self, kind: object) -> int | None:
        return {"golf": self.golf_holes, "count_up": self.count_up_rounds}.get(
            str(kind)
        )

    def _start(self, index: int) -> int:
        """The score a player starts X01 legs from: their own, or the game's.
        Partners play from the start of the first player of their team."""
        if not self.game:
            return 0
        own = self.starts[index % 2 if self._teamed() else index]
        return own or self.game

    def _teamed(self) -> bool:
        """Four players of X01 or a Cricket game play as two teams."""
        return (
            self.teams
            and len(self.players) == TEAM_PLAYERS
            and bool(self.game or self.cricket)
        )

    def _side(self, index: int) -> list[int]:
        """The player and their partner in a team, in seat order."""
        return [index % 2, index % 2 + 2] if self._teamed() else [index]

    def _winners(self) -> list[int]:
        return [] if self.winner is None else self._side(self.winner)

    def _team_name(self, team: int) -> str | None:
        """Alex & Kim, when both players of the team have a name."""
        names = [self.names[team], self.names[team + 2]]
        return " & ".join(names) if all(names) else None

    def _share(self, index: int) -> None:
        """Partners keep one score: the remaining score and the opening double
        in X01, the marks and points in Cricket."""
        player = self.players[index]
        for other in self._side(index):
            partner = self.players[other]
            partner.remaining, partner.opened = player.remaining, player.opened
            partner.marks = list(player.marks)
            if self.cricket:
                partner.points = player.points

    def _teams_snapshot(self) -> list[dict[str, Any]] | None:
        if not self._teamed():
            return None
        return [
            {
                "team": team + 1,
                "name": self._team_name(team),
                "players": [team + 1, team + 3],
            }
            for team in (0, 1)
        ]

    @property
    def kind(self) -> int | str | None:
        """The X01, Cricket or party game being played; None otherwise."""
        return self._kind() if self._playing() else None

    @property
    def thrower(self) -> str | None:
        """The name of the player at the board in a game, if they have one."""
        if not self._playing():
            return None
        return self._name(self.bulling.thrower if self.bulling else self.current)

    def _who(self, index: int) -> dict[str, Any]:
        who = {
            "game": self._kind(),
            "player": index + 1,
            "name": self._name(index),
            "players": len(self.players),
        }
        if self._teamed():
            who["team"] = index % 2 + 1
            who["team_name"] = self._team_name(index % 2)
        return who

    def _sum(self, index: int, key: str) -> int:
        """A number of the player, or of both partners in a team."""
        return sum(getattr(self.players[other], key) for other in self._side(index))

    def _thrown(self) -> list[dict[str, Any]]:
        return self._visit[self._skip : VISIT_DARTS]

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
        """Legs in the set, sets and the match decision after the player wins
        this leg; a won set keeps its legs until the next set starts."""
        player = self.players[index]
        legs, sets = player.legs + 1, player.sets
        if len(self.players) == 1:
            return legs, sets, False
        if legs >= self.legs_to_win:
            sets += 1
        return legs, sets, sets >= self.sets_to_win

    def _final(self, winner: int, legs: int, sets: int) -> list[dict[str, Any]]:
        """Legs and sets of everybody once this leg decides the match."""
        side = self._side(winner)
        return [
            {
                "player": index + 1,
                "name": self._name(index),
                "legs": legs if index in side else player.legs,
                "sets": sets if index in side else player.sets,
                **({"team": index % 2 + 1} if self._teamed() else {}),
            }
            for index, player in enumerate(self.players)
        ]

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
        leg_darts = self._sum(self.current, "darts") + darts
        start = self._start(self.current)
        legs, sets, match = self._result(self.current)
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "leg_won",
                {
                    **self._who(self.current),
                    "darts": leg_darts,
                    "average": _average(start, leg_darts),
                    "checkout": player.remaining,
                    "start": start,
                    "double_out": self.double_out,
                    "double_in": self.double_in,
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
                        "legs": legs,
                        "sets": sets,
                        "scores": self._final(self.current, legs, sets),
                        "average": _average(
                            self._sum(self.current, "match_points") + player.remaining,
                            self._sum(self.current, "match_darts") + darts,
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
                self._share(self.current)
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
        winner = bulling.book(
            self._thrown()[0], self._position(0), self.bull_off_distance
        )
        if winner is None:
            return [self._turn()]
        won = {"distance": bulling.distances[winner], "hit": bulling.hits[winner]}
        self.bulling = None
        self.starter = self.set_starter = winner
        self.new_leg()
        return [("bull_off_won", {**self._who(winner), **won}), self._turn()]

    def _bull_off_snapshot(self) -> dict[str, Any] | None:
        bulling = self.bulling
        if bulling is None:
            return None
        thrown = self._thrown()
        live = {
            "distance": distance_mm(self._position(0)) if thrown else None,
            "hit": hit_key(thrown[0]) if thrown else None,
        }
        return {
            "player": bulling.thrower + 1,
            "name": self._name(bulling.thrower),
            "rethrow": bulling.rethrow,
            "by_distance": self.bull_off_distance,
            "throws": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    **(
                        live
                        if index == bulling.thrower
                        else {
                            "distance": bulling.distances.get(index),
                            "hit": bulling.hits.get(index),
                        }
                    ),
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

    def _opponents(self) -> list[int]:
        side = self._side(self.current)
        return [index for index in range(len(self.players)) if index not in side]

    def _cricket_visit(self) -> CricketVisit:
        player = self.players[self.current]
        opponents = [self.players[index] for index in self._opponents()]
        return play_visit(
            player.marks,
            player.points,
            self._thrown(),
            [item.marks for item in opponents],
            [item.points for item in opponents],
            self._numbers(),
            self.cricket == "cut_throat",
        )

    def _track_cricket(self) -> list[tuple[str, dict[str, Any]]]:
        visit = self._cricket_visit()
        outcome = "won" if visit.won else None
        if outcome == self._announced:
            return []
        self._announced = outcome
        if not visit.won:
            return []
        legs, sets, match = self._result(self.current)
        leg_darts = self._sum(self.current, "darts") + visit.darts
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "leg_won",
                {
                    **self._who(self.current),
                    "darts": leg_darts,
                    "points": visit.points,
                    "mpr": marks_per_round(
                        self._sum(self.current, "marks_hit") + visit.counted, leg_darts
                    ),
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
                        "legs": legs,
                        "sets": sets,
                        "scores": self._final(self.current, legs, sets),
                        "mpr": marks_per_round(
                            self._sum(self.current, "match_marks") + visit.counted,
                            self._sum(self.current, "match_darts") + visit.darts,
                        ),
                    },
                )
            )
        return events

    def _book_cricket(self) -> list[tuple[str, dict[str, Any]]]:
        visit = self._cricket_visit()
        player = self.players[self.current]
        player.marks, player.points = visit.marks, visit.points
        # Cut-Throat gives the points to the others.
        for index, points in zip(self._opponents(), visit.others, strict=True):
            self.players[index].points = points
        player.darts += visit.darts
        player.match_darts += visit.darts
        player.marks_hit += visit.counted
        player.match_marks += visit.counted
        self._share(self.current)
        if visit.won:
            self._book_leg()
        else:
            self.current = (self.current + 1) % len(self.players)
        return [] if self.winner is not None else [self._turn()]

    def _cricket_snapshot(self, common: dict[str, Any]) -> dict[str, Any]:
        visit = self._cricket_visit()
        side, opponents = self._side(self.current), self._opponents()
        done = visit.won or self.winner is not None
        darts = self._sum(self.current, "darts") + visit.darts

        def points(index: int) -> int:
            if index in side:
                return visit.points
            return visit.others[opponents.index(index)]

        return {
            "game": self.cricket,
            **common,
            "player": self.current + 1,
            "name": self._name(self.current),
            "winner": None if self.winner is None else self.winner + 1,
            "remaining": None,
            "checkout": None,
            "target": None if done else next_target(visit.marks, self._numbers()),
            "bust": False,
            "won": visit.won,
            "visit": [hit_key(dart) for dart in self._thrown()],
            "darts": darts,
            "average": None,
            "points": visit.points,
            "mpr": marks_per_round(
                self._sum(self.current, "marks_hit") + visit.counted, darts
            ),
            "numbers": list(self._numbers()),
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "marks": list(visit.marks if index in side else item.marks),
                    "points": points(index),
                    "legs": item.legs,
                    "sets": item.sets,
                    "match_legs": item.match_legs,
                    "mpr": marks_per_round(
                        item.match_marks
                        + (visit.counted if index == self.current else 0),
                        item.match_darts
                        + (visit.darts if index == self.current else 0),
                    ),
                    **({"team": index % 2 + 1} if self._teamed() else {}),
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
            events.append(
                (
                    "match_won",
                    {
                        **self._who(winner),
                        "legs": legs,
                        "sets": sets,
                        "scores": self._final(winner, legs, sets),
                    },
                )
            )
        return events

    def _party_darts(self) -> list[dict[str, Any]]:
        """The darts of the visit, with the single bed the board saw them in."""
        return [
            {**dart, "inner": inner_single(self._position(index))}
            for index, dart in enumerate(self._thrown())
        ]

    def _party_visit(self) -> Visit:
        assert self.party is not None
        return self.party.visit(self.current, self._party_darts())

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
        darts = result.darts if won == self.current else 0
        return self._party_won(won, darts, result.points[won])

    def _book_party(self) -> list[tuple[str, dict[str, Any]]]:
        assert self.party is not None
        if not self._party_ready():
            return []
        announced = self._announced == "won"
        result = self.party.book(self.current, self._party_darts())
        events: list[tuple[str, dict[str, Any]]] = []
        if result.won is not None and result.won >= 0 and not announced:
            # A win at the end of the last round is known only now.
            darts = result.darts if result.won == self.current else 0
            events = self._party_won(result.won, darts, result.points[result.won])
        # Darts after the one that decided the leg do not count.
        player = self.players[self.current]
        player.darts += result.darts
        player.match_darts += result.darts
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
        choosing = party.kind == "killer" and None in getattr(party, "numbers", [])
        playoff = party.playoff()
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
            "darts": player.darts + (result.darts if result else 0),
            "average": None,
            "points": points[self.current],
            "round": party.shown_round,
            "rounds": party.rounds,
            "playoff": None if playoff is None else [index + 1 for index in playoff],
            "phase": "choose" if choosing else "play",
            "needs_players": None if ready else 2,
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "points": points[index],
                    "legs": item.legs,
                    "sets": item.sets,
                    "match_legs": item.match_legs,
                    **details[index],
                }
                for index, item in enumerate(self.players)
            ],
        }

    def _leg_entries(self) -> list[dict[str, Any]]:
        """Every player's numbers of the leg that just ended, for the profiles."""
        entries = []
        side = self._side(self.current)
        for index, player in enumerate(self.players):
            entry: dict[str, Any] = {
                "name": self._name(index),
                "won": index in side,
                "darts": player.darts,
            }
            if self._teamed():
                # A team leg sets no record of fewest darts for one player.
                entry["team"] = True
            if self.cricket:
                entry["marks"] = player.marks_hit
            elif not self.party:
                entry.update(
                    points=player.points,
                    first9_points=player.first9_points,
                    first9_darts=player.first9_darts,
                    at_double=player.at_double,
                    double_out=self.double_out,
                    double_in=self.double_in,
                    start=self._start(index),
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
                "match_legs": player.match_legs,
            }
            if self._teamed():
                entry["team"] = index % 2 + 1
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
        side = self._side(self.current)
        darts = self._sum(self.current, "darts")
        if self.cricket:
            record = {
                "darts": darts,
                "points": winner.points,
                "mpr": marks_per_round(self._sum(self.current, "marks_hit"), darts),
            }
        elif self.party:
            record = {"darts": darts, "points": self.party.points[self.current]}
        else:
            self._book_stats()
            record = {
                "darts": darts,
                "average": _average(self._start(self.current), darts),
                "checkout": winner.remaining,
                "start": self._start(self.current),
                "double_out": self.double_out,
                "double_in": self.double_in,
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
        self.legs_total += 1
        legs, sets, match = self._result(self.current)
        set_won = sets > winner.sets
        for index in side:
            player = self.players[index]
            player.legs, player.sets = legs, sets
            player.match_legs += 1
        if match:
            # The result stays: the winners keep the legs of the deciding set.
            for index in side:
                self.players[index].remaining = 0
            self.winner = self.current
            self.profiles.match(
                self._kind(),
                self._match_entries(),
                self.current,
                self.legs_to_win,
                self.sets_to_win,
                side,
            )
            return
        players = len(self.players)
        if set_won:
            # A won set starts the next one from zero legs for everybody, and
            # the next player in turn throws first in the new set.
            for player in self.players:
                player.legs = 0
            self.set_starter = (self.set_starter + 1) % players
            self.starter = self.set_starter
        else:
            self.starter = (self.starter + 1) % players
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
            "teams": self._teams_snapshot(),
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
        side = self._side(self.current)
        # A bust takes an opening double of the visit back.
        opened = (
            not self.double_in
            or player.opened
            or (self._opening() < thrown and outcome != "bust")
        )
        if outcome == "won" or self.winner is not None or not opened:
            route: tuple[str, ...] = ()
        elif outcome == "bust" or thrown >= 3:
            # The visit is over; the next one starts with three darts.
            route = self._route(remaining, 3)
        else:
            route = self._route(remaining, 3 - thrown)
        scored = player.remaining - remaining
        leg_darts = self._sum(self.current, "darts") + darts
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
            "average": _average(self._sum(self.current, "points") + scored, leg_darts),
            "opened": opened,
            "start": self._start(self.current),
            "scores": [
                {
                    "player": index + 1,
                    "name": self._name(index),
                    "remaining": remaining if index in side else item.remaining,
                    "opened": opened
                    if index in side
                    else item.opened or not self.double_in,
                    "start": self._start(index),
                    "legs": item.legs,
                    "sets": item.sets,
                    "match_legs": item.match_legs,
                    "average": _average(
                        item.match_points + (scored if index == self.current else 0),
                        item.match_darts + (darts if index == self.current else 0),
                    ),
                    **({"team": index % 2 + 1} if self._teamed() else {}),
                }
                for index, item in enumerate(self.players)
            ],
        }

    # -- analysis ----------------------------------------------------------------

    def booking(self) -> Booking:
        """The visit that finish_visit books next, for the players' statistics.

        Every dart of the visit comes with its position and, where the game
        knows it, the bed it was aimed at; the darts that count for the player
        at the board follow from the start and end of the booked darts.
        """
        visit = list(self._visit)
        booking = Booking(
            visit=visit,
            positions=[
                self._positions[index] if index < len(self._positions) else None
                for index in range(len(visit))
            ],
            aims=[None] * len(visit),
            start=self._skip,
            end=self._skip + len(self._thrown()),
        )
        thrown = self._thrown()
        if not thrown:
            return booking
        if self.drill:
            self._drill_booking(booking, thrown)
        elif not self._playing() or self.winner is not None:
            return booking
        elif self.bulling:
            booking.player = self.bulling.thrower
            booking.game = "bull_off"
            booking.end = booking.start + 1
            booking.aims[booking.start] = "BULL"
        else:
            booking.player, booking.game = self.current, self._kind()
            if self.game:
                self._x01_booking(booking, thrown)
            elif self.party and self.party.kind == "shanghai":
                booking.shanghai = self._party_visit().won == self.current
        booking.name = None if booking.player is None else self._name(booking.player)
        return booking

    def _x01_booking(self, booking: Booking, thrown: list[dict[str, Any]]) -> None:
        player = self.players[self.current]
        opening = None if player.opened or not self.double_in else self._opening()
        aims = x01_aims(player.remaining, thrown, self.double_out, opening, self._route)
        booking.aims[booking.start : booking.end] = aims
        booking.scored = player.remaining - self._evaluate()[0]

    def _drill_booking(self, booking: Booking, thrown: list[dict[str, Any]]) -> None:
        """Training games are for player 1; most know the bed aimed at."""
        assert self.drill is not None
        drill = self.drills[self.drill]
        booking.player, booking.game = 0, self.drill
        if isinstance(drill, CheckoutDrill):
            aims = x01_aims(drill.start, thrown, True, None, checkout)
            if evaluate_visit(drill.start, thrown, True)[1] == "won":
                booking.checkout = drill.start
        else:
            doubles = [double for double, _ in drill.double_attempts()]
            aims = [*doubles, *[None] * len(thrown)][: len(thrown)]
        booking.aims[booking.start : booking.end] = aims


@dataclass
class Booking:
    """A visit as the practice game books it, see PracticeGame.booking."""

    visit: list[dict[str, Any]]
    # Positions and aimed beds, one per dart of the visit.
    positions: list[tuple[float, float] | None]
    aims: list[str | None]
    # The darts from start to end count for the player at the board, if any.
    start: int = 0
    end: int = 0
    player: int | None = None
    name: str | None = None
    game: int | str | None = None
    # X01 points the visit scores, nothing for a bust.
    scored: int | None = None
    # A Shanghai: a single, double and treble of the round's number.
    shanghai: bool = False
    # The score the visit checked out in the checkout training.
    checkout: int | None = None

    @property
    def darts(self) -> list[dict[str, Any]]:
        return self.visit[self.start : self.end]

    @property
    def booked_positions(self) -> list[tuple[float, float] | None]:
        return self.positions[self.start : self.end]

    @property
    def booked_aims(self) -> list[str | None]:
        return self.aims[self.start : self.end]
