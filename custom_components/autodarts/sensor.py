"""Sensor platform for the Autodarts integration."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    SENSOR_BOARD_EVENT,
    SENSOR_BOARD_STATUS,
    SENSOR_DARTS_THROWN,
    SENSOR_GAME_MODE,
    SENSOR_LAST_THROW,
    SENSOR_MATCH_STATE,
    SENSOR_NUM_THROWS,
    SENSOR_ROUND,
    SENSOR_VISIT_SCORE,
)
from .coordinator import AutodartsDataUpdateCoordinator
from .entity import AutodartsEntity, AutodartsLocalEntity
from .local_coordinator import AutodartsLocalCoordinator
from .online import SENSOR_KEY as ONLINE_SENSOR_KEY
from .online import OnlineBridge
from .runtime import AutodartsConfigEntry
from .training import COUNTERS

# Session values that can go down again, unlike the counters.
TRAINING_MEASUREMENTS = ("average", "highest_visit")
# Units match the live sensors: darts count darts, scores count points.
TRAINING_UNITS = {
    "darts": "darts",
    "triples": "darts",
    "doubles": "darts",
    "bulls": "darts",
    "misses": "darts",
    "points": "points",
    "average": "points",
    "highest_visit": "points",
    "visits": "visits",
    "scores_100": "visits",
    "scores_140": "visits",
    "scores_180": "visits",
}

PARALLEL_UPDATES = 0

# Board Manager detection states, translated in strings.json.
LOCAL_STATES = [
    "offline",
    "starting",
    "stopping",
    "stopped",
    "throw",
    "takeout",
    "takeout_in_progress",
    "calibrating",
    "error",
]
MATCH_STATES = ["no_match", "active", "finished"]
BOARD_STATES = ["connected", "disconnected"]

# ---------------------------------------------------------------------------
# Helpers to extract values from coordinator data
# ---------------------------------------------------------------------------
# coordinator.data = {"board": {...}, "match": {...} | None, "local": {...}}


def _board(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("board") or {}


def _match(data: dict[str, Any]) -> dict[str, Any] | None:
    return data.get("match")


def _local(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("local") or {}


# -- value extractors -------------------------------------------------------


def _get_board_status(data: dict[str, Any]) -> str:
    """Board connected / disconnected (from cloud board state)."""
    board = _board(data)
    state = board.get("state") or {}
    if state.get("connected"):
        return "connected"
    return "disconnected"


def _text(value: Any) -> str | None:
    """Board text short enough for a state; Home Assistant stores 255 characters."""
    return value if isinstance(value, str) and 0 < len(value) <= 255 else None


def _get_board_event(data: dict[str, Any]) -> str | None:
    """Last board event from local detection or cloud."""
    local = _local(data)
    if local:
        return _text(local.get("event")) or _text(local.get("status"))
    board = _board(data)
    state = board.get("state") or {}
    return state.get("event") or board.get("status")


def _get_game_mode(data: dict[str, Any]) -> str | None:
    """Game variant (X01, Cricket, etc.) from match."""
    match = _match(data)
    if not match:
        return None
    return match.get("variant")


def _get_match_state(data: dict[str, Any]) -> str | None:
    """Match state — active / finished / etc."""
    match = _match(data)
    if not match:
        return "no_match"
    if match.get("finished"):
        return "finished"
    return "active"


def _get_round(data: dict[str, Any]) -> int | None:
    """Current round number."""
    match = _match(data)
    if not match:
        return None
    return match.get("round")


BEDS = frozenset(
    {"Single", "SingleInner", "SingleOuter", "Double", "Triple", "Outside"}
)
SEGMENT_KEYS = ("segment", "number", "multiplier", "bed")


def _dart(dart: Any) -> dict[str, Any] | None:
    """A dart's scoring segment and normalized board position for dashboards."""
    segment = dart.get("segment") if isinstance(dart, dict) else None
    if not isinstance(segment, dict):
        return None
    number, multiplier = segment.get("number"), segment.get("multiplier")
    if type(number) is not int or type(multiplier) is not int:
        return None
    result = {
        "segment": segment["name"] if isinstance(segment.get("name"), str) else None,
        "number": number,
        "multiplier": multiplier,
        "score": number * multiplier,
        "bed": segment["bed"] if segment.get("bed") in BEDS else None,
    }
    coords = dart.get("coords")
    if isinstance(coords, dict) and all(
        type(coords.get(axis)) in (int, float) and math.isfinite(coords[axis])
        for axis in ("x", "y")
    ):
        # 1.0 is the outer edge of the double ring; y points to the 20.
        result["x"], result["y"] = round(coords["x"], 3), round(coords["y"], 3)
    return result


