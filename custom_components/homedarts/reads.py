"""The reads of a board besides its state, and how they recover.

Board Manager 2 reports everything in one read, /api/system; Board Manager 1
in a read for each value, and its settings and version every half minute. A
read that fails keeps the last value, a route the board lacks reads as empty,
and an answer in an unknown format counts until a repair issue asks for an
update of the integration. BoardReads asks the board's generation which reads
apply and tells it what the board answers, see BoardGeneration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Coroutine
from typing import Any

from .errors import AutodartsApiError
from .generation import BoardGeneration
from .local_api import (
    AutodartsEndpointMissing,
    AutodartsLocalClient,
    AutodartsProtocolError,
)

_LOGGER = logging.getLogger(__name__)
# Board Manager 1 reports its settings and version in separate reads.
METADATA_SECONDS = 30
# The board PC changes only with system or Board Manager updates.
HOST_REFRESH_SECONDS = 3600
# Unknown answers in a row to a required read before a repair notice appears.
PROTOCOL_FAILURES = 3
REQUIRED_PATHS = ("/api/state", "/api/config", "/api/system")
# What a failed read of /api/system leaves: every value as it was, including
# the metadata.
SYSTEM_READS = (
    "config",
    "version",
    "system",
    "stats",
    "camera_stats",
    "motion",
    "camera_state",
)


class BoardReads:
    """The reads of one board besides its state, see the module."""

    def __init__(
        self, client: AutodartsLocalClient, generation: BoardGeneration
    ) -> None:
        self.client = client
        self.generation = generation
        # When Board Manager 1 last reported its settings and version; 0 asks
        # for them with the next read.
        self.metadata_updated = 0.0
        # The board PC of Board Manager 2, read anew once an hour.
        self.host: dict[str, Any] | None = None
        self._host_updated = 0.0
        # Unknown answers in a row by read, and the reads that logged one.
        self.protocol_failures: dict[str, int] = {}
        self._protocol_logged: set[str] = set()

    def result(self, path: str, error: BaseException | None) -> None:
        """Count unknown answers per read; warn once for each read."""
        if not isinstance(error, AutodartsProtocolError):
            if error is None:
                self.protocol_failures.pop(path, None)
            return
        self.protocol_failures[path] = self.protocol_failures.get(path, 0) + 1
        if path not in self._protocol_logged:
            self._protocol_logged.add(path)
            _LOGGER.warning(
                "Board Manager answered %s in an unknown format; this Board Manager "
                "version may not be supported yet",
                path,
            )

    def failing(self) -> list[str]:
        """The required reads that keep answering in an unknown format."""
        return sorted(
            path
            for path, count in self.protocol_failures.items()
            if path in REQUIRED_PATHS and count >= PROTOCOL_FAILURES
        )

    async def optional(self, operation: Coroutine[Any, Any, Any], path: str) -> Any:
        """Unsupported endpoints read as empty; a failed read returns None."""
        try:
            result = await operation
        except AutodartsEndpointMissing:
            self.result(path, None)
            return {}
        except AutodartsApiError as err:
            self.result(path, err)
            return None
        self.result(path, None)
        return result

    async def _read_system(self) -> dict[str, Any] | None:
        """Board Manager 2 reports everything in one read; None if unsupported."""
        try:
            reads = await self.client.get_system()
        except AutodartsEndpointMissing:
            return None
        except AutodartsApiError as err:
            self.result("/api/system", err)
            # A failed read keeps every value, including the metadata.
            return dict.fromkeys(SYSTEM_READS)
        self.result("/api/system", None)
        return reads

    async def _read_legacy(self) -> dict[str, Any]:
        client = self.client
        stats, camera_stats, motion, camera_state = await asyncio.gather(
            self.optional(client.get_stats(), "/api/state/stats"),
            self.optional(client.get_camera_stats(), "/api/cams/stats"),
            self.optional(client.get_motion_state(), "/api/state/motion"),
            self.optional(client.get_camera_state(), "/api/cams/state"),
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
            not self.metadata_updated
            or time.monotonic() - self.metadata_updated >= METADATA_SECONDS
        ):
            # Marked before the read: a setting changed while the answer is on
            # its way resets the mark, so the next poll reads it again.
            self.metadata_updated = time.monotonic()
            reads["config"], reads["version"] = await asyncio.gather(
                self.optional(client.get_config(), "/api/config"),
                self.optional(client.get_version(), "/api/version"),
            )
        return reads

    async def read(self) -> dict[str, Any]:
        """Everything besides the state, in one read on Board Manager 2."""
        now = time.monotonic()
        generation = self.generation
        if generation.probe_due(now):
            # An unknown board reveals its generation through its version first.
            generation.probed(
                await self.optional(self.client.get_version(), "/api/version")
            )
        if not generation.board_manager_2 and await self._system_back(now):
            generation.system_back()
        if generation.board_manager_2:
            reads = await self._read_system()
            if reads is not None:
                generation.system_answered()
                return reads
            generation.system_missing(now)
        return await self._read_legacy()

    async def _system_back(self, now: float) -> bool:
        """Whether /api/system, found missing before, answers again."""
        if not self.generation.recheck_due(now):
            return False
        try:
            await self.client.get_system()
        except AutodartsApiError:
            return False
        return True

    async def read_host(self, version_changed: bool) -> None:
        """The board PC of Board Manager 2: with the first read, after an
        update of the Board Manager and once an hour."""
        if not self.generation.board_manager_2 or not (
            self.host is None
            or version_changed
            or time.monotonic() - self._host_updated >= HOST_REFRESH_SECONDS
        ):
            return
        # Boards without the endpoint answer {} and are asked again later.
        host = await self.optional(self.client.get_host(), "/api/host")
        if host is not None:
            self.host, self._host_updated = host, time.monotonic()
