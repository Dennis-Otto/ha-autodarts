"""Actions of the integration: start a practice game with one call."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_get_config_entry

from .const import DOMAIN
from .local_coordinator import AutodartsLocalCoordinator
from .practice import GAME_OPTIONS, MAX_LEGS, MAX_PLAYERS, MAX_SETS
from .profiles import NAME_LENGTH

SERVICE_START_GAME = "start_game"
SERVICE_DELETE_PLAYER = "delete_player"

START_GAME_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("game"): vol.All(cv.string, vol.In(GAME_OPTIONS)),
        vol.Optional("players"): vol.All(
            cv.ensure_list,
            [vol.All(cv.string, vol.Length(max=NAME_LENGTH))],
            vol.Length(min=1, max=MAX_PLAYERS),
        ),
        vol.Optional("legs"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_LEGS)),
        vol.Optional("sets"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SETS)),
        vol.Optional("double_out"): cv.boolean,
        vol.Optional("double_in"): cv.boolean,
        vol.Optional("bull_off"): cv.boolean,
        vol.Optional("bull_off_distance"): cv.boolean,
    }
)


DELETE_PLAYER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=NAME_LENGTH)),
    }
)


def _coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> AutodartsLocalCoordinator:
    """The board of the given entry, or the only local board there is."""
    if entry_id:
        # Home Assistant explains an unknown, foreign or unloaded entry itself.
        entries = [async_get_config_entry(hass, DOMAIN, entry_id)]
    else:
        # Entries without a local board, or not loaded, are no candidates.
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
    boards: list[AutodartsLocalCoordinator] = [
        entry.runtime_data.local for entry in entries if entry.runtime_data.local
    ]
    if not boards:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_board"
        )
    if len(boards) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="several_boards"
        )
    return boards[0]


def _check_players(game: str, names: list[str] | None, players: int) -> None:
    """Every player needs a name of their own, and Killer two players."""
    seen: set[str] = set()
    for name in names or []:
        key = name.strip().casefold()
        if key in seen:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="duplicate_player",
                translation_placeholders={"name": name.strip()},
            )
        if key:
            seen.add(key)
    if game == "killer" and (len(names) if names else players) < 2:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="killer_players"
        )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def start_game(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        game: str = call.data["game"]
        names: list[str] | None = call.data.get("players")
        _check_players(game, names, len(coordinator.practice.players))
        await coordinator.async_start_game(
            int(game) if game.isdigit() else game,
            names=names,
            legs=call.data.get("legs"),
            sets=call.data.get("sets"),
            double_out=call.data.get("double_out"),
            double_in=call.data.get("double_in"),
            bull_off=call.data.get("bull_off"),
            bull_off_distance=call.data.get("bull_off_distance"),
        )

    async def delete_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        if not await coordinator.async_delete_player(call.data["name"]):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_player",
                translation_placeholders={"name": call.data["name"]},
            )

    hass.services.async_register(
        DOMAIN, SERVICE_START_GAME, start_game, schema=START_GAME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_PLAYER, delete_player, schema=DELETE_PLAYER_SCHEMA
    )