def _darts(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Valid darts of the current visit; malformed board data is ignored."""
    throws = _local(data).get("throws")
    return list(filter(None, map(_dart, throws if isinstance(throws, list) else [])))


def _get_last_throw(data: dict[str, Any]) -> str | None:
    """Last detected throw segment name (e.g. T20, D16, S5, M2)."""
    darts = _darts(data)
    return darts[-1]["segment"] if darts else None


def _number(value: Any) -> int | float | None:
    """A board value a numeric sensor can show; anything else reads as unknown."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _get_num_throws(data: dict[str, Any]) -> int | float | None:
    """Number of throws in the current turn (from local board, 0–3)."""
    local = _local(data)
    if local:
        return _number(local.get("numThrows"))
    return None


def _get_visit_score(data: dict[str, Any]) -> int | None:
    """Total score of the current turn/visit."""
    match = _match(data)
    if not match:
        return None
    return match.get("turnScore")


def _get_darts_thrown(data: dict[str, Any]) -> int | None:
    """Total darts thrown in the match (across all players)."""
    match = _match(data)
    if not match:
        return None
    turns = match.get("turns")
    if isinstance(turns, list):
        return sum(len(t.get("throws", [])) for t in turns)
    return None


# ---------------------------------------------------------------------------
# Sensor descriptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class AutodartsSensorEntityDescription(SensorEntityDescription):
    """Describe an Autodarts sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


STATIC_SENSORS: tuple[AutodartsSensorEntityDescription, ...] = (
    AutodartsSensorEntityDescription(
        key=SENSOR_BOARD_STATUS,
        translation_key=SENSOR_BOARD_STATUS,
        device_class=SensorDeviceClass.ENUM,
        options=BOARD_STATES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_get_board_status,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_BOARD_EVENT,
        translation_key=SENSOR_BOARD_EVENT,
        value_fn=_get_board_event,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_GAME_MODE,
        translation_key=SENSOR_GAME_MODE,
        value_fn=_get_game_mode,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_MATCH_STATE,
        translation_key=SENSOR_MATCH_STATE,
        device_class=SensorDeviceClass.ENUM,
        options=MATCH_STATES,
        value_fn=_get_match_state,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_ROUND,
        translation_key=SENSOR_ROUND,
        value_fn=_get_round,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_LAST_THROW,
        translation_key=SENSOR_LAST_THROW,
        value_fn=_get_last_throw,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_NUM_THROWS,
        translation_key=SENSOR_NUM_THROWS,
        native_unit_of_measurement="darts",
        value_fn=_get_num_throws,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_VISIT_SCORE,
        translation_key=SENSOR_VISIT_SCORE,
        native_unit_of_measurement="points",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_get_visit_score,
    ),
    AutodartsSensorEntityDescription(
        key=SENSOR_DARTS_THROWN,
        translation_key=SENSOR_DARTS_THROWN,
        native_unit_of_measurement="darts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_get_darts_thrown,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Autodarts sensors from a config entry."""
    runtime = entry.runtime_data
    entities: list[SensorEntity] = []
    local_keys = {SENSOR_BOARD_EVENT, SENSOR_LAST_THROW, SENSOR_NUM_THROWS}
    if runtime.cloud:
        entities.extend(
            AutodartsSensor(runtime.cloud, description)
            for description in STATIC_SENSORS
            if runtime.local is None or description.key not in local_keys
        )
    if runtime.local:
        entities.extend(
            (
                AutodartsTrainingDartsSensor
                if key == "darts"
                else AutodartsTrainingSensor
            )(runtime.local, key)
            for key in (*COUNTERS, *TRAINING_MEASUREMENTS, "started")
        )
        entities.append(AutodartsLastSessionSensor(runtime.local))
        entities.extend(
            AutodartsPracticeSensor(runtime.local, key)
            for key in ("remaining", "checkout", "target")
        )
        entities.extend(
            AutodartsPracticeStatistic(runtime.local, key)
            for key in PRACTICE_STATISTICS
        )
        entities.append(AutodartsCorrectionRate(runtime.local))
        entities.extend(
            (
                AutodartsPersonalBest(runtime.local),
                AutodartsDailyDarts(runtime.local),
                AutodartsStreak(runtime.local),
                AutodartsPlayerProfiles(runtime.local),
                AutodartsDoubles(runtime.local),
                AutodartsLastMatch(runtime.local),
                AutodartsWeeklyReport(runtime.local),
            )
        )
        entities.extend(
            AutodartsLocalSensor(runtime.local, description)
            for description in STATIC_SENSORS
            if description.key in local_keys
        )
        if runtime.local.board_manager_2:
            entities.extend(
                AutodartsLocalSensor(runtime.local, description)
                for description in SYSTEM_SENSORS
            )
        entities.extend(
            (
                AutodartsVisitSensor
                if description.key == "local_visit_score"
                else AutodartsLocalSensor
            )(runtime.local, description)
            for description in LOCAL_SENSORS
        )
        if runtime.bridge:
            entities.append(AutodartsOnlineBridgeSensor(runtime.local, runtime.bridge))
    async_add_entities(entities)
    if coordinator := runtime.local:
        known: set[int] = set()

        @callback
        def discover_cameras() -> None:
            count = (coordinator.data or {}).get("settings", {}).get("camera_count", 0)
            new = set(range(count)) - known
            if not new:
                return
            known.update(new)
            async_add_entities(
                [
                    AutodartsCameraSensor(
                        coordinator,
                        index,
                        AutodartsSensorEntityDescription(
                            key=f"camera_{index}_fps",
                            translation_key="camera_fps",
                            translation_placeholders={"number": str(index + 1)},
                            native_unit_of_measurement="fps",
                            state_class=SensorStateClass.MEASUREMENT,
                            entity_category=EntityCategory.DIAGNOSTIC,
                            entity_registry_enabled_default=False,
                            value_fn=partial(_camera_fps, index=index),
                        ),
                    )
                    for index in sorted(new)
                ]
            )

        discover_cameras()
        entry.async_on_unload(coordinator.async_add_listener(discover_cameras))


# ---------------------------------------------------------------------------
# Sensor entity classes
# ---------------------------------------------------------------------------


class AutodartsSensor(AutodartsEntity, SensorEntity):
    """Representation of a static Autodarts sensor."""

    entity_description: AutodartsSensorEntityDescription

    def __init__(
        self,
        coordinator: AutodartsDataUpdateCoordinator,
        description: AutodartsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.board_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})


