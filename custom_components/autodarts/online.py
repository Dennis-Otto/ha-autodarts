"""Moments of Autodarts online matches, sent by the browser extension Tools for Autodarts.

The integration sees the darts on the local board, but not the game of an
online match on play.autodarts.io: busts, game shots and the darts of the
opponents happen in the browser. The WLED feature of Tools for Autodarts calls a
URL of your choice for each of its triggers. The bridge offers such a URL as a
secret Home Assistant webhook and turns the calls into board events of the
source "online". It is off until it is switched on in the options.
"""

from __future__ import annotations

import json
import logging
import re
from collections import deque
from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime
from http import HTTPStatus
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote

from aiohttp.web import Request, Response
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .const import CONF_BOARD_ID, DOMAIN

if TYPE_CHECKING:
    from .local_coordinator import AutodartsLocalCoordinator

_LOGGER = logging.getLogger(__name__)

# Options of a config entry.
CONF_ONLINE_BRIDGE = "online_bridge"
CONF_ONLINE_REMOTE = "online_bridge_remote"
CONF_WEBHOOK_ID = "online_bridge_webhook_id"
# Asks the options flow for a new address; never stored.
CONF_NEW_ADDRESS = "online_bridge_new_address"

SENSOR_KEY = "online_bridge_last_event"

ONLINE_EVENT_TYPES = [
    "online_game_on",
    "online_visit",
    "online_dart",
    "online_busted",
    "online_game_shot",
    "online_match_shot",
    "online_bull_off",
    "online_tournament_ready",
    "online_match_left",
]

# Tools for Autodarts sends a few calls per visit; more than this in a second,
# or in a minute, is no game, so a leaked address cannot flood the recorder or
# keep the automations busy.
RATE_LIMITS = ((1.0, 20), (60.0, 120))
MAX_QUERY = 1024
MAX_BODY = 1024
MAX_TRIGGER = 64
MAX_NAME = 50

# Triggers that name a moment without details, as Tools for Autodarts names them.
MOMENTS = {
    "gameon": "online_game_on",
    "bot_throw": "online_game_on",
    "busted": "online_busted",
    "bulloff": "online_bull_off",
    "tournament_ready": "online_tournament_ready",
    "idle": "online_match_left",
}
# Sent instead of any other trigger for darts on a board that is not yours.
OTHER_BOARD = "other"
# The triggers the options offer as ready-made effects to import.
EFFECT_TRIGGERS = (
    "gameon",
    "180",
    "busted",
    "gameshot",
    "matchshot",
    "bulloff",
    "tournament_ready",
    "idle",
    OTHER_BOARD,
)

_NUMBER = r"1\d|20|[1-9]"
# A dart as Tools for Autodarts names it: s20, d16, t19, s25 or 25, bull, and
# m17 or miss for a dart beside the numbers.
_DART = rf"[sdt](?:{_NUMBER})|s25|25|bull|m(?:{_NUMBER})|miss"
_POINTS = r"180|1[0-7]\d|[1-9]?\d"
# A query string turns the "+" of "gameshot+d10" into a space.
_SHOT = re.compile(rf"(gameshot|matchshot)(?:[+ ]({_DART})|_(.+))?")
_VISIT = re.compile(_POINTS)
_RANGE = re.compile(rf"(?:range_)?({_POINTS})[-_]({_POINTS})")
_COMBINED = re.compile(rf"({_DART})_({_DART})_({_DART})")
_SINGLE = re.compile(rf"{_DART}|outside")


def dart(name: str) -> tuple[str, int]:
    """Bed and score of a dart, with the bed named as in the training: T20, 25, BULL."""
    if name == "bull":
        return "BULL", 50
    if name in ("25", "s25"):
        return "25", 25
    if name[0] in "sdt":
        number = int(name[1:])
        return f"{name[0].upper()}{number}", number * ("sdt".index(name[0]) + 1)
    # m1 to m20, miss and outside: beside the numbers or off the board.
    return "MISS", 0


def _moment(trigger: str, attributes: dict[str, Any]) -> str | None:
    """The event type of a trigger, adding its details; "" for another board."""
    if trigger in MOMENTS:
        return MOMENTS[trigger]
    if trigger == OTHER_BOARD:
        return ""
    if match := _SHOT.fullmatch(trigger):
        shot, bed, name = match.groups()
        if bed:
            attributes["segment"] = dart(bed)[0]
        if name:
            attributes["name"] = name
        return "online_game_shot" if shot == "gameshot" else "online_match_shot"
    if _VISIT.fullmatch(trigger):
        attributes["score"] = int(trigger)
        return "online_visit"
    if (match := _RANGE.fullmatch(trigger)) and int(match[1]) <= int(match[2]):
        attributes |= {"score_min": int(match[1]), "score_max": int(match[2])}
        return "online_visit"
    if match := _COMBINED.fullmatch(trigger):
        darts = [dart(name) for name in match.groups()]
        attributes |= {
            "score": sum(score for _, score in darts),
            "darts": len(darts),
            "segments": [bed for bed, _ in darts],
        }
        return "online_visit"
    if _SINGLE.fullmatch(trigger):
        attributes["segment"], attributes["score"] = dart(trigger)
        return "online_dart"
    return None


