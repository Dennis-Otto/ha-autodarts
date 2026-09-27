"""Player profiles: statistics and personal bests per name, matches and head-to-head.

Profiles exist for named players only; a name is the same player regardless of
upper and lower case. Legs count in every game; X01 legs add the averages and
the checkout rate, Cricket legs the marks per round. The highest checkout and
the fewest darts come from X01 legs with double out only; the fewest darts
also only from legs a player played alone, from one of the X01 start scores.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import split_entity_id, valid_entity_id
from homeassistant.util import dt as dt_util

from .doubles import DoubleStats

# The X01 start scores; a leg from another start sets no fewest darts.
GAMES = (101, 301, 501, 701, 901, 1001)

MATCH_HISTORY = 20
NAME_LENGTH = 20


def _key(name: str) -> str:
    return name.strip().casefold()


def _person(value: object) -> str | None:
    """A person entity ID such as person.alex, or None."""
    if not isinstance(value, str) or not valid_entity_id(value):
        return None
    return value if split_entity_id(value)[0] == "person" else None


def _ratio(part: int, whole: int, factor: int, digits: int) -> float | None:
    return round(part * factor / whole, digits) if whole else None


def _count(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


@dataclass
class Profile:
    """Lifetime numbers of one player."""

    name: str
    legs_played: int = 0
    legs_won: int = 0
    matches_played: int = 0
    matches_won: int = 0
    x01_darts: int = 0
    x01_points: int = 0
    first9_points: int = 0
    first9_darts: int = 0
    at_double: int = 0
    checkouts: int = 0
    cricket_darts: int = 0
    cricket_marks: int = 0
    highest_visit: int = 0
    highest_checkout: int = 0
    best_mpr: float = 0.0
    # Start score -> fewest darts for a won X01 leg.
    fewest_darts: dict[str, int] = field(default_factory=dict)
    # Double -> attempts and hits.
    doubles: dict[str, list[int]] = field(default_factory=dict)
    last_played: str | None = None
    # The Home Assistant person this player is, for the picture and presence.
    person: str | None = None

    def double_stats(self) -> DoubleStats:
        stats = DoubleStats()
        stats.counts = self.doubles
        return stats

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "legs_played": self.legs_played,
            "legs_won": self.legs_won,
            "matches_played": self.matches_played,
            "matches_won": self.matches_won,
            "average": _ratio(self.x01_points, self.x01_darts, 3, 2),
            "first_9_average": _ratio(self.first9_points, self.first9_darts, 3, 2),
            "checkout_rate": _ratio(self.checkouts, self.at_double, 100, 1),
            "mpr": _ratio(self.cricket_marks, self.cricket_darts, 3, 2),
            "highest_visit": self.highest_visit or None,
            "highest_checkout": self.highest_checkout or None,
            "best_mpr": self.best_mpr or None,
            "fewest_darts": dict(self.fewest_darts),
            "doubles": self.double_stats().snapshot(),
            "last_played": self.last_played,
            "person": self.person,
        }

    @classmethod
    def restored(cls, saved: dict[str, Any]) -> Profile | None:
        name = saved.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        profile = cls(name=name.strip()[:NAME_LENGTH])
        for key, value in asdict(cls(name="")).items():
            if type(value) is int:
                setattr(profile, key, _count(saved.get(key)))
        mpr = saved.get("best_mpr")
        if isinstance(mpr, int | float) and not isinstance(mpr, bool) and mpr >= 0:
            profile.best_mpr = float(mpr)
        fewest = saved.get("fewest_darts")
        if isinstance(fewest, dict):
            profile.fewest_darts = {
                str(game): darts
                for game, darts in fewest.items()
                if str(game).isdigit() and type(darts) is int and darts > 0
            }
        doubles = DoubleStats()
        doubles.restore(saved.get("doubles"))
        profile.doubles = doubles.counts
        if isinstance(saved.get("last_played"), str):
            profile.last_played = saved["last_played"]
        profile.person = _person(saved.get("person"))
        return profile


class Profiles:
    """Every named player, the last matches and who beat whom."""

    def __init__(self) -> None:
        self.players: dict[str, Profile] = {}
        self.matches: list[dict[str, Any]] = []
        # "a\x00b" with names in a fixed order -> wins of a and of b.
        self.head_to_head: dict[str, list[int]] = {}

    def _profile(self, name: str | None) -> Profile | None:
        if not name or not name.strip():
            return None
        key = _key(name)
        if key not in self.players:
            self.players[key] = Profile(name=name.strip()[:NAME_LENGTH])
        profile = self.players[key]
        profile.last_played = dt_util.utcnow().isoformat()
        return profile

    # -- recording -------------------------------------------------------------

    def visit(self, name: str | None, points: int) -> None:
        """The score of an X01 visit: nothing for a bust or before double in."""
        if profile := self._profile(name):
            profile.highest_visit = max(profile.highest_visit, points)

    def doubles(self, name: str | None, attempts: list[tuple[str, bool]]) -> None:
        """Darts a player threw at doubles."""
        if attempts and (profile := self._profile(name)):
            profile.double_stats().record(attempts)

    def preferred(self, name: str | None) -> tuple[str, ...]:
        """The doubles a named player hits best, strongest first."""
        profile = self.players.get(_key(name)) if name and name.strip() else None
        return profile.double_stats().preferred() if profile else ()

    def leg(self, game: int | str, players: list[dict[str, Any]]) -> None:
        """A finished leg, with every player's numbers of that leg."""
        for entry in players:
            profile = self._profile(entry.get("name"))
            if profile is None:
                continue
            won = entry.get("won") is True
            team = entry.get("team") is True
            profile.legs_played += 1
            profile.legs_won += int(won)
            darts = _count(entry.get("darts"))
            if isinstance(game, int):
                profile.x01_darts += darts
                profile.x01_points += _count(entry.get("points"))
                profile.first9_points += _count(entry.get("first9_points"))
                profile.first9_darts += _count(entry.get("first9_darts"))
                profile.at_double += _count(entry.get("at_double"))
                double_out = entry.get("double_out") is True
                # In a team, the checkout counts for the partner who threw it.
                checkout = _count(entry.get("checkout"))
                if won and double_out and checkout:
                    profile.checkouts += 1
                    profile.highest_checkout = max(profile.highest_checkout, checkout)
                # The fewest darts count for the score the player really started
                # from, and only for a leg the player played alone.
                start = entry.get("start", game)
                if won and darts and double_out and start in GAMES and not team:
                    best = profile.fewest_darts.get(str(start))
                    profile.fewest_darts[str(start)] = min(best or darts, darts)
            elif game == "cricket":
                marks = _count(entry.get("marks"))
                profile.cricket_darts += darts
                profile.cricket_marks += marks
                # Marks of a team leg are no one player's best.
                if won and darts and not team:
                    profile.best_mpr = max(
                        profile.best_mpr, round(marks * 3 / darts, 2)
                    )

    def match(
        self,
        game: int | str,
        players: list[dict[str, Any]],
        winner: int,
        legs_to_win: int,
        sets_to_win: int,
        winners: list[int] | None = None,
        started: str | None = None,
    ) -> None:
        """A finished match of several players: history and head-to-head.

        In a team match, both players of the winning team win it, and each of
        them beats both opponents; partners play no head-to-head. The match
        started with its first dart, for the training calendar.
        """
        side = winners or [winner]
        for index, entry in enumerate(players):
            if profile := self._profile(entry.get("name")):
                profile.matches_played += 1
                profile.matches_won += int(index in side)
        match: dict[str, Any] = {
            "started": started,
            "ended": dt_util.utcnow().isoformat(),
            "game": game,
            "legs_to_win": legs_to_win,
            "sets_to_win": sets_to_win,
            "winner": winner + 1,
            "players": [dict(entry) for entry in players],
        }
        if len(side) > 1:
            match["winners"] = [index + 1 for index in side]
        self.matches.insert(0, match)
        del self.matches[MATCH_HISTORY:]
        for index in side:
            self._beat(players[index].get("name"), players, side)

    def _beat(
        self, champion: str | None, players: list[dict[str, Any]], side: list[int]
    ) -> None:
        """A win of the champion over every named opponent."""
        for index, entry in enumerate(players):
            other = entry.get("name")
            if index in side or not champion or not other:
                continue
            first, second = sorted((champion.strip(), other.strip()), key=_key)
            pair = f"{_key(first)}\x00{_key(second)}"
            wins = self.head_to_head.setdefault(pair, [0, 0])
            wins[0 if _key(first) == _key(champion) else 1] += 1

    def delete(self, name: str) -> bool:
        """Forget a player and their head-to-head records; matches stay."""
        key = _key(name)
        if key not in self.players:
            return False
        del self.players[key]
        for pair in [pair for pair in self.head_to_head if key in pair.split("\x00")]:
            del self.head_to_head[pair]
        return True

    def link(self, name: str, person: str) -> bool:
        """Make a player a Home Assistant person; a person is one player only.

        Linking creates the profile of a player who has not played yet, so the
        picture shows from the first game. False without a valid name or person.
        """
        if not name.strip() or _person(person) is None:
            return False
        key = _key(name)
        for other in self.players.values():
            if other.person == person:
                other.person = None
        profile = self.players.setdefault(key, Profile(name=name.strip()[:NAME_LENGTH]))
        profile.person = person
        return True

    def unlink(self, name: str) -> bool:
        """Forget which person a player is; False when there is no such profile."""
        profile = self.players.get(_key(name))
        if profile is None:
            return False
        profile.person = None
        return True

    # -- storage ---------------------------------------------------------------

    def stored(self) -> dict[str, Any]:
        return {
            "players": [asdict(profile) for profile in self.players.values()],
            "matches": [dict(match) for match in self.matches],
            "head_to_head": {
                pair: list(wins) for pair, wins in self.head_to_head.items()
            },
        }

    def restore(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        players = saved.get("players")
        self.players = {}
        for entry in players if isinstance(players, list) else []:
            if isinstance(entry, dict) and (profile := Profile.restored(entry)):
                self.players[_key(profile.name)] = profile
        matches = saved.get("matches")
        self.matches = [
            dict(match)
            for match in (matches if isinstance(matches, list) else [])
            if isinstance(match, dict)
            and isinstance(match.get("ended"), str)
            and isinstance(match.get("players"), list)
        ][:MATCH_HISTORY]
        pairs = saved.get("head_to_head")
        self.head_to_head = {
            pair: list(wins)
            for pair, wins in (pairs if isinstance(pairs, dict) else {}).items()
            if isinstance(pair, str)
            and pair.count("\x00") == 1
            and isinstance(wins, list)
            and len(wins) == 2
            and all(type(win) is int and win >= 0 for win in wins)
        }

    # -- state -----------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        names = {key: profile.name for key, profile in self.players.items()}
        return {
            "players": [
                profile.summary()
                for profile in sorted(
                    self.players.values(),
                    key=lambda profile: profile.last_played or "",
                    reverse=True,
                )
            ],
            "matches": [dict(match) for match in self.matches],
            "head_to_head": [
                {
                    "players": [names.get(key, key) for key in pair.split("\x00")],
                    "wins": list(wins),
                }
                for pair, wins in sorted(
                    self.head_to_head.items(), key=lambda item: -sum(item[1])
                )
            ],
        }
