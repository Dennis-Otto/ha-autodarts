"""Local detection, upstream connection, settings, training, practice games and
tournaments."""

from functools import partial
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsLocalEntity
from .local_api import CONFIG_SWITCHES
from .local_coordinator import AutodartsLocalCoordinator
from .practice import OPTIONS as PRACTICE_OPTIONS
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        # Board Manager 2 manages its cloud link itself; it offers no toggle.
        upstream = () if coordinator.board_manager_2 else ("upstream",)
        async_add_entities(
            [
                *(
                    AutodartsSwitch(coordinator, key)
                    for key in ("detection", *upstream, *CONFIG_SWITCHES)
                ),
                AutodartsTrainingSwitch(coordinator, "training_session"),
                AutodartsTrainingSwitch(coordinator, "training_auto_start"),
                *(
                    AutodartsPracticeSwitch(coordinator, option)
                    for option in PRACTICE_OPTIONS
                ),
                AutodartsAchievementsSwitch(coordinator),
                AutodartsTournamentSwitch(coordinator, "third_place"),
                AutodartsTournamentSwitch(coordinator, "random_draw"),
            ]
        )


class AutodartsSwitch(AutodartsLocalEntity, SwitchEntity):
    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        if key in CONFIG_SWITCHES:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        if self._key in CONFIG_SWITCHES:
            setting = data.get("settings", {}).get(self._key)
            return setting if isinstance(setting, bool) else None
        value = data.get("local", {}).get(
            "running" if self._key == "detection" else "connected"
        )
        return value if isinstance(value, bool) else None

    async def _async_set(self, enabled: bool) -> None:
        client = self.coordinator.client
        if self._key == "detection":
            action = partial(client.command, "start" if enabled else "stop")
        elif self._key == "upstream":
            action = partial(client.command, "connect" if enabled else "disconnect")
        else:
            action = partial(client.set_config_switch, self._key, enabled)
        await self.coordinator.async_action(action)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)


class AutodartsTrainingSwitch(AutodartsLocalEntity, SwitchEntity):
    """Start or end a training session, or let the first dart start one."""

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        if key == "training_auto_start":
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        # Sessions live in Home Assistant and work while the board is offline.
        return True

    @property
    def is_on(self) -> bool:
        training = self.coordinator.training
        return (
            training.active if self._key == "training_session" else training.auto_start
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self._key == "training_session":
            await self.coordinator.async_start_session()
        else:
            await self.coordinator.async_set_auto_start(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._key == "training_session":
            await self.coordinator.async_end_session()
        else:
            await self.coordinator.async_set_auto_start(False)


class AutodartsPracticeSwitch(AutodartsLocalEntity, SwitchEntity):
    """A rule of the practice game."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsLocalCoordinator, option: str) -> None:
        super().__init__(coordinator, f"practice_{option}")
        self._option = option

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.practice.setting(self._option)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_practice_option(self._option, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_practice_option(self._option, False)


class AutodartsAchievementsSwitch(AutodartsLocalEntity, SwitchEntity):
    """Unlock the players' achievements and announce them."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "achievements_enabled")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.progress.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_achievements(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_achievements(False)


class AutodartsTournamentSwitch(AutodartsLocalEntity, SwitchEntity):
    """A setting of the next tournament: the third-place match or a random draw."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsLocalCoordinator, option: str) -> None:
        super().__init__(coordinator, f"tournament_{option}")
        self._option = option

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.coordinator.tournament.setup, self._option))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_tournament(**{self._option: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_tournament(**{self._option: False})
