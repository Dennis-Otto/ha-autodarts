"""Deterministic Board Manager double for the Docker end-to-end test.

Serves the local HTTP and WebSocket protocol used by the integration, records every
write command and rejects routes the integration is not expected to call.
BOARD_MANAGER=2 switches to the headless Board Manager 2: /api/system, no
upstream routes, and an mDNS announcement like the real board.

POST /control/fault injects the faults of a real network and board: dropped or
refused sockets, failing or slow reads, malformed frames and restarts.
"""

from __future__ import annotations

import asyncio
import copy
import os
import socket
import time

from aiohttp import WSCloseCode, WSMsgType, web

BOARD_ID = "e2e-board"
# Synthetic secret: it must never reach Home Assistant state, diagnostics or logs.
API_KEY = "e2e-only-board-api-key"
TLS_KEY = "e2e-only-tls-key"
PORT = 3180
GENERATION = int(os.environ.get("BOARD_MANAGER", "1"))
VERSION = "2.0.0" if GENERATION >= 2 else "1.0.7"
UPDATE = "2.0.2"
V1_ONLY = {("PUT", "/api/upstream/connect"), ("PUT", "/api/upstream/disconnect")}

COMMANDS = {
    ("PUT", "/api/start"): {"running": True, "status": "Throw", "event": "Started"},
    ("PUT", "/api/stop"): {"running": False, "status": "Stopped", "event": "Stopped"},
    ("POST", "/api/reset"): {"numThrows": 0, "throws": []},
    ("POST", "/api/restart"): {},
    ("POST", "/api/config/calibration/auto"): {},
    ("PUT", "/api/upstream/connect"): {"connected": True},
    ("PUT", "/api/upstream/disconnect"): {"connected": False},
    ("PUT", "/api/streams/start"): {},
    ("PUT", "/api/streams/stop"): {},
}


class Board:
    def __init__(self) -> None:
        self.state = {
            "connected": True,
            "running": False,
            "status": "Stopped",
            "event": "Stopped",
            "numThrows": 0,
            "throws": [],
        }
        self.config = {
            "auth": {"board_id": BOARD_ID, "api_key": API_KEY},
            "cam": {
                "cams": ["/dev/video0", "/dev/video2", "/dev/video4"],
                "width": 1280,
                "height": 1024,
                "fps": 30,
                "auto_calibrate_on_start": True,
                "auto_calibrate": True,
                "auto_distortion": False,
            },
            "motion": {"standby_minutes": 15},
        }
        self.commands: list[dict] = []
        self.unexpected: list[str] = []
        # Reads by path, so a test can tell when an injected fault was read.
        self.reads: dict[str, int] = {}
        self.sockets: set[web.WebSocketResponse] = set()
        self.clear_faults()

    def clear_faults(self) -> None:
        # Refused sockets, failing or slow reads and a restart in progress.
        self.refuse_sockets = False
        self.http_status: int | None = None
        self.delay = 0.0
        self.fault_paths: list[str] | None = None
        self.fault_count: int | None = None
        self.down_until = 0.0

    def read_fault(self, path: str) -> tuple[int | None, float]:
        """The status and delay a read gets; a counted fault is used up."""
        if time.monotonic() < self.down_until:
            return 503, 0.0
        if self.fault_paths is not None and path not in self.fault_paths:
            return None, 0.0
        if self.fault_count is not None:
            if self.fault_count <= 0:
                return None, 0.0
            self.fault_count -= 1
        return self.http_status, self.delay

    async def drop_sockets(self) -> None:
        for client in list(self.sockets):
            await client.close(code=WSCloseCode.GOING_AWAY)

    async def send_raw(self, frame: str | bytes) -> None:
        for client in list(self.sockets):
            if isinstance(frame, bytes):
                await client.send_bytes(frame)
            else:
                await client.send_str(frame)

    async def record(self, request: web.Request) -> None:
        body = await request.json() if request.can_read_body else None
        self.commands.append(
            {"method": request.method, "path": request.path_qs, "body": body}
        )

    async def publish(self, changes: dict) -> None:
        self.state.update(changes)
        self.state["numThrows"] = len(self.state["throws"])
        for client in list(self.sockets):
            await client.send_json({"type": "state", "data": self.state})


