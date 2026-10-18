"""Native HA events for observed darts, corrections, takeout transitions and the
moments of online matches."""

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import event_signal
from .coordinator import AutodartsDataUpdateCoordinator
from .entity import AutodartsEntity, AutodartsStoredEntity
from .games_coordinator import AutodartsGamesCoordinator
from .local_coordinator import EVENT_TYPES
from .online import ONLINE_EVENT_TYPES
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    if coordinator := runtime.local:
        async_add_entities([AutodartsBoardEvent(coordinator)])
    elif runtime.cloud:
        # A board that only the cloud reaches, such as Lens: its online moments.
        async_add_entities(
            [AutodartsCloudBoardEvent(runtime.cloud, event_signal(entry.entry_id))]
        )


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


class AutodartsCloudBoardEvent(AutodartsEntity, EventEntity):
    """The events of a board without a Board Manager in the network: the moments
    of its online matches, which the cloud reports."""

    _attr_event_types = ONLINE_EVENT_TYPES
    _attr_translation_key = "board_events"

    def __init__(
        self, coordinator: AutodartsDataUpdateCoordinator, signal: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.board_id}_board_events"
        self._signal = signal

    @property
    def available(self) -> bool:
        """Like the events of a board in the network, it stays while the cloud
        is away; it has nothing to report meanwhile."""
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._receive)
        )

    @callback
    def _receive(self, kind: str, attributes: dict[str, Any]) -> None:
        self._trigger_event(kind, attributes)
        self.async_write_ha_state()
