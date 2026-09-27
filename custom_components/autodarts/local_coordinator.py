"""Combine local push notifications, HTTP recovery, training and practice games."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable, Coroutine
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .camera_health import CameraHealth
from .const import (
    BOARD_MANAGER_2_URL,
    CONF_API_GENERATION,
    CONF_HOST,
    CONF_NO_SYSTEM_API,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    LIFECYCLE_STATUSES,
)
from .discovery import cloud_addresses
from .errors import AutodartsApiError
from .local_api import (
    AutodartsEndpointMissing,
    AutodartsLocalAuthError,
    AutodartsLocalClient,
    AutodartsProtocolError,
    board_generation,
    camera_state_summary,
    number,
    stats_summary,
)
from .online import ONLINE_EVENT_TYPES
from .practice import PracticeGame
from .quality import RECALIBRATE_RATE, RECOVERED_RATE, DetectionQuality
from .records import PersonalRecords
from .report import BoardReports
from .storage import TrainingStore
from .training import TrainingSession, segments

_LOGGER = logging.getLogger(__name__)
# Poll quickly without realtime events; with them, polling only reconciles.
POLL_INTERVAL = timedelta(seconds=2)
STREAM_POLL_INTERVAL = timedelta(seconds=30)
# Board Manager 2 announces no camera changes, so it is read more often.
STREAM_POLL_INTERVAL_V2 = timedelta(seconds=10)
# A board that stays away, for example while its PC is off, is asked less often.
OFFLINE_POLL_INTERVAL = timedelta(seconds=15)
OFFLINE_AFTER_FAILURES = 10
# Failed polls in a row that keep the last values, like a short Wi-Fi hiccup.
TOLERATED_FAILURES = 2
# Board Manager 1 reports its settings and version in separate reads.
METADATA_SECONDS = 30
# The board PC changes only with system or Board Manager updates.
HOST_REFRESH_SECONDS = 3600
# Answers without /api/system in a row before a board counts as Board Manager 1.
SYSTEM_MISSES = 3
# Unknown answers in a row to a required read before a repair notice appears.
PROTOCOL_FAILURES = 3
REQUIRED_PATHS = ("/api/state", "/api/config", "/api/system")
# Realtime reconnects wait 1, 2, 4 ... 60 seconds, each shortened by up to a fifth.
RECONNECT_MIN = 1
RECONNECT_MAX = 60
RECONNECT_JITTER = 0.2
# A realtime connection that lasted this long starts the back-off over.
RECONNECT_RESET_SECONDS = 30
# Failed realtime attempts in a row before a warning, about half a minute.
STREAM_WARN_ATTEMPTS = 5
# A board away this long is looked for at the addresses the Autodarts cloud reports.
REDISCOVER_SECONDS = 300
REDISCOVER_INTERVAL = 1800
MOTION_FLAGS = (
    "isWaiting",
    "isStable",
    "isDart",
    "isHand",
    "isTakeoutPartial",
    "isTakeoutFull",
)
# High-rate values that change no entity by themselves, except the camera alarm.
TELEMETRY = ("stats", "camera_stats")
EVENT_TYPES = [
    "dart_detected",
    "dart_corrected",
    "takeout_started",
    "takeout_finished",
    "status_changed",
    "visit_thrown",
    "visit_completed",
    "session_started",
    "session_ended",
    "bust",
    "leg_won",
    "match_won",
    "turn_changed",
    "drill_finished",
    "checkout_attempt",
    "personal_best",
    "daily_goal_reached",
    "bull_off_won",
    "weekly_report",
    # Moments of online matches, from the browser extension Tools for Autodarts.
    *ONLINE_EVENT_TYPES,
]
# Dart and visit events name the practice game being played, so that callers
# can leave the game to the practice caller.
PLAY_EVENTS = ("dart_detected", "dart_corrected", "visit_thrown", "visit_completed")
# Repair issues of an entry, named <issue>_<entry_id>.
ISSUES = (
    "wrong_board",
    "board_manager_1",
    "calibration",
    "board_moved",
    "board_access_denied",
    "unsupported_response",
)
# Jitter only spreads reconnects; it needs no cryptographic randomness.
_RANDOM = random.Random()  # noqa: S311


def _throw_positions(state: dict[str, Any]) -> list[tuple[float, float] | None] | None:
    """Board positions of the darts on the board; None for a state training rejects."""
    if segments(state) is None:
        return None
    positions: list[tuple[float, float] | None] = []
    for dart in state.get("throws", []):
        coords = dart.get("coords")
        x, y = (
            number(coords.get(axis)) if isinstance(coords, dict) else None
            for axis in ("x", "y")
        )
        positions.append(None if x is None or y is None else (float(x), float(y)))
    return positions


def _lifecycle(state: dict[str, Any]) -> tuple[object, str]:
    """Whether the detection runs and where it is in starting or stopping."""
    status = str(state.get("status", "")).lower()
    return state.get("running"), status if status in LIFECYCLE_STATUSES else "running"


def _error_name(error: BaseException) -> str:
    """The kind of a failure, for diagnostics; messages may contain addresses."""
    return type(error.__cause__ or error).__name__


@dataclass
class ConnectionStats:
    """Connection history for diagnostics; no addresses, messages or payloads."""

    failures: int = 0
    last_error: str | None = None
    last_success: datetime | None = None
    offline_since: float | None = None
    poll_seconds: float | None = None
    connects: int = 0
    stream_failures: int = 0
    reconnect_delay: float = RECONNECT_MIN
    last_close: str | None = None


class AutodartsLocalCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keep controls local and reconcile push notifications with periodic reads."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AutodartsLocalClient,
        board_id: str,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_local",
            config_entry=entry,
            update_interval=POLL_INTERVAL,
            # A poll that changes nothing leaves the entities alone; the data
            # carries a revision that changes with the training and games.
            always_update=False,
            # Show the result of consecutive user actions without a long cooldown.
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=1, immediate=True
            ),
        )
        self._entry: ConfigEntry = entry
        self.client = client
        self.board_id = board_id
        self.device_name = "Autodarts Board"
        self.event_signal = f"{DOMAIN}_{entry.entry_id}_event"
        self.training = TrainingSession()
        self.practice = PracticeGame()
        self.quality = DetectionQuality()
        self.records = PersonalRecords()
        self.reports = BoardReports(hass, entry.entry_id, self)
        self._midnight_unsub: CALLBACK_TYPE | None = None
        self._store = TrainingStore(hass, entry.entry_id)
        self._training_dirty = False
        self._revision = 0
        self._idle_unsub: CALLBACK_TYPE | None = None
        self._health = CameraHealth()
        self._settings: dict[str, Any] = {}
        self._version: str | None = None
        # Board Manager 1 (classic app) or 2 (headless board); None until known.
        self.generation: int | None = entry.data.get(CONF_API_GENERATION)
        self.setup_generation: int | None = None
        # The Board Manager version that answered without /api/system, if any.
        self._no_system_api: str | None = entry.data.get(CONF_NO_SYSTEM_API)
        self._system_misses = 0
        self._metadata_updated = 0.0
        self._host: dict[str, Any] | None = None
        self._host_updated = 0.0
        self._identity_valid = True
        self._access_denied = False
        self._protocol_failures: dict[str, int] = {}
        self._protocol_logged: set[str] = set()
        self._game_error_logged = False
        self._action_lock = asyncio.Lock()
        # One read at a time: an older answer must never replace a newer one.
        self._poll_lock = asyncio.Lock()
        self.connection = ConnectionStats()
        self._rediscovered_at: float | None = None
        self._stream_task: asyncio.Task[None] | None = None
        self.stream_connected = False
        # A valid notification arrived since the socket opened.
        self._stream_live = False
        self._stream_warned = False
        self._stream_error_logged = False
        self._reconnect_now = asyncio.Event()
        self._revisions: dict[str, int] = {}
        self._observed_state: dict[str, Any] | None = None
        self._observed_motion: dict[str, Any] | None = None
        self._taking_out = False
        self._positions: list[tuple[float, float] | None] = []

    async def _async_setup(self) -> None:
        saved = await self._store.async_load()
        self.training.restore(saved)
        self.practice.restore(
            saved.get("practice") if isinstance(saved, dict) else None
        )
        self.records.restore(saved.get("records") if isinstance(saved, dict) else None)
        if saved is None:
            self._save_training()
        await self.reports.async_load()

    def _stored(self) -> dict[str, Any]:
        """Training sessions, the practice game and personal bests, saved together."""
        return {
            **self.training.stored(),
            "practice": self.practice.stored(),
            "records": self.records.stored(),
        }

    def _save_training(self) -> None:
        self._training_dirty = True
        self._store.async_delay_save(self._stored, 5)

    @callback
    def async_start(self) -> None:
        # Entities exist now, so an overdue idle end is announced, too.
        self._schedule_idle_end()
        # Issues of earlier runs are not kept across restarts.
        self._report_generation()
        self.reports.async_start()
        if self._midnight_unsub is None:
            # Darts today and the streak change with the date, not with a dart.
            self._midnight_unsub = async_track_time_change(
                self.hass, self._async_new_day, hour=0, minute=0, second=1
            )
        if self._stream_task is None:
            self._stream_task = self._entry.async_create_background_task(
                self.hass, self._listen(), f"{DOMAIN} local events"
            )

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        if self._stream_task:
            self._stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stream_task
            self._stream_task = None
        if self._idle_unsub:
            self._idle_unsub()
            self._idle_unsub = None
        if self._midnight_unsub:
            self._midnight_unsub()
            self._midnight_unsub = None
        if self._training_dirty:
            await self._store.async_save(self._stored())
            self._training_dirty = False
        await self.reports.async_shutdown()

    # -- realtime events ---------------------------------------------------------

    async def _listen(self) -> None:
        """Follow the push notifications until async_shutdown cancels this task."""
        delay: float = RECONNECT_MIN
        while True:
            lasted = await self._follow_events()
            if lasted is not None and lasted >= RECONNECT_RESET_SECONDS:
                delay = RECONNECT_MIN
            self.connection.reconnect_delay = delay
            woken = await self._wait_before_reconnect(
                delay * (1 - RECONNECT_JITTER * _RANDOM.random())
            )
            # A board that answers polls again is reconnected at once.
            delay = RECONNECT_MIN if woken else min(delay * 2, RECONNECT_MAX)

    async def _follow_events(self) -> float | None:
        """One realtime connection; how long it lasted, None if it never opened."""
        self._reconnect_now.clear()
        connected_at: float | None = None
        try:
            async for kind, payload in self.client.events():
                if kind == "connected":
                    connected_at = time.monotonic()
                    self.connection.connects += 1
                    self.stream_connected = True
                    self.async_update_listeners()
                elif kind == "closed":
                    self.connection.last_close = (
                        f"closed by the board ({payload['code']})"
                    )
                else:
                    self.async_receive(kind, payload)
        except AutodartsApiError as err:
            self.connection.last_close = _error_name(err)
            _LOGGER.debug("Local event stream unavailable; HTTP polling remains active")
        except Exception:
            # Never let one bad message end realtime updates until a reload.
            self.connection.last_close = "unexpected error"
            if self._stream_error_logged:
                _LOGGER.debug(
                    "Unexpected error in the local event stream", exc_info=True
                )
            else:
                self._stream_error_logged = True
                _LOGGER.exception("Unexpected error in the local event stream")
        finally:
            live, self._stream_live = self._stream_live, False
            self.stream_connected = False
            self.update_interval = self._poll_interval()
            if connected_at is not None:
                self._suspend_tracking()
            if not self._shutdown_requested:
                self.async_update_listeners()
        lasted = None if connected_at is None else time.monotonic() - connected_at
        if connected_at is not None:
            # Resume fast polling right away instead of after the long interval.
            await self.async_request_refresh()
        if not live and (lasted is None or lasted < RECONNECT_RESET_SECONDS):
            self._stream_attempt_failed()
        return lasted

    async def _wait_before_reconnect(self, delay: float) -> bool:
        """Wait for the next attempt; True when a poll found the board back first."""
        try:
            async with asyncio.timeout(delay):
                await self._reconnect_now.wait()
        except TimeoutError:
            return False
        self._reconnect_now.clear()
        return True

    @callback
    def _stream_attempt_failed(self) -> None:
        """Warn once when realtime events stay away although the board answers."""
        self.connection.stream_failures += 1
        if (
            self.connection.stream_failures >= STREAM_WARN_ATTEMPTS
            and self.last_update_success
            and self.data
            and not self._stream_warned
        ):
            self._stream_warned = True
            _LOGGER.warning(
                "Board Manager answers, but its realtime events at %s/api/events are "
                "unavailable; values update by polling every 2 seconds instead",
                self.client.base_url,
            )

    @callback
    def _stream_active(self) -> None:
        """The first valid notification: polling can slow down to reconciling."""
        if self._stream_live or not self.stream_connected:
            return
        self._stream_live = True
        self.connection.stream_failures = 0
        self.update_interval = self._poll_interval()
        if self._stream_warned:
            self._stream_warned = False
            _LOGGER.info("Realtime events from the Board Manager are available again")

    def _poll_interval(self) -> timedelta:
        if self._stream_live:
            return (
                STREAM_POLL_INTERVAL_V2
                if self.board_manager_2
                else STREAM_POLL_INTERVAL
            )
        if self.connection.failures >= OFFLINE_AFTER_FAILURES:
            return OFFLINE_POLL_INTERVAL
        return POLL_INTERVAL

    def _suspend_tracking(self) -> None:
        """Changes may be missed; the next state tells how the visit went on."""
        self.training.suspend()
        self._observed_motion = None

    def _message(
        self, kind: str, payload: dict[str, Any]
    ) -> tuple[str, dict[str, Any]] | None:
        """The data field a notification updates, reduced to known values."""
        if kind == "state":
            return (
                ("local", payload) if isinstance(payload.get("running"), bool) else None
            )
        if kind == "motion_state":
            return "motion", self._motion(payload)
        if kind == "cam_state":
            return "camera_state", camera_state_summary(payload)
        if kind == "stats":
            return "stats", stats_summary(payload)
        if kind != "cam_stats":
            return None
        index, fps = payload.get("id"), number(payload.get("fps"))
        count = self._settings.get("camera_count", 0)
        if type(index) is not int or not 0 <= index < count or fps is None:
            return None
        current = (self.data or {}).get("camera_stats", {}).get("fps")
        frames = list(current) if isinstance(current, list) else []
        frames.extend([None] * max(0, count - len(frames)))
        frames[index] = fps
        return "camera_stats", {"fps": frames}

    @callback
    def async_receive(self, kind: str, payload: dict[str, Any]) -> None:
        """Merge a push message; high-rate telemetry only updates the camera alarm."""
        if (
            not isinstance(payload, dict)
            or not self._identity_valid
            or self._shutdown_requested
        ):
            return
        message = self._message(kind, payload)
        if message is None:
            return
        field, value = message
        self._stream_active()
        self._revisions[field] = self._revisions.get(field, 0) + 1
        data = dict(self.data or {})
        previous = data.get(field)
        data[field] = value
        if field in TELEMETRY:
            problems = self._health.update(data, time.monotonic())
            alarm = problems != data.get("camera_problems")
            data["camera_problems"] = problems
            self.data = data
            if alarm:
                self.async_update_listeners()
            return
        self._process(data, {field}, "websocket")
        self.data = data
        recovered = field == "local" and not self.last_update_success
        if recovered:
            _LOGGER.info("Local Board Manager is available again")
        if field == "local":
            self.last_update_success = True
        if previous != value or recovered:
            self.async_update_listeners()
        if (
            field == "local"
            and isinstance(previous, dict)
            and _lifecycle(previous) != _lifecycle(value)
        ):
            # Board Manager 2 announces no camera changes; read them right after a
            # start or stop instead of waiting for the next slow poll.
            self._entry.async_create_task(
                self.hass, self.async_request_refresh(), f"{DOMAIN} camera state"
            )

    # -- training, games and events ----------------------------------------------

    @staticmethod
    def _motion(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: payload[key]
            for key in MOTION_FLAGS
            if isinstance(payload.get(key), bool)
        }

    def _emit(self, kind: str, attributes: dict[str, Any], source: str) -> None:
        # Publish the corresponding sensor states before event consumers run.
        self.hass.loop.call_soon(
            async_dispatcher_send,
            self.hass,
            self.event_signal,
            kind,
            {**attributes, "source": source},
        )

    def _recorded(
        self, events: list[tuple[str, dict[str, Any]]]
    ) -> list[tuple[str, dict[str, Any]]]:
        """The events, each followed by the personal bests or daily goal it brings."""
        now = dt_util.now()
        result: list[tuple[str, dict[str, Any]]] = []
        for kind, attributes in events:
            result.append((kind, attributes))
            result.extend(self.records.observe(kind, attributes, now))
        self.reports.observe(result, now)
        return result

    @callback
    def _async_new_day(self, _now: datetime) -> None:
        self.async_update_listeners()

    def _start_takeout(self, source: str) -> None:
        if not self._taking_out:
            self._taking_out = True
            self._emit("takeout_started", {}, source)

    def _finish_takeout(self, source: str) -> None:
        if self._taking_out:
            self._taking_out = False
            self._emit("takeout_finished", {}, source)

    def _process(self, data: dict[str, Any], fields: set[str], source: str) -> None:
        state = data.get("local", {})
        if "local" in fields:
            self._guarded(lambda: self._track(data, state, source))
            if self._observed_state is not None:
                self._observe_status(self._observed_state, state, source)
            self._observed_state = state
        if "motion" in fields:
            self._observe_motion(data.get("motion", {}), state, source)
        data["camera_problems"] = self._health.update(data, time.monotonic())

    def _guarded(self, action: Callable[[], None]) -> None:
        """A fault in the games must never cost the connection to the board."""
        try:
            action()
        except Exception:
            if self._game_error_logged:
                _LOGGER.debug("Training or practice game failed again", exc_info=True)
            else:
                self._game_error_logged = True
                _LOGGER.exception(
                    "Training or practice game failed; the board stays connected"
                )

    def _track(self, data: dict[str, Any], state: dict[str, Any], source: str) -> None:
        """Training, practice game and records follow the darts on the board."""
        announced = False
        for kind, attributes in self._recorded(self.training.observe(state)):
            announced = True
            self.quality.record(kind, attributes)
            if kind in PLAY_EVENTS:
                attributes = {
                    **attributes,
                    "game": self.practice.kind,
                    "name": self.practice.thrower,
                }
            self._emit(kind, attributes, source)
            if kind == "visit_completed":
                for turn, details in self._recorded(self.practice.finish_visit()):
                    self._emit(turn, details, source)
        if (positions := _throw_positions(state)) is not None:
            self._positions = positions
        visit = self.training.visit()
        # The visit is the last darts on the board; positions of rejected states
        # never shift onto them.
        known = self._positions[-len(visit) :] if visit else []
        aligned: list[tuple[float, float] | None] = [None] * (len(visit) - len(known))
        aligned.extend(known)
        for kind, attributes in self._recorded(self.practice.track(visit, aligned)):
            announced = True
            self._emit(kind, attributes, source)
        self._publish_game(data, announced)

    def _publish_game(self, data: dict[str, Any], announced: bool) -> None:
        """Snapshots for the entities; a change is saved and raises the revision."""
        training, practice = self.training.snapshot(), self.practice.snapshot()
        # The first snapshots only show what was restored; async_start schedules
        # an overdue pause once the entities that announce its end exist.
        if announced or (
            "training" in data
            and (training != data["training"] or practice != data.get("practice"))
        ):
            self._revision += 1
            self._save_training()
            self._schedule_idle_end()
        data.update(
            training=training,
            practice=practice,
            quality=self.quality.snapshot(),
            revision=self._revision,
        )
        self._report_quality()

    def _observe_status(
        self, previous: dict[str, Any], state: dict[str, Any], source: str
    ) -> None:
        """Status changes and takeouts the board reports in its state."""
        status = state.get("status")
        if isinstance(status, str) and status != previous.get("status"):
            self._emit("status_changed", {"status": status}, source)
        marker = str(state.get("event") or status or "").lower()
        if (
            state.get("running") is not True
            or str(status).lower() in LIFECYCLE_STATUSES
        ):
            self._taking_out = False
        elif marker in ("takeout started", "takeout in progress"):
            self._start_takeout(source)
        elif marker == "takeout finished" or state.get("numThrows") == 0:
            self._finish_takeout(source)

    def _observe_motion(
        self, motion: dict[str, Any], state: dict[str, Any], source: str
    ) -> None:
        """A hand at the board starts a takeout; an empty board finishes it."""
        previous = self._observed_motion
        if (
            previous is not None
            and state.get("running") is True
            and str(state.get("status", "")).lower() not in LIFECYCLE_STATUSES
        ):
            started = any(
                motion.get(key) is True and previous.get(key) is not True
                for key in ("isHand", "isTakeoutPartial")
            )
            count = state.get("numThrows")
            if started and type(count) is int and count > 0:
                self._start_takeout(source)
            if (
                motion.get("isTakeoutFull") is True
                and previous.get("isTakeoutFull") is not True
            ):
                self._finish_takeout(source)
        self._observed_motion = motion

    # -- repair issues -----------------------------------------------------------

    def _issue_id(self, name: str) -> str:
        return f"{name}_{self._entry.entry_id}"

    @callback
    def _report_identity(self) -> None:
        """A repair issue explains why a board at the wrong address stays offline."""
        issue = self._issue_id("wrong_board")
        if self._identity_valid:
            ir.async_delete_issue(self.hass, DOMAIN, issue)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="wrong_board",
            translation_placeholders={"address": self.client.base_url},
        )

    @callback
    def _report_generation(self) -> None:
        """Autodarts retires the classic Board Manager; point to the new one."""
        issue = self._issue_id("board_manager_1")
        if self.generation != 1:
            ir.async_delete_issue(self.hass, DOMAIN, issue)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="board_manager_1",
            learn_more_url=BOARD_MANAGER_2_URL,
        )

    @callback
    def _report_access(self) -> None:
        """The board normally needs no login; something refuses Home Assistant."""
        issue = self._issue_id("board_access_denied")
        if not self._access_denied:
            ir.async_delete_issue(self.hass, DOMAIN, issue)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="board_access_denied",
            translation_placeholders={"address": self.client.base_url},
        )

    @callback
    def _protocol_result(self, path: str, error: BaseException | None) -> None:
        """Count unknown answers per read; warn once for each read."""
        if not isinstance(error, AutodartsProtocolError):
            if error is None:
                self._protocol_failures.pop(path, None)
            return
        self._protocol_failures[path] = self._protocol_failures.get(path, 0) + 1
        if path not in self._protocol_logged:
            self._protocol_logged.add(path)
            _LOGGER.warning(
                "Board Manager answered %s in an unknown format; this Board Manager "
                "version may not be supported yet",
                path,
            )

    @callback
    def _report_protocol(self) -> None:
        """Required reads that keep failing ask for an update of the integration."""
        issue = self._issue_id("unsupported_response")
        failing = sorted(
            path
            for path, count in self._protocol_failures.items()
            if path in REQUIRED_PATHS and count >= PROTOCOL_FAILURES
        )
        if not failing:
            ir.async_delete_issue(self.hass, DOMAIN, issue)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unsupported_response",
            translation_placeholders={"reads": ", ".join(failing)},
        )

    @property
    def board_manager_2(self) -> bool:
        """Entities and endpoints of the headless Board Manager 2 apply."""
        return (self.generation or 1) >= 2

    @callback
    def _set_generation(self, generation: int) -> None:
        """Remember the board's generation; a change rebuilds its entities."""
        self.generation = generation
        self._report_generation()
        entry = self._entry
        # Unchanged data leaves the entry as it is.
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_API_GENERATION: generation}
        )
        if self.setup_generation is not None and (
            (self.setup_generation >= 2) != self.board_manager_2
        ):
            _LOGGER.info(
                "Board Manager %s detected; reloading to update the entities",
                generation,
            )
            self.setup_generation = generation
            self.hass.config_entries.async_schedule_reload(entry.entry_id)

    @callback
    def _remember_no_system_api(self, version: str | None) -> None:
        """Keep across restarts which version lacks /api/system, or forget it."""
        self._no_system_api = version
        self._system_misses = 0
        data = {
            key: value
            for key, value in self._entry.data.items()
            if key != CONF_NO_SYSTEM_API
        }
        if version is not None:
            data[CONF_NO_SYSTEM_API] = version
        self.hass.config_entries.async_update_entry(self._entry, data=data)

    @callback
    def _check_generation(self) -> None:
        """The version tells the generation, unless /api/system is known missing."""
        generation = board_generation(self._version)
        missing = self._no_system_api
        if missing is not None and self._version and missing not in ("", self._version):
            # Another Board Manager version may bring /api/system: ask again.
            _LOGGER.info(
                "Board Manager %s found; checking again for /api/system", self._version
            )
            self._remember_no_system_api(None)
        elif missing is not None and generation and generation >= 2:
            generation = 1
        if generation and generation != self.generation:
            self._set_generation(generation)

    # -- polling -----------------------------------------------------------------

    async def _optional(self, operation: Coroutine[Any, Any, Any], path: str) -> Any:
        """Unsupported endpoints read as empty; a failed read returns None."""
        try:
            result = await operation
        except AutodartsEndpointMissing:
            self._protocol_result(path, None)
            return {}
        except AutodartsApiError as err:
            self._protocol_result(path, err)
            return None
        self._protocol_result(path, None)
        return result

    async def _read_system(self) -> dict[str, Any] | None:
        """Board Manager 2 reports everything in one read; None if unsupported."""
        try:
            reads = await self.client.get_system()
        except AutodartsEndpointMissing:
            return None
        except AutodartsApiError as err:
            self._protocol_result("/api/system", err)
            # A failed read keeps every value, including the metadata.
            return dict.fromkeys(
                (
                    "config",
                    "version",
                    "system",
                    "stats",
                    "camera_stats",
                    "motion",
                    "camera_state",
                )
            )
        self._protocol_result("/api/system", None)
        return reads

    async def _read_legacy(self) -> dict[str, Any]:
        stats, camera_stats, motion, camera_state = await asyncio.gather(
            self._optional(self.client.get_stats(), "/api/state/stats"),
            self._optional(self.client.get_camera_stats(), "/api/cams/stats"),
            self._optional(self.client.get_motion_state(), "/api/state/motion"),
            self._optional(self.client.get_camera_state(), "/api/cams/state"),
        )
        reads = {
            "stats": stats,
            "camera_stats": camera_stats,
            "motion": motion,
            "camera_state": camera_state,
            "config": None,
            "version": None,
        }
        if (
            not self._metadata_updated
            or time.monotonic() - self._metadata_updated >= METADATA_SECONDS
        ):
            reads["config"], reads["version"] = await asyncio.gather(
                self._optional(self.client.get_config(), "/api/config"),
                self._optional(self.client.get_version(), "/api/version"),
            )
            self._metadata_updated = time.monotonic()
        return reads

    async def _reads(self) -> dict[str, Any]:
        """Everything besides the state, in one read on Board Manager 2."""
        if self.generation is None:
            # An unknown board reveals its generation through its version first.
            version = await self._optional(self.client.get_version(), "/api/version")
            if generation := board_generation(version):
                self._version = version
                self._set_generation(generation)
        if self.board_manager_2:
            reads = await self._read_system()
            if reads is not None:
                self._system_misses = 0
                return reads
            self._system_misses += 1
            # A board that is still starting may miss the route for a moment.
            if self._system_misses >= SYSTEM_MISSES:
                _LOGGER.info(
                    "Board Manager %s answers without /api/system; using the "
                    "protocol of Board Manager 1",
                    self._version or "?",
                )
                self._remember_no_system_api(self._version or "")
                self._set_generation(1)
        return await self._read_legacy()

    async def _async_update_data(self) -> dict[str, Any]:
        async with self._poll_lock:
            started = time.monotonic()
            try:
                return await self._poll()
            finally:
                self.connection.poll_seconds = round(time.monotonic() - started, 3)
                self._report_protocol()
                self.update_interval = self._poll_interval()

    async def _poll(self) -> dict[str, Any]:
        revisions = dict(self._revisions)
        try:
            state = await self.client.get_state()
        except AutodartsApiError as err:
            self._protocol_result("/api/state", err)
            return self._poll_failed(err)
        self._protocol_result("/api/state", None)
        reads = await self._reads()
        config, version = reads["config"], reads["version"]
        if config:
            self._identity_valid = (
                config.get("board_id", self.board_id) == self.board_id
            )
        self._report_identity()
        if not self._identity_valid:
            # Notifications are ignored meanwhile, so darts may be missed.
            self._suspend_tracking()
            self._offline("wrong board")
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="wrong_board")
        self._poll_succeeded()
        if config is not None:
            # A failed read keeps the last settings instead of hiding controls.
            self._settings = config
        previous_version = self._version
        self._version = (version if isinstance(version, str) else None) or (
            self._version
        )
        if previous_version and self._version != previous_version:
            self._update_device_version()
        self._check_generation()
        if self.board_manager_2 and (
            self._host is None
            or self._version != previous_version
            or time.monotonic() - self._host_updated >= HOST_REFRESH_SECONDS
        ):
            # Boards without the endpoint answer {} and are asked again later.
            host = await self._optional(self.client.get_host(), "/api/host")
            if host is not None:
                self._host, self._host_updated = host, time.monotonic()
        data = dict(self.data or {})
        if reads.get("system") is not None:
            data["system"] = reads["system"]
        if self._host is not None:
            data["board_pc"] = self._host
        fields = set()
        motion = reads["motion"]
        for field, value in {
            "local": state,
            "stats": reads["stats"],
            "camera_stats": reads["camera_stats"],
            "motion": None if motion is None else self._motion(motion),
            "camera_state": reads["camera_state"],
        }.items():
            if value is None and field in data:
                continue  # A failed optional read keeps the last known value.
            # A completed HTTP read must not roll back a newer socket message.
            if self._revisions.get(field, 0) == revisions.get(field, 0):
                data[field] = value or {}
                fields.add(field)
        data.update(settings=self._settings, version=self._version)
        self._process(data, fields, "poll")
        return data

    @callback
    def _offline(self, error: str) -> None:
        """Count a failed poll; a lasting outage is looked into."""
        connection = self.connection
        connection.failures += 1
        connection.last_error = error
        if connection.offline_since is None:
            connection.offline_since = time.monotonic()
        self._rediscover()

    def _poll_failed(self, error: AutodartsApiError) -> dict[str, Any]:
        """Keep the last values through a short hiccup; then the board is offline."""
        self._offline(_error_name(error))
        if isinstance(error, AutodartsLocalAuthError):
            if not self._access_denied:
                _LOGGER.warning(
                    "Board Manager at %s refused access (HTTP 401 or 403); it "
                    "normally needs no login, so check proxies and firewalls between "
                    "Home Assistant and the board",
                    self.client.base_url,
                )
                self._access_denied = True
                self._report_access()
        if self.stream_connected and self.data:
            # Realtime events still arrive, so a missed poll is no outage.
            _LOGGER.debug("Board Manager missed a poll; realtime events continue")
            return dict(self.data)
        self._suspend_tracking()
        if self.data and self.connection.failures <= TOLERATED_FAILURES:
            _LOGGER.debug("Board Manager missed a poll; keeping the last values")
            return dict(self.data)
        self._health = CameraHealth()
        if isinstance(error, AutodartsLocalAuthError):
            key = "board_access_denied"
        elif isinstance(error, AutodartsProtocolError):
            key = "unsupported_response"
        else:
            key = "board_unavailable"
        raise UpdateFailed(translation_domain=DOMAIN, translation_key=key) from error

    @callback
    def _poll_succeeded(self) -> None:
        connection = self.connection
        if connection.failures and not self.stream_connected:
            # The board is back: reconnect realtime events now, not after a back-off.
            self._reconnect_now.set()
        connection.failures = 0
        connection.offline_since = None
        connection.last_success = dt_util.utcnow()
        if self._access_denied:
            self._access_denied = False
            self._report_access()
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id("board_moved"))

    @callback
    def _rediscover(self) -> None:
        """A board away for minutes may answer at an address the cloud reports."""
        now = time.monotonic()
        since = self.connection.offline_since
        if since is None or now - since < REDISCOVER_SECONDS:
            return
        if (
            self._rediscovered_at is not None
            and now - self._rediscovered_at < REDISCOVER_INTERVAL
        ):
            return
        cloud = getattr(getattr(self._entry, "runtime_data", None), "cloud", None)
        board = ((cloud.data if cloud else None) or {}).get("board") or {}
        current = (
            self._entry.data.get(CONF_HOST),
            self._entry.data.get(CONF_PORT, DEFAULT_PORT),
        )
        candidates = [
            address
            for address in cloud_addresses(board.get("ip"))
            if address != current
        ]
        if not candidates:
            return
        self._rediscovered_at = now
        self._entry.async_create_task(
            self.hass, self._async_rediscover(candidates), f"{DOMAIN} rediscovery"
        )

    async def _async_rediscover(self, candidates: list[tuple[str, int]]) -> None:
        """Offer a repair to switch to the first address that answers as this board."""
        session = async_get_clientsession(self.hass)
        for host, port in candidates:
            client = AutodartsLocalClient(host, port, session)
            try:
                identity = await client.identify()
            except AutodartsApiError:
                continue
            if identity["board_id"] != self.board_id:
                continue
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id("board_moved"),
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="board_moved",
                translation_placeholders={
                    "old": self.client.base_url,
                    "new": client.base_url,
                },
                data={"entry_id": self._entry.entry_id, "host": host, "port": port},
            )
            return

    def diagnostics(self) -> dict[str, Any]:
        """How the connection went, without addresses, messages or secrets."""
        connection = self.connection
        since = connection.offline_since
        return {
            "consecutive_failures": connection.failures,
            "last_error": connection.last_error,
            "last_success": connection.last_success.isoformat()
            if connection.last_success
            else None,
            "offline_seconds": None
            if since is None
            else round(time.monotonic() - since),
            "last_poll_seconds": connection.poll_seconds,
            "board_manager_version": self._version,
            "system_api_missing": self._no_system_api is not None,
            "system_api_misses": self._system_misses,
            "identity_valid": self._identity_valid,
            "access_denied": self._access_denied,
            "unknown_answers": sorted(self._protocol_failures),
            "realtime": {
                "connected": self.stream_connected,
                "receiving": self._stream_live,
                "connects": connection.connects,
                "failed_attempts": connection.stream_failures,
                "reconnect_delay_seconds": connection.reconnect_delay,
                "last_close": connection.last_close,
                "ignored_frames": self.client.ignored_frames,
            },
        }

    @callback
    def _update_device_version(self) -> None:
        """Show a Board Manager update on the device page without a reload."""
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier(
            (DOMAIN, self.board_id), self._entry.entry_id
        )
        if device and device.sw_version != self._version:
            registry.async_update_device(device.id, sw_version=self._version)

    # -- actions -----------------------------------------------------------------

    async def _async_training(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        """Save a session change at once, then announce it."""
        events = self._recorded(events)
        stored = self._stored()
        await self._store.async_save(stored)
        self._training_dirty = self._stored() != stored
        for kind, attributes in events:
            self._emit(kind, attributes, "training")
        self._revision += 1
        self.data = {
            **(self.data or {}),
            "training": self.training.snapshot(),
            "practice": self.practice.snapshot(),
            "revision": self._revision,
        }
        self._schedule_idle_end()
        self.async_update_listeners()

    async def async_start_session(self) -> None:
        started = self.training.start()
        await self._async_training([started] if started else [])

    async def async_end_session(self) -> None:
        ended = self.training.end("manual")
        await self._async_training([ended] if ended else [])

    async def async_new_session(self) -> None:
        await self._async_training(self.training.new_session())

    async def async_set_auto_start(self, enabled: bool) -> None:
        self.training.auto_start = enabled
        await self._async_training([])

    async def async_set_daily_goal(self, darts: int) -> None:
        self.records.set_goal(darts, dt_util.now().date())
        await self._async_training([])

    async def async_set_idle_minutes(self, minutes: int) -> None:
        self.training.idle_minutes = minutes
        await self._async_training([])

    async def async_play(self, game: int | str) -> None:
        """Start an X01 match or a training game, or stop playing with 0."""
        self.practice.play(game)
        await self._async_training([])

    async def async_new_leg(self) -> None:
        self.practice.new_leg()
        await self._async_training([])

    async def async_delete_player(self, name: str) -> bool:
        """Forget a player profile, and the name in the records and the player
        slots; False when there is no profile by that name."""
        deleted = self.practice.profiles.delete(name)
        if deleted:
            self.practice.forget(name)
            self.records.forget(name)
            await self._async_training([])
        return deleted

    async def async_link_player(self, name: str, person: str | None) -> bool:
        """Link a player to a person, or unlink with None; False when that fails."""
        profiles = self.practice.profiles
        changed = profiles.link(name, person) if person else profiles.unlink(name)
        if changed:
            await self._async_training([])
        return changed

    async def async_set_practice_option(self, option: str, enabled: bool) -> None:
        """Double out, routes and the bull-off rule apply at once; double in and
        the bull-off start anew."""
        setattr(self.practice, option, enabled)
        if option in ("double_in", "bull_off"):
            self.practice.new_match()
        await self._async_training([])

    async def async_new_match(self) -> None:
        self.practice.new_match()
        await self._async_training([])

    async def async_set_players(self, count: int) -> None:
        """A different number of players starts a new match."""
        self.practice.set_players(count)
        await self._async_training([])

    async def async_set_match_format(
        self, legs: int | None = None, sets: int | None = None
    ) -> None:
        self.practice.set_format(legs, sets)
        await self._async_training([])

    async def async_set_player_name(self, index: int, name: str) -> None:
        self.practice.set_name(index, name)
        await self._async_training([])

    async def async_start_game(
        self,
        game: int | str,
        names: list[str] | None = None,
        legs: int | None = None,
        sets: int | None = None,
        double_out: bool | None = None,
        double_in: bool | None = None,
        bull_off: bool | None = None,
        bull_off_distance: bool | None = None,
    ) -> None:
        """Set up a practice game in one step; unset values stay as they are."""
        practice = self.practice
        for option, value in (
            ("double_out", double_out),
            ("double_in", double_in),
            ("bull_off", bull_off),
            ("bull_off_distance", bull_off_distance),
        ):
            if value is not None:
                setattr(practice, option, value)
        if names:
            for index in range(len(practice.names)):
                practice.set_name(index, names[index] if index < len(names) else "")
            practice.set_players(len(names))
        practice.set_format(legs, sets)
        practice.play(game)
        await self._async_training([])

    @callback
    def _report_quality(self) -> None:
        """Suggest a calibration while many darts need corrections."""
        issue = self._issue_id("calibration")
        rate = self.quality.rate
        if self.quality.enough and rate is not None and rate >= RECALIBRATE_RATE:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue,
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="calibration_recommended",
                translation_placeholders={"rate": f"{rate:.0f}"},
                data={"entry_id": self._entry.entry_id},
            )
        elif rate is None or rate < RECOVERED_RATE:
            ir.async_delete_issue(self.hass, DOMAIN, issue)

    async def async_recalibrate(self) -> None:
        """Calibrate all cameras and count the corrections from zero."""
        await self.async_action(lambda: self.client.command("calibrate"))
        self.quality.reset()
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id("calibration"))
        # The correction rate starts over now, not with the next read.
        self.async_update_listeners()

    def _idle_due(self) -> datetime | None:
        """When a running session ends without darts, if the user wants that."""
        training = self.training
        last = dt_util.parse_datetime(training.last_activity or "")
        if not training.active or not training.idle_minutes or last is None:
            return None
        return last + timedelta(minutes=training.idle_minutes)

    @callback
    def _schedule_idle_end(self) -> None:
        if self._idle_unsub:
            self._idle_unsub()
            self._idle_unsub = None
        if (due := self._idle_due()) is not None:
            self._idle_unsub = async_track_point_in_utc_time(
                self.hass, self._async_end_idle, max(due, dt_util.utcnow())
            )

    async def _async_end_idle(self, _now: datetime) -> None:
        self._idle_unsub = None
        due = self._idle_due()
        if due is None or due > dt_util.utcnow():
            # A dart arrived in the meantime and rescheduled the end.
            self._schedule_idle_end()
            return
        # The session ended with its last dart, not when the pause ran out.
        ended = self.training.end("idle", at=self.training.last_activity)
        await self._async_training([ended] if ended else [])

    async def async_action(
        self, action: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        async with self._action_lock:
            try:
                await action()
            except AutodartsEndpointMissing as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="not_supported"
                ) from err
            except AutodartsLocalAuthError as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="board_access_denied"
                ) from err
            except AutodartsApiError as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="action_failed"
                ) from err
            self._metadata_updated = 0
            await self.async_request_refresh()
