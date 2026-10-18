"""Explicit local Board Manager actions, also usable by HA automations."""

from functools import partial

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import (
    AutodartsLocalEntity,
    AutodartsStoredEntity,
    async_track_cameras,
    camera_count,
)
from .local_coordinator import AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 1

# Command -> enabled by default, entity category. Detection controls are used
# every session, so they appear on generated dashboards.
BUTTONS = {
    "start": (True, None),
    "stop": (True, None),
    "reset": (True, None),
    "restart": (True, EntityCategory.CONFIG),
    "calibrate": (True, EntityCategory.CONFIG),
    "connect": (False, EntityCategory.CONFIG),
    "disconnect": (False, EntityCategory.CONFIG),
    "start_streams": (False, EntityCategory.CONFIG),
    "stop_streams": (False, EntityCategory.CONFIG),
}
# Board Manager 2 has no routes to connect or disconnect its cloud link.
V1_BUTTONS = ("connect", "disconnect")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        unsupported = V1_BUTTONS if coordinator.board_manager_2 else ()
        # A dartboard without Autodarts has nothing to start, reset or calibrate.
        async_add_entities(
            [
                AutodartsButton(coordinator, key)
                for key in BUTTONS
                if key not in unsupported and not coordinator.manual_board
            ]
            + [
                AutodartsTrainingReset(coordinator),
                AutodartsNewLeg(coordinator),
                AutodartsNewMatch(coordinator),
                *(
                    AutodartsTournamentButton(coordinator, action)
                    for action in ("start", "next_match", "stop")
                ),
            ]
        )
        async_track_cameras(
            entry,
            coordinator,
            partial(AutodartsCameraCalibration, coordinator),
            async_add_entities,
        )


class AutodartsButton(AutodartsLocalEntity, ButtonEntity):
    def __init__(self, coordinator: AutodartsLocalCoordinator, command: str) -> None:
        super().__init__(coordinator, command)
        self._command = command
        enabled, category = BUTTONS[command]
        self._attr_entity_registry_enabled_default = enabled
        self._attr_entity_category = category
        if command == "restart":
            self._attr_device_class = ButtonDeviceClass.RESTART

    async def async_press(self) -> None:
        await self.coordinator.async_action(
            lambda: self.coordinator.client.command(self._command)
        )


class AutodartsCameraCalibration(AutodartsLocalEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsLocalCoordinator, index: int) -> None:
        super().__init__(coordinator, f"calibrate_camera_{index}")
        self._index = index
        self._attr_translation_key = "calibrate_camera"
        self._attr_translation_placeholders = {"number": str(index + 1)}
        self._attr_extra_state_attributes = {"camera": index + 1}

    @property
    def available(self) -> bool:
        return super().available and self._index < camera_count(self.coordinator)

    async def async_press(self) -> None:
        await self.coordinator.async_action(
            lambda: self.coordinator.client.calibrate_camera(self._index)
        )


class AutodartsTrainingReset(AutodartsStoredEntity, ButtonEntity):
    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "reset_training")

    async def async_press(self) -> None:
        await self.coordinator.async_new_session()


class AutodartsNewLeg(AutodartsStoredEntity, ButtonEntity):
    """Start the practice leg again from the full score."""

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "practice_new_leg")

    async def async_press(self) -> None:
        await self.coordinator.async_new_leg()


class AutodartsNewMatch(AutodartsStoredEntity, ButtonEntity):
    """Start the practice match again from zero legs and sets."""

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "practice_new_match")

    async def async_press(self) -> None:
        await self.coordinator.async_new_match()


class AutodartsTournamentButton(AutodartsStoredEntity, ButtonEntity):
    """Start a tournament with its settings, start its next match or stop it."""

    def __init__(self, coordinator: AutodartsLocalCoordinator, action: str) -> None:
        super().__init__(coordinator, f"tournament_{action}")
        self._action = action

    async def async_press(self) -> None:
        if self._action == "start":
            await self.coordinator.async_start_tournament()
        elif self._action == "next_match":
            await self.coordinator.async_next_tournament_match()
        else:
            await self.coordinator.async_stop_tournament()
