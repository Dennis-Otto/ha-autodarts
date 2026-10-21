"""Detection quality: how many of the recent darts the board had to correct."""

from __future__ import annotations

from collections import deque
from typing import Any

from .scoring import rate

# The last hundred darts decide; fewer than fifty say too little.
QUALITY_DARTS = 100
QUALITY_MINIMUM = 50
# A repair suggests to recalibrate from this share of corrected darts, and
# goes away again below the lower one.
RECALIBRATE_RATE = 20.0
RECOVERED_RATE = 10.0


class DetectionQuality:
    """Share of corrected darts among the last detected ones."""

    def __init__(self) -> None:
        self._darts: deque[bool] = deque(maxlen=QUALITY_DARTS)
        # Dart index in the visit -> running number of that detection.
        self._visit: dict[int, int] = {}
        self._count = 0

    def record(self, kind: str, attributes: dict[str, Any]) -> None:
        if kind == "visit_completed":
            self._visit.clear()
            return
        index = attributes.get("dart_index")
        if type(index) is not int:
            return
        if kind == "dart_detected" and (
            attributes.get("manual") or attributes.get("bot")
        ):
            # Darts entered by hand or thrown by the bot were never detected; a
            # correction by hand of a detected dart counts like one on the board.
            return
        if kind == "dart_detected":
            self._darts.append(False)
            self._count += 1
            self._visit[index] = self._count
        elif kind == "dart_corrected" and index in self._visit:
            position = len(self._darts) - 1 - (self._count - self._visit[index])
            if 0 <= position < len(self._darts):
                self._darts[position] = True

    def reset(self) -> None:
        """Start counting again, for example after a calibration."""
        self._darts.clear()
        self._visit.clear()

    @property
    def rate(self) -> float | None:
        return rate(sum(self._darts), len(self._darts))

    @property
    def enough(self) -> bool:
        return len(self._darts) >= QUALITY_MINIMUM

    def snapshot(self) -> dict[str, Any]:
        return {
            "rate": self.rate,
            "darts": len(self._darts),
            "corrected": sum(self._darts),
        }