def parse(trigger: str, player: str | None = None) -> tuple[str, dict[str, Any]] | None:
    """The board event of a trigger of Tools for Autodarts, None if unknown.

    The event type is empty for a moment on another board, which is ignored.
    """
    trigger = " ".join(trigger.split()).lower()
    attributes: dict[str, Any] = {"trigger": trigger}
    if player:
        attributes["name"] = player
    kind = _moment(trigger, attributes)
    return None if kind is None else (kind, attributes)


class InvalidCall(Exception):
    """A call the bridge refuses, with the answer for the caller."""

    def __init__(self, status: HTTPStatus, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


def _known(values: Mapping[str, Any]) -> dict[str, str]:
    """The fields the bridge reads; everything else is ignored."""
    fields = {}
    for key in ("event", "player"):
        value = values.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, str | int):
            raise InvalidCall(HTTPStatus.BAD_REQUEST, f"invalid {key}")
        fields[key] = str(value)
    return fields


async def _body(request: Request) -> bytes:
    """The body, refused beyond MAX_BODY bytes without reading more."""
    # A request of the WebSocket API creates a new reader on each access.
    stream = request.content
    body = b""
    while chunk := await stream.read(MAX_BODY + 1 - len(body)):
        body += chunk
        if len(body) > MAX_BODY:
            raise InvalidCall(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body too large")
    return body


def _body_fields(body: bytes) -> dict[str, str]:
    """Fields of a POST body: JSON, form fields or the bare trigger.

    Tools for Autodarts sends the JSON of an effect of type JSON API as text/plain,
    so the content type tells nothing.
    """
    try:
        text = body.decode().strip()
    except UnicodeDecodeError as err:
        raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid text") from err
    if not text:
        return {}
    if text[0] in '{["':
        try:
            value = json.loads(text)
        except ValueError as err:
            raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid JSON") from err
        if isinstance(value, str):
            return {"event": value}
        if isinstance(value, dict):
            return _known(value)
        raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid JSON")
    if "=" in text:
        try:
            return _known(dict(parse_qsl(text, max_num_fields=10)))
        except ValueError as err:
            raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid fields") from err
    return {"event": text}


async def read_call(request: Request) -> tuple[str, str | None]:
    """Trigger and player of a call, from the query string and a POST body."""
    if len(request.query_string) > MAX_QUERY:
        raise InvalidCall(HTTPStatus.REQUEST_URI_TOO_LONG, "address too long")
    fields = _known(request.query)
    if request.method == "POST":
        fields |= _body_fields(await _body(request))
    trigger = fields.get("event", "").strip()
    if not trigger:
        raise InvalidCall(HTTPStatus.BAD_REQUEST, "event missing")
    if len(trigger) > MAX_TRIGGER or not trigger.isprintable():
        raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid event")
    player = fields.get("player", "").strip() or None
    if player is not None and (len(player) > MAX_NAME or not player.isprintable()):
        raise InvalidCall(HTTPStatus.BAD_REQUEST, "invalid player")
    return trigger, player


def bridge_url(hass: HomeAssistant, webhook_id: str, remote: bool) -> str:
    """The address for Tools for Autodarts: https from outside when that is allowed.

    Without remote calls, the address of the home network: a call through Home
    Assistant Cloud or another external address would be refused.
    """
    path = webhook.async_generate_path(webhook_id)
    attempts: list[dict[str, Any]] = [{"allow_external": False, "allow_cloud": False}]
    if remote:
        attempts.insert(0, {"allow_internal": False, "require_ssl": True})
    for arguments in attempts:
        with suppress(NoURLAvailableError):
            return f"{get_url(hass, **arguments)}{path}"
    return f"http://homeassistant.local:8123{path}"


def effects_csv(url: str) -> str:
    """Effects for the CSV import of Tools for Autodarts, one per trigger."""
    return "\n".join(
        f"Home Assistant: {trigger};URL;{url}?event={quote(trigger, safe='')};{trigger}"
        for trigger in EFFECT_TRIGGERS
    )


class OnlineBridge:
    """The webhook of one board; it exists while the bridge is switched on."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: AutodartsLocalCoordinator,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._webhook_id: str = entry.options[CONF_WEBHOOK_ID]
        self.remote = bool(entry.options.get(CONF_ONLINE_REMOTE, False))
        self.signal = f"{DOMAIN}_{entry.entry_id}_online"
        # When the calls of the last minute came.
        self._calls: deque[float] = deque()
        self._unknown_logged = False
        self.last_event: datetime | None = None
        self.last_trigger: str | None = None
        self.last_event_type: str | None = None
        self.counts = {"events": 0, "ignored": 0, "invalid": 0, "limited": 0}

    @callback
    def async_register(self) -> None:
        webhook.async_register(
            self.hass,
            DOMAIN,
            "Autodarts online matches",
            self._webhook_id,
            self._async_handle,
            local_only=not self.remote,
            allowed_methods=("GET", "POST"),
        )
        self._entry.async_on_unload(self._async_unregister)

    @callback
    def _async_unregister(self) -> None:
        webhook.async_unregister(self.hass, self._webhook_id)

    @callback
    def restore(
        self, last_event: datetime | None, trigger: Any, event_type: Any
    ) -> None:
        """The last moment before a restart, as the sensor remembers it."""
        if self.last_event is None and last_event is not None:
            self.last_event = last_event
            self.last_trigger = trigger if isinstance(trigger, str) else None
            self.last_event_type = event_type if isinstance(event_type, str) else None

    def _limited(self, now: float) -> bool:
        """Whether a call exceeds a limit; refused calls use up none of them."""
        longest = max(window for window, _ in RATE_LIMITS)
        while self._calls and now - self._calls[0] >= longest:
            self._calls.popleft()
        for window, limit in RATE_LIMITS:
            if sum(now - call < window for call in self._calls) >= limit:
                return True
        self._calls.append(now)
        return False

    async def _async_handle(
        self, hass: HomeAssistant, webhook_id: str, request: Request
    ) -> Response:
        """Answer every call; Tools for Autodarts ignores the answers."""
        if self._limited(monotonic()):
            self.counts["limited"] += 1
            return Response(status=HTTPStatus.TOO_MANY_REQUESTS, text="too many calls")
        try:
            trigger, player = await read_call(request)
        except InvalidCall as err:
            self.counts["invalid"] += 1
            return Response(status=err.status, text=err.reason)
        moment = parse(trigger, player)
        if moment is None:
            self.counts["invalid"] += 1
            self._log_unknown(trigger)
            return Response(status=HTTPStatus.BAD_REQUEST, text="unknown event")
        kind, attributes = moment
        if not kind:
            self.counts["ignored"] += 1
            return Response(text="ignored")
        self._fire(kind, attributes)
        return Response(text="ok")

    def _log_unknown(self, trigger: str) -> None:
        """Explain an effect set up with a trigger the bridge does not know, once."""
        if self._unknown_logged:
            _LOGGER.debug("Online bridge ignored the unknown event %r", trigger)
            return
        self._unknown_logged = True
        _LOGGER.warning(
            "The online bridge ignored the unknown event %r; the documentation lists "
            "the triggers of Tools for Autodarts it understands",
            trigger,
        )

    @callback
    def _fire(self, kind: str, attributes: dict[str, Any]) -> None:
        self.counts["events"] += 1
        self.last_event = dt_util.utcnow()
        self.last_trigger = attributes["trigger"]
        self.last_event_type = kind
        # The sensor shows the moment before automations react to the event.
        async_dispatcher_send(self.hass, self.signal)
        async_dispatcher_send(
            self.hass,
            self._coordinator.event_signal,
            kind,
            {**attributes, "source": "online"},
        )

    def diagnostics(self) -> dict[str, Any]:
        """Counts and the last event type; never the address or player names."""
        return {
            "enabled": True,
            "remote": self.remote,
            **self.counts,
            "last_event": (
                self.last_event.isoformat(timespec="seconds")
                if self.last_event
                else None
            ),
            "last_event_type": self.last_event_type,
        }


async def async_setup_bridge(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AutodartsLocalCoordinator | None,
) -> OnlineBridge | None:
    """Open the webhook when the bridge is on; the board events deliver its moments."""
    if not (
        coordinator
        and entry.options.get(CONF_ONLINE_BRIDGE)
        and entry.options.get(CONF_WEBHOOK_ID)
        # Home Assistant loads webhooks with its default configuration.
        and await async_setup_component(hass, webhook.DOMAIN, {})
    ):
        # The sensor of a bridge that was switched off disappears with it.
        registry = er.async_get(hass)
        if entity_id := registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.data[CONF_BOARD_ID]}_{SENSOR_KEY}"
        ):
            registry.async_remove(entity_id)
        return None
    bridge = OnlineBridge(hass, entry, coordinator)
    bridge.async_register()
    return bridge
