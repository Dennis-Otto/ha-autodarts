"""Dart positions for the cards, thousands of them too many for attributes, and
the sounds of a voice pack for the caller of the scoreboard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .games_coordinator import AutodartsGamesCoordinator
from .profiles import NAME_LENGTH
from .voices import PACK_LENGTH, async_voice_pack


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_positions)
    websocket_api.async_register_command(hass, ws_voice_pack)


def _board(hass: HomeAssistant, device_id: str) -> AutodartsGamesCoordinator | None:
    """The local board of an Autodarts device, if it is loaded."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for entry in hass.config_entries.async_entries(DOMAIN):
        local: AutodartsGamesCoordinator | None = (
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
        # Only the aim map asks for the aim model, the positions alone cost nothing.
        vol.Optional("aim", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_positions(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The positions of the session's darts, or of a player's last darts, and
    their aim model when asked."""
    board = _board(hass, msg["device_id"])
    if board is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No loaded Autodarts board"
        )
        return
    player = msg.get("player")
    aim = await board.async_aim(player) if msg["aim"] else None
    result = board.games.progress.positions(player)
    connection.send_result(msg["id"], result if aim is None else {**result, "aim": aim})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/voice_pack",
        vol.Required("pack"): vol.All(str, vol.Length(min=1, max=PACK_LENGTH)),
    }
)
@websocket_api.async_response
async def ws_voice_pack(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Every sound of a voice pack by its key, with the addresses the scoreboard
    loads them from with its login; not found for a pack without sounds."""
    sounds = await async_voice_pack(hass, msg["pack"])
    if not sounds:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No such voice pack"
        )
        return
    connection.send_result(msg["id"], {"pack": msg["pack"], "sounds": sounds})
