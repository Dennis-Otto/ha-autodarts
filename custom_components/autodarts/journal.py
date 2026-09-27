"""A year of training sessions and practice matches, for the training calendar.

The training session keeps its last 20 sessions and the player profiles their
last 20 matches. The journal takes over every finished one and keeps it for
365 days in a compact form, bounded in size, so the calendar and exports reach
further back.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

JOURNAL_DAYS = 365
# At most this many sessions and as many matches, the newest.
JOURNAL_SIZE = 3000
SESSION_COUNTS = (
    "darts",
    "points",
    "visits",
    "highest_visit",
    "scores_100",
    "scores_140",
    "scores_180",
    "triples",
    "doubles",
    "bulls",
    "misses",
)
# A player's result of a match: the X01 average, Cricket MPR or party points.
RESULTS = ("average", "mpr", "points")
GAME_NAMES = {
    "cricket": "Cricket",
    "shanghai": "Shanghai",
    "halve_it": "Halve-It",
    "killer": "Killer",
}
# Calendar events last at least this long, also a session of one dart.
MINIMUM_LENGTH = timedelta(minutes=1)
NAME_LENGTH = 20


def _count(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def _number(value: object) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def _moment(value: object) -> datetime | None:
    parsed = dt_util.parse_datetime(value) if isinstance(value, str) else None
    return dt_util.as_utc(parsed) if parsed and parsed.tzinfo else None


def _utc(value: str) -> datetime:
    """A timestamp the journal validated when it took the entry over."""
    return dt_util.as_utc(datetime.fromisoformat(value))


def _game(value: object) -> int | str | None:
    if type(value) is int and value > 0:
        return value
    return value if value in GAME_NAMES else None


def session_entry(saved: object) -> dict[str, Any] | None:
    """A finished session as the journal keeps it, or None if invalid."""
    if not isinstance(saved, dict):
        return None
    started, ended = _moment(saved.get("started")), _moment(saved.get("ended"))
    if started is None or ended is None or ended < started:
        return None
    return {
        "started": started.isoformat(),
        "ended": ended.isoformat(),
        **{key: _count(saved.get(key)) for key in SESSION_COUNTS},
    }


def _player(saved: object) -> dict[str, Any]:
    data = saved if isinstance(saved, dict) else {}
    name = data.get("name")
    if isinstance(name, str):
        name = name.strip()[:NAME_LENGTH] or None
    player: dict[str, Any] = {
        "name": name if isinstance(name, str) else None,
        "legs": _count(data.get("legs")),
        "sets": _count(data.get("sets")),
    }
    # Legs won in the whole match; matches before version 1.6 do not know them.
    if type(data.get("match_legs")) is int:
        player["match_legs"] = _count(data["match_legs"])
    for key in RESULTS:
        if (value := _number(data.get(key))) is not None:
            player[key] = value
    return player


def match_entry(saved: object) -> dict[str, Any] | None:
    """A finished match as the journal keeps it, or None if invalid."""
    if not isinstance(saved, dict):
        return None
    ended, game, players = (
        _moment(saved.get("ended")),
        saved.get("game"),
        saved.get("players"),
    )
    if ended is None or _game(game) is None or not isinstance(players, list):
        return None
    if not 1 <= len(players) <= 4:
        return None
    started = _moment(saved.get("started"))
    winner = saved.get("winner")
    return {
        "started": started.isoformat() if started and started <= ended else None,
        "ended": ended.isoformat(),
        "game": game,
        "legs_to_win": max(_count(saved.get("legs_to_win")), 1),
        "sets_to_win": max(_count(saved.get("sets_to_win")), 1),
        "winner": winner
        if type(winner) is int and 1 <= winner <= len(players)
        else None,
        "players": [_player(player) for player in players],
    }


def average(entry: dict[str, Any]) -> float | None:
    """The 3-dart average of a session."""
    darts: int = entry["darts"]
    return round(entry["points"] * 3 / darts, 2) if darts else None


def duration_minutes(entry: dict[str, Any]) -> float:
    seconds = (_utc(entry["ended"]) - _utc(entry["started"])).total_seconds()
    return round(seconds / 60, 1)


def player_label(player: dict[str, Any], index: int) -> str:
    """A player's name, or the position for a player without one."""
    name: str | None = player["name"]
    return name or f"#{index + 1}"


