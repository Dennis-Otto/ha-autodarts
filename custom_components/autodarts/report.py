"""The weekly training report and the stores it shares with the training journal.

The report counts every detected dart of the week, in a session or not, like
the darts of the day. At the report time it announces the week and starts the
next one. Report and journal are saved in stores of their own: the report
changes with every dart, the journal only when a session or a match ends.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .journal import TrainingJournal

if TYPE_CHECKING:
    from .local_coordinator import AutodartsLocalCoordinator
    from .practice import PracticeGame

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
# A pause longer than this between two darts is no training time.
TRAINING_GAP = timedelta(minutes=5)
# Personal bests of the week in the report, the latest first.
REPORT_BESTS = 10
# Counters of the week; each week starts them from zero.
COUNTS = (
    "darts",
    "visits",
    "visit_darts",
    "points",
    "scores_180",
    "sessions",
    "training_seconds",
    "legs",
    "matches",
    "darts_at_double",
    "checkouts",
    "daily_goals",
)
# Numbers of a report as the event and the sensor carry them.
REPORT_NUMBERS = (
    "darts",
    "visits",
    "sessions",
    "training_minutes",
    "scores_180",
    "darts_at_double",
    "checkouts",
    "legs",
    "matches",
    "streak",
    "daily_goals",
)
REPORT_VALUES = ("average", "average_change", "highest_visit", "checkout_rate")
SAVE_DELAY = 10


def _count(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def _value(value: object) -> float | int | None:
    """A finite number, or None."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return value if math.isfinite(value) else None


def _moment(value: object) -> datetime | None:
    """A stored timestamp with a time zone, in UTC."""
    parsed = dt_util.parse_datetime(value) if isinstance(value, str) else None
    return dt_util.as_utc(parsed) if parsed and parsed.tzinfo else None


def _utc(value: str) -> datetime:
    """A timestamp checked before."""
    return dt_util.as_utc(datetime.fromisoformat(value))


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


def _at(day: date, at: time) -> datetime:
    """The report time on a day in the local time zone, in UTC.

    Home Assistant's time zone decides, so a week that changes to or from
    daylight saving time lasts an hour more or less.
    """
    local = datetime.combine(day, at, tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(local)


def report_week(moment: datetime, weekday: int, at: time) -> tuple[datetime, datetime]:
    """Start and end of the report week around the moment, both in UTC."""
    local = dt_util.as_local(moment)
    day = local.date() - timedelta(days=(local.weekday() - weekday) % 7)
    if _at(day, at) > dt_util.as_utc(moment):
        day -= timedelta(days=7)
    return _at(day, at), _at(day + timedelta(days=7), at)


def _average(points: int, darts: int) -> float | None:
    return round(points * 3 / darts, 2) if darts else None


def _restored_best(saved: object) -> dict[str, Any] | None:
    if not isinstance(saved, dict) or not isinstance(saved.get("record"), str):
        return None
    name = saved.get("name")
    return {
        "record": saved["record"],
        "value": _value(saved.get("value")),
        "name": name if isinstance(name, str) and name else None,
    }


def _restored_report(saved: object) -> dict[str, Any] | None:
    """A report of an earlier week, with every value checked."""
    if not isinstance(saved, dict):
        return None
    start, end = _moment(saved.get("week_start")), _moment(saved.get("week_end"))
    if start is None or end is None:
        return None
    bests = saved.get("personal_bests")
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        **{key: _count(saved.get(key)) for key in REPORT_NUMBERS},
        **{key: _value(saved.get(key)) for key in REPORT_VALUES},
        "personal_bests": [
            best
            for best in map(_restored_best, bests if isinstance(bests, list) else [])
            if best
        ][:REPORT_BESTS],
    }


