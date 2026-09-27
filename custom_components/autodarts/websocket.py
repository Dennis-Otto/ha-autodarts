"""Dart positions for the cards; thousands of them are too many for attributes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .local_coordinator import AutodartsLocalCoordinator
from .profiles import NAME_LENGTH


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_positions)


def _board(hass: HomeAssistant, device_id: str) -> AutodartsLocalCoordinator | None:
    """The local board of an Autodarts device, if it is loaded."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry in hass.config_entries.async_entries(DOMAIN):
        local: AutodartsLocalCoordinator | None = (
            entry.runtime_data.local if entry.state is ConfigEntryState.LOADED else None
        )
        if local and (DOMAIN, local.board_id) in device.identifiers:
            return local
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/positions",
        vol.Required("device_id"): str,
        vol.Optional("player"): vol.All(str, vol.Length(max=NAME_LENGTH)),
    }
)
@callback
def ws_positions(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The positions of the session's darts, or of a player's last darts."""
    board = _board(hass, msg["device_id"])
    if board is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No loaded Autodarts board"
        )
        return
    connection.send_result(msg["id"], board.progress.positions(msg.get("player")))