def _last_throw_score(data: dict[str, Any]) -> int | None:
    darts = _darts(data)
    return darts[-1]["score"] if darts else None


def _local_visit_score(data: dict[str, Any]) -> int:
    return sum(dart["score"] for dart in _darts(data))


def _local_status(data: dict[str, Any]) -> str | None:
    """Board Manager status as a translatable state; unknown ones read as unknown."""
    status = _local(data).get("status")
    if not isinstance(status, str):
        return None
    state = "_".join(status.lower().split())
    return state if state in LOCAL_STATES else None


def _camera_fps(data: dict[str, Any], index: int) -> float | None:
    fps = data.get("camera_stats", {}).get("fps")
    return _number(fps[index]) if isinstance(fps, list) and index < len(fps) else None


LOCAL_SENSORS = (
    AutodartsSensorEntityDescription(
        key="local_status",
        translation_key="local_status",
        device_class=SensorDeviceClass.ENUM,
        options=LOCAL_STATES,
        value_fn=_local_status,
    ),
    AutodartsSensorEntityDescription(
        key="last_throw_score",
        translation_key="last_throw_score",
        native_unit_of_measurement="points",
        value_fn=_last_throw_score,
    ),
    AutodartsSensorEntityDescription(
        key="local_visit_score",
        translation_key="local_visit_score",
        native_unit_of_measurement="points",
        value_fn=_local_visit_score,
    ),
    AutodartsSensorEntityDescription(
        key="detection_fps",
        translation_key="detection_fps",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _number(data.get("stats", {}).get("fps")),
    ),
)


