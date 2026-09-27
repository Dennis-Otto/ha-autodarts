"""Camera standby of the Board Manager and the practice game."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsLocalEntity
from .local_api import STANDBY_MINUTES
from .local_coordinator import AutodartsLocalCoordinator
from .practice import GAME_OPTIONS
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities(
            [AutodartsStandbySelect(coordinator), AutodartsPracticeGame(coordinator)]
        )


class AutodartsStandbySelect(AutodartsLocalEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [str(value) for value in STANDBY_MINUTES]

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "standby_minutes")

    @property
    def available(self) -> bool:
        return super().available and self.current_option is not None

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get("settings", {}).get("standby_minutes")
        return str(value) if value in STANDBY_MINUTES else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_action(
            lambda: self.coordinator.client.set_standby_minutes(int(option))
        )


class AutodartsPracticeGame(AutodartsLocalEntity, SelectEntity):
    """X01, Cricket, a party or training game; a choice starts it anew."""

    _attr_options = ["off", *GAME_OPTIONS]

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "practice_game")

    @property
    def available(self) -> bool:
        # The game lives in Home Assistant, like training sessions.
        return True

    @property
    def current_option(self) -> str:
        practice = self.coordinator.practice
        if practice.drill:
            return practice.drill
        if practice.cricket:
            return "cricket"
        if practice.party:
            return practice.party.kind
        return str(practice.game) if practice.game else "off"

    async def async_select_option(self, option: str) -> None:
        if option == "off":
            await self.coordinator.async_play(0)
        elif option.isdigit():
            await self.coordinator.async_play(int(option))
        else:
            await self.coordinator.async_play(option)
