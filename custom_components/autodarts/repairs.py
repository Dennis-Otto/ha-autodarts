"""Repairs the integration can fix itself: calibrate, or follow a moved board."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import (
    ConfirmRepairFlow,
    RepairsFlow,
    RepairsFlowResult,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

from .const import CONF_BOARD_ID, CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .errors import AutodartsApiError
from .local_api import AutodartsLocalClient


def address_title(entry: ConfigEntry, host: str) -> str:
    """The entry's title at a new address: a title that named the old address
    names the new one; a board's name stays."""
    old = entry.data.get(CONF_HOST)
    if old and entry.title == f"Autodarts ({old})":
        return f"Autodarts ({host})"
    return entry.title


def _address(host: str, port: int) -> str:
    return str(URL.build(scheme="http", host=host, port=port))


@callback
def async_offer_address(
    hass: HomeAssistant, entry: ConfigEntry, host: str, port: int
) -> None:
    """A board with the entry's board ID answers at another address. Any device
    can claim a board ID, so the entry moves only once the user confirms."""
    old = entry.data.get(CONF_HOST)
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"board_moved_{entry.entry_id}",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="board_moved",
        translation_placeholders={
            "old": _address(old, entry.data.get(CONF_PORT, DEFAULT_PORT))
            if old
            else "",
            "new": _address(host, port),
        },
        data={"entry_id": entry.entry_id, "host": host, "port": port},
    )


class CalibrationFlow(RepairsFlow):
    """Many corrected darts: calibrate once the board is empty."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        if user_input is None:
            issue = ir.async_get(self.hass).async_get_issue(DOMAIN, self.issue_id)
            return self.async_show_form(
                step_id="confirm",
                description_placeholders=issue.translation_placeholders
                if issue
                else None,
            )
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        loaded = entry is not None and entry.state is ConfigEntryState.LOADED
        coordinator = entry.runtime_data.local if entry and loaded else None
        if coordinator is None:
            return self.async_abort(reason="board_unavailable")
        try:
            await coordinator.async_recalibrate()
        except HomeAssistantError:
            return self.async_abort(reason="calibration_failed")
        return self.async_create_entry(data={})


class BoardMovedFlow(RepairsFlow):
    """The board answers at another address: switch to it once confirmed."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        entry = self.hass.config_entries.async_get_entry(
            str(self._data.get("entry_id", ""))
        )
        host, port = self._data.get("host"), self._data.get("port")
        if entry is None or not isinstance(host, str) or type(port) is not int:
            return self.async_abort(reason="board_unavailable")
        client = AutodartsLocalClient(host, port, async_get_clientsession(self.hass))
        if user_input is None:
            return self.async_show_form(
                step_id="confirm", description_placeholders={"new": client.base_url}
            )
        # The board may have moved again since the notice appeared.
        try:
            identity = await client.identify()
        except AutodartsApiError:
            return self.async_abort(reason="board_unavailable")
        if identity["board_id"] != entry.data[CONF_BOARD_ID]:
            return self.async_abort(reason="board_unavailable")
        self.hass.config_entries.async_update_entry(
            entry,
            title=address_title(entry, host),
            data={**entry.data, CONF_HOST: host, CONF_PORT: port},
        )
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """The flow of a fixable issue, named <issue>_<entry_id>."""
    data = data or {}
    if issue_id.startswith("board_moved_"):
        return BoardMovedFlow(data)
    if issue_id.startswith("calibration_"):
        return CalibrationFlow(str(data.get("entry_id", "")))
    # Only the issues above are fixable; any other one has nothing to confirm.
    return ConfirmRepairFlow()
