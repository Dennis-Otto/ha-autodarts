"""Names of the practice and tournament players, for the scoreboard and events."""

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsLocalEntity
from .local_coordinator import AutodartsLocalCoordinator
from .practice import MAX_PLAYERS
from .profiles import NAME_LENGTH
from .runtime import AutodartsConfigEntry
from .tournament import parse_players

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities(
            [
                *(
                    AutodartsPlayerName(coordinator, index)
                    for index in range(MAX_PLAYERS)
                ),
                AutodartsTournamentPlayers(coordinator),
            ]
        )


class AutodartsPlayerName(AutodartsLocalEntity, TextEntity):
    """An empty name shows as "Player N" on the card."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "practice_player"
    _attr_native_min = 0
    _attr_native_max = NAME_LENGTH

    def __init__(self, coordinator: AutodartsLocalCoordinator, index: int) -> None:
        super().__init__(coordinator, f"practice_player_{index + 1}")
        self._attr_translation_key = "practice_player"
        self._attr_translation_placeholders = {"number": str(index + 1)}
        self._index = index

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.practice.names[self._index]

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_set_player_name(self._index, value)


class AutodartsTournamentPlayers(AutodartsLocalEntity, TextEntity):
    """The players of the next tournament, their names separated by commas."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 0
    _attr_native_max = 255

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "tournament_players")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return ", ".join(self.coordinator.tournament.setup.players)

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_set_tournament(players=parse_players(value))
