"""A dartboard without Autodarts: the games of a board, without a Board Manager.

AutodartsManualCoordinator plays the games of AutodartsGamesCoordinator, as
AutodartsLocalCoordinator does, but beside it rather than on top of it: it has
no client, no realtime events and no reads, so no change of the transport can
reach a dartboard without Autodarts. Every dart is entered in Home Assistant:
on the keypad, by voice or an action, or by a Granboard over Bluetooth, whose
GranboardLink enters its darts as the action throw_dart does.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_GRANBOARD
from .games_coordinator import AutodartsGamesCoordinator
from .granboard import GranboardLink

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
        # The Granboard whose darts the dartboard receives, if it has one.
        address = entry.data.get(CONF_GRANBOARD)
        self.granboard = None
        if address:
            self.granboard = GranboardLink(hass, entry, self, address)
            self.device_model = "Granboard"

    @callback
    def async_start(self) -> None:
        super().async_start()
        if self.granboard:
            self.granboard.async_start()

    async def async_shutdown(self) -> None:
        # No dart of the Granboard comes in while the games are saved.
        try:
            if self.granboard:
                await self.granboard.async_stop()
        finally:
            await super().async_shutdown()

    def diagnostics(self) -> dict[str, Any]:
        """What a dartboard without Autodarts connects to: nothing, or a Granboard."""
        if self.granboard is None:
            return {"manual_board": True}
        return {"manual_board": True, "granboard": self.granboard.diagnostics()}

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