def player_results(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Every player's result, with the legs each won in the deciding set.

    The practice game starts the winner's legs from zero with the set that
    decides the match; the winner won the legs that set needed.
    """
    return [
        {
            "player": index + 1,
            **player,
            "legs": entry["legs_to_win"]
            if index + 1 == entry["winner"]
            else player["legs"],
        }
        for index, player in enumerate(entry["players"])
    ]


def scores(entry: dict[str, Any]) -> list[int]:
    """Sets won, or legs won when one set decides the match."""
    key = "sets" if entry["sets_to_win"] > 1 else "legs"
    return [player[key] for player in player_results(entry)]


def game_name(game: int | str) -> str:
    return GAME_NAMES.get(str(game), str(game))


def _decimal(value: float | int, digits: int) -> str:
    return f"{value:.{digits}f}"


def session_title(entry: dict[str, Any]) -> str:
    """For example "Training · 312 Darts · Ø 54.2", the same in every language."""
    parts = ["Training", f"{entry['darts']} Darts"]
    if (value := average(entry)) is not None:
        parts.append(f"Ø {_decimal(value, 1)}")
    return " · ".join(parts)


def session_description(entry: dict[str, Any]) -> str:
    return " · ".join(
        [
            f"180: {entry['scores_180']}",
            f"140+: {entry['scores_140']}",
            f"100+: {entry['scores_100']}",
            f"Max: {entry['highest_visit']}",
        ]
    )


def match_title(entry: dict[str, Any]) -> str:
    """For example "501 · Alex 3:2 Sam", or every player with their score."""
    game = game_name(entry["game"])
    players = entry["players"]
    labels = [player_label(player, index) for index, player in enumerate(players)]
    won = scores(entry)
    if len(players) == 2:
        return f"{game} · {labels[0]} {won[0]}:{won[1]} {labels[1]}"
    return f"{game} · " + " · ".join(
        f"{label} {score}" for label, score in zip(labels, won, strict=True)
    )


def match_description(entry: dict[str, Any]) -> str:
    """Every player's result: the average, marks per round or points."""
    lines = []
    for index, player in enumerate(entry["players"]):
        label = player_label(player, index)
        if "average" in player:
            lines.append(f"{label}: Ø {_decimal(player['average'], 1)}")
        elif "mpr" in player:
            lines.append(f"{label}: MPR {_decimal(player['mpr'], 2)}")
        elif "points" in player:
            lines.append(f"{label}: {player['points']}")
    return "\n".join(lines)


@dataclass(frozen=True)
class JournalEvent:
    """A session or a match as the calendar shows it."""

    uid: str
    start: datetime
    end: datetime
    summary: str
    description: str


def _event(kind: str, entry: dict[str, Any]) -> JournalEvent:
    end = _utc(entry["ended"])
    # Matches from before the journal did not keep their first dart. A short
    # event starts earlier instead of reaching past the moment it ended.
    start = _utc(entry["started"]) if entry["started"] else end
    start = min(start, end - MINIMUM_LENGTH)
    if kind == "session":
        summary, description = session_title(entry), session_description(entry)
    else:
        summary, description = match_title(entry), match_description(entry)
    return JournalEvent(
        uid=f"{kind}-{entry['ended']}",
        start=start,
        end=end,
        summary=summary,
        description=description,
    )


class TrainingJournal:
    """Finished sessions and matches of the last year, oldest first."""

    def __init__(self) -> None:
        self.sessions: list[dict[str, Any]] = []
        self.matches: list[dict[str, Any]] = []
        # When the first dart of the running match landed, and in which game.
        self.match_start: tuple[datetime, int | str] | None = None

    def observe_dart(self, now: datetime, game: int | str | None) -> None:
        """A match starts with its first dart; without a match nothing starts."""
        if game is None:
            self.match_start = None
        elif self.match_start is None or self.match_start[1] != game:
            self.match_start = (dt_util.as_utc(now), game)

    def sync(
        self,
        history: list[dict[str, Any]],
        matches: list[dict[str, Any]],
        now: datetime,
    ) -> bool:
        """Take over sessions and matches that ended since the last entries.

        Both sources list the newest first. Returns whether anything changed.
        """
        sessions = self._fresh(self.sessions, map(session_entry, history))
        new = self._fresh(self.matches, map(match_entry, matches))
        if new and self.match_start:
            # The first dart belongs to the match that ended first.
            began, game = self.match_start
            if game == new[0]["game"] and began <= _utc(new[0]["ended"]):
                new[0]["started"] = began.isoformat()
            self.match_start = None
        self.sessions.extend(sessions)
        self.matches.extend(new)
        return self._prune(now) or bool(sessions or new)

    @staticmethod
    def _fresh(
        entries: list[dict[str, Any]],
        newest_first: Iterable[dict[str, Any] | None],
    ) -> list[dict[str, Any]]:
        """Entries that ended after the last one kept, oldest first."""
        last = _utc(entries[-1]["ended"]) if entries else None
        fresh = []
        for entry in newest_first:
            if entry is None:
                continue
            if last is not None and _utc(entry["ended"]) <= last:
                break
            fresh.append(entry)
        fresh.reverse()
        return fresh

    def _prune(self, now: datetime) -> bool:
        """Forget entries older than a year, and the oldest beyond the limit."""
        oldest = dt_util.as_utc(now) - timedelta(days=JOURNAL_DAYS)
        changed = False
        for entries in (self.sessions, self.matches):
            while entries and (
                len(entries) > JOURNAL_SIZE or _utc(entries[0]["ended"]) < oldest
            ):
                del entries[0]
                changed = True
        return changed

    # -- calendar ----------------------------------------------------------------

    def events(self, start: datetime, end: datetime) -> list[JournalEvent]:
        """Sessions and matches that overlap the period, in order."""
        begin, finish = dt_util.as_utc(start), dt_util.as_utc(end)
        found = [
            event for event in self._all() if event.start < finish and event.end > begin
        ]
        return sorted(found, key=lambda event: (event.start, event.uid))

    def latest(self) -> JournalEvent | None:
        """The session or match that ended last; both lists are in that order."""
        last = [
            _event(kind, entries[-1])
            for kind, entries in (("session", self.sessions), ("match", self.matches))
            if entries
        ]
        return max(last, key=lambda event: event.end, default=None)

    def _all(self) -> list[JournalEvent]:
        return [
            *(_event("session", entry) for entry in self.sessions),
            *(_event("match", entry) for entry in self.matches),
        ]

    # -- storage -------------------------------------------------------------------

    def stored(self) -> dict[str, Any]:
        start = self.match_start
        return {
            "sessions": [dict(entry) for entry in self.sessions],
            "matches": [
                {**entry, "players": [dict(player) for player in entry["players"]]}
                for entry in self.matches
            ],
            "match_start": {"time": start[0].isoformat(), "game": start[1]}
            if start
            else None,
        }

    def restore(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        sessions, matches = saved.get("sessions"), saved.get("matches")
        self.sessions, self.matches = [], []
        for entries, stored, convert in (
            (self.sessions, sessions, session_entry),
            (self.matches, matches, match_entry),
        ):
            for entry in map(convert, stored if isinstance(stored, list) else []):
                # Entries stay in the order they ended; anything else is dropped.
                if entry and self._fresh(entries, [entry]):
                    entries.append(entry)
        start = saved.get("match_start")
        start = start if isinstance(start, dict) else {}
        began, game = _moment(start.get("time")), _game(start.get("game"))
        self.match_start = (began, game) if began and game is not None else None
