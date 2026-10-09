"""Base entity for the Autodarts integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AutodartsDataUpdateCoordinator
from .local_coordinator import AutodartsLocalCoordinator


class AutodartsEntity(CoordinatorEntity[AutodartsDataUpdateCoordinator]):
    """Base class for Autodarts entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AutodartsDataUpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        board = coordinator.data.get("board", {}) if coordinator.data else {}
        board_name = board.get("name", "Autodarts Board")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.board_id)},
            name=board_name,
            manufacturer="Autodarts",
            model="Dart Board",
        )


class AutodartsLocalEntity(CoordinatorEntity[AutodartsLocalCoordinator]):
    """All local entities remain independent of cloud availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.board_id}_{key}"
        self._attr_translation_key = key
        if coordinator.manual_board:
            # A dartboard of any make, without a Board Manager to open.
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.board_id)},
                name=coordinator.device_name,
                model="Dart Board",
            )
            return
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.board_id)},
            name=coordinator.device_name,
            manufacturer="Autodarts",
            model="Dart Board",
            configuration_url=coordinator.client.base_url,
            sw_version=(coordinator.data or {}).get("version"),
        )
