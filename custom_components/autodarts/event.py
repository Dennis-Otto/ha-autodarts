"""Native HA events for observed darts, corrections and takeout transitions."""

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsLocalEntity
from .local_coordinator import EVENT_TYPES, AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities([AutodartsBoardEvent(coordinator)])


class AutodartsBoardEvent(AutodartsLocalEntity, EventEntity):
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "board_events")

    @property
    def available(self) -> bool:
        # Sessions, personal bests and daily goals are announced without the board.
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.event_signal, self._receive
            )
        )

    @callback
    def _receive(self, kind: str, attributes: dict[str, Any]) -> None:
        self._trigger_event(kind, attributes)
        self.async_write_ha_state()
