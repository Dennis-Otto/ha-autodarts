"""A Granboard over Home Assistant's Bluetooth: its darts on a dartboard without Autodarts.

Experimental until a real board was tested. A Granboard is a soft-tip board
with Bluetooth LE. A hit sends a short ASCII frame on a notify characteristic
of the board's service: the line and the pin of the switch under the bed, such
as ``3.4@`` for the treble 20, and ``BTN@`` for the button beside the board.
GranboardLink connects through Home Assistant's Bluetooth, so an ESPHome
Bluetooth proxy anywhere in the house reaches the board too, enters every dart
in the games of the dartboard as the action ``throw_dart`` does, and passes to
the next player at the button, as ``next_player`` does. A board that goes away,
asleep, switched off or out of reach, connects again when Home Assistant sees
it once more, and otherwise on a backoff.

The frames are the board's switch matrix as the MIT-licensed Granboard apps of
sobassy (gran-app) and bastiennoel93 (granboard-app) read it; the tests replay
them, and docs/granboard.md tells a tester how to check every bed.
"""

from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import async_call_later

from .manual import parse_bed

if TYPE_CHECKING:
    from .games_coordinator import AutodartsGamesCoordinator

_LOGGER = logging.getLogger(__name__)

# The service of the board, which it announces and whose notifications carry the hits.
SERVICE_UUID = "442f1570-8a00-9a28-cbe1-e1d4212d53eb"
# The frames of each number: its inner single, treble, outer single and double.
_MATRIX: dict[int, tuple[str, str, str, str]] = {
    1: ("2.3", "2.4", "2.5", "2.6"),
    2: ("9.1", "9.0", "9.2", "8.2"),
    3: ("7.1", "7.0", "7.2", "8.4"),
    4: ("0.1", "0.3", "0.5", "0.6"),
    5: ("5.1", "5.2", "5.4", "4.6"),
    6: ("1.0", "1.1", "1.3", "4.4"),
    7: ("11.1", "11.2", "11.4", "8.6"),
    8: ("6.2", "6.4", "6.5", "6.6"),
    9: ("9.3", "9.4", "9.5", "9.6"),
    10: ("2.0", "2.1", "2.2", "4.3"),
    11: ("7.3", "7.4", "7.5", "7.6"),
    12: ("5.0", "5.3", "5.5", "5.6"),
    13: ("0.0", "0.2", "0.4", "4.5"),
    14: ("10.3", "10.4", "10.5", "10.6"),
    15: ("3.0", "3.1", "3.2", "4.2"),
    16: ("11.0", "11.3", "11.5", "11.6"),
    17: ("10.1", "10.0", "10.2", "8.3"),
    18: ("1.2", "1.4", "1.5", "1.6"),
    19: ("6.1", "6.0", "6.3", "8.5"),
    20: ("3.3", "3.4", "3.5", "3.6"),
}
# The button beside the board, which ends the visit.
BUTTON = "BTN"
# Every frame ends with this byte.
END = b"@"
# More bytes than any frame has without its end are noise, and are dropped.
MAX_FRAME = 16
# Frames right after a connection are dropped: a board may report its last hit
# again as notifications start, which would count a dart twice.
WARM_UP_SECONDS = 2.0
# The waits between two attempts to connect: doubling up to five minutes. A
# board that Home Assistant sees again is connected at once.
RETRY_FIRST_SECONDS = 2.0
RETRY_MAX_SECONDS = 300.0
# How many unknown frames the diagnostics keep, for a tester to report.
UNKNOWN_KEPT = 10
# What the diagnostics count: attempts, frames and what came of them.
COUNTED = (
    "connections",
    "disconnects",
    "failures",
    "frames",
    "darts",
    "buttons",
    "refused",
    "warm_up",
)


@dataclass(frozen=True)
class Hit:
    """What a frame reports: a bed as the actions name it (S20, T20, 25, BULL),
    or the button; for a single, whether it is the inner one."""

    bed: str
    inner: bool | None = None


FRAMES: dict[str, Hit] = {
    **{
        frame: Hit(f"{prefix}{number}", inner)
        for number, frames in _MATRIX.items()
        for frame, (prefix, inner) in zip(
            frames,
            (("S", True), ("T", None), ("S", False), ("D", None)),
            strict=True,
        )
    },
    "8.0": Hit("25"),
    "4.0": Hit("BULL"),
    BUTTON: Hit(BUTTON),
}


