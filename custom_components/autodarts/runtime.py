"""Independent cloud and local coordinators for one board."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .coordinator import AutodartsDataUpdateCoordinator
from .local_coordinator import AutodartsLocalCoordinator
from .online import OnlineBridge


@dataclass
class AutodartsRuntimeData:
    cloud: AutodartsDataUpdateCoordinator | None = None
    local: AutodartsLocalCoordinator | None = None
    # The webhook for online matches, while it is switched on.
    bridge: OnlineBridge | None = None


type AutodartsConfigEntry = ConfigEntry[AutodartsRuntimeData]