def _system(data: dict[str, Any], key: str) -> int | float | None:
    return _number((data.get("system") or {}).get(key))


# Host load reported by Board Manager 2.
def _host(data: dict[str, Any]) -> dict[str, Any]:
    host = data.get("board_pc")
    return host if isinstance(host, dict) else {}


def _operating_system(data: dict[str, Any]) -> str | None:
    """For example Debian 13, from the distribution or the plain system name."""
    host = _host(data)
    name = host.get("platform") or host.get("os")
    if not isinstance(name, str):
        return None
    version = host.get("platform_version")
    name = name[:1].upper() + name[1:]
    return f"{name} {version}" if isinstance(version, str) else name


SYSTEM_SENSORS = (
    AutodartsSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _system(data, "cpu_percent"),
    ),
    AutodartsSensorEntityDescription(
        key="memory_usage",
        translation_key="memory_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _system(data, "memory_bytes"),
    ),
    AutodartsSensorEntityDescription(
        key="host_os",
        translation_key="host_os",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_operating_system,
        attr_fn=lambda data: {
            "kernel": _host(data).get("kernel"),
            "architecture": _host(data).get("architecture"),
        },
    ),
    AutodartsSensorEntityDescription(
        key="host_processor",
        translation_key="host_processor",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _host(data).get("cpu_model"),
        attr_fn=lambda data: {"cores": _host(data).get("cpu_cores")},
    ),
    AutodartsSensorEntityDescription(
        key="vision_version",
        translation_key="vision_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _host(data).get("vision_version"),
        attr_fn=lambda data: {"opencv_version": _host(data).get("opencv_version")},
    ),
)


class AutodartsLocalSensor(AutodartsLocalEntity, SensorEntity):
    entity_description: AutodartsSensorEntityDescription

    def __init__(
        self,
        coordinator: AutodartsLocalCoordinator,
        description: AutodartsSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if attr_fn := self.entity_description.attr_fn:
            return attr_fn(self.coordinator.data or {})
        return None


class AutodartsCameraSensor(AutodartsLocalSensor):
    """A per-camera value; the camera number lets cards group its entities."""

    def __init__(
        self,
        coordinator: AutodartsLocalCoordinator,
        index: int,
        description: AutodartsSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)
        self._attr_extra_state_attributes = {"camera": index + 1}


class AutodartsVisitSensor(AutodartsLocalSensor):
    """The detected visit, with each dart's segment and position for cards."""

    # Live positions and recent visits are for display only and must not grow
    # the recorder database.
    _unrecorded_attributes = frozenset({"throws", "recent_visits"})

    def __init__(
        self,
        coordinator: AutodartsLocalCoordinator,
        description: AutodartsSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)
        self._throws: list[dict[str, Any]] = []
        self._update_throws()

    def _update_throws(self) -> None:
        throws: list[dict[str, Any]] = []
        for dart in _darts(self.coordinator.data or {}):
            previous = (
                self._throws[len(throws)] if len(throws) < len(self._throws) else {}
            )
            if all(previous.get(key) == dart[key] for key in SEGMENT_KEYS):
                # Camera jitter moves an unchanged dart slightly; keep it steady.
                dart |= {
                    axis: previous[axis] for axis in ("x", "y") if axis in previous
                }
            throws.append(dart)
        self._throws = throws

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_throws()
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "throws": self._throws,
            # Copies: a stored state must not change with the next visit.
            "recent_visits": [
                dict(visit) for visit in self.coordinator.training.recent_visits
            ],
        }


