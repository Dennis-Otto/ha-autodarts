"""The pause that ends a session, the daily goal and the practice match format.

Also the start scores of the players and the rounds of Count-Up.
"""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import AutodartsLocalEntity
from .local_coordinator import AutodartsLocalCoordinator
from .party import MAX_ROUNDS
from .practice import MAX_LEGS, MAX_PLAYERS, MAX_SETS, MAX_START, valid_start
from .records import DAILY_GOAL_MAX
from .runtime import AutodartsConfigEntry
from .training import IDLE_MINUTES_MAX

PARALLEL_UPDATES = 0

# Practice setting -> largest value. Every setting starts a new match.
PRACTICE_NUMBERS = {
    "practice_players": MAX_PLAYERS,
    "practice_legs": MAX_LEGS,
    "practice_sets": MAX_SETS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities(
            [
                AutodartsIdleTimeout(coordinator),
                AutodartsDailyGoal(coordinator),
                *(
                    AutodartsPracticeNumber(coordinator, key)
                    for key in PRACTICE_NUMBERS
                ),
                *(
                    AutodartsStartScore(coordinator, index)
                    for index in range(MAX_PLAYERS)
                ),
                AutodartsCountUpRounds(coordinator),
            ]
        )


class AutodartsIdleTimeout(AutodartsLocalEntity, NumberEntity):
    """Minutes without darts before a session ends; 0 keeps it running."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 0
    _attr_native_max_value = IDLE_MINUTES_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "training_idle_timeout")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.training.idle_minutes

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_idle_minutes(int(value))


class AutodartsDailyGoal(AutodartsLocalEntity, NumberEntity):
    """Darts to throw every day; 0 sets no goal."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "darts"
    _attr_native_min_value = 0
    _attr_native_max_value = DAILY_GOAL_MAX
    _attr_native_step = 10
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "training_daily_goal")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.records.goal

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_daily_goal(int(value))


class AutodartsPracticeNumber(AutodartsLocalEntity, NumberEntity):
    """Players of a practice match, legs per set and sets to win."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AutodartsLocalCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_native_max_value = PRACTICE_NUMBERS[key]

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        practice = self.coordinator.practice
        if self._key == "practice_players":
            return len(practice.players)
        return (
            practice.legs_to_win
            if self._key == "practice_legs"
            else practice.sets_to_win
        )

    async def async_set_native_value(self, value: float) -> None:
        if self._key == "practice_players":
            await self.coordinator.async_set_players(int(value))
        elif self._key == "practice_legs":
            await self.coordinator.async_set_match_format(legs=int(value))
        else:
            await self.coordinator.async_set_match_format(sets=int(value))


class AutodartsStartScore(AutodartsLocalEntity, NumberEntity):
    """A player's own X01 start score for a handicap; 0 plays the game's."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_START
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AutodartsLocalCoordinator, index: int) -> None:
        super().__init__(coordinator, f"practice_start_{index + 1}")
        self._attr_translation_key = "practice_start"
        self._attr_translation_placeholders = {"number": str(index + 1)}
        self._index = index

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.practice.starts[self._index]

    async def async_set_native_value(self, value: float) -> None:
        start = int(value)
        if not valid_start(start):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_start_score"
            )
        await self.coordinator.async_set_start_score(self._index, start)


class AutodartsCountUpRounds(AutodartsLocalEntity, NumberEntity):
    """Rounds of Count-Up; a change starts a game of Count-Up anew."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = MAX_ROUNDS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "practice_count_up_rounds")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.practice.count_up_rounds

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_party_rounds(count_up_rounds=int(value))
