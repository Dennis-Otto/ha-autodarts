"""Board software version and the update Board Manager 2 announces."""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsBoardEntity
from .local_coordinator import AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.local
    if (
        isinstance(coordinator, AutodartsLocalCoordinator)
        and coordinator.board_manager_2
    ):
        async_add_entities([AutodartsBoardUpdate(coordinator)])


class AutodartsBoardUpdate(AutodartsBoardEntity, UpdateEntity):
    """Installing stays on the board PC (`autodarts update`); HA shows the news."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = "Autodarts Board Manager"

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "board_software")

    @property
    def installed_version(self) -> str | None:
        version = (self.coordinator.data or {}).get("version")
        return version if isinstance(version, str) else None

    @property
    def latest_version(self) -> str | None:
        system = (self.coordinator.data or {}).get("system") or {}
        latest = system.get("update_available")
        return latest if isinstance(latest, str) and latest else self.installed_version
