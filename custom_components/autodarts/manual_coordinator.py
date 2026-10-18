"""A dartboard without Autodarts: the games of a board, without a Board Manager.

AutodartsManualCoordinator plays the games of AutodartsGamesCoordinator, as
AutodartsLocalCoordinator does, but beside it rather than on top of it: it has
no client, no realtime events and no reads, so no change of the transport can
reach a dartboard without Autodarts. Every dart is entered in Home Assistant.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .games_coordinator import AutodartsGamesCoordinator

# A dartboard without Autodarts stands like a board whose detection is stopped:
# the darts entered by hand make every visit on their own, see ManualDarts.
MANUAL_STATE = {"running": False, "status": "Manual", "numThrows": 0, "throws": []}


class AutodartsManualCoordinator(AutodartsGamesCoordinator):
    """A dartboard without Autodarts: every dart is entered in Home Assistant.

    The training, the games and the statistics work as they do with a board.
    There is no Board Manager to read or to control, so nothing is polled.
    """

    manual_board = True

    def __init__(self, hass: HomeAssistant, board_id: str, entry: ConfigEntry) -> None:
        super().__init__(hass, board_id, entry, update_interval=None)

    def _restore(self, saved: object) -> None:
        super()._restore(saved)
        # Without detection, the darts entered by hand are the only darts.
        self.games.practice.manual_entry = True

    async def _async_update_data(self) -> dict[str, Any]:
        """The board as it stands, from the start: darts only come by hand."""
        data = dict(self.data or {})
        if "local" not in data:
            state = data["local"] = dict(MANUAL_STATE)
            self._guarded(lambda: self._follow_visit(data, state, "manual"))
        return data
