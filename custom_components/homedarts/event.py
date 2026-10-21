"""Native HA events for observed darts, corrections, takeout transitions and the
moments of online matches."""

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsStoredEntity
from .games_coordinator import AutodartsGamesCoordinator
from .local_coordinator import EVENT_TYPES
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([AutodartsBoardEvent(entry.runtime_data.local)])


class AutodartsBoardEvent(AutodartsStoredEntity, EventEntity):
    _attr_event_types = EVENT_TYPES

    def __init__(self, coordinator: AutodartsGamesCoordinator) -> None:
        super().__init__(coordinator, "board_events")

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
