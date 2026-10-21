"""The time of day at which the weekly report ends the week."""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsStoredEntity
from .games_coordinator import AutodartsGamesCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([AutodartsReportTime(entry.runtime_data.local)])


class AutodartsReportTime(AutodartsStoredEntity, TimeEntity):
    """Local time of the weekly report, to the minute; midnight by default."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsGamesCoordinator) -> None:
        super().__init__(coordinator, "weekly_report_time")

    @property
    def native_value(self) -> time:
        return self.coordinator.reports.report.time

    async def async_set_value(self, value: time) -> None:
        reports = self.coordinator.reports
        await reports.async_set_schedule(reports.report.weekday, value)
