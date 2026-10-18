"""Independent cloud and local coordinators for one board."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .coordinator import AutodartsDataUpdateCoordinator
from .games_coordinator import AutodartsGamesCoordinator
from .online import OnlineBridge


@dataclass
class AutodartsRuntimeData:
    cloud: AutodartsDataUpdateCoordinator | None = None
    # The board's games: AutodartsLocalCoordinator with a Board Manager, or
    # AutodartsManualCoordinator for a dartboard without Autodarts.
    local: AutodartsGamesCoordinator | None = None
    # The webhook for online matches, while it is switched on.
    bridge: OnlineBridge | None = None


type AutodartsConfigEntry = ConfigEntry[AutodartsRuntimeData]