class WeeklyReport:
    """The running week's darts, visits and results, and the last week's report."""

    def __init__(self) -> None:
        self.weekday = 0
        self.time = time(0, 0)
        self.started: datetime | None = None
        self.ends: datetime | None = None
        self.counts = dict.fromkeys(COUNTS, 0)
        self.highest_visit = 0
        self.bests: list[dict[str, Any]] = []
        self.last_dart: datetime | None = None
        # When the newest X01 leg counted ended; "" before the first one.
        self.last_leg: str | None = None
        self.last: dict[str, Any] | None = None

    # -- schedule --------------------------------------------------------------

    def begin(self, now: datetime) -> None:
        """Start counting the week that contains this moment."""
        self.started, self.ends = report_week(now, self.weekday, self.time)
        self.counts = dict.fromkeys(COUNTS, 0)
        self.highest_visit = 0
        self.bests = []

    def set_schedule(self, weekday: int, at: time, now: datetime) -> None:
        """A new report time ends the running week at its next occurrence."""
        self.weekday, self.time = weekday, at.replace(second=0, microsecond=0)
        if self.started is None:
            self.begin(now)
        else:
            self.ends = report_week(now, self.weekday, self.time)[1]

    def rollover(self, now: datetime, streak: int) -> dict[str, Any] | None:
        """The report of the week that ended, if it did, and the next week."""
        if self.ends is None or dt_util.as_utc(now) < self.ends:
            return None
        report = self.snapshot(streak)
        self.last = report
        # Weeks while Home Assistant was stopped had no darts and are skipped.
        self.begin(now)
        return report

    # -- counting --------------------------------------------------------------

    def observe(self, kind: str, attributes: dict[str, Any], now: datetime) -> None:
        count = self.counts
        value = attributes.get
        if kind == "dart_detected":
            count["darts"] += 1
            if self.last_dart and timedelta(0) < now - self.last_dart <= TRAINING_GAP:
                count["training_seconds"] += round(
                    (now - self.last_dart).total_seconds()
                )
            self.last_dart = dt_util.as_utc(now)
        elif kind == "visit_completed":
            darts, score = _count(value("darts")), _count(value("score"))
            if darts:
                count["visits"] += 1
                count["visit_darts"] += darts
                count["points"] += score
            if 0 < darts <= 3:
                # Merged visits after a missed takeout are not one visit.
                self.highest_visit = max(self.highest_visit, score)
                count["scores_180"] += int(darts == 3 and score == 180)
        elif kind == "session_ended":
            count["sessions"] += int(_count(value("darts")) > 0)
        elif kind == "leg_won":
            count["legs"] += 1
        elif kind == "match_won":
            count["matches"] += 1
        elif kind == "daily_goal_reached":
            count["daily_goals"] += 1
        elif kind == "personal_best" and (best := _restored_best(attributes)):
            self.bests.insert(0, best)
            del self.bests[REPORT_BESTS:]

    def book_legs(
        self, legs: list[dict[str, Any]], stats: list[dict[str, int]]
    ) -> bool:
        """Darts at a double and checkouts of the X01 legs booked since last time.

        The practice game keeps its last legs and a statistics record of each
        X01 leg among them, both newest first. The first look only learns the
        newest leg. Returns whether anything changed.
        """
        ended = [
            leg["ended"]
            for leg in legs
            if type(leg.get("game")) is int and _moment(leg.get("ended"))
        ]
        seen, self.last_leg = self.last_leg, ended[0] if ended else ""
        if seen is None:
            return True
        last = _moment(seen)
        for index, moment in enumerate(ended[: len(stats)]):
            if last and _utc(moment) <= last:
                break
            self.counts["darts_at_double"] += _count(stats[index].get("at_double"))
            self.counts["checkouts"] += _count(stats[index].get("checkouts"))
        return seen != self.last_leg

    # -- state -----------------------------------------------------------------

    def snapshot(self, streak: int) -> dict[str, Any]:
        """The week so far, compared with the last week's report."""
        count = self.counts
        average = _average(count["points"], count["visit_darts"])
        previous = (self.last or {}).get("average")
        at_double = count["darts_at_double"]
        return {
            "week_start": _iso(self.started),
            "week_end": _iso(self.ends),
            "darts": count["darts"],
            "visits": count["visits"],
            "sessions": count["sessions"],
            "training_minutes": round(count["training_seconds"] / 60),
            "average": average,
            "average_change": round(average - previous, 2)
            if average is not None and previous is not None
            else None,
            "highest_visit": self.highest_visit or None,
            "scores_180": count["scores_180"],
            "checkout_rate": round(count["checkouts"] * 100 / at_double, 1)
            if at_double
            else None,
            "darts_at_double": at_double,
            "checkouts": count["checkouts"],
            "legs": count["legs"],
            "matches": count["matches"],
            "streak": streak,
            "daily_goals": count["daily_goals"],
            "personal_bests": [dict(best) for best in self.bests],
        }

    def stored(self) -> dict[str, Any]:
        return {
            "weekday": self.weekday,
            "time": self.time.isoformat(timespec="minutes"),
            "started": _iso(self.started),
            "ends": _iso(self.ends),
            "counts": dict(self.counts),
            "highest_visit": self.highest_visit,
            "bests": [dict(best) for best in self.bests],
            "last_dart": _iso(self.last_dart),
            "last_leg": self.last_leg,
            "last": dict(self.last) if self.last else None,
        }

    def restore(self, saved: object) -> None:
        if not isinstance(saved, dict):
            return
        weekday = saved.get("weekday")
        if type(weekday) is int and 0 <= weekday < len(WEEKDAYS):
            self.weekday = weekday
        try:
            self.time = time.fromisoformat(str(saved.get("time"))).replace(
                second=0, microsecond=0, tzinfo=None
            )
        except ValueError:
            self.time = time(0, 0)
        self.started, self.ends = (
            _moment(saved.get("started")),
            _moment(saved.get("ends")),
        )
        if self.started is None or self.ends is None or self.ends <= self.started:
            self.started = self.ends = None
        counts = saved.get("counts")
        self.counts = {
            key: _count(counts.get(key) if isinstance(counts, dict) else None)
            for key in COUNTS
        }
        self.highest_visit = _count(saved.get("highest_visit"))
        bests = saved.get("bests")
        self.bests = [
            best
            for best in map(_restored_best, bests if isinstance(bests, list) else [])
            if best
        ][:REPORT_BESTS]
        self.last_dart = _moment(saved.get("last_dart"))
        last_leg = saved.get("last_leg")
        valid = isinstance(last_leg, str) and (not last_leg or _moment(last_leg))
        self.last_leg = last_leg if valid and isinstance(last_leg, str) else None
        self.last = _restored_report(saved.get("last"))