def routes(board: Board) -> web.RouteTableDef:
    api = web.RouteTableDef()

    @api.get("/health")
    async def health(request):
        return web.Response(text="ok")

    @api.get("/api/state")
    async def state(request):
        return web.json_response(board.state)

    @api.get("/api/config")
    async def config(request):
        return web.json_response(board.config)

    @api.patch("/api/config")
    async def patch_config(request):
        await board.record(request)
        for section, values in (await request.json()).items():
            board.config[section].update(values)
        # The real Board Manager echoes its full configuration, including the key.
        return web.json_response(board.config)

    @api.get("/api/version")
    async def version(request):
        return web.Response(text=f"{VERSION}\n")

    @api.get("/api/state/stats")
    async def stats(request):
        return web.json_response({"fps": 12.5 if board.state["running"] else 0.0})

    @api.get("/api/cams/stats")
    async def camera_stats(request):
        fps = 30.0 if board.state["running"] else 0.0
        return web.json_response({"fps": [fps] * len(board.config["cam"]["cams"])})

    @api.get("/api/cams/state")
    async def camera_state(request):
        running = board.state["running"]
        return web.json_response({"isRunning": running, "isOpened": running})

    @api.get("/api/state/motion")
    async def motion(request):
        return web.json_response(
            {
                "isWaiting": False,
                "isStable": True,
                "isDart": False,
                "isHand": False,
                "isTakeoutPartial": False,
                "isTakeoutFull": False,
            }
        )

    @api.post("/api/config/calibration/auto/{index:\\d+}")
    async def calibrate_camera(request):
        await board.record(request)
        return web.json_response({})

    async def system(request):
        running = board.state["running"]
        fps = 30.0 if running else 0.0
        cams = board.config["cam"]["cams"]
        config = copy.deepcopy(board.config)
        config["host"] = {"port": str(PORT), "tls_key": TLS_KEY, "tls_cert": ""}
        return web.json_response(
            {
                "state": {k: board.state[k] for k in ("connected", "event", "running")}
                | {"numThrows": board.state["numThrows"]},
                "config": config,
                "stats": {
                    "cpuPercent": 7.5,
                    "fps": 12.5 if running else 0.0,
                    "memoryBytes": 268435456,
                },
                "camStats": [{"fps": fps, "id": index} for index in range(len(cams))],
                "camState": {"isRunning": running, "isOpened": running},
                "motion": {
                    "isStable": True,
                    "isHand": False,
                    "isTakeoutPartial": False,
                    "isTakeoutFull": False,
                    "camStates": [],
                },
                "link": "connected" if board.state["connected"] else "disconnected",
                "version": VERSION,
                "updateAvailable": UPDATE,
                "calibrated": True,
                "blocker": "none",
            }
        )

    async def host(request):
        # Like the real board PC, including the details the integration drops.
        return web.json_response(
            {
                "os": "linux",
                "platform": "debian",
                "platformVersion": "13",
                "kernelArch": "x86_64",
                "kernelVersion": "6.12.107+deb13-amd64",
                "cpu": {
                    "cores": 4,
                    "mhz": 3400.4,
                    "model": "Intel(R) Core(TM) i3-9100T",
                },
                "visionVersion": VERSION,
                "openCVVersion": "5.0.0",
                "clientVersion": VERSION,
                "hostname": "e2e-dartboard",
                "ip": "192.0.2.99",
                "cam1": {"name": "E2E Camera", "pid": "0001", "vid": "0002"},
            }
        )

    if GENERATION >= 2:
        api.get("/api/system")(system)
        api.get("/api/host")(host)

    @api.get("/api/events")
    async def events(request):
        if board.refuse_sockets or time.monotonic() < board.down_until:
            raise web.HTTPServiceUnavailable
        websocket = web.WebSocketResponse()
        await websocket.prepare(request)
        board.sockets.add(websocket)
        try:
            async for message in websocket:
                if message.type == WSMsgType.ERROR:
                    break
        finally:
            board.sockets.discard(websocket)
        return websocket

    @api.post("/control/state")
    async def control_state(request):
        await board.publish(await request.json())
        return web.json_response(board.state)

    @api.post("/control/fault")
    async def control_fault(request):
        fault = await request.json()
        if fault.get("clear"):
            board.clear_faults()
        if "refuse_sockets" in fault:
            board.refuse_sockets = fault["refuse_sockets"]
        if "http_status" in fault or "delay" in fault:
            board.http_status = fault.get("http_status")
            board.delay = fault.get("delay", 0.0)
            board.fault_paths = fault.get("paths")
            board.fault_count = fault.get("count")
        if restart := fault.get("restart"):
            # Down for a few seconds, like the Board Manager after a restart.
            board.down_until = time.monotonic() + restart
        if fault.get("drop_sockets") or fault.get("restart"):
            await board.drop_sockets()
        if "frame" in fault:
            await board.send_raw(fault["frame"])
        if fault.get("binary"):
            await board.send_raw(b"\x00\x01")
        return web.json_response({"sockets": len(board.sockets)})

    @api.get("/control/requests")
    async def control_requests(request):
        return web.json_response(
            {
                "commands": board.commands,
                "unexpected": board.unexpected,
                "sockets": len(board.sockets),
                "reads": board.reads,
                # Counted faults not yet used up; None without a counted fault.
                "faults_left": board.fault_count,
            }
        )

    return api


