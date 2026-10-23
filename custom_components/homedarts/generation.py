"""The generation of a board's Board Manager: 1, the classic app, or 2, the
headless board.

A board tells its generation by its version. Board Manager 2 answers
everything in one read, /api/system; a board that keeps answering without it
counts as Board Manager 1 until another version is found or the route answers
again, which is asked once an hour, as an update may keep the version.
BoardGeneration keeps what it found with the entry across restarts, raises the
repair issue of Board Manager 1 and reloads the entry when the entities of the
other generation apply; the reads of a board ask it, see BoardReads.
"""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import BOARD_MANAGER_2_URL, CONF_API_GENERATION, CONF_NO_SYSTEM_API, DOMAIN
from .local_api import board_generation

_LOGGER = logging.getLogger(__name__)
# How often a board of unknown generation is asked for its version, as often as
# Board Manager 1 is read for its settings and version.
PROBE_SECONDS = 30
# Answers without /api/system in a row, over at least this long, before a board
# counts as Board Manager 1; a board that is still starting may miss it a while.
SYSTEM_MISSES = 3
SYSTEM_MISS_SECONDS = 300
# How often a board without /api/system is asked again, as after an update: as
# often as the board PC is read anew.
SYSTEM_RECHECK_SECONDS = 3600


class BoardGeneration:
    """The Board Manager generation of one board, see the module."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, issue: str) -> None:
        self.hass = hass
        self._entry = entry
        # The repair issue of Board Manager 1.
        self._issue = issue
        # Board Manager 1 (classic app) or 2 (headless board); None until known.
        self.generation: int | None = entry.data.get(CONF_API_GENERATION)
        self.setup_generation: int | None = None
        # The Board Manager version, as far as the board told it.
        self.version: str | None = None
        # The Board Manager version that answered without /api/system, if any.
        self.no_system_api: str | None = entry.data.get(CONF_NO_SYSTEM_API)
        self.system_misses = 0
        # When the misses in a row began, and when a board without the route
        # was last asked again; None before.
        self._system_missing_since: float | None = None
        self._system_checked: float | None = None
        # When a board of unknown generation was last asked for its version.
        self._version_probed: float | None = None

    @property
    def board_manager_2(self) -> bool:
        """Entities and endpoints of the headless Board Manager 2 apply."""
        return (self.generation or 1) >= 2

    @callback
    def report(self) -> None:
        """Autodarts retires the classic Board Manager; point to the new one."""
        if self.generation != 1:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._issue,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="board_manager_1",
            learn_more_url=BOARD_MANAGER_2_URL,
        )

    @callback
    def set(self, generation: int) -> None:
        """Remember the board's generation; a change rebuilds its entities."""
        self.generation = generation
        self.report()
        entry = self._entry
        # Unchanged data leaves the entry as it is.
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_API_GENERATION: generation}
        )
        if self.setup_generation is not None and (
            (self.setup_generation >= 2) != self.board_manager_2
        ):
            _LOGGER.info(
                "Board Manager %s detected; reloading to update the entities",
                generation,
            )
            self.setup_generation = generation
            self.hass.config_entries.async_schedule_reload(entry.entry_id)

    @callback
    def _remember_no_system_api(self, version: str | None) -> None:
        """Keep across restarts which version lacks /api/system, or forget it."""
        self.no_system_api = version
        self.system_misses = 0
        self._system_missing_since = None
        self._system_checked = time.monotonic()
        data = {
            key: value
            for key, value in self._entry.data.items()
            if key != CONF_NO_SYSTEM_API
        }
        if version is not None:
            data[CONF_NO_SYSTEM_API] = version
        self.hass.config_entries.async_update_entry(self._entry, data=data)

    @callback
    def check(self) -> None:
        """The version tells the generation, unless /api/system is known missing."""
        version = self.version
        generation = board_generation(version)
        missing = self.no_system_api
        if missing == "" and version:
            # The version that lacked /api/system, once known: another one
            # asks again.
            self.no_system_api = missing = version
            self.hass.config_entries.async_update_entry(
                self._entry, data={**self._entry.data, CONF_NO_SYSTEM_API: missing}
            )
        if missing is not None and version and missing != version:
            # Another Board Manager version may bring /api/system: ask again.
            _LOGGER.info(
                "Board Manager %s found; checking again for /api/system", version
            )
            self._remember_no_system_api(None)
        elif missing is not None and generation and generation >= 2:
            generation = 1
        if generation and generation != self.generation:
            self.set(generation)

    def probe_due(self, now: float) -> bool:
        """Whether to ask a board of unknown generation for its version now:
        it reveals its generation through its version first."""
        if self.generation is not None or (
            self._version_probed is not None
            and now - self._version_probed < PROBE_SECONDS
        ):
            return False
        self._version_probed = now
        return True

    @callback
    def probed(self, version: str | None) -> None:
        """The version a board of unknown generation answered, if any."""
        if generation := board_generation(version):
            self.version = version
            self.set(generation)

    def recheck_due(self, now: float) -> bool:
        """Whether to ask again for /api/system, found missing before; once
        an hour, as the version may stay the same across an update."""
        checked = self._system_checked
        if self.no_system_api is None or (
            checked is not None and now - checked < SYSTEM_RECHECK_SECONDS
        ):
            return False
        self._system_checked = now
        return True

    @callback
    def system_back(self) -> None:
        """/api/system, found missing before, answers again."""
        _LOGGER.info("Board Manager answers /api/system again; using its protocol")
        self._remember_no_system_api(None)
        self.set(2)

    def system_answered(self) -> None:
        """Board Manager 2 answered /api/system."""
        self.system_misses = 0
        self._system_missing_since = None

    @callback
    def system_missing(self, now: float) -> None:
        """Board Manager 2 answered without /api/system. A board that is still
        starting may miss the route for a while; one that keeps missing it is
        read as Board Manager 1."""
        self.system_misses += 1
        if self._system_missing_since is None:
            self._system_missing_since = now
        if (
            self.system_misses >= SYSTEM_MISSES
            and now - self._system_missing_since >= SYSTEM_MISS_SECONDS
        ):
            _LOGGER.info(
                "Board Manager %s answers without /api/system; using the "
                "protocol of Board Manager 1",
                self.version or "?",
            )
            self._remember_no_system_api(self.version or "")
            self.set(1)
