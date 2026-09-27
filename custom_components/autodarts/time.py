"""The time of day at which the weekly report ends the week."""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import AutodartsLocalEntity
from .local_coordinator import AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities([AutodartsReportTime(coordinator)])


class AutodartsReportTime(AutodartsLocalEntity, TimeEntity):
    """Local time of the weekly report, to the minute; midnight by default."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "weekly_report_time")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> time:
        return self.coordinator.reports.report.time

    async def async_set_value(self, value: time) -> None:
        reports = self.coordinator.reports
        await reports.async_set_schedule(reports.report.weekday, value)