class AutodartsTrainingSensor(AutodartsLocalEntity, SensorEntity):
    """Locally stored session totals remain readable while the board is offline."""

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, f"training_{key}")
        self._key = key
        self._attr_native_unit_of_measurement = TRAINING_UNITS.get(key)
        if key == "started":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif key in TRAINING_MEASUREMENTS:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            if key == "average":
                self._attr_suggested_display_precision = 1
        else:
            # Totals only grow until the session is reset, like a meter.
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> datetime | float | int | None:
        session = self.coordinator.training.snapshot()
        if self._key == "started":
            return dt_util.parse_datetime(session["started"])
        if self._key == "average":
            # Points per three darts, as darts players compare their level.
            darts = session["darts"]
            return round(session["points"] / darts * 3, 2) if darts else None
        return int(session[self._key])


class AutodartsTrainingDartsSensor(AutodartsTrainingSensor):
    """Darts of the session, with hits per bed for heatmaps."""

    # The breakdown is for cards; long-term history only needs the total.
    _unrecorded_attributes = frozenset({"hits"})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"hits": self.coordinator.training.snapshot()["hits"]}


class AutodartsLastSessionSensor(AutodartsLocalEntity, SensorEntity):
    """The 3-dart average of the last finished session, one value per session.

    Its history shows the progress from session to session; the attributes
    hold the details and the recent sessions for cards.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "points"
    _attr_suggested_display_precision = 1
    # The session list is for cards; the recorder keeps one value per session.
    _unrecorded_attributes = frozenset({"sessions"})

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "training_last_session")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float | None:
        history = self.coordinator.training.history
        return history[0]["average"] if history else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        history = [dict(summary) for summary in self.coordinator.training.history]
        last = history[0] if history else {}
        return {
            **{key: value for key, value in last.items() if key != "average"},
            "sessions": history,
        }


class AutodartsPracticeSensor(AutodartsLocalEntity, SensorEntity):
    """Remaining score and checkout of X01, the target of Cricket or a training game."""

    # Darts, scores, results and the match summary are for cards; the
    # recorder keeps the state.
    _unrecorded_attributes = frozenset(
        {"visit", "legs", "scores", "results", "summary"}
    )

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, f"practice_{key}")
        self._key = key

    @property
    def available(self) -> bool:
        return True

    def _game(self) -> dict[str, Any]:
        """The snapshot the coordinator published; computed only before the first."""
        game = (self.coordinator.data or {}).get("practice")
        return game if isinstance(game, dict) else self.coordinator.practice.snapshot()

    @property
    def native_value(self) -> int | str | None:
        game = self._game()
        if self._key == "target":
            return (game["drill"] or {}).get("target") or game.get("target")
        return game.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        game = self._game()
        if self._key == "target":
            drill = game["drill"] or {}
            return {key: value for key, value in drill.items() if key != "target"}
        if self._key != "remaining":
            return None
        return {
            key: value
            for key, value in game.items()
            if key not in ("remaining", "drill")
        }


# Practice statistic -> unit; legs only grow, like a meter.
PRACTICE_STATISTICS = {
    "first_9_average": "points",
    "checkout_rate": PERCENTAGE,
    "doubles_rate": PERCENTAGE,
    "legs_played": None,
}


class AutodartsPracticeStatistic(AutodartsLocalEntity, SensorEntity):
    """First-9 average, checkout and doubles rate of the last ten legs."""

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, f"practice_{key}")
        self._key = key
        self._attr_native_unit_of_measurement = PRACTICE_STATISTICS[key]
        if key == "legs_played":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float | int | None:
        value: float | int | None = self.coordinator.practice.statistics()[self._key]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._key == "legs_played":
            return None
        statistics = self.coordinator.practice.statistics()
        return {
            "legs_counted": statistics["legs_counted"],
            "darts_at_double": statistics["darts_at_double"],
        }


class AutodartsRecordsEntity(AutodartsLocalEntity, SensorEntity):
    """Personal bests, darts per day and the streak; kept across restarts."""

    @property
    def available(self) -> bool:
        return True

    def _records(self) -> dict[str, Any]:
        return self.coordinator.records.snapshot(dt_util.now().date())


class AutodartsPersonalBest(AutodartsRecordsEntity):
    """When the last personal best fell, with every best value as attributes."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "personal_best")

    @property
    def native_value(self) -> datetime | None:
        latest = self._records()["latest"]
        return dt_util.parse_datetime(latest["date"]) if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        records = self._records()
        latest = records["latest"] or {}
        return {
            **{key: latest.get(key) for key in ("record", "value", "previous", "name")},
            **records["bests"],
        }


