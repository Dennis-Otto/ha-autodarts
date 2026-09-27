"""Drive a real Home Assistant instance against the Board Manager double.

Runs inside the Home Assistant container and uses only its public REST and
WebSocket APIs: onboarding, config flow, services, registries and diagnostics.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import socket
import time
from pathlib import Path

import aiohttp
from board_mock import API_KEY, BOARD_ID, GENERATION, PORT, TLS_KEY, UPDATE, VERSION
from pictures import board_photo

HA = "http://127.0.0.1:8123"
BOARD = f"http://board-mock:{PORT}"
CLIENT_ID = f"{HA}/"
PASSWORD = "e2e-only-password"
LOG = Path("/config/home-assistant.log")
# The highlight gallery in the media folder of the Home Assistant container.
GALLERY = Path("/media/autodarts/highlights")
PHOTO = "2026-09-26_21-05-33_E2E Player_180.jpg"

# Darts as Board Manager 2.0 reports them, with the bed and normalized position.
T20 = {
    "segment": {"name": "T20", "number": 20, "multiplier": 3, "bed": "Triple"},
    "coords": {"x": 0.0123, "y": 0.5981},
}
S20 = {
    "segment": {"name": "S20", "number": 20, "multiplier": 1, "bed": "SingleOuter"},
    "coords": {"x": -0.021, "y": 0.781},
}
BULL = {
    "segment": {"name": "Bull", "number": 25, "multiplier": 2, "bed": "Double"},
    "coords": {"x": 0.004, "y": -0.011},
}


def dart(number: int, multiplier: int, bed: str, radius: float) -> dict:
    """A dart in a bed of the number, at a distance from the centre."""
    angle = math.radians(18 * SECTORS.index(number))
    name = f"{'SDT'[multiplier - 1]}{number}"
    return {
        "segment": {
            "name": name,
            "number": number,
            "multiplier": multiplier,
            "bed": bed,
        },
        "coords": {"x": radius * math.sin(angle), "y": radius * math.cos(angle)},
    }


SECTORS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]
S1 = {
    "segment": {"name": "S1", "number": 1, "multiplier": 1, "bed": "SingleOuter"},
    "coords": {"x": 0.244, "y": 0.751},
}
D20 = {
    "segment": {"name": "D20", "number": 20, "multiplier": 2, "bed": "Double"},
    "coords": {"x": 0.0, "y": 0.976},
}
# 101 in one visit: 60, 1 and the double 20.
CHECKOUT_101 = [T20, S1, D20]
# Names that appear nowhere else, so diagnostics can be searched for them.
TOURNAMENT_PLAYERS = ["Anneliese", "Bertram", "Cordula"]
# Logged while the fault injection makes the board unavailable.
EXPECTED_LOGS = (
    "Board Manager does not answer",
    "realtime events at",
    # The online bridge explains an unknown trigger once.
    "The online bridge ignored the unknown event 'takeout'",
    # The WebSocket API logs the refused export of the reports step.
    "The export folder ../outside must be inside",
)
EXPECTED_TRACEBACK = "[custom_components.autodarts.local_coordinator] Full error:"
MANIFEST = Path("/config/custom_components/autodarts/manifest.json")
CARD = MANIFEST.parent / "frontend" / "autodarts-card.js"

# Unique ID suffix -> platform of the entities a three-camera board must create.
ENTITIES = {
    "local_connected": "binary_sensor",
    "realtime_connected": "binary_sensor",
    "camera_2_problem": "binary_sensor",
    "start": "button",
    "calibrate_camera_1": "button",
    "detection": "switch",
    "auto_calibrate_on_start": "switch",
    "auto_calibrate": "switch",
    "auto_distortion": "switch",
    "standby_minutes": "select",
    "board_events": "event",
    "local_status": "sensor",
    "last_throw": "sensor",
    "num_throws": "sensor",
    "last_throw_score": "sensor",
    "local_visit_score": "sensor",
    "detection_fps": "sensor",
    "training_darts": "sensor",
    "training_triples": "sensor",
    "training_bulls": "sensor",
    "training_points": "sensor",
    "training_visits": "sensor",
    "training_average": "sensor",
    "training_highest_visit": "sensor",
    "training_session": "switch",
    "training_auto_start": "switch",
    "training_idle_timeout": "number",
    "training_last_session": "sensor",
    "practice_game": "select",
    "practice_double_out": "switch",
    "practice_new_leg": "button",
    "practice_remaining": "sensor",
    "practice_checkout": "sensor",
    "practice_target": "sensor",
    "correction_rate": "sensor",
    "personal_best": "sensor",
    "darts_today": "sensor",
    "training_streak": "sensor",
    "training_daily_goal": "number",
    "practice_double_in": "switch",
    "practice_bull_off": "switch",
    "player_profiles": "sensor",
    "last_match": "sensor",
    "favourite_double": "sensor",
    "practice_personal_routes": "switch",
    "practice_legs_played": "sensor",
    "practice_first_9_average": "sensor",
    "practice_players": "number",
    "practice_legs": "number",
    "practice_sets": "number",
    "practice_new_match": "button",
    "practice_player_1": "text",
    "practice_player_4": "text",
    "tournament": "sensor",
    "tournament_format": "select",
    "tournament_game": "select",
    "tournament_players": "text",
    "tournament_pause": "number",
    "tournament_third_place": "switch",
    "tournament_random_draw": "switch",
    "tournament_start": "button",
    "tournament_next_match": "button",
    "tournament_stop": "button",
    "weekly_report": "sensor",
    "weekly_report_day": "select",
    "weekly_report_time": "time",
    "training_calendar": "calendar",
    "practice_teams": "switch",
    "practice_start_1": "number",
    "practice_start_4": "number",
    "practice_golf_holes": "select",
    "practice_count_up_rounds": "number",
    "achievements": "sensor",
    "achievements_enabled": "switch",
}
if GENERATION >= 2:
    # Board Manager 2 reports its cloud link, load and updates, and has no toggle.
    ENTITIES |= {
        "cloud_link": "binary_sensor",
        "cpu_usage": "sensor",
        "memory_usage": "sensor",
        "board_software": "update",
    }
    DISABLED_BY_DEFAULT = {"detection_fps", "memory_usage"}
    ABSENT = {"upstream", "connect", "disconnect"}
else:
    ENTITIES |= {"connect": "button", "upstream": "switch"}
    DISABLED_BY_DEFAULT = {"connect", "detection_fps"}
    ABSENT = {"cloud_link", "cpu_usage", "memory_usage", "board_software"}


class E2EFailure(AssertionError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise E2EFailure(message)


async def wait_for(probe, description: str, timeout: float = 30):
    """Poll an async probe until it returns a truthy value."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = await probe()
        if last:
            return last
        await asyncio.sleep(0.5)
    raise E2EFailure(f"Timed out waiting for {description}; last result: {last!r}")


