"""Darts corrected, entered or thrown in Home Assistant, on top of the board's.

The board reports the darts it sees. The training session and the practice
game follow the visit as Home Assistant knows it: the board's darts with the
corrections made in Home Assistant, darts entered by hand and the darts of the
bot, in the order they came. A visit that ends in Home Assistant hides the
board's darts until they are pulled; while the detection does not run, the
darts entered by hand make the visit on their own.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .const import LIFECYCLE_STATUSES
from .training import DART_FLAGS, is_takeout, segments

# Beds as the actions name them: S1 to T20, 25 for the outer bull, BULL and MISS.
BEDS: dict[str, tuple[int, int]] = {
    **{
        f"{prefix}{number}": (number, multiplier)
        for multiplier, prefix in enumerate("SDT", 1)
        for number in range(1, 21)
    },
    "25": (25, 1),
    "BULL": (25, 2),
    "MISS": (0, 0),
}
# Other names players use for the bulls: the single or outer bull, and the
# double bull or bullseye by its score.
ALIASES = {
    "S25": "25",
    "SB": "25",
    "OB": "25",
    "D25": "BULL",
    "DB": "BULL",
    "50": "BULL",
}


def parse_bed(name: object) -> dict[str, Any] | None:
    """A dart in the named bed, in any upper and lower case; None if unknown."""
    key = name.strip().upper() if isinstance(name, str) else ""
    key = ALIASES.get(key, key)
    if key not in BEDS:
        return None
    number, multiplier = BEDS[key]
    return {"number": number, "multiplier": multiplier, "name": key}


def _key(dart: dict[str, Any]) -> tuple[int, int, str | None]:
    return dart["number"], dart["multiplier"], dart["name"]


def _segment(dart: dict[str, Any]) -> dict[str, Any]:
    return {key: dart[key] for key in ("name", "number", "multiplier")}


@dataclass
class Extra:
    """A dart of Home Assistant's: entered by hand, thrown by the bot or replayed."""

    dart: dict[str, Any]
    position: tuple[float, float] | None
    # The board's darts of the visit that came before it.
    after: int


@dataclass
class Fix:
    """A board dart put into another bed in Home Assistant."""

    # What the board saw, to tell when the board changes its mind.
    reading: dict[str, Any]
    dart: dict[str, Any]
    # Where the correction says the dart is. The board's position is left
    # behind: where the board misread the bed, it misread the spot as well.
    position: tuple[float, float] | None