def board_id(address: str) -> str:
    """The board ID of the dartboard of a Granboard: its address without
    separators, so that the board is set up only once."""
    return "granboard_" + re.sub(r"[^0-9a-z]", "", address.lower())


def is_granboard(info: bluetooth.BluetoothServiceInfoBleak) -> bool:
    """Whether a device that Home Assistant's Bluetooth sees is a Granboard."""
    return SERVICE_UUID in (uuid.lower() for uuid in info.service_uuids)


@callback
def async_discovered(hass: HomeAssistant) -> list[bluetooth.BluetoothServiceInfoBleak]:
    """The Granboards that Home Assistant's Bluetooth sees now; none without it."""
    if "bluetooth" not in hass.config.components:
        return []
    return [
        info
        for info in bluetooth.async_discovered_service_info(hass, connectable=True)
        if is_granboard(info)
    ]


class FrameReader:
    """The frames in the notifications of the board, whole even when a
    notification splits a frame or carries several."""

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, data: bytes | bytearray) -> list[str]:
        """The frames that the data completes, without their end byte."""
        *frames, rest = (self._buffer + bytes(data)).split(END)
        self._buffer = rest if len(rest) <= MAX_FRAME else b""
        texts = (
            frame.decode("ascii", "replace").strip("\x00\r\n ") for frame in frames
        )
        return [text for text in texts if text]