def fault_injection(board: Board):
    """Reads of the Board Manager API fail or answer slowly while a fault is set."""

    @web.middleware
    async def middleware(request, handler):
        # The socket has faults of its own: dropped or refused connections.
        if (
            request.method == "GET"
            and request.path.startswith("/api/")
            and request.path != "/api/events"
        ):
            board.reads[request.path] = board.reads.get(request.path, 0) + 1
            status, delay = board.read_fault(request.path)
            if delay:
                await asyncio.sleep(delay)
            if status:
                return web.Response(status=status, text="injected fault")
        return await handler(request)

    return middleware


def create_app() -> web.Application:
    board = Board()
    app = web.Application(middlewares=[fault_injection(board)])
    app.add_routes(routes(board))

    for (method, path), changes in COMMANDS.items():
        if GENERATION >= 2 and (method, path) in V1_ONLY:
            continue  # Board Manager 2 has no upstream routes.

        async def command(request, changes=changes):
            await board.record(request)
            if changes:
                await board.publish(copy.deepcopy(changes))
            return web.json_response({})

        app.router.add_route(method, path, command)

    async def unexpected(request):
        board.unexpected.append(f"{request.method} {request.path_qs}")
        raise web.HTTPNotFound

    # Registered last, so only routes without a Board Manager double end here.
    app.router.add_route("*", "/{tail:.*}", unexpected)
    return app


async def announce(app: web.Application) -> None:
    """Board Manager 2 announces itself on the LAN like the real board."""
    from zeroconf import ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf

    address = socket.gethostbyname(socket.gethostname())
    zeroconf = AsyncZeroconf(interfaces=[address])
    info = ServiceInfo(
        "_autodarts-board._tcp.local.",
        "autodarts-board._autodarts-board._tcp.local.",
        addresses=[socket.inet_aton(address)],
        port=PORT,
        properties={"id": "e2e0000000000001", "ip": address, "cams": "3"},
        server="autodarts-e2e.local.",
    )
    await zeroconf.async_register_service(info)

    async def withdraw(app: web.Application) -> None:
        await zeroconf.async_unregister_service(info)
        await zeroconf.async_close()

    app.on_cleanup.append(withdraw)


if __name__ == "__main__":
    app = create_app()
    if GENERATION >= 2:
        app.on_startup.append(announce)
    web.run_app(app, port=PORT, print=None)
