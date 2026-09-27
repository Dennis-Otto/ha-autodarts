"""The training calendar: finished training sessions and practice matches."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import AutodartsLocalEntity
from .journal import JournalEvent
from .local_coordinator import AutodartsLocalCoordinator
from .runtime import AutodartsConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AutodartsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if coordinator := entry.runtime_data.local:
        async_add_entities([AutodartsTrainingCalendar(coordinator)])


def _calendar_event(event: JournalEvent) -> CalendarEvent:
    """In local time, like the events of Home Assistant's own calendars."""
    return CalendarEvent(
        start=dt_util.as_local(event.start),
        end=dt_util.as_local(event.end),
        summary=event.summary,
        description=event.description,
        uid=event.uid,
    )


class AutodartsTrainingCalendar(AutodartsLocalEntity, CalendarEntity):
    """Read-only: every entry is something that happened on the board.

    The state attributes show the entry that ended last, so the state is off
    unless a calendar trigger asks for the events of a period.
    """

    def __init__(self, coordinator: AutodartsLocalCoordinator) -> None:
        super().__init__(coordinator, "training_calendar")

    @property
    def available(self) -> bool:
        return True

    @property
    def event(self) -> CalendarEvent | None:
        latest = self.coordinator.reports.journal.latest()
        return _calendar_event(latest) if latest else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        journal = self.coordinator.reports.journal
        return [
            _calendar_event(event) for event in journal.events(start_date, end_date)
        ]
