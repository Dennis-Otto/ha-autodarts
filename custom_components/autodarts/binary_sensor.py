"""Connectivity to the local manager, distinct from its cloud connection."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LIFECYCLE_STATUSES
from .entity import AutodartsLocalEntity
from .local_coordinator import AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0

# Motion flags of the detection; they change with nearly every dart and takeout.
MOTION_SENSORS = {
    "hand_detected": "isHand",
    "image_stable": "isStable",
    "takeout_partial": "isTakeoutPartial",
    "takeout_full": "isTakeoutFull",
}
# The live card shows a hand at the board and a takeout; the others are for
# diagnosis only and would just fill the recorder.
MOTION_DISABLED = ("image_stable", "takeout_full")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities(
            [AutodartsLocalConnectivity(coordinator)]
            + [
                AutodartsLocalState(coordinator, key)
                for key in (
                    *MOTION_SENSORS,
                    "cameras_active",
                    "calibrating",
                    "realtime_connected",
                    "camera_problem",
                    *(("cloud_link",) if coordinator.board_manager_2 else ()),
                )
            ]
        )
        known: set[int] = set()

        @callback
        def discover_cameras() -> None:
            count = (coordinator.data or {}).get("settings", {}).get("camera_count", 0)
            new = set(range(count)) - known
            if new:
                known.update(new)
                async_add_entities(
                    [
                        AutodartsLocalState(coordinator, "camera_problem", index)
                        for index in sorted(new)
                    ]
                )

        discover_cameras()
        entry.async_on_unload(coordinator.async_add_listener(discover_cameras))


class AutodartsLocalConnectivity(AutodartsLocalEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "local_connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success


class AutodartsLocalState(AutodartsLocalEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: AutodartsLocalCoordinator,
        key: str,
        index: int | None = None,
    ) -> None:
        super().__init__(
            coordinator, key if index is None else f"camera_{index}_problem"
        )
        self._key, self._index = key, index
        if key in MOTION_SENSORS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = key not in MOTION_DISABLED
        elif key == "camera_problem":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif key in ("cameras_active", "calibrating"):
            self._attr_device_class = BinarySensorDeviceClass.RUNNING
        else:  # realtime_connected and cloud_link
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if index is not None:
            self._attr_translation_key = "individual_camera_problem"
            self._attr_translation_placeholders = {"number": str(index + 1)}
            self._attr_extra_state_attributes = {"camera": index + 1}

    @property
    def available(self) -> bool:
        if self._key == "realtime_connected":
            return True
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        state = data.get("local", {})
        if self._key in MOTION_SENSORS:
            if (
                state.get("running") is False
                or str(state.get("status", "")).lower() in LIFECYCLE_STATUSES
            ):
                return False
            motion = data.get("motion", {}).get(MOTION_SENSORS[self._key])
            return motion if isinstance(motion, bool) else None
        if self._key == "cameras_active":
            running = data.get("camera_state", {}).get("isRunning")
            return running if isinstance(running, bool) else None
        if self._key == "calibrating":
            status = state.get("status")
            return status.lower() == "calibrating" if isinstance(status, str) else None
        if self._key == "realtime_connected":
            return self.coordinator.stream_connected
        if self._key == "cloud_link":
            link = (data.get("system") or {}).get("cloud_link")
            return link == "connected" if isinstance(link, str) else None
        problems = data.get("camera_problems", [])
        if self._index is not None:
            return problems[self._index] if self._index < len(problems) else None
        if any(problem is True for problem in problems):
            return True
        return (
            False
            if problems and all(problem is False for problem in problems)
            else None
        )