class AutodartsDailyDarts(AutodartsRecordsEntity):
    """Darts detected today, towards the daily goal."""

    _attr_native_unit_of_measurement = "darts"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "darts_today")

    @property
    def native_value(self) -> int:
        value: int = self._records()["darts_today"]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        records = self._records()
        return {key: records[key] for key in ("goal", "goal_reached", "progress")}


class AutodartsStreak(AutodartsRecordsEntity):
    """Days in a row with at least one dart; today does not break it yet."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "training_streak")

    @property
    def native_value(self) -> int:
        value: int = self._records()["streak"]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        records = self._records()
        return {
            key: records[key] for key in ("best_streak", "trained_today", "last_day")
        }


class AutodartsPlayerProfiles(AutodartsLocalEntity, SensorEntity):
    """Named players with their statistics and personal bests."""

    _unrecorded_attributes = frozenset({"players"})
    _attr_native_unit_of_measurement = "players"

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "player_profiles")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return len(self.coordinator.practice.profiles.players)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"players": self.coordinator.practice.profiles.snapshot()["players"]}


class AutodartsDoubles(AutodartsLocalEntity, SensorEntity):
    """The double hit best, with the hit rate of every double."""

    _unrecorded_attributes = frozenset({"doubles"})

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "favourite_double")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str | None:
        value: str | None = self.coordinator.practice.doubles.snapshot()["favourite"]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self.coordinator.practice.doubles.snapshot()
        return {key: snapshot[key] for key in ("attempts", "hits", "rate", "doubles")}


class AutodartsLastMatch(AutodartsLocalEntity, SensorEntity):
    """When the last match of several players ended, with the recent matches."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _unrecorded_attributes = frozenset({"matches", "head_to_head"})

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "last_match")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> datetime | None:
        matches = self.coordinator.practice.profiles.matches
        return dt_util.parse_datetime(matches[0]["ended"]) if matches else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self.coordinator.practice.profiles.snapshot()
        last = snapshot["matches"][0] if snapshot["matches"] else {}
        winner = last.get("winner")
        players = last.get("players", [])
        return {
            "game": last.get("game"),
            "winner": players[winner - 1].get("name")
            if isinstance(winner, int) and 0 < winner <= len(players)
            else None,
            "matches": snapshot["matches"],
            "head_to_head": snapshot["head_to_head"],
        }


class AutodartsCorrectionRate(AutodartsLocalEntity, SensorEntity):
    """Share of the last hundred darts that the board corrected."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "correction_rate")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.quality.rate

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        quality = self.coordinator.quality.snapshot()
        return {"darts": quality["darts"], "corrected": quality["corrected"]}


class AutodartsOnlineBridgeSensor(AutodartsLocalEntity, RestoreEntity, SensorEntity):
    """When the last moment of an online match arrived, to check the bridge."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AutodartsLocalCoordinator, bridge: OnlineBridge
    ) -> None:
        super().__init__(coordinator, ONLINE_SENSOR_KEY)
        self._bridge = bridge

    @property
    def available(self) -> bool:
        # Online matches do not need the board.
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if last := await self.async_get_last_state():
            self._bridge.restore(
                dt_util.parse_datetime(last.state),
                last.attributes.get("trigger"),
                last.attributes.get("event_type"),
            )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._bridge.signal, self.async_write_ha_state
            )
        )

    @property
    def native_value(self) -> datetime | None:
        return self._bridge.last_event

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "trigger": self._bridge.last_trigger,
            "event_type": self._bridge.last_event_type,
        }


class AutodartsWeeklyReport(AutodartsLocalEntity, SensorEntity):
    """Darts of the running report week, with the week so far and the last report."""

    _attr_native_unit_of_measurement = "darts"
    # A new week starts from zero, like a meter that is reset.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _unrecorded_attributes = frozenset({"personal_bests", "last_week"})

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "weekly_report")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.reports.report.counts["darts"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self.coordinator.reports.snapshot()
        return {key: value for key, value in snapshot.items() if key != "darts"}