class ManualDarts:
    """The visit as Home Assistant knows it, from the board's darts."""

    def __init__(self) -> None:
        self.extras: list[Extra] = []
        # Place among the board's darts of the visit -> the correction, while
        # the board keeps its reading.
        self.fixes: dict[int, Fix] = {}
        # Darts on the board that belong to an ended visit, until they are
        # pulled: the board's readings, told apart from new darts by content.
        self.hidden: list[dict[str, Any]] = []
        # Where each dart of the last visit came from: ("board", place),
        # ("extra", index) or ("hidden", place).
        self.sources: list[tuple[str, int]] = []
        self._board: list[dict[str, Any]] = []
        self._readings: list[dict[str, Any]] = []
        self._running = False

    @property
    def pending(self) -> bool:
        """Whether the visit has darts or corrections of Home Assistant's."""
        return bool(self.extras or self.fixes)

    def bot_darts(self) -> int:
        return sum(bool(extra.dart.get("bot")) for extra in self.extras)

    @staticmethod
    def _running_state(state: dict[str, Any]) -> bool:
        status = str(state.get("status", "")).lower()
        return state.get("running") is True and status not in LIFECYCLE_STATUSES

    def _places(self, board: list[dict[str, Any]]) -> list[int]:
        """Where the board's darts of the visit are, besides the hidden ones;
        a hidden reading stands for its first dart on the board."""
        budget = Counter(map(_key, self.hidden))
        places = []
        for place, dart in enumerate(board):
            if budget[_key(dart)]:
                budget[_key(dart)] -= 1
            else:
                places.append(place)
        return places

    def board_darts(self, state: dict[str, Any]) -> int:
        """Darts the board shows beyond those of an ended visit."""
        board = segments(state)
        if board is None or not self._running_state(state):
            return 0
        return len(self._places(board))

    def held(self, state: dict[str, Any]) -> dict[str, Any]:
        """The board as it was before its new darts: only the hidden ones."""
        places = set(self._places(segments(state) or []))
        throws = [
            throw
            for place, throw in enumerate(state.get("throws", []))
            if place not in places
        ]
        return {**state, "numThrows": len(throws), "throws": throws}

    def apply(self, state: dict[str, Any]) -> dict[str, Any]:
        """The board's state with the visit as Home Assistant knows it."""
        board = segments(state)
        if board is None:
            return state
        running = self._running_state(state)
        if self._running and not running:
            # A stopped detection ends the visit, as it does on the board.
            self.extras = []
        self._running = running
        if not running:
            # The darts in the board belong to no visit: they stay as they are,
            # and the darts entered by hand follow them.
            self.hidden, self.fixes = list(board), {}
            self._board, self._readings = board, []
            if not self.extras:
                self.sources = []
                return state
            playing = {**state, "running": True, "status": "Throw", "event": "Throw"}
            return self._effective(playing, [], state.get("throws", []))
        # Hidden darts that were pulled are gone for good.
        present = Counter(map(_key, board))
        hidden = []
        for dart in self.hidden:
            if present[_key(dart)]:
                present[_key(dart)] -= 1
                hidden.append(dart)
        self.hidden = hidden
        self._follow(state, board)
        places = self._places(board)
        visible = [board[place] for place in places]
        self._board, self._readings = board, visible
        self.fixes = {
            place: fix
            for place, fix in self.fixes.items()
            if place < len(visible) and visible[place] == fix.reading
        }
        throws = state.get("throws", [])
        return self._effective(state, [throws[place] for place in places])

    def _follow(self, state: dict[str, Any], board: list[dict[str, Any]]) -> None:
        """Pulled or replaced darts end the visit, as they do for the training."""
        visible = [board[place] for place in self._places(board)]
        if len(visible) >= len(self._readings):
            return
        if not visible or is_takeout(state):
            # The darts still on the board are pulled next; they stay hidden.
            self.extras, self.fixes = [], {}
            self.hidden = list(board)
        elif Counter(map(_key, visible)) - Counter(map(_key, self._readings)):
            # New darts without an empty board in between: a missed takeout.
            self.extras, self.fixes = [], {}

    def _effective(
        self,
        state: dict[str, Any],
        raw: list[dict[str, Any]],
        hidden: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """The board's darts of the visit with the extras between them, after
        the hidden darts where they stay in the list."""
        throws: list[dict[str, Any]] = list(hidden or [])
        sources = [("hidden", place) for place in range(len(throws))]
        for place in range(len(raw) + 1):
            last = place == len(raw)
            for index, extra in enumerate(self.extras):
                if extra.after == place or (last and extra.after > place):
                    throws.append(self._throw(extra.dart, extra.position))
                    sources.append(("extra", index))
            if not last:
                fix = self.fixes.get(place)
                throws.append(self._fixed(raw[place], fix) if fix else raw[place])
                sources.append(("board", place))
        self.sources = sources
        return {**state, "numThrows": len(throws), "throws": throws}

    @staticmethod
    def _throw(
        dart: dict[str, Any], position: tuple[float, float] | None
    ) -> dict[str, Any]:
        """A dart of Home Assistant's, shaped like the board's darts."""
        throw: dict[str, Any] = {
            "segment": _segment(dart),
            **{flag: True for flag in DART_FLAGS if dart.get(flag)},
        }
        if position is not None:
            throw["coords"] = {"x": position[0], "y": position[1]}
        return throw

    @staticmethod
    def _fixed(raw: dict[str, Any], fix: Fix) -> dict[str, Any]:
        """A board dart in the bed it was corrected to, at the position the
        correction gives, if any."""
        throw = {key: value for key, value in raw.items() if key != "coords"}
        if fix.position is not None:
            throw["coords"] = {"x": fix.position[0], "y": fix.position[1]}
        return {**throw, "segment": _segment(fix.dart), "corrected": True}

    # -- changes -------------------------------------------------------------------

    def add(
        self, dart: dict[str, Any], position: tuple[float, float] | None, flag: str
    ) -> None:
        """A dart entered by hand (manual) or thrown by the bot (bot)."""
        self.extras.append(Extra({**dart, flag: True}, position, len(self._readings)))

    def correct(
        self,
        place: int,
        dart: dict[str, Any],
        position: tuple[float, float] | None = None,
    ) -> None:
        """Put the dart at this place of the last visit into another bed, at
        the position given, or without one."""
        kind, index = self.sources[place]
        if kind == "extra":
            extra = self.extras[index]
            if _key(extra.dart) != _key(dart):
                manual = {"manual": True} if extra.dart.get("manual") else {}
                extra.dart = {**dart, **manual, "corrected": True}
                extra.position = position
            elif position is not None:
                # The same bed, now with the spot where the dart is.
                extra.position = position
            return
        reading = self._readings[index]
        if _key(reading) == _key(dart):
            # Back to what the board saw, where the board saw it.
            self.fixes.pop(index, None)
        else:
            self.fixes[index] = Fix(reading, dict(dart), position)

    def end_visit(self) -> None:
        """The visit ends in Home Assistant; its darts on the board stay hidden."""
        self.hidden = list(self._board)
        self._readings = []
        self.extras, self.fixes = [], {}

    def replay(
        self, darts: list[dict[str, Any]], positions: list[tuple[float, float] | None]
    ) -> None:
        """The darts of an undone visit come back as the current visit."""
        self.extras = [
            Extra(dict(dart), position, len(self._readings))
            for dart, position in zip(darts, positions, strict=True)
        ]
        self.fixes = {}