class GranboardLink:
    """The connection to one Granboard, whose darts the dartboard receives."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        board: AutodartsGamesCoordinator,
        address: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self.board = board
        self.address = address
        self._reader = FrameReader()
        self._client: BleakClientWithServiceCache | None = None
        self._hits: deque[Hit] = deque()
        self._unknown: deque[str] = deque(maxlen=UNKNOWN_KEPT)
        self._seen_unsub: CALLBACK_TYPE | None = None
        self._retry_unsub: CALLBACK_TYPE | None = None
        self._warm_unsub: CALLBACK_TYPE | None = None
        self._retries = 0
        self._connecting = False
        self._draining = False
        self._stopped = True
        # Whether Home Assistant did not see the board at the last attempt.
        self._away = False
        self._counts = dict.fromkeys(COUNTED, 0)
        self._last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    def diagnostics(self) -> dict[str, Any]:
        """The state and the counts of the connection, without the address."""
        return {
            "connected": self.connected,
            "away": self._away,
            **self._counts,
            "last_error": self._last_error,
            # Frames that decode to no bed, for a tester to report.
            "unknown_frames": list(self._unknown),
        }

    # -- connecting --------------------------------------------------------------

    @callback
    def async_start(self) -> None:
        """Connect now, and again whenever Home Assistant sees the board."""
        if "bluetooth" not in self.hass.config.components:
            _LOGGER.warning(
                "Home Assistant's Bluetooth is not set up, so the Granboard of %s "
                "cannot connect; set up Bluetooth, then reload the integration",
                self.board.device_name,
            )
            return
        self._stopped = False
        self._seen_unsub = bluetooth.async_register_callback(
            self.hass,
            self._async_seen,
            bluetooth.BluetoothCallbackMatcher(address=self.address, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
        self._try_now()

    async def async_stop(self) -> None:
        """Stop connecting, and let the board go."""
        self._stopped = True
        self._hits.clear()
        for unsub in (self._seen_unsub, self._retry_unsub, self._warm_unsub):
            if unsub:
                unsub()
        self._seen_unsub = self._retry_unsub = self._warm_unsub = None
        client, self._client = self._client, None
        if client is not None:
            await client.disconnect()

    @callback
    def _async_seen(
        self,
        _info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        """The board is back: connect at once, rather than after the wait."""
        if self._away and not (self.connected or self._connecting):
            self._try_now()

    @callback
    def _try_now(self) -> None:
        if self._retry_unsub:
            self._retry_unsub()
            self._retry_unsub = None
        self._connecting = True
        self._entry.async_create_background_task(
            self.hass, self._async_connect(), f"autodarts granboard {self.address}"
        )

    @callback
    def _retry_later(self) -> None:
        """Try again after a wait that doubles with every failed attempt."""
        if self._stopped:
            return
        delay = min(RETRY_FIRST_SECONDS * 2**self._retries, RETRY_MAX_SECONDS)
        self._retries += 1

        @callback
        def retry(_now: Any) -> None:
            self._retry_unsub = None
            self._try_now()

        self._retry_unsub = async_call_later(self.hass, delay, retry)

    async def _async_connect(self) -> None:
        try:
            await self._async_open()
        finally:
            self._connecting = False

    async def _async_open(self) -> None:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        self._away = device is None
        if device is None:
            _LOGGER.debug("The Granboard of %s is out of reach", self.board.device_name)
            self._retry_later()
            return
        client: BleakClientWithServiceCache | None = None
        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self.board.device_name,
                disconnected_callback=self._disconnected,
                ble_device_callback=lambda: (
                    bluetooth.async_ble_device_from_address(
                        self.hass, self.address, connectable=True
                    )
                    or device
                ),
            )
            await client.start_notify(_notify_characteristic(client), self._notified)
        except (BleakError, TimeoutError) as err:
            self._counts["failures"] += 1
            self._last_error = type(err).__name__
            _LOGGER.debug(
                "The Granboard of %s did not connect: %s", self.board.device_name, err
            )
            if client is not None:
                await client.disconnect()
            self._retry_later()
            return
        if self._stopped:
            await client.disconnect()
            return
        self._client = client
        self._retries = 0
        self._counts["connections"] += 1
        self._warm_unsub = async_call_later(self.hass, WARM_UP_SECONDS, self._warmed)
        _LOGGER.info("The Granboard of %s is connected", self.board.device_name)
        self.board.async_update_listeners()

    @callback
    def _warmed(self, _now: Any) -> None:
        self._warm_unsub = None

    @callback
    def _disconnected(self, client: Any) -> None:
        if client is not self._client:
            # A client given up already, or one that never connected.
            return
        self._client = None
        self._counts["disconnects"] += 1
        if self._warm_unsub:
            self._warm_unsub()
            self._warm_unsub = None
        _LOGGER.info("The Granboard of %s disconnected", self.board.device_name)
        self.board.async_update_listeners()
        self._retry_later()

    # -- darts -----------------------------------------------------------------

    @callback
    def _notified(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        for frame in self._reader.feed(data):
            self._counts["frames"] += 1
            hit = FRAMES.get(frame)
            _LOGGER.debug(
                "Granboard frame %r: %s", frame, hit.bed if hit else "unknown"
            )
            if self._warm_unsub:
                self._counts["warm_up"] += 1
            elif hit is None:
                self._unknown.append(frame)
            else:
                self._hits.append(hit)
        if self._hits and not self._draining:
            self._draining = True
            self._entry.async_create_background_task(
                self.hass,
                self._async_drain(),
                f"autodarts granboard darts {self.address}",
            )

    async def _async_drain(self) -> None:
        """Enter the hits one after another, in the order the board sent them."""
        try:
            while self._hits:
                await self._async_enter(self._hits.popleft())
        finally:
            self._draining = False

    async def _async_enter(self, hit: Hit) -> None:
        try:
            if hit.bed == BUTTON:
                self._counts["buttons"] += 1
                await self.board.async_next_player()
                return
            self._counts["darts"] += 1
            bed = parse_bed(hit.bed)
            assert bed is not None  # Every bed of FRAMES is one of the actions'.
            await self.board.async_throw_dart(bed)
        except ServiceValidationError as err:
            # As the keypad would be refused: the bot's turn, a full visit, or
            # the button without a dart while the game knows no pass.
            self._counts["refused"] += 1
            _LOGGER.debug(
                "The Granboard's %s does not count: %s", hit.bed, err.translation_key
            )


def _notify_characteristic(
    client: BleakClientWithServiceCache,
) -> BleakGATTCharacteristic:
    """The characteristic of the board's service whose notifications carry the hits."""
    service = client.services.get_service(SERVICE_UUID)
    for characteristic in service.characteristics if service else ():
        if "notify" in characteristic.properties:
            return characteristic
    raise BleakError(f"No notify characteristic in the service {SERVICE_UUID}")