class Scenario:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self.headers: dict[str, str] = {}
        self.entities: dict[str, str] = {}
        self.socket: aiohttp.ClientWebSocketResponse | None = None
        self.message_id = 0
        self.pending: dict[int, asyncio.Future] = {}
        self.events: asyncio.Queue = asyncio.Queue()
        self.reader: asyncio.Task | None = None
        # Discovery stores the announced address instead of the service name.
        self.board_ip = socket.gethostbyname("board-mock")
        self.webhook_id: str | None = None
        self.device_id = ""

    async def http(self, method: str, url: str, *, status: int = 200, **kwargs):
        async with self.session.request(
            method, url, headers=self.headers, **kwargs
        ) as response:
            body = await response.text()
            check(
                response.status == status,
                f"{method} {url}: expected HTTP {status}, got {response.status}: {body}",
            )
            return json.loads(body) if body else None

    async def api(self, method: str, path: str, **kwargs):
        return await self.http(method, f"{HA}{path}", **kwargs)

    async def board(self, method: str, path: str, **kwargs):
        return await self.http(method, f"{BOARD}{path}", **kwargs)

    # Authentication and WebSocket API

    async def onboard(self) -> None:
        created = await self.api(
            "POST",
            "/api/onboarding/users",
            json={
                "client_id": CLIENT_ID,
                "name": "E2E Admin",
                "username": "e2e-admin",
                "password": PASSWORD,
                "language": "en",
            },
        )
        token = await self.api(
            "POST",
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": created["auth_code"],
                "client_id": CLIENT_ID,
            },
        )
        self.headers = {"Authorization": f"Bearer {token['access_token']}"}

        async def running():
            # Onboarding answers before every configured integration has loaded.
            async with self.session.get(
                f"{HA}/api/config", headers=self.headers
            ) as response:
                return (
                    response.status == 200
                    and (await response.json())["state"] == "RUNNING"
                )

        await wait_for(running, "Home Assistant to finish starting", timeout=120)
        # Complete onboarding like a user, so the regular dashboards are served.
        await self.api("POST", "/api/onboarding/core_config")
        await self.api("POST", "/api/onboarding/analytics")
        await self.api(
            "POST",
            "/api/onboarding/integration",
            json={
                "client_id": CLIENT_ID,
                "redirect_uri": f"{CLIENT_ID}?auth_callback=1",
            },
        )

    async def connect(self) -> None:
        self.socket = await self.session.ws_connect(f"{HA}/api/websocket")
        check(
            (await self.socket.receive_json())["type"] == "auth_required",
            "WebSocket API did not request authentication",
        )
        await self.socket.send_json(
            {
                "type": "auth",
                "access_token": self.headers["Authorization"].removeprefix("Bearer "),
            }
        )
        check(
            (await self.socket.receive_json())["type"] == "auth_ok",
            "WebSocket authentication failed",
        )
        self.reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        async for message in self.socket:
            payload = message.json()
            if payload["type"] == "event":
                self.events.put_nowait(payload["event"])
            elif future := self.pending.pop(payload["id"], None):
                future.set_result(payload)

    async def ws_result(self, command: str, **payload) -> dict:
        self.message_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[self.message_id] = future
        await self.socket.send_json({"id": self.message_id, "type": command, **payload})
        return await asyncio.wait_for(future, 30)

    async def ws(self, command: str, **payload):
        result = await self.ws_result(command, **payload)
        check(result["success"], f"{command} failed: {result.get('error')}")
        return result["result"]

    # Home Assistant helpers

    def entity(self, key: str) -> str:
        return self.entities[f"{BOARD_ID}_{key}"]

    async def state(self, key: str) -> dict:
        return await self.api("GET", f"/api/states/{self.entity(key)}")

    async def expect_states(self, expected: dict[str, str], timeout: float = 30):
        async def probe():
            actual = {key: (await self.state(key))["state"] for key in expected}
            return actual == expected or None

        try:
            await wait_for(probe, f"states {expected}", timeout)
        except E2EFailure:
            actual = {key: (await self.state(key))["state"] for key in expected}
            raise E2EFailure(f"Expected {expected}, got {actual}") from None

    async def service(self, domain: str, service: str, key: str, **data) -> None:
        await self.api(
            "POST",
            f"/api/services/{domain}/{service}",
            json={"entity_id": self.entity(key), **data},
        )

    async def entry_is(self, state: str) -> bool:
        entries = await self.api(
            "GET", "/api/config/config_entries/entry?domain=autodarts"
        )
        return len(entries) == 1 and entries[0]["state"] == state

    async def flow(self, flow_id: str | None = None, **data) -> dict:
        if flow_id is None:
            return await self.api(
                "POST", "/api/config/config_entries/flow", json={"handler": "autodarts"}
            )
        return await self.api(
            "POST", f"/api/config/config_entries/flow/{flow_id}", json=data
        )

    async def local_flow(self, host: str, port: int) -> dict:
        menu = await self.flow()
        check(
            menu["type"] == "menu" and menu["menu_options"] == ["discover", "local"],
            f"Unexpected setup menu: {menu}",
        )
        form = await self.flow(menu["flow_id"], next_step_id="local")
        check(form["step_id"] == "local", f"Local setup form missing: {form}")
        return await self.flow(form["flow_id"], host=host, port=port)

    # Scenario steps

    async def setup(self) -> str:
        result = await self.local_flow("http://board-mock", PORT)
        check(result["errors"] == {"host": "invalid_host"}, f"URL accepted: {result}")
        result = await self.local_flow("board-mock", PORT + 1)
        check(
            result["errors"] == {"base": "cannot_connect_local"},
            f"Closed port accepted: {result}",
        )
        if GENERATION >= 2:
            result = await self.discovered_setup()
        else:
            result = await self.local_flow("Board-Mock", PORT)
            check(
                result["title"] == "Autodarts (board-mock)",
                f"Title: {result['title']}",
            )
        check(result["type"] == "create_entry", f"Local setup failed: {result}")
        entry_id = result["result"]["entry_id"]

        duplicate = await self.local_flow("board-mock", PORT)
        check(
            duplicate.get("reason") == "already_configured",
            f"Second entry for the same board was not rejected: {duplicate}",
        )

        await wait_for(lambda: self.entry_is("loaded"), "the config entry to load")
        return entry_id

    async def discovered_setup(self) -> dict:
        """Home Assistant finds the announced Board Manager 2 on its own."""

        async def announced():
            flows = await self.ws("config_entries/flow/progress")
            return next(
                (
                    flow
                    for flow in flows
                    if flow["handler"] == "autodarts"
                    and flow["context"].get("source") == "zeroconf"
                ),
                None,
            )

        flow = await wait_for(announced, "the mDNS announcement to be discovered", 60)
        check(flow["step_id"] == "zeroconf_confirm", f"Discovery flow: {flow}")
        result = await self.api(
            "GET", f"/api/config/config_entries/flow/{flow['flow_id']}"
        )
        check(result["step_id"] == "zeroconf_confirm", f"Discovery form: {result}")
        placeholders = result["description_placeholders"]
        check(
            placeholders["version"] == VERSION and placeholders["cameras"] == "3",
            f"Discovery details: {placeholders}",
        )
        return await self.flow(flow["flow_id"])

    async def registries(self, entry_id: str) -> None:
        registered: dict[str, dict] = {}

        async def discovered():
            registered.clear()
            for item in await self.ws("config/entity_registry/list"):
                if item["config_entry_id"] == entry_id:
                    registered[item["unique_id"]] = item
            return all(f"{BOARD_ID}_{key}" in registered for key in ENTITIES)

        await wait_for(discovered, "all local entities, including discovered cameras")
        for key, platform in ENTITIES.items():
            item = registered[f"{BOARD_ID}_{key}"]
            check(item["platform"] == "autodarts", f"{key}: wrong integration")
            check(
                item["entity_id"].startswith(f"{platform}."),
                f"{key}: expected {platform}, got {item['entity_id']}",
            )
            disabled = item["disabled_by"] == "integration"
            check(
                disabled == (key in DISABLED_BY_DEFAULT),
                f"{key}: unexpected disabled_by {item['disabled_by']!r}",
            )
        unexpected = {f"{BOARD_ID}_{key}" for key in ABSENT} & set(registered)
        check(not unexpected, f"Entities of the other generation: {unexpected}")
        self.entities = {
            unique_id: item["entity_id"] for unique_id, item in registered.items()
        }

        devices = [
            device
            for device in await self.ws("config/device_registry/list")
            if ["autodarts", BOARD_ID] in device["identifiers"]
        ]
        check(len(devices) == 1, f"Expected one board device, got {devices}")
        device = devices[0]
        self.device_id = device["id"]
        check(device["sw_version"] == VERSION, f"Firmware: {device['sw_version']}")
        check(
            device["configuration_url"] in (BOARD, f"http://{self.board_ip}:{PORT}"),
            f"Configuration URL: {device['configuration_url']}",
        )

    async def initial_state(self) -> None:
        expected = {
            "local_connected": "on",
            "realtime_connected": "on",
            "detection": "off",
            "auto_calibrate_on_start": "on",
            "auto_calibrate": "on",
            "auto_distortion": "off",
            "standby_minutes": "15",
            "local_status": "stopped",
            "training_darts": "0",
        }
        if GENERATION >= 2:
            expected |= {"cloud_link": "on", "cpu_usage": "7.5", "board_software": "on"}
        else:
            expected |= {"upstream": "on"}
        await self.expect_states(expected)
        if GENERATION >= 2:
            update = await self.state("board_software")
            versions = (
                update["attributes"]["installed_version"],
                update["attributes"]["latest_version"],
            )
            check(versions == (VERSION, UPDATE), f"Update versions: {versions}")

    async def controls(self) -> None:
        await self.service("button", "press", "start")
        await self.expect_states({"detection": "on", "local_status": "throw"})
        await self.service("switch", "turn_on", "auto_distortion")
        await self.expect_states({"auto_distortion": "on"})
        await self.service("select", "select_option", "standby_minutes", option="30")
        await self.expect_states({"standby_minutes": "30"})
        await self.service("button", "press", "calibrate_camera_1")
        if GENERATION < 2:
            await self.service("switch", "turn_off", "upstream")
            await self.expect_states({"upstream": "off"})
            await self.service("switch", "turn_on", "upstream")
            await self.expect_states({"upstream": "on"})

        board = await self.board("GET", "/control/requests")
        expected = [
            {"method": "PUT", "path": "/api/start", "body": None},
            {
                "method": "PATCH",
                "path": "/api/config",
                "body": {"cam": {"auto_distortion": True}},
            },
            {
                "method": "PATCH",
                "path": "/api/config",
                "body": {"motion": {"standby_minutes": 30}},
            },
            {
                "method": "POST",
                "path": "/api/config/calibration/auto/1?distortion=true",
                "body": None,
            },
        ]
        if GENERATION < 2:
            expected += [
                {"method": "PUT", "path": "/api/upstream/disconnect", "body": None},
                {"method": "PUT", "path": "/api/upstream/connect", "body": None},
            ]
        check(
            board["commands"] == expected,
            f"Board commands differ:\n{json.dumps(board['commands'], indent=2)}",
        )

    async def realtime(self, entry_id: str) -> None:
        # Without polling, every following change must arrive over the board socket.
        await self.ws(
            "config_entries/update", entry_id=entry_id, pref_disable_polling=True
        )
        await wait_for(
            lambda: self.entry_is("loaded"), "the reloaded entry without polling"
        )
        await self.expect_states({"realtime_connected": "on", "detection": "on"})
        await self.service("select", "select_option", "practice_game", option="301")
        await self.expect_states({"practice_game": "301", "practice_remaining": "301"})
        await self.ws("subscribe_events", event_type="state_changed")

        await self.board(
            "POST", "/control/state", json={"event": "Throw detected", "throws": [T20]}
        )
        await self.expect_states({"last_throw": "T20", "last_throw_score": "60"})
        await self.board("POST", "/control/state", json={"throws": [T20, BULL]})
        await self.expect_states(
            {"last_throw": "Bull", "local_visit_score": "110", "num_throws": "2"}
        )
        throws = (await self.state("local_visit_score"))["attributes"]["throws"]
        check(
            throws
            == [
                {
                    "segment": "T20",
                    "number": 20,
                    "multiplier": 3,
                    "score": 60,
                    "bed": "Triple",
                    "x": 0.012,
                    "y": 0.598,
                },
                {
                    "segment": "Bull",
                    "number": 25,
                    "multiplier": 2,
                    "score": 50,
                    "bed": "Double",
                    "x": 0.004,
                    "y": -0.011,
                },
            ],
            f"Unexpected dart details for the dashboard card: {throws}",
        )
        await self.board(
            "POST",
            "/control/state",
            json={"event": "Dart corrected", "throws": [S20, BULL]},
        )
        await self.expect_states({"local_visit_score": "70"})
        await self.board(
            "POST",
            "/control/state",
            json={"status": "Takeout in progress", "event": "Takeout started"},
        )
        await self.board(
            "POST",
            "/control/state",
            json={"status": "Throw", "event": "Takeout finished", "throws": []},
        )
        await self.expect_states(
            {
                "num_throws": "0",
                "local_visit_score": "0",
                "training_darts": "2",
                "training_triples": "0",
                "training_bulls": "1",
                "training_points": "70",
                "training_visits": "1",
                "training_highest_visit": "70",
                "training_average": "105.0",
                "practice_remaining": "231",
            }
        )
        hits = (await self.state("training_darts"))["attributes"]["hits"]
        check(hits == {"BULL": 1, "S20": 1}, f"Unexpected hits for the heatmap: {hits}")

        fired = self.fired_board_events()
        board_events = [
            (
                item["event_type"],
                item.get("segment"),
                item.get("score"),
                item.get("status"),
            )
            for item in fired
        ]
        check(
            board_events
            == [
                ("dart_detected", "T20", 60, None),
                ("dart_detected", "Bull", 50, None),
                ("dart_corrected", "S20", 20, None),
                ("status_changed", None, None, "Takeout in progress"),
                ("takeout_started", None, None, None),
                ("visit_completed", None, 70, None),
                # The practice game announces the next visit.
                ("turn_changed", None, None, None),
                ("status_changed", None, None, "Throw"),
                ("takeout_finished", None, None, None),
            ],
            f"Unexpected board events: {fired}",
        )
        check(
            all(item["source"] == "websocket" for item in fired),
            f"Events did not arrive in realtime: {fired}",
        )

        store = Path(f"/config/.storage/autodarts.{entry_id}.training")

        async def persisted():
            if not store.exists():
                return None
            return json.loads(store.read_text())["data"]["darts"] == 2

        await wait_for(persisted, "the persisted training session", timeout=20)

    def fired_board_events(self) -> list[dict]:
        """Attributes of the board events since the last call, in order."""
        fired = []
        while not self.events.empty():
            event = self.events.get_nowait()["data"]
            if event["entity_id"] == self.entity("board_events") and event["new_state"]:
                fired.append(event["new_state"]["attributes"])
        return fired

    def state_changes(self, key: str) -> list[str]:
        """States an entity passed through since the events were last read."""
        changes = []
        while not self.events.empty():
            data = self.events.get_nowait()["data"]
            if data["entity_id"] == self.entity(key) and data["new_state"]:
                changes.append(data["new_state"]["state"])
        return changes

    async def fault(self, **fault) -> None:
        await self.board("POST", "/control/fault", json=fault)

    async def resilience(self, entry_id: str) -> None:
        """Faults of a real network and board: visits and entities survive them."""
        # Polling is back, as it notices a board that is away.
        await self.ws(
            "config_entries/update", entry_id=entry_id, pref_disable_polling=False
        )
        await wait_for(lambda: self.entry_is("loaded"), "the entry with polling")
        await self.expect_states({"realtime_connected": "on", "local_connected": "on"})
        self.fired_board_events()

        # 1. The socket drops mid-visit; polling finds the second dart meanwhile.
        await self.board("POST", "/control/state", json={"throws": [T20]})
        await self.expect_states({"last_throw": "T20"})
        await self.fault(drop_sockets=True, refuse_sockets=True)
        await self.expect_states({"realtime_connected": "off"})
        await self.board("POST", "/control/state", json={"throws": [T20, T20]})
        await self.expect_states({"num_throws": "2", "local_visit_score": "120"})
        await self.fault(refuse_sockets=False)
        await self.expect_states({"realtime_connected": "on"}, timeout=90)
        await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"practice_remaining": "111", "training_darts": "4"})
        visit = [
            (item["event_type"], item.get("dart_index"), item["source"])
            for item in self.fired_board_events()
            if item["event_type"] in ("dart_detected", "visit_completed")
        ]
        check(
            [item[:2] for item in visit]
            == [("dart_detected", 1), ("dart_detected", 2), ("visit_completed", None)]
            and visit[1][2] == "poll",
            f"The visit did not survive the dropped socket: {visit}",
        )

        # 2. The board is away while its darts are pulled and one is thrown again.
        await self.board("POST", "/control/state", json={"throws": [S20]})
        await self.expect_states({"last_throw": "S20"})
        await self.fault(drop_sockets=True, refuse_sockets=True, http_status=503)
        # Two missed polls are a hiccup; the third makes the board unavailable.
        await self.expect_states(
            {"local_connected": "off", "detection": "unavailable"}, timeout=40
        )
        # The board events stay available for the events of Home Assistant itself.
        events = await self.state("board_events")
        check(events["state"] != "unavailable", f"Board events: {events}")
        await self.board("POST", "/control/state", json={"throws": []})
        await self.board("POST", "/control/state", json={"throws": [BULL]})
        await self.fault(clear=True)
        # The visit ended during the outage; the dart after it is not counted.
        await self.expect_states(
            {
                "local_connected": "on",
                "last_throw": "Bull",
                "practice_remaining": "91",
                "training_darts": "5",
            },
            timeout=40,
        )
        await self.expect_states({"realtime_connected": "on"}, timeout=90)
        completed = [
            item
            for item in self.fired_board_events()
            if item["event_type"] == "visit_completed"
        ]
        check(
            [(item["score"], item["segments"]) for item in completed]
            == [(20, ["S20"])],
            f"The visit of the outage was not completed once: {completed}",
        )
        await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"num_throws": "0", "training_darts": "5"})

        # 3. Failing and slow reads for a few seconds are no outage.
        await self.fault(drop_sockets=True, refuse_sockets=True)
        await self.expect_states({"realtime_connected": "off"})
        self.fired_board_events()
        await self.fault(http_status=503, paths=["/api/state"], count=2)
        await asyncio.sleep(8)
        # Longer than the ten seconds a read may take.
        await self.fault(delay=11, paths=["/api/state"], count=1)
        await asyncio.sleep(14)
        check(
            "off" not in self.state_changes("local_connected"),
            "A few failed reads made the board unavailable",
        )
        await self.expect_states({"local_connected": "on"})
        await self.fault(clear=True)
        await self.expect_states({"realtime_connected": "on"}, timeout=90)

        # 4. Malformed frames are skipped; the next notification works.
        for frame in (
            "not json",
            '{"type":"state","data":{"running":"yes","throws":[]}}',
            '{"type":"cam_stats","data":{"id":9,"fps":NaN}}',
        ):
            await self.fault(frame=frame)
        await self.fault(binary=True)
        await self.board("POST", "/control/state", json={"throws": [T20]})
        await self.expect_states({"last_throw": "T20", "practice_remaining": "31"})
        await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"training_darts": "6"})

        # 5. The Board Manager restarts: away for a few seconds, then back.
        await self.fault(restart=3)
        await self.expect_states({"realtime_connected": "off"})
        await self.expect_states(
            {"realtime_connected": "on", "local_connected": "on"}, timeout=90
        )
        report = await self.api("GET", f"/api/diagnostics/config_entry/{entry_id}")
        realtime = report["data"]["connection"]["realtime"]
        check(
            realtime["ignored_frames"] >= 2 and realtime["connects"] >= 4,
            f"Diagnostics do not show the faults: {realtime}",
        )

    async def options(
        self, flow_id: str | None = None, entry_id: str | None = None, **data
    ) -> dict:
        if flow_id is None:
            return await self.api(
                "POST",
                "/api/config/config_entries/options/flow",
                json={"handler": entry_id},
            )
        return await self.api(
            "POST", f"/api/config/config_entries/options/flow/{flow_id}", json=data
        )

    async def bridge_sensor(self) -> str | None:
        for item in await self.ws("config/entity_registry/list"):
            if item["unique_id"] == f"{BOARD_ID}_online_bridge_last_event":
                return item["entity_id"]
        return None

    async def webhook(self, method: str, path: str, **kwargs) -> tuple[int, str]:
        """A call as Tools for Autodarts makes it: no login, no JSON content type."""
        async with self.session.request(method, f"{HA}{path}", **kwargs) as response:
            return response.status, await response.text()

    async def online_bridge(self, entry_id: str) -> None:
        """Moments of an online match arrive through the webhook of the options."""
        form = await self.options(entry_id=entry_id)
        check(form["step_id"] == "init", f"Unexpected options: {form}")
        shown = await self.options(
            form["flow_id"], online_bridge=True, online_bridge_remote=False
        )
        check(shown["step_id"] == "online_bridge", f"No bridge address: {shown}")
        url = shown["description_placeholders"]["url"]
        webhook_id = url.rsplit("/", 1)[1]
        check(re.fullmatch("[0-9a-f]{64}", webhook_id) is not None, f"Address: {url}")
        effects = shown["description_placeholders"]["effects"].splitlines()
        check(
            f"Home Assistant: 180;URL;{url}?event=180;180" in effects,
            f"Unexpected effects to import: {effects}",
        )
        done = await self.options(shown["flow_id"])
        check(done["type"] == "create_entry", f"Options were not saved: {done}")
        self.webhook_id = webhook_id
        sensor = await wait_for(self.bridge_sensor, "the online bridge sensor", 60)
        self.entities[f"{BOARD_ID}_online_bridge_last_event"] = sensor
        await self.expect_states(
            {"online_bridge_last_event": "unknown", "realtime_connected": "on"},
            timeout=90,
        )
        self.fired_board_events()

        path = f"/api/webhook/{webhook_id}"
        answers = [
            await self.webhook("GET", f"{path}?event=180"),
            await self.webhook(
                "POST",
                path,
                data='{"event": "busted", "player": "Lea"}',
                headers={"Content-Type": "text/plain;charset=UTF-8"},
            ),
            await self.webhook("GET", f"{path}?event=takeout"),
        ]
        check(
            answers == [(200, "ok"), (200, "ok"), (400, "unknown event")],
            f"Unexpected webhook answers: {answers}",
        )
        fired: list[dict] = []

        async def arrived():
            fired.extend(
                item
                for item in self.fired_board_events()
                if item.get("event_type", "").startswith("online_")
            )
            return len(fired) >= 2

        await wait_for(arrived, "the online board events")
        check(
            [
                (item["event_type"], item.get("score"), item.get("name"))
                for item in fired
            ]
            == [("online_visit", 180, None), ("online_busted", None, "Lea")]
            and all(item["source"] == "online" for item in fired),
            f"Unexpected online events: {fired}",
        )
        last = await self.state("online_bridge_last_event")
        check(
            last["state"] not in ("unknown", "unavailable")
            and last["attributes"]["trigger"] == "busted",
            f"Unexpected last event: {last}",
        )
        report = await self.api("GET", f"/api/diagnostics/config_entry/{entry_id}")
        check(
            webhook_id not in json.dumps(report),
            "Diagnostics expose the webhook address",
        )
        summary = report["data"]["online_bridge"]
        check(
            summary["events"] == 2 and summary["invalid"] == 1,
            f"Unexpected bridge diagnostics: {summary}",
        )

        # Switched off, the address answers like any unknown one. The reloaded
        # event entity restores its last event, which is not a new one.
        last_event = (await self.state("board_events"))["state"]
        form = await self.options(entry_id=entry_id)
        done = await self.options(
            form["flow_id"],
            online_bridge=False,
            online_bridge_remote=False,
            online_bridge_new_address=False,
        )
        check(done["type"] == "create_entry", f"Options were not saved: {done}")

        async def removed():
            return await self.bridge_sensor() is None

        await wait_for(removed, "the online bridge sensor to be removed", 60)
        del self.entities[f"{BOARD_ID}_online_bridge_last_event"]
        answer = await self.webhook("GET", f"{path}?event=180")
        check(answer == (200, ""), f"The switched-off bridge answered: {answer}")
        await self.expect_states({"realtime_connected": "on"}, timeout=90)
        new_online_events = []
        while not self.events.empty():
            data = self.events.get_nowait()["data"]
            new = data["new_state"]
            if (
                data["entity_id"] == self.entity("board_events")
                and new
                and new["state"] != last_event
                and new["attributes"].get("event_type", "").startswith("online_")
            ):
                new_online_events.append(new["attributes"])
        check(
            not new_online_events,
            f"The switched-off bridge fired events: {new_online_events}",
        )

    async def call(self, domain: str, service: str, **data) -> dict:
        """An action with its response, over the WebSocket API like the cards."""
        result = await self.ws(
            "call_service",
            domain=domain,
            service=service,
            return_response=True,
            **data,
        )
        return result["response"]

    async def refused(self, command: str, **payload) -> dict:
        """A command that must fail, with the error it reports."""
        self.message_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[self.message_id] = future
        await self.socket.send_json({"id": self.message_id, "type": command, **payload})
        result = await asyncio.wait_for(future, 30)
        check(not result["success"], f"{command} did not fail: {result}")
        return result["error"]

    async def download(self, path: str, headers: dict[str, str]) -> tuple[int, str]:
        async with self.session.get(f"{HA}{path}", headers=headers) as response:
            return response.status, await response.text(encoding="utf-8-sig")

    async def reports(self, entry_id: str) -> None:
        """Weekly report, training calendar and exports over the real API."""
        await self.expect_states(
            {"weekly_report_day": "monday", "weekly_report_time": "00:00:00"}
        )
        # The week counts every dart so far; the session started with the first.
        training = {
            key: (await self.state(f"training_{key}"))["state"]
            for key in ("darts", "visits", "average")
        }
        report = await self.state("weekly_report")
        attributes = report["attributes"]
        check(
            (report["state"], str(attributes["visits"]), str(attributes["average"]))
            == (training["darts"], training["visits"], training["average"])
            and attributes["last_week"] is None,
            f"The weekly report {report} differs from the session {training}",
        )
        await self.service(
            "select", "select_option", "weekly_report_day", option="sunday"
        )
        await self.service("time", "set_value", "weekly_report_time", time="20:30:00")
        await self.expect_states(
            {"weekly_report_day": "sunday", "weekly_report_time": "20:30:00"}
        )

        # A new session ends the one with the darts of the earlier steps.
        await self.service("button", "press", "reset_training")
        calendar = self.entity("training_calendar")
        period = {
            "start_date_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - 86400)
            ),
            "end_date_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() + 3600)
            ),
        }

        async def listed():
            events = (
                await self.call(
                    "calendar",
                    "get_events",
                    service_data=period,
                    target={"entity_id": calendar},
                )
            )[calendar]["events"]
            return events or None

        events = await wait_for(listed, "the finished session in the calendar")
        darts, average = int(training["darts"]), float(training["average"])
        check(
            [event["summary"] for event in events]
            == [f"Training · {darts} Darts · Ø {average:.1f}"],
            f"Unexpected training calendar: {events}",
        )

        export = await self.call(
            "autodarts", "export", service_data={"format": "json", "what": "all"}
        )
        name = Path(export["path"]).name
        check(
            export["path"] == f"/config/www/autodarts/{name}"
            and name.startswith("autodarts-all-")
            and export["url"] == f"/local/autodarts/{name}"
            and export["download"] == f"/api/autodarts/export/{name}"
            and export["rows"] == {"sessions": 1, "matches": 0, "profiles": 0},
            f"Unexpected export: {export}",
        )
        status, body = await self.download(export["download"], self.headers)
        check(status == 200, f"Export download failed: HTTP {status}")
        sessions = json.loads(body)["sessions"]
        check(
            [(item["darts"], item["average"]) for item in sessions]
            == [(darts, average)],
            f"Unexpected exported sessions: {sessions}",
        )
        status, _ = await self.download(export["download"], {})
        check(status == 401, f"Export downloadable without login: HTTP {status}")
        # The players card downloads with a signed path, as a browser link does.
        signed = await self.ws("auth/sign_path", path=export["download"], expires=60)
        status, _ = await self.download(signed["path"], {})
        check(status == 200, f"Signed export download failed: HTTP {status}")

        export = await self.call(
            "autodarts", "export", service_data={"what": "sessions"}
        )
        status, body = await self.download(export["download"], self.headers)
        check(
            status == 200 and body.splitlines()[0].startswith("started,ended,"),
            f"Unexpected CSV export: HTTP {status} {body[:200]}",
        )
        error = await self.refused(
            "call_service",
            domain="autodarts",
            service="export",
            service_data={"folder": "../outside"},
            return_response=True,
        )
        check(
            error["code"] == "service_validation_error",
            f"An export outside the configuration folder was not refused: {error}",
        )

        store = Path(f"/config/.storage/autodarts.{entry_id}.journal")

        async def persisted():
            if not store.exists():
                return None
            return len(json.loads(store.read_text())["data"]["sessions"]) == 1 or None

        await wait_for(persisted, "the persisted training journal", timeout=30)

    async def start_game(self, **data) -> None:
        await self.api("POST", "/api/services/autodarts/start_game", json=data)

    async def visit(self, *darts: dict) -> None:
        """Throw a visit and pull the darts."""
        await self.board("POST", "/control/state", json={"throws": list(darts)})
        await self.expect_states({"num_throws": str(len(darts))})
        await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"num_throws": "0"})

    async def events_until(self, kind: str) -> list[dict]:
        """The board events until one of this kind arrived."""
        fired: list[dict] = []

        async def arrived():
            fired.extend(self.fired_board_events())
            return any(item["event_type"] == kind for item in fired)

        await wait_for(arrived, f"a {kind} event")
        return fired

    async def games(self) -> None:
        """New games, a team match and start scores, set up with the action."""
        self.fired_board_events()
        # Golf alone: nine holes, and the last dart of a visit counts.
        await self.start_game(game="golf", players=["Alex"], holes=9)
        await self.expect_states({"practice_game": "golf", "practice_target": "1"})
        # An inner single is three strokes: the board's position tells the bed.
        await self.visit(dart(1, 1, "SingleInner", 0.35))
        await self.visit(dart(2, 3, "Triple", 0.6), dart(2, 1, "SingleOuter", 0.8))
        for hole in range(3, 10):
            await self.visit(dart(hole, 3, "Triple", 0.6))
        won = [
            item
            for item in await self.events_until("leg_won")
            if item["event_type"] == "leg_won"
        ]
        check(
            [(item["game"], item["points"], item["darts"]) for item in won]
            == [("golf", 3 + 4 + 7, 10)],
            f"Unexpected end of the Golf leg: {won}",
        )

        # Tactics for two: the numbers go down to 10.
        await self.start_game(game="tactics", players=["Alex", "Sam"])
        await self.expect_states({"practice_game": "tactics", "practice_target": "T20"})
        await self.visit(dart(10, 3, "Triple", 0.6), dart(10, 3, "Triple", 0.6))
        game = (await self.state("practice_remaining"))["attributes"]
        check(
            len(game["numbers"]) == 12
            and [score["points"] for score in game["scores"]] == [30, 0]
            and game["scores"][0]["marks"][10] == 3
            and game["player"] == 2,
            f"Unexpected Tactics chalkboard: {game}",
        )

        # Two teams of two, the second team from 201.
        await self.start_game(
            game="301",
            players=["Alex", "Sam", "Kim", "Lea"],
            teams=True,
            start_scores=[0, 201],
        )
        await self.expect_states({"practice_teams": "on", "practice_start_2": "201"})
        self.fired_board_events()
        await self.visit(T20)
        game = (await self.state("practice_remaining"))["attributes"]
        check(
            [score["remaining"] for score in game["scores"]] == [241, 201, 241, 201]
            and [team["name"] for team in game["teams"]] == ["Alex & Kim", "Sam & Lea"],
            f"Unexpected team match: {game}",
        )
        turns = [
            (item["player"], item.get("team"), item.get("team_name"))
            for item in await self.events_until("turn_changed")
            if item["event_type"] == "turn_changed"
        ]
        check(turns == [(2, 2, "Sam & Lea")], f"Unexpected turn: {turns}")
        await self.start_game(
            game="501", players=["Alex"], teams=False, start_scores=[]
        )

    async def achievements(self) -> None:
        """A 180 of a named player unlocks a badge; the cards read the positions.

        The games before gave Alex other badges and darts already.
        """
        await self.api(
            "POST",
            "/api/services/autodarts/start_game",
            json={"game": "501", "players": ["Alex"]},
        )
        await self.expect_states({"practice_game": "501", "practice_remaining": "501"})
        badges = int((await self.state("achievements"))["state"])
        self.fired_board_events()
        for count in range(1, 4):
            await self.board(
                "POST",
                "/control/state",
                json={"event": "Throw detected", "throws": [T20] * count},
            )
        await self.expect_states({"local_visit_score": "180"})
        await self.board(
            "POST",
            "/control/state",
            json={"status": "Takeout in progress", "event": "Takeout started"},
        )
        await self.board(
            "POST",
            "/control/state",
            json={"status": "Throw", "event": "Takeout finished", "throws": []},
        )
        await self.expect_states(
            {"practice_remaining": "321", "achievements": str(badges + 1)}
        )
        unlocked = [
            {key: item.get(key) for key in ("player", "name", "achievement", "tier")}
            for item in self.fired_board_events()
            if item["event_type"] == "achievement_unlocked"
        ]
        check(
            unlocked
            == [{"player": 1, "name": "Alex", "achievement": "maximum", "tier": 1}],
            f"Unexpected achievements: {unlocked}",
        )
        attributes = (await self.state("achievements"))["attributes"]
        alex = next(item for item in attributes["players"] if item["name"] == "Alex")
        check(
            attributes["latest"]["achievement"] == "maximum"
            and alex["badges"]["maximum"]["tier"] == 1,
            f"Unexpected achievements sensor: {attributes}",
        )
        profiles = (await self.state("player_profiles"))["attributes"]["players"]
        alex = next(item for item in profiles if item["name"] == "Alex")
        check(
            alex["maximums"] == 1
            and alex["hits"]["T20"] >= 3
            and alex["trend"]["maximums"][-1] == 1,
            f"Unexpected progress of Alex: {alex}",
        )
        player = await self.ws(
            "autodarts/positions", device_id=self.device_id, player="alex"
        )
        check(
            player["player"] == "Alex"
            and player["positions"][-3:] == [[0.012, 0.598]] * 3,
            f"Unexpected positions of Alex: {player}",
        )
        session = await self.ws("autodarts/positions", device_id=self.device_id)
        check(
            session["positions"][-3:] == [[0.012, 0.598]] * 3,
            f"Unexpected positions of the session: {session}",
        )
        await self.service("select", "select_option", "practice_game", option="off")
        await self.expect_states({"practice_game": "off"})

    async def match_summary(self) -> None:
        """A match ends with its summary; double out waits for the next leg."""
        await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"num_throws": "0"})
        await self.start_game(game="101", players=["Alex", "Sam"], legs=1)
        await self.expect_states({"practice_remaining": "101"})
        self.fired_board_events()
        await self.visit(
            T20, dart(1, 1, "SingleOuter", 0.8), dart(20, 2, "Double", 0.97)
        )

        async def summarized():
            attributes = (await self.state("practice_remaining"))["attributes"]
            return attributes.get("summary")

        summary = await wait_for(summarized, "the summary of the match")
        players = [
            (item["name"], item["legs"], item["darts"], item["average"])
            for item in summary["players"]
        ]
        check(
            summary["winner"] == 1
            and players == [("Alex", 1, 3, 101.0), ("Sam", 0, 0, None)]
            and summary["players"][0]["highest_checkout"] == 101,
            f"Unexpected match summary: {summary}",
        )
        won = [
            item
            for item in self.fired_board_events()
            if item["event_type"] == "match_won"
        ]
        check(
            len(won) == 1 and won[0]["summary"] == summary["players"],
            f"match_won does not carry the summary: {won}",
        )

        # Double out switched on during a leg applies from the next one.
        await self.start_game(game="301", players=["Alex"], double_out=False)
        await self.expect_states({"practice_remaining": "301"})
        await self.visit(T20)
        await self.expect_states({"practice_remaining": "241"})
        await self.service("switch", "turn_on", "practice_double_out")
        await self.expect_states({"practice_double_out": "on"})
        leg = (await self.state("practice_remaining"))["attributes"]
        check(leg["double_out"] is False, f"Double out changed the leg: {leg}")
        await self.service("button", "press", "practice_new_leg")
        await self.expect_states({"practice_remaining": "301"})
        leg = (await self.state("practice_remaining"))["attributes"]
        check(leg["double_out"] is True, f"Double out missing in the next leg: {leg}")

    async def card(self) -> None:
        """The bundled dashboard card is served and loaded without a resource."""
        version = json.loads(MANIFEST.read_text())["version"]
        digest = hashlib.sha256(CARD.read_bytes()).hexdigest()[:8]
        url = f"/autodarts/autodarts-card.js?v={version}-{digest}"
        async with self.session.get(f"{HA}{url}") as response:
            source = await response.text()
            check(response.status == 200, f"Card not served: HTTP {response.status}")
            check(
                "javascript" in response.headers.get("Content-Type", ""),
                f"Card served as {response.headers.get('Content-Type')}",
            )
        for element in (
            "autodarts-card",
            "autodarts-training-card",
            "autodarts-status-card",
            "autodarts-scoreboard-card",
            "autodarts-players-card",
            "autodarts-doubles-card",
            "autodarts-leaderboard-card",
        ):
            check(f'"{element}"' in source, f"Card element {element} missing")
        async with self.session.get(f"{HA}/") as response:
            page = await response.text()
        check(url in page, "Dashboards do not load the Autodarts card")

    async def people(self) -> None:
        """A player becomes a person of Home Assistant, and stops being one."""
        await self.api(
            "POST",
            "/api/states/person.e2e_player",
            status=201,
            json={"state": "home", "attributes": {"entity_picture": "/e2e.png"}},
        )

        async def person() -> str | None:
            players = (await self.state("player_profiles"))["attributes"]["players"]
            return next(
                (p["person"] for p in players if p["name"] == "E2E Player"), "missing"
            )

        async def linked() -> bool:
            return await person() == "person.e2e_player"

        async def unlinked() -> bool:
            return await person() is None

        await self.api(
            "POST",
            "/api/services/autodarts/link_player",
            json={"player": "E2E Player", "person": "person.e2e_player"},
        )
        await wait_for(linked, "the player linked to the person")
        await self.api(
            "POST",
            "/api/services/autodarts/unlink_player",
            json={"player": "e2e player"},
        )
        await wait_for(unlinked, "the link to be undone")
        await self.api(
            "POST", "/api/services/autodarts/delete_player", json={"name": "E2E Player"}
        )
        await self.api("DELETE", "/api/states/person.e2e_player")

    async def gallery(self) -> None:
        """The media browser lists the highlight photos by month and serves them."""
        GALLERY.mkdir(parents=True, exist_ok=True)
        photo = board_photo(["T20", "T20", "T20"])
        (GALLERY / PHOTO).write_bytes(photo)
        outside = GALLERY.parents[1] / "e2e-outside.jpg"
        outside.write_bytes(photo)
        try:
            sources = await self.ws(
                "media_source/browse_media", media_content_id="media-source://"
            )
            titles = [child["title"] for child in sources["children"]]
            check("Autodarts" in titles, f"Media sources: {titles}")
            root = await self.ws(
                "media_source/browse_media", media_content_id="media-source://autodarts"
            )
            months = [
                (child["title"], child["can_expand"]) for child in root["children"]
            ]
            check(months == [("September 2026", True)], f"Months: {months}")
            month = await self.ws(
                "media_source/browse_media",
                media_content_id="media-source://autodarts/2026-09",
            )
            photos = [
                (child["title"], child["media_class"], child["media_content_type"])
                for child in month["children"]
            ]
            check(
                photos == [("180 · E2E Player · Sep 26", "image", "image/jpeg")],
                f"Photos: {photos}",
            )
            resolved = await self.ws(
                "media_source/resolve_media",
                media_content_id=f"media-source://autodarts/{PHOTO}",
            )
            check(
                resolved["url"].startswith(
                    "/media/local/autodarts/highlights/2026-09-26_21-05-33_E2E%20Player_180.jpg?authSig="
                ),
                f"Resolved: {resolved}",
            )
            # The signed address works without a login, like in an image element.
            async with self.session.get(f"{HA}{resolved['url']}") as response:
                check(response.status == 200, f"Photo: HTTP {response.status}")
                check(await response.read() == photo, "The photo has other bytes")
            # Nothing outside the gallery resolves.
            for identifier in ("../e2e-outside.jpg", "..%2Fe2e-outside.jpg", "2026-09"):
                failed = await self.ws_result(
                    "media_source/resolve_media",
                    media_content_id=f"media-source://autodarts/{identifier}",
                )
                check(not failed["success"], f"{identifier} resolved: {failed}")
            unknown = await self.ws_result(
                "media_source/browse_media",
                media_content_id="media-source://autodarts/../..",
            )
            check(not unknown["success"], f"Browsing outside: {unknown}")
        finally:
            (GALLERY / PHOTO).unlink()
            outside.unlink()

    async def tournament(self) -> None:
        """A round robin of three at 101, started by the action and played on the board."""
        self.fired_board_events()
        await self.api(
            "POST",
            "/api/services/autodarts/start_tournament",
            json={
                "players": TOURNAMENT_PLAYERS,
                "format": "round_robin",
                "game": "101",
                "legs": 1,
                "sets": 1,
                "double_out": True,
                "bull_off": False,
                "pause": 1,
            },
        )
        await self.expect_states(
            {
                "tournament": "round_1",
                "practice_game": "101",
                "practice_remaining": "101",
            }
        )
        pairings = []
        for number in (1, 2, 3):

            async def current(number: int = number) -> dict | None:
                match = (await self.state("tournament"))["attributes"]["current"]
                return match if match and match["match"] == number else None

            match = await wait_for(current, f"tournament match {number}")
            pairings.append(match["players"])
            # The first player of every match checks out 101 in one visit.
            for count in range(1, 4):
                await self.board(
                    "POST", "/control/state", json={"throws": CHECKOUT_101[:count]}
                )
            await self.expect_states({"practice_remaining": "0"})
            await self.board("POST", "/control/state", json={"throws": []})
        await self.expect_states({"tournament": "finished"})
        attributes = (await self.state("tournament"))["attributes"]
        first, second, third = TOURNAMENT_PLAYERS
        check(
            pairings == [[third, second], [first, third], [second, first]],
            f"Unexpected order of play: {pairings}",
        )
        # Everybody won once, 1:0 with the same average: the order of the draw decides.
        check(
            attributes["winner"] == first
            and [row["name"] for row in attributes["standings"]] == TOURNAMENT_PLAYERS
            and all(row["points"] == 2 for row in attributes["standings"]),
            f"Unexpected table: {attributes['standings']}",
        )
        fired = [
            item
            for item in self.fired_board_events()
            if item["event_type"].startswith("tournament_")
        ]
        check(
            [item["event_type"] for item in fired]
            == [
                "tournament_started",
                *["tournament_match_finished"] * 3,
                "tournament_finished",
            ]
            and fired[-1]["winner"] == first
            and fired[1]["next"] == [first, third],
            f"Unexpected tournament events: {fired}",
        )
        # The matches count for the profiles like any other match.
        profiles = (await self.state("player_profiles"))["attributes"]["players"]
        won = {player["name"]: player["matches_won"] for player in profiles}
        check(
            all(won.get(name) == 1 for name in TOURNAMENT_PLAYERS),
            f"Tournament matches missing in the profiles: {won}",
        )
        await self.api("POST", "/api/services/autodarts/stop_tournament", json={})
        await self.expect_states({"tournament": "no_tournament"})

    async def diagnostics(self, entry_id: str) -> None:
        report = await self.api("GET", f"/api/diagnostics/config_entry/{entry_id}")
        data = report["data"]
        check(API_KEY not in json.dumps(report), "Diagnostics expose the board API key")
        for name in TOURNAMENT_PLAYERS:
            check(
                name not in json.dumps(report), f"Diagnostics expose the player {name}"
            )
        check(TLS_KEY not in json.dumps(report), "Diagnostics expose the TLS key")
        check(BOARD_ID not in json.dumps(data), "Diagnostics expose the board ID")
        check("Alex" not in json.dumps(report), "Diagnostics expose a player name")
        check(
            data["local_available"] is True
            and data["realtime_connected"] is True
            and data["cloud_configured"] is False,
            f"Unexpected diagnostics summary: {data}",
        )

    async def logs(self) -> None:
        problems = [
            item
            for item in await self.ws("system_log/list")
            if (
                item["level"] in ("ERROR", "CRITICAL")
                or item["name"].startswith("custom_components.autodarts")
            )
            and not any(
                expected in " ".join(item["message"]) for expected in EXPECTED_LOGS
            )
        ]
        check(not problems, f"Home Assistant logged problems: {problems}")
        log = LOG.read_text() if LOG.exists() else ""
        check(API_KEY not in log, "Home Assistant log contains the board API key")
        check(TLS_KEY not in log, "Home Assistant log contains the TLS key")
        check(
            self.webhook_id is not None and self.webhook_id not in log,
            "Home Assistant log contains the webhook address",
        )
        # Records start with a timestamp; the outage of the fault injection logs
        # its cause at debug level, every other traceback is a problem.
        records = re.split(r"\n(?=\d{4}-\d{2}-\d{2} )", log)
        tracebacks = [
            record
            for record in records
            if "Traceback" in record and EXPECTED_TRACEBACK not in record
        ]
        check(not tracebacks, f"Home Assistant log contains tracebacks: {tracebacks}")

        board = await self.board("GET", "/control/requests")
        check(
            not board["unexpected"],
            f"Unexpected Board Manager calls: {board['unexpected']}",
        )

    async def remove(self, entry_id: str) -> None:
        await self.api("DELETE", f"/api/config/config_entries/entry/{entry_id}")

        async def disconnected():
            return (await self.board("GET", "/control/requests"))["sockets"] == 0

        await wait_for(disconnected, "the board socket to close after removal")
        remaining = [
            item
            for item in await self.ws("config/entity_registry/list")
            if item["platform"] == "autodarts"
        ]
        check(not remaining, f"Entities remain after removal: {remaining}")
        for store in ("training", "report", "journal"):
            check(
                not Path(f"/config/.storage/autodarts.{entry_id}.{store}").exists(),
                f"The {store} store was not deleted with the integration",
            )


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        scenario = Scenario(session)
        await scenario.onboard()
        await scenario.connect()
        entry_id = await scenario.setup()
        await scenario.registries(entry_id)
        await scenario.initial_state()
        await scenario.controls()
        await scenario.realtime(entry_id)
        await scenario.resilience(entry_id)
        await scenario.online_bridge(entry_id)
        await scenario.reports(entry_id)
        await scenario.games()
        await scenario.achievements()
        await scenario.match_summary()
        await scenario.card()
        await scenario.people()
        await scenario.gallery()
        await scenario.tournament()
        await scenario.diagnostics(entry_id)
        await scenario.logs()
        await scenario.remove(entry_id)
        await scenario.socket.close()
    print(
        f"Docker E2E passed for Board Manager {GENERATION}: onboarding, "
        + ("mDNS discovery, " if GENERATION >= 2 else "")
        + "local config flow and validation, registries, "
        "controls, realtime darts/corrections/takeouts with positions, persistence, "
        "dropped sockets mid-visit, outages, failing and slow reads, malformed "
        "frames, a restart, the online bridge, weekly report, training calendar, "
        "exports, Golf, Tactics and a team match with start scores, an achievement "
        "with dart positions, a match "
        "summary, double out from the next leg, dashboard card, players linked to "
        "persons, the highlight gallery in the media browser, a round robin "
        "tournament, private diagnostics, clean logs and removal."
    )


if __name__ == "__main__":
    asyncio.run(main())