def _store(hass: HomeAssistant, entry_id: str, name: str) -> Store[dict[str, Any]]:
    return Store(hass, 1, f"{DOMAIN}.{entry_id}.{name}", private=True)


def match_game(practice: PracticeGame) -> int | str | None:
    """The practice match of several players being played, if any."""
    return practice.kind if len(practice.players) > 1 else None


class BoardReports:
    """The weekly report and the training journal of one board.

    Fed with the board events of the coordinator; announces the report with
    the event weekly_report at the report time.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        coordinator: AutodartsLocalCoordinator,
    ) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self.report = WeeklyReport()
        self.journal = TrainingJournal()
        # Private like the training: both keep the names of players.
        self._report_store = _store(hass, entry_id, "report")
        self._journal_store = _store(hass, entry_id, "journal")
        self._report_dirty = False
        self._journal_dirty = False
        self._unsub: CALLBACK_TYPE | None = None

    async def async_load(self) -> None:
        """Restore both stores; a new journal takes over the stored history."""
        self.report.restore(await self._report_store.async_load())
        self.journal.restore(await self._journal_store.async_load())
        if self.report.started is None:
            self.report.begin(dt_util.utcnow())
            self._save_report()
        self.observe([], dt_util.now())

    @callback
    def async_start(self) -> None:
        """Announce a report that became due while Home Assistant was stopped."""
        self._schedule()

    async def async_shutdown(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._report_dirty:
            await self._report_store.async_save(self.report.stored())
            self._report_dirty = False
        if self._journal_dirty:
            await self._journal_store.async_save(self.journal.stored())
            self._journal_dirty = False

    @staticmethod
    async def async_remove(hass: HomeAssistant, entry_id: str) -> None:
        """Delete the stores together with the integration."""
        for name in ("report", "journal"):
            await _store(hass, entry_id, name).async_remove()

    # -- counting --------------------------------------------------------------

    def observe(self, events: list[tuple[str, dict[str, Any]]], now: datetime) -> None:
        """Count the events and take over finished sessions, matches and legs."""
        coordinator = self._coordinator
        practice = coordinator.practice
        game = match_game(practice)
        for kind, attributes in events:
            if kind == "dart_detected":
                self.journal.observe_dart(now, game)
            self.report.observe(kind, attributes, now)
        booked = self.report.book_legs(practice.legs, practice.leg_stats)
        if events or booked:
            self._save_report()
        if self.journal.sync(
            coordinator.training.history, practice.profiles.matches, now
        ):
            self._journal_dirty = True
            self._journal_store.async_delay_save(self.journal.stored, SAVE_DELAY)

    def _save_report(self) -> None:
        self._report_dirty = True
        self._report_store.async_delay_save(self.report.stored, SAVE_DELAY)

    def snapshot(self) -> dict[str, Any]:
        """The running week for the sensor, with the last week's report."""
        streak: int = self._coordinator.records.snapshot(dt_util.now().date())["streak"]
        return {**self.report.snapshot(streak), "last_week": self.report.last}

    # -- schedule --------------------------------------------------------------

    async def async_set_schedule(self, weekday: int, at: time) -> None:
        self.report.set_schedule(weekday, at, dt_util.utcnow())
        await self._report_store.async_save(self.report.stored())
        self._report_dirty = False
        self._schedule()
        self._coordinator.async_update_listeners()

    @callback
    def _schedule(self) -> None:
        if self._unsub:
            self._unsub()
        due = self.report.ends or dt_util.utcnow()
        self._unsub = async_track_point_in_utc_time(
            self.hass, self._async_report, max(due, dt_util.utcnow())
        )

    async def _async_report(self, _now: datetime) -> None:
        now = dt_util.now()
        streak: int = self._coordinator.records.snapshot(now.date())["streak"]
        report = self.report.rollover(now, streak)
        if report is not None:
            await self._report_store.async_save(self.report.stored())
            self._report_dirty = False
            coordinator = self._coordinator
            # The sensor shows the new week before automations read the report.
            coordinator.async_update_listeners()
            self.hass.loop.call_soon(
                async_dispatcher_send,
                self.hass,
                coordinator.event_signal,
                "weekly_report",
                {**report, "source": "schedule"},
            )
        self._schedule()
