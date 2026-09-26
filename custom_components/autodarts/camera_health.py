"""Detect sustained zero camera FPS without alarming on normal stops/standby."""

import math
from typing import Any

from .const import LIFECYCLE_STATUSES

CAMERA_FAILURE_SECONDS = 15


class CameraHealth:
    def __init__(self) -> None:
        self._zero_since: dict[int, float] = {}

    def update(self, data: dict[str, Any], now: float) -> list[bool | None]:
        count = data.get("settings", {}).get("camera_count", 0)
        state = data.get("local", {})
        camera_state = data.get("camera_state", {})
        fps = data.get("camera_stats", {}).get("fps", [])
        expected = (
            state.get("running") is True and camera_state.get("isRunning") is True
        )
        expected = (
            expected and str(state.get("status", "")).lower() not in LIFECYCLE_STATUSES
        )
        result: list[bool | None] = []
        for index in range(count):
            value = fps[index] if isinstance(fps, list) and index < len(fps) else None
            if not expected:
                self._zero_since.pop(index, None)
                result.append(
                    False
                    if state.get("running") is False
                    or isinstance(camera_state.get("isRunning"), bool)
                    else None
                )
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                self._zero_since.pop(index, None)
                result.append(None)
            elif value > 0:
                self._zero_since.pop(index, None)
                result.append(False)
            else:
                since = self._zero_since.setdefault(index, now)
                result.append(now - since >= CAMERA_FAILURE_SECONDS)
        self._zero_since = {
            index: value for index, value in self._zero_since.items() if index < count
        }
        return result
