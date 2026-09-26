"""Synthetic fixtures shaped like Board Manager 1.0.7 responses."""

from copy import deepcopy

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


def local_entry_data():
    return {
        "board_id": "board-1",
        "host": "192.0.2.10",
        "port": 3180,
        "local_only": True,
    }


def mock_board_v2(mock, *, system=None, state=None, host=None, base=BASE):
    """A Board Manager 2 board: /api/system instead of upstream routes."""
    mock.get(f"{base}/api/system", json=deepcopy(SYSTEM if system is None else system))
    mock.get(f"{base}/api/host", json=deepcopy(HOST if host is None else host))
    mock.put(f"{base}/api/upstream/connect", status=404)
    mock.put(f"{base}/api/upstream/disconnect", status=404)
    mock_board(mock, state=state, version="2.0.0", base=base)
