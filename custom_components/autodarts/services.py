"""Actions of the integration: start a practice game with one call, and more."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_get_config_entry

from .const import DOMAIN
from .export import DEFAULT_FOLDER, EXPORT_CONTENTS, EXPORT_FORMATS, async_export
from .local_coordinator import AutodartsLocalCoordinator
from .practice import GAME_OPTIONS, MAX_LEGS, MAX_PLAYERS, MAX_SETS
from .profiles import NAME_LENGTH

SERVICE_START_GAME = "start_game"
SERVICE_DELETE_PLAYER = "delete_player"
SERVICE_EXPORT = "export"

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

# A player name as the profiles know it: trimmed, never empty.
PLAYER_NAME = vol.All(cv.string, vol.Strip, vol.Length(min=1, max=NAME_LENGTH))
SERVICE_LINK_PLAYER = "link_player"
SERVICE_UNLINK_PLAYER = "unlink_player"
LINK_PLAYER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("player"): PLAYER_NAME,
        vol.Required("person"): cv.entity_domain("person"),
    }
)
UNLINK_PLAYER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("player"): PLAYER_NAME,
    }
)


EXPORT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("format", default="csv"): vol.In(EXPORT_FORMATS),
        vol.Optional("what", default="all"): vol.In(EXPORT_CONTENTS),
        vol.Optional("folder", default=DEFAULT_FOLDER): vol.All(
            cv.string, vol.Length(min=1, max=255)
        ),
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

    async def export(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        return await async_export(
            hass,
            coordinator,
            call.data["format"],
            call.data["what"],
            call.data["folder"],
        )

    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_PLAYER, delete_player, schema=DELETE_PLAYER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT,
        export,
        schema=EXPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def link_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        person: str = call.data["person"]
        if hass.states.get(person) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_person",
                translation_placeholders={"person": person},
            )
        await coordinator.async_link_player(call.data["player"], person)

    async def unlink_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        if not await coordinator.async_link_player(call.data["player"], None):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_player",
                translation_placeholders={"name": call.data["player"]},
            )

    hass.services.async_register(
        DOMAIN, SERVICE_LINK_PLAYER, link_player, schema=LINK_PLAYER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNLINK_PLAYER, unlink_player, schema=UNLINK_PLAYER_SCHEMA
    )
