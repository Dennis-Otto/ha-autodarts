"""Readings of a board that change faster than the rest, and the entities that
show them.

The motion flags of the detection change several times per visit, the frame
rates and the load of the board PC with nearly every read. A change of them
alone tells only the entities of its topic, instead of every entity of the
board as an update of the coordinator does.
"""

from __future__ import annotations

import logging
from enum import StrEnum

from homeassistant.core import CALLBACK_TYPE, callback

_LOGGER = logging.getLogger(__name__)


class Topic(StrEnum):
    """A kind of reading, see AutodartsLocalCoordinator.readings."""

    # Frame rates and the board PC's load, which every poll reports anew.
    TELEMETRY = "telemetry"
    # A hand at the board, a stable image, a takeout.
    MOTION = "motion"
    # Whether the cameras run.
    CAMERA_STATE = "camera_state"


class BoardTopics:
    """The listeners of each topic; publishing a topic calls only its own."""

    def __init__(self) -> None:
        self._callbacks: dict[Topic, dict[int, CALLBACK_TYPE]] = {}
        self._last_id = 0

    @callback
    def async_add_listener(
        self, topic: Topic, update_callback: CALLBACK_TYPE
    ) -> CALLBACK_TYPE:
        """Call update_callback whenever topic is published, until the function
        this returns is called."""
        self._last_id += 1
        listener_id = self._last_id
        callbacks = self._callbacks.setdefault(topic, {})
        callbacks[listener_id] = update_callback

        @callback
        def remove() -> None:
            callbacks.pop(listener_id, None)

        return remove

    def listeners(self, topic: Topic) -> int:
        """How many listeners topic has."""
        return len(self._callbacks.get(topic, {}))

    @callback
    def async_publish(self, topic: Topic) -> None:
        """Tell the listeners of topic that its readings changed; one that
        fails leaves the others."""
        for update_callback in list(self._callbacks.get(topic, {}).values()):
            try:
                update_callback()
            except Exception:
                _LOGGER.exception("Unexpected error updating an entity of %s", topic)
