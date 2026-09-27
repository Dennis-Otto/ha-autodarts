"""Tournaments of three to eight named players at one board.

A tournament is a series of practice matches between two players at a time:
X01, with a start score of their own for a handicap if wanted, or a Cricket
game. In a round robin everyone plays everyone once and a table
ranks the players; in a knockout the winners go on through a bracket until the
final. When a match ends, its result goes into the table or the bracket, and
the next match starts after the summary of the match and a pause, never while
darts of a visit are on the board. The matches count for the player profiles like any other match.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .cricket import CRICKET_GAMES, marks_per_round
from .practice import GAMES, MAX_LEGS, MAX_SETS, PracticeGame, valid_start
from .profiles import NAME_LENGTH
from .scoring import average

ROUND_ROBIN = "round_robin"
KNOCKOUT = "knockout"
FORMATS = (ROUND_ROBIN, KNOCKOUT)
# The head-to-head games a tournament plays: X01 and the Cricket games.
TOURNAMENT_GAMES = (*(str(game) for game in GAMES), *CRICKET_GAMES)
MIN_ENTRANTS = 3
MAX_ENTRANTS = 8
# Seconds between two matches; 0 waits until the next match is started.
DEFAULT_PAUSE = 10
MAX_PAUSE = 600
# Seconds the summary of a match shows before the pause begins, so that the
# table or the bracket with the next match gets the whole pause.
DEFAULT_SUMMARY = 8
MAX_SUMMARY = 60
MAX_SEED = 999_999
# A won match of the round robin is worth two points, as in the Premier League.
WIN_POINTS = 2
# The rules every match of a tournament is played with.
RULES = ("double_out", "double_in", "bull_off", "bull_off_distance")
# A match for third place needs two losing semi-finalists.
THIRD_PLACE_ENTRANTS = 4

TOURNAMENT_EVENTS = (
    "tournament_started",
    "tournament_match_finished",
    "tournament_finished",
)
PLAYING = "playing"
WAITING = "waiting"
FINISHED = "finished"
# Knockout rounds counted back from the final; eight players need three.
KNOCKOUT_STAGES = ("final", "semi_final", "quarter_final")
THIRD_PLACE = "third_place"
# Seven players play seven rounds of the round robin, and so do eight.
MAX_ROUNDS = 7
# The states of the tournament sensor: the stage being played.
STATES = [
    "no_tournament",
    *(f"round_{number}" for number in range(1, MAX_ROUNDS + 1)),
    "quarter_final",
    "semi_final",
    THIRD_PLACE,
    "final",
    FINISHED,
]

# The draw needs no cryptographic randomness.
_RANDOM = random.Random()  # noqa: S311


def _invalid(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


def _name(name: str) -> str:
    """A player name as the practice game keeps it."""
    return name.strip()[:NAME_LENGTH]


def parse_players(text: str) -> list[str]:
    """Names separated by commas, semicolons or new lines; empty ones are dropped."""
    return [_name(name) for name in re.split(r"[,;\n]", text) if name.strip()]


def _flag(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _count(value: object, low: int, high: int, default: int) -> int:
    return value if type(value) is int and low <= value <= high else default


@dataclass
class TournamentSetup:
    """The settings of the next tournament, as its entities show them."""

    format: str = ROUND_ROBIN
    game: str = "501"
    players: list[str] = field(default_factory=list)
    third_place: bool = False
    random_draw: bool = False
    pause: int = DEFAULT_PAUSE
    summary: int = DEFAULT_SUMMARY

    @classmethod
    def restored(cls, saved: object) -> TournamentSetup:
        data = saved if isinstance(saved, dict) else {}
        players = data.get("players")
        return cls(
            format=data["format"] if data.get("format") in FORMATS else ROUND_ROBIN,
            game=data["game"] if data.get("game") in TOURNAMENT_GAMES else "501",
            players=[
                _name(name)
                for name in (players if isinstance(players, list) else [])
                if isinstance(name, str) and name.strip()
            ][:MAX_ENTRANTS],
            third_place=_flag(data.get("third_place"), False),
            random_draw=_flag(data.get("random_draw"), False),
            pause=_count(data.get("pause"), 0, MAX_PAUSE, DEFAULT_PAUSE),
            summary=_count(data.get("summary"), 0, MAX_SUMMARY, DEFAULT_SUMMARY),
        )


def _pair() -> list[int]:
    return [0, 0]


@dataclass
class Match:
    """A match between two players, given by their place in the draw."""

    round: int
    stage: str
    # The place of a knockout match in its round, for the bracket.
    slot: int = 0
    # A player is None until an earlier match decides them, and for a bye.
    players: list[int | None] = field(default_factory=lambda: [None, None])
    bye: bool = False
    winner: int | None = None
    # Per player: the legs of the whole match and the sets, and the points of
    # X01 or the marks of Cricket with the darts they took, for the averages.
    legs: list[int] = field(default_factory=_pair)
    sets: list[int] = field(default_factory=_pair)
    points: list[int] = field(default_factory=_pair)
    marks: list[int] = field(default_factory=_pair)
    darts: list[int] = field(default_factory=_pair)
    ended: str | None = None

    @property
    def ready(self) -> bool:
        """Both players are known and the match is still to be played."""
        return not self.bye and self.winner is None and None not in self.players

    @property
    def played(self) -> bool:
        return not self.bye and self.winner is not None

    @property
    def loser(self) -> int | None:
        if not self.played:
            return None
        return self.players[1] if self.players[0] == self.winner else self.players[0]


def round_robin(count: int) -> list[Match]:
    """Everyone against everyone, in rounds of the circle method.

    With an odd number of players, one of them has a bye in every round. The
    player with fewer matches as the first to throw throws first; the players
    of a round's last match open the next round only when nobody else can.
    """
    seats: list[int | None] = [*range(count), *([None] if count % 2 else [])]
    size = len(seats)
    first = [0] * count
    last: set[int] = set()
    matches: list[Match] = []
    for number in range(1, size):
        pairs: list[tuple[int, int]] = []
        for index in range(size // 2):
            one, two = seats[index], seats[size - 1 - index]
            if one is None or two is None:
                continue
            if first[two] < first[one] or (
                first[two] == first[one] and (number + index) % 2 == 0
            ):
                one, two = two, one
            first[one] += 1
            pairs.append((one, two))
        pairs.sort(key=lambda pair: bool(last & set(pair)))
        matches.extend(
            Match(round=number, stage=f"round_{number}", players=[one, two])
            for one, two in pairs
        )
        last = set(pairs[-1])
        seats = [seats[0], seats[-1], *seats[1:-1]]
    return matches


def knockout(count: int, third_place: bool) -> list[Match]:
    """A bracket for the next power of two, seeded so that the first two seeds
    meet in the final at the earliest; the top seeds get the byes."""
    size = 1 << (count - 1).bit_length()
    rounds = size.bit_length() - 1
    seats = [0]
    while len(seats) < size:
        seats = [seat for top in seats for seat in (top, 2 * len(seats) - 1 - top)]
    matches: list[Match] = []
    for number in range(1, rounds + 1):
        stage = KNOCKOUT_STAGES[rounds - number]
        if number == rounds and third_place:
            matches.append(Match(round=number, stage=THIRD_PLACE, slot=1))
        for slot in range(size >> number):
            match = Match(round=number, stage=stage, slot=slot)
            if number == 1:
                top, bottom = seats[2 * slot], seats[2 * slot + 1]
                # The lower seed of a pair is the one missing.
                match.players = [top, bottom if bottom < count else None]
                match.bye = bottom >= count
            matches.append(match)
    return matches


class Tournament:
    """A tournament being played, or finished."""

    def __init__(
        self,
        *,
        format: str,
        game: str,
        players: list[str],
        legs: int,
        sets: int,
        rules: dict[str, bool],
        starts: list[int] | None = None,
        third_place: bool = False,
        seed: int | None = None,
        started: str | None = None,
    ) -> None:
        self.format = format
        self.game = game
        # The names in the order of the draw, and the X01 start score of every
        # player: 0 for the game's, another one for a handicap.
        self.players = list(players)
        self.starts = [
            start if valid_start(start) and game.isdigit() else 0
            for start in [*(starts or []), *[0] * len(players)][: len(players)]
        ]
        self.legs_to_win = legs
        self.sets_to_win = sets
        self.rules = dict(rules)
        self.third_place = (
            third_place and format == KNOCKOUT and len(players) >= THIRD_PLACE_ENTRANTS
        )
        self.seed = seed
        self.started = started
        self.ended: str | None = None
        self.status = PLAYING
        self.matches = (
            knockout(len(players), self.third_place)
            if format == KNOCKOUT
            else round_robin(len(players))
        )
        for index, match in enumerate(self.matches):
            if match.bye:
                match.winner = match.players[0]
                self._advance(index)

    @property
    def kind(self) -> int | str:
        """The game as the practice game names it: 501 or cricket."""
        return int(self.game) if self.game.isdigit() else self.game

    @property
    def rounds(self) -> int:
        return max(match.round for match in self.matches)

    def upcoming(self) -> int | None:
        """The match to play next: the first one whose players are known."""
        return next(
            (index for index, match in enumerate(self.matches) if match.ready), None
        )

    def current(self) -> int | None:
        """The match being played."""
        return self.upcoming() if self.status == PLAYING else None

    def last_played(self) -> int | None:
        """The match that ended last."""
        played = [index for index, match in enumerate(self.matches) if match.played]
        return played[-1] if played else None

    def names(self, match: Match) -> list[str | None]:
        return [
            None if player is None else self.players[player] for player in match.players
        ]

    def _find(self, round_: int, slot: int, stage: str | None = None) -> Match:
        return next(
            match
            for match in self.matches
            if match.round == round_
            and match.slot == slot
            and (match.stage == THIRD_PLACE) == (stage == THIRD_PLACE)
        )

    def _advance(self, index: int) -> None:
        """The winner of a knockout match goes on, the loser of a semi-final
        to the match for third place."""
        match = self.matches[index]
        if self.format != KNOCKOUT or match.round == self.rounds:
            return
        side = match.slot % 2
        self._find(match.round + 1, match.slot // 2).players[side] = match.winner
        if self.third_place and match.round == self.rounds - 1:
            self._find(self.rounds, 1, THIRD_PLACE).players[side] = match.loser

    def record(self, index: int, practice: PracticeGame, ended: str) -> None:
        """The result of the practice match that just ended."""
        match = self.matches[index]
        assert practice.winner is not None
        players = practice.players
        match.winner = match.players[practice.winner]
        match.legs = [player.match_legs for player in players]
        match.sets = [player.sets for player in players]
        match.points = [player.match_points for player in players]
        match.marks = [player.match_marks for player in players]
        match.darts = [player.match_darts for player in players]
        match.ended = ended
        self._advance(index)

    # -- results ---------------------------------------------------------------

    def _averages(self, scored: list[int], darts: list[int]) -> list[float | None]:
        """3-dart averages in X01, marks per round in Cricket."""
        rate = marks_per_round if self.game in CRICKET_GAMES else average
        return [rate(part, count) for part, count in zip(scored, darts, strict=True)]

    @property
    def _statistic(self) -> str:
        return "mpr" if self.game in CRICKET_GAMES else "average"

    def _scored(self, match: Match) -> list[int]:
        return match.marks if self.game in CRICKET_GAMES else match.points

    def standings(self) -> list[dict[str, Any]]:
        """The round robin table: points, then the points of the matches among
        the players level on points, the leg difference, the average and the
        order of the draw."""
        count = len(self.players)
        won, lost, legs_for, legs_against, scored, darts = (
            [0] * count for _ in range(6)
        )
        played = [match for match in self.matches if match.played]
        for match in played:
            for side, player in enumerate(match.players):
                assert player is not None
                won[player] += int(player == match.winner)
                lost[player] += int(player != match.winner)
                legs_for[player] += match.legs[side]
                legs_against[player] += match.legs[1 - side]
                scored[player] += self._scored(match)[side]
                darts[player] += match.darts[side]
        points = [wins * WIN_POINTS for wins in won]
        averages = self._averages(scored, darts)

        def among(player: int) -> int:
            level = {other for other in range(count) if points[other] == points[player]}
            return sum(
                WIN_POINTS
                for match in played
                if match.winner == player and match.loser in level
            )

        def rank(player: int) -> tuple[int, int, int, float, int]:
            value = averages[player]
            return (
                -points[player],
                -among(player),
                legs_against[player] - legs_for[player],
                -(value if value is not None else -1.0),
                player,
            )

        return [
            {
                "position": position,
                "name": self.players[player],
                "played": won[player] + lost[player],
                "won": won[player],
                "lost": lost[player],
                "legs_for": legs_for[player],
                "legs_against": legs_against[player],
                "leg_difference": legs_for[player] - legs_against[player],
                "points": points[player],
                self._statistic: averages[player],
            }
            for position, player in enumerate(sorted(range(count), key=rank), 1)
        ]

    def podium(self) -> list[str | None]:
        """Winner, runner-up and third of a finished tournament."""
        if self.format == ROUND_ROBIN:
            return [row["name"] for row in self.standings()[:3]]
        final = self._find(self.rounds, 0)
        third = (
            self._find(self.rounds, 1, THIRD_PLACE).winner if self.third_place else None
        )
        return [
            self.players[player] if player is not None else None
            for player in (final.winner, final.loser, third)
        ]

    # -- state -----------------------------------------------------------------

    def numbers(self) -> dict[int, int]:
        """Matches to play by their place in the order of play, from 1; byes have none."""
        played = [index for index, match in enumerate(self.matches) if not match.bye]
        return {index: number for number, index in enumerate(played, 1)}

    def match(self, index: int | None) -> dict[str, Any] | None:
        if index is None:
            return None
        match = self.matches[index]
        result: dict[str, Any] = {
            "match": self.numbers().get(index),
            "round": match.round,
            "stage": match.stage,
            "players": self.names(match),
            "winner": None if match.winner is None else self.players[match.winner],
            "bye": match.bye,
            "legs": list(match.legs),
            "sets": list(match.sets),
            "ended": match.ended,
        }
        if match.played:
            result[self._statistic] = self._averages(self._scored(match), match.darts)
        return result

    def after(self, index: int) -> int | None:
        """The match after this one in the order of play, known or not."""
        return next(
            (
                later
                for later in range(index + 1, len(self.matches))
                if not self.matches[later].bye and self.matches[later].winner is None
            ),
            None,
        )

    def bracket(self) -> list[dict[str, Any]]:
        """The knockout rounds with their matches, byes included; the match for
        third place comes after the final."""
        rounds: list[dict[str, Any]] = []
        for stage in (*KNOCKOUT_STAGES[::-1], THIRD_PLACE):
            indexes = [
                index
                for index, match in enumerate(self.matches)
                if match.stage == stage
            ]
            if indexes:
                rounds.append(
                    {
                        "stage": stage,
                        "round": self.matches[indexes[0]].round,
                        "matches": [self.match(index) for index in indexes],
                    }
                )
        return rounds

    def stored(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "game": self.game,
            "players": list(self.players),
            "starts": list(self.starts),
            "legs_to_win": self.legs_to_win,
            "sets_to_win": self.sets_to_win,
            "rules": dict(self.rules),
            "third_place": self.third_place,
            "seed": self.seed,
            "started": self.started,
            "ended": self.ended,
            "status": self.status,
            "matches": [asdict(match) for match in self.matches],
        }

    @classmethod
    def restored(cls, saved: object) -> Tournament | None:
        """The stored tournament; the draw is made again and the stored results
        are replayed onto it as far as they fit."""
        if not isinstance(saved, dict):
            return None
        players = saved.get("players")
        if not (
            saved.get("format") in FORMATS
            and saved.get("game") in TOURNAMENT_GAMES
            and isinstance(players, list)
            and MIN_ENTRANTS <= len(players) <= MAX_ENTRANTS
            and all(isinstance(name, str) and name.strip() for name in players)
        ):
            return None
        rules = saved.get("rules")
        rules = rules if isinstance(rules, dict) else {}
        starts = saved.get("starts")
        seed = saved.get("seed")
        tournament = cls(
            format=saved["format"],
            game=saved["game"],
            players=[_name(name) for name in players],
            legs=_count(saved.get("legs_to_win"), 1, MAX_LEGS, 1),
            sets=_count(saved.get("sets_to_win"), 1, MAX_SETS, 1),
            rules={
                rule: _flag(rules.get(rule), rule == "double_out") for rule in RULES
            },
            starts=starts if isinstance(starts, list) else None,
            third_place=saved.get("third_place") is True,
            seed=seed if type(seed) is int else None,
            started=saved["started"] if isinstance(saved.get("started"), str) else None,
        )
        matches = saved.get("matches")
        for index, stored in enumerate(matches if isinstance(matches, list) else []):
            if not tournament._replay(index, stored):
                break
        if tournament.upcoming() is None:
            tournament.status = FINISHED
            ended = saved.get("ended")
            tournament.ended = ended if isinstance(ended, str) else None
        elif saved.get("status") == WAITING and tournament.last_played() is not None:
            tournament.status = WAITING
        return tournament

    def _replay(self, index: int, saved: object) -> bool:
        """A stored result for the match at this place; False where it does not fit."""
        if index >= len(self.matches) or not isinstance(saved, dict):
            return False
        match = self.matches[index]
        if match.bye:
            return True
        winner, ended = saved.get("winner"), saved.get("ended")
        if winner is None:
            return True
        if (
            not match.ready
            or saved.get("players") != match.players
            or winner not in match.players
            or not isinstance(ended, str)
            or dt_util.parse_datetime(ended) is None
        ):
            return False
        for key in ("legs", "sets", "points", "marks", "darts"):
            values = saved.get(key)
            if (
                isinstance(values, list)
                and len(values) == 2
                and all(type(value) is int and value >= 0 for value in values)
            ):
                setattr(match, key, list(values))
        match.winner, match.ended = winner, ended
        self._advance(index)
        return True


class TournamentDirector:
    """The setup of the next tournament and the tournament being played.

    It sets the practice game up for every match and takes the result when the
    match is booked. Between two matches, the practice game holds the result:
    darts thrown meanwhile start no new match.
    """

    def __init__(self) -> None:
        self.setup = TournamentSetup()
        self.tournament: Tournament | None = None

    @property
    def waiting(self) -> bool:
        return self.tournament is not None and self.tournament.status == WAITING

    def configure(self, **values: Any) -> None:
        """Settings of the next tournament; None leaves one as it is."""
        for key, value in values.items():
            if value is not None:
                setattr(self.setup, key, value)

    # -- the tournament ------------------------------------------------------------

    def start(
        self,
        practice: PracticeGame,
        now: datetime,
        *,
        players: list[str] | None = None,
        start_scores: list[int] | None = None,
        legs: int | None = None,
        sets: int | None = None,
        seed: int | None = None,
        rules: dict[str, bool | None] | None = None,
        **setup: Any,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Draw a tournament and set the practice game up for its first match.

        Unset values come from the setup; legs, sets and rules from the practice
        game. Start scores go with the players in their order; 0 or none plays
        the game's. A seed draws the order at random, the same order for the
        same seed.
        """
        given_starts = list(start_scores or [])
        entrants = [
            (_name(name), given_starts[index] if index < len(given_starts) else 0)
            for index, name in enumerate(
                self.setup.players if players is None else players
            )
            if name.strip()
        ]
        names = [name for name, _ in entrants]
        seen: set[str] = set()
        for name in names:
            if name.casefold() in seen:
                raise _invalid("duplicate_player", name=name)
            seen.add(name.casefold())
        if not MIN_ENTRANTS <= len(names) <= MAX_ENTRANTS:
            raise _invalid("tournament_players", count=str(len(names)))
        self.configure(players=names, **setup)
        if seed is None and self.setup.random_draw:
            seed = _RANDOM.randint(1, MAX_SEED)
        order = list(entrants)
        if seed is not None:
            random.Random(seed).shuffle(order)
        given = rules or {}
        self.tournament = Tournament(
            format=self.setup.format,
            game=self.setup.game,
            players=[name for name, _ in order],
            starts=[start for _, start in order],
            legs=practice.legs_to_win if legs is None else legs,
            sets=practice.sets_to_win if sets is None else sets,
            rules={
                rule: bool(getattr(practice, rule))
                if given.get(rule) is None
                else bool(given[rule])
                for rule in RULES
            },
            third_place=self.setup.third_place,
            seed=seed,
            started=now.isoformat(),
        )
        self._play(practice)
        tournament = self.tournament
        return [
            (
                "tournament_started",
                {
                    **self._about(tournament),
                    "players": list(tournament.players),
                    "start_scores": list(tournament.starts),
                    "legs_to_win": tournament.legs_to_win,
                    "sets_to_win": tournament.sets_to_win,
                    "seed": tournament.seed,
                },
            )
        ]

    def stop(self, practice: PracticeGame) -> None:
        """End the tournament; the practice match being played goes on."""
        if self.tournament is None:
            raise _invalid("no_tournament")
        self.tournament = None
        practice.hold = False

    def next_match(self, practice: PracticeGame) -> None:
        """Start the next match now, or set the current one up again when the
        practice game plays something else."""
        tournament = self.tournament
        if tournament is None or tournament.status == FINISHED:
            raise _invalid("no_tournament")
        index = tournament.upcoming()
        assert index is not None
        if tournament.status == PLAYING and self.plays(practice):
            first, second = tournament.names(tournament.matches[index])
            raise _invalid(
                "tournament_match_running", first=str(first), second=str(second)
            )
        tournament.status = PLAYING
        self._play(practice)

    def _play(self, practice: PracticeGame) -> None:
        """The practice game as the current match wants it."""
        tournament = self.tournament
        assert tournament is not None
        index = tournament.current()
        assert index is not None
        entrants = tournament.matches[index].players
        names = self._current_names()
        for rule, value in tournament.rules.items():
            setattr(practice, rule, value)
        # The rules of the tournament, not a double out left for the next leg.
        practice.double_out_next = None
        for slot in range(len(practice.names)):
            practice.set_name(slot, names[slot] if slot < len(names) else "")
            entrant = entrants[slot] if slot < len(entrants) else None
            practice.set_start(
                slot, 0 if entrant is None else tournament.starts[entrant]
            )
        practice.hold = False
        # Tournaments are for the players: the bot sits them out.
        practice.bot_level = 0
        practice.set_players(len(names))
        practice.set_format(tournament.legs_to_win, tournament.sets_to_win)
        practice.play(tournament.kind)

    def _current_names(self) -> list[str]:
        tournament = self.tournament
        assert tournament is not None
        index = tournament.current()
        assert index is not None
        return [str(name) for name in tournament.names(tournament.matches[index])]

    def plays(self, practice: PracticeGame) -> bool:
        """Whether the practice game plays the current match of the tournament."""
        tournament = self.tournament
        if tournament is None or tournament.current() is None:
            return False
        names = self._current_names()
        return (
            practice.kind == tournament.kind
            and len(practice.players) == len(names)
            and practice.names[: len(names)] == names
        )

    def booked(
        self, practice: PracticeGame, now: datetime
    ) -> list[tuple[str, dict[str, Any]]]:
        """The result of a tournament match the practice game just booked."""
        tournament = self.tournament
        if tournament is None or practice.winner is None or not self.plays(practice):
            return []
        index = tournament.current()
        assert index is not None
        tournament.record(index, practice, now.isoformat())
        match = tournament.matches[index]
        winner, loser = match.winner, match.loser
        assert winner is not None and loser is not None
        following = tournament.upcoming()
        result = {
            **self._about(tournament),
            "match": tournament.numbers()[index],
            "round": match.round,
            "stage": match.stage,
            "players": tournament.names(match),
            "winner": tournament.players[winner],
            "loser": tournament.players[loser],
            "legs": list(match.legs),
            "sets": list(match.sets),
            "next": None
            if following is None
            else tournament.names(tournament.matches[following]),
        }
        events: list[tuple[str, dict[str, Any]]] = [
            ("tournament_match_finished", result)
        ]
        if following is not None:
            tournament.status = WAITING
            practice.hold = True
            return events
        tournament.status, tournament.ended = FINISHED, now.isoformat()
        champion, runner_up, third = tournament.podium()
        events.append(
            (
                "tournament_finished",
                {
                    **self._about(tournament),
                    "winner": champion,
                    "runner_up": runner_up,
                    "third": third,
                    "players": list(tournament.players),
                },
            )
        )
        return events

    @staticmethod
    def _about(tournament: Tournament) -> dict[str, Any]:
        return {
            "format": tournament.format,
            "game": tournament.kind,
            "matches": len(tournament.numbers()),
        }

    def due_at(self) -> datetime | None:
        """When the next match is due: the summary of the last match, then the
        pause; None without a pause."""
        tournament = self.tournament
        if tournament is None or tournament.status != WAITING or not self.setup.pause:
            return None
        last = tournament.last_played()
        assert last is not None
        ended = tournament.matches[last].ended
        ended_at = dt_util.parse_datetime(ended or "") or dt_util.utcnow()
        return ended_at + timedelta(seconds=self.setup.summary + self.setup.pause)

    def due(self, now: datetime) -> bool:
        return (at := self.due_at()) is not None and at <= now

    @staticmethod
    def free(practice: PracticeGame) -> bool:
        """Whether the practice game can make way for the next match by itself:
        it shows a result, or nothing is played. Another game chosen during the
        pause is played to its end first."""
        return practice.winner is not None or (
            practice.kind is None and practice.drill is None
        )

    # -- storage and state ---------------------------------------------------------

    def stored(self) -> dict[str, Any]:
        return {
            "setup": asdict(self.setup),
            "tournament": self.tournament.stored() if self.tournament else None,
        }

    def restore(self, saved: object) -> None:
        data = saved if isinstance(saved, dict) else {}
        self.setup = TournamentSetup.restored(data.get("setup"))
        self.tournament = Tournament.restored(data.get("tournament"))

    def state(self) -> str:
        """The stage being played, or the next one during a pause."""
        tournament = self.tournament
        if tournament is None:
            return "no_tournament"
        if tournament.status == FINISHED:
            return FINISHED
        index = tournament.upcoming()
        assert index is not None
        return tournament.matches[index].stage

    def snapshot(self) -> dict[str, Any]:
        """Everything a card or an automation needs to know about the tournament."""
        tournament = self.tournament
        if tournament is None:
            return {
                "status": None,
                "format": None,
                "game": None,
                "players": [],
                "winner": None,
                "fixtures": [],
            }
        current = tournament.current()
        upcoming = tournament.upcoming()
        following = tournament.after(current) if current is not None else upcoming
        last = tournament.last_played()
        due = self.due_at()
        numbers = tournament.numbers()
        finished = tournament.status == FINISHED
        return {
            "status": tournament.status,
            "format": tournament.format,
            "game": tournament.kind,
            "legs_to_win": tournament.legs_to_win,
            "sets_to_win": tournament.sets_to_win,
            **tournament.rules,
            "third_place": tournament.third_place,
            "seed": tournament.seed,
            "players": list(tournament.players),
            "start_scores": list(tournament.starts),
            "round": None if upcoming is None else tournament.matches[upcoming].round,
            "rounds": tournament.rounds,
            "matches_played": sum(match.played for match in tournament.matches),
            "matches_total": len(numbers),
            "current": tournament.match(current),
            "next": tournament.match(following),
            "last_result": tournament.match(last),
            "pause": self.setup.pause,
            "summary": self.setup.summary,
            "next_at": due.isoformat() if due else None,
            "winner": tournament.podium()[0] if finished else None,
            "started": tournament.started,
            "ended": tournament.ended,
            "fixtures": [tournament.match(index) for index in numbers],
            **(
                {"bracket": tournament.bracket()}
                if tournament.format == KNOCKOUT
                else {"standings": tournament.standings()}
            ),
        }
