"""What a loaded board keeps while Home Assistant runs."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .games_coordinator import AutodartsGamesCoordinator
from .online import OnlineBridge


@dataclass
class AutodartsRuntimeData:
    # The board's games: AutodartsLocalCoordinator with a Board Manager, or
    # AutodartsManualCoordinator for a dartboard without Autodarts.
    local: AutodartsGamesCoordinator
    # The webhook for online matches, while it is switched on.
    bridge: OnlineBridge | None = None


type AutodartsConfigEntry = ConfigEntry[AutodartsRuntimeData]
