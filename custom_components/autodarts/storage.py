"""The stored training sessions, practice game and records of a board."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
# Raised with each change of the stored layout; every part restores older
# layouts itself, see _async_migrate_func. 2: version 1.6 added the progress,
# the tournament, the match summary and the bot. 3: the switch that frees a
# stuck takeout.
STORAGE_MINOR_VERSION = 3


def storage_key(entry_id: str) -> str:
    """The file in .storage that holds the training of an entry."""
    return f"{DOMAIN}.{entry_id}.training"


class TrainingStore(Store[dict[str, Any]]):
    """Kept private: player names and personal bests are stored with the darts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        super().__init__(
            hass,
            STORAGE_VERSION,
            storage_key(entry_id),
            private=True,
            minor_version=STORAGE_MINOR_VERSION,
        )

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Data of another minor version loads as it is.

        Every part restores older layouts and ignores fields it does not know,
        so data written by a newer release also loads after a downgrade; the
        coordinator keeps its unknown parts when it saves. Home Assistant
        refuses a newer major version before it calls this.
        """
        return old_data
