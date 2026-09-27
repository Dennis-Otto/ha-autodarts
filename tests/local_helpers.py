"""Synthetic fixtures shaped like Board Manager 1.0.7 responses, and the helpers
that set a board up in Home Assistant."""

from copy import deepcopy

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import MockConfigEntry

BASE = "http://192.0.2.10:3180"
STATE = {
    "connected": True,
    "running": False,
    "status": "Stopped",
    "event": "Stopped",
    "numThrows": 0,
}
CONFIG = {
    "auth": {"board_id": "board-1", "api_key": "private-board-api-key"},
    "cam": {
        "cams": ["/dev/video0", "/dev/video2", "/dev/video4"],
        "width": 1280,
        "height": 1024,
        "fps": 30,
        "auto_calibrate_on_start": True,
        "auto_calibrate": True,
        "auto_distortion": False,
    },
    "motion": {"standby_minutes": 15, "sensitive_calibration_setting": 123},
}


# Shaped like Board Manager 2.0.0's /api/system, including its secrets.
SYSTEM = {
    "blocker": "none",
    "calibrated": True,
    "camState": {"isOpened": True, "isRunning": True},
    "camStats": [
        {"fps": 29.9, "id": 0, "resolution": {"height": 1024, "width": 1280}},
        {"fps": 30, "id": 1, "resolution": {"height": 1024, "width": 1280}},
        {"fps": 29.8, "id": 2, "resolution": {"height": 1024, "width": 1280}},
    ],
    "config": {
        **deepcopy(CONFIG),
        "host": {"port": "3180", "tls_key": "private-tls-key", "tls_cert": ""},
    },
    "link": "connected",
    "motion": {
        "isStable": True,
        "isHand": False,
        "isTakeoutPartial": False,
        "isTakeoutFull": False,
        "camStates": [],
    },
    "state": {"connected": True, "event": "Stopped", "numThrows": 0, "running": False},
    "stats": {"cpuPercent": 12.5, "fps": 12.5, "memoryBytes": 314363904},
    "takenOver": False,
    "updateAvailable": "2.0.2",
    "version": "2.0.0",
}


# Shaped like Board Manager 2.0.0's /api/host, with made-up names and addresses.
HOST = {
    "appVersion": None,
    "clientVersion": "2.0.0",
    "desktopVersion": None,
    "os": "linux",
    "platform": "debian",
    "platformFamily": "debian",
    "platformVersion": "13",
    "kernelArch": "x86_64",
    "kernelVersion": "6.12.107+deb13-amd64",
    "model": "",
    "openCVVersion": "5.0.0",
    "visionVersion": "2.0.0",
    "hasAutodartsVisionCam": False,
    "hostname": "dartboard-pc",
    "ip": "198.51.100.7",
    "cpu": {
        "cores": 4,
        "mhz": 3400.4,
        "model": "Intel(R) Core(TM) i3-9100T CPU @ 3.10GHz",
    },
    "cpu2": None,
    "cam1": {"name": "USB Camera", "pid": "0001", "vid": "0002"},
    "cam2": {"name": "", "pid": "", "vid": ""},
    "cam3": {"name": "", "pid": "", "vid": ""},
    "protocol": "",
    "port": "",
    "tlsPort": "",
    "insecurePort": "",
}


def mock_board(
    mock,
    *,
    state=None,
    config=None,
    config_status=200,
    version="1.0.7",
    base=BASE,
):
    mock.get(f"{base}/api/state", json=deepcopy(STATE if state is None else state))
    mock.get(
        f"{base}/api/config",
        json=deepcopy(CONFIG if config is None else config),
        status=config_status,
    )
    mock.get(f"{base}/api/version", text=version)
    mock.get(f"{base}/api/state/stats", json={"fps": 12.5})
    mock.get(f"{base}/api/cams/stats", json={"fps": [29.9, 30, 29.8]})
    mock.get(f"{base}/api/cams/state", json={"isRunning": False, "isOpened": False})
    mock.get(
        f"{base}/api/state/motion",
        json={
            "isStable": True,
            "isHand": False,
            "isTakeoutPartial": False,
            "isTakeoutFull": False,
        },
    )


def local_entry_data(board_id="board-1", host="192.0.2.10"):
    return {
        "board_id": board_id,
        "host": host,
        "port": 3180,
        "local_only": True,
    }


def entry_data():
    """A cloud entry, linked with a registered client ID."""
    return {
        "client_id": "registered-test-client",
        "board_id": "board-1",
        "token": {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": 0,
        },
    }


def mock_board_v2(mock, *, system=None, state=None, host=None, base=BASE):
    """A Board Manager 2 board: /api/system instead of upstream routes."""
    mock.get(f"{base}/api/system", json=deepcopy(SYSTEM if system is None else system))
    mock.get(f"{base}/api/host", json=deepcopy(HOST if host is None else host))
    mock.put(f"{base}/api/upstream/connect", status=404)
    mock.put(f"{base}/api/upstream/disconnect", status=404)
    mock_board(mock, state=state, version="2.0.0", base=base)


# A second board in the same home: its own ID, address and two cameras.
SECOND_BASE = "http://192.0.2.20:3180"


def second_board_config():
    config = deepcopy(CONFIG)
    config["auth"]["board_id"] = "board-2"
    config["cam"]["cams"] = ["/dev/video0", "/dev/video2"]
    return config


def board(*hits, **changes):
    """A running board with the given darts of the current visit."""
    return {
        "running": True,
        "connected": True,
        "status": "Throw",
        "event": "Throw",
        "numThrows": len(hits),
        "throws": [
            {"segment": {"name": name, "number": number, "multiplier": multiplier}}
            for name, number, multiplier in hits
        ],
        **changes,
    }


T20 = ("T20", 20, 3)
S20 = ("S20", 20, 1)
BULL = ("Bull", 25, 2)
OUTER_BULL = ("25", 25, 1)
MISS = ("M", 0, 0)


async def setup_local(hass, aioclient_mock, **kwargs):
    """A Board Manager 1 board, set up locally."""
    mock_board(aioclient_mock, **kwargs)
    entry = MockConfigEntry(domain="autodarts", version=2, data=local_entry_data())
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    return entry


# Options of an entry with the online bridge switched on.
WEBHOOK_ID = "0123456789abcdef" * 4
WEBHOOK_PATH = f"/api/webhook/{WEBHOOK_ID}"
BRIDGE = {"online_bridge": True, "online_bridge_webhook_id": WEBHOOK_ID}


async def setup_bridge(hass, aioclient_mock, options=None, **kwargs):
    """A Board Manager 1 board whose entry has the options, by default the bridge on."""
    mock_board(aioclient_mock, **kwargs)
    entry = MockConfigEntry(
        domain="autodarts",
        version=2,
        data=local_entry_data(),
        options=BRIDGE if options is None else options,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    return entry


async def setup_v2(hass, aioclient_mock, **kwargs):
    """A Board Manager 2 board, set up locally."""
    mock_board_v2(aioclient_mock, **kwargs)
    entry = MockConfigEntry(domain="autodarts", version=2, data=local_entry_data())
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity_id(hass, platform, key, board_id="board-1"):
    result = er.async_get(hass).async_get_entity_id(
        platform, "autodarts", f"{board_id}_{key}"
    )
    assert result is not None
    return result


def state(hass, platform, key, board_id="board-1"):
    return hass.states.get(entity_id(hass, platform, key, board_id)).state


def unique_ids(hass, entry) -> set[str]:
    registry = er.async_get(hass)
    return {
        item.unique_id
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


def record(hass, coordinator) -> list[tuple[str, dict]]:
    """The events the board announces from now on."""
    events: list[tuple[str, dict]] = []

    @callback
    def receive(kind: str, attributes: dict) -> None:
        events.append((kind, attributes))

    async_dispatcher_connect(hass, coordinator.event_signal, receive)
    return events


async def switch(hass, key: str, on: bool) -> None:
    await hass.services.async_call(
        "switch",
        "turn_on" if on else "turn_off",
        {"entity_id": entity_id(hass, "switch", key)},
        blocking=True,
    )
    await hass.async_block_till_done()


def mock_cloud(mock, board_id="board-1"):
    """The Autodarts cloud: a token refresh and a board without a match."""
    from custom_components.autodarts.api import API_BASE, REFRESH_URL

    mock.post(
        REFRESH_URL,
        json={"access_token": "new", "refresh_token": "rotated", "expires_in": 900},
    )
    mock.get(
        f"{API_BASE}/bs/v0/boards/{board_id}",
        json={"id": board_id, "name": "My Board", "state": {"connected": True}},
    )


def entity_summary(hass, entry) -> dict[str, str]:
    """By unique ID: entity ID, category, whether it starts disabled, device
    class, unit, state class and translation key, and whether it is named
    after its device."""
    registry = er.async_get(hass)
    return {
        item.unique_id: " | ".join(
            (
                item.entity_id,
                item.entity_category or "-",
                "disabled" if item.disabled_by else "enabled",
                item.original_device_class or "-",
                item.unit_of_measurement or "-",
                (item.capabilities or {}).get("state_class") or "-",
                item.translation_key or "-",
                "named" if item.has_entity_name else "unnamed",
            )
        )
        for item in sorted(
            er.async_entries_for_config_entry(registry, entry.entry_id),
            key=lambda item: item.unique_id,
        )
    }
