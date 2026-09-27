"""Actions of the integration: start a practice game or a tournament with one call,
correct and enter darts, pass the turn, undo a visit, and more."""

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

from .bot import valid_level
from .const import DOMAIN
from .cricket import CRICKET_GAMES
from .export import DEFAULT_FOLDER, EXPORT_CONTENTS, EXPORT_FORMATS, async_export
from .local_coordinator import AutodartsLocalCoordinator
from .manual import parse_bed
from .party import GOLF_HOLES, MAX_ROUNDS
from .practice import (
    GAME_OPTIONS,
    MAX_LEGS,
    MAX_PLAYERS,
    MAX_SETS,
    TEAM_PLAYERS,
    valid_start,
)
from .profiles import NAME_LENGTH
from .tournament import (
    FORMATS,
    MAX_ENTRANTS,
    MAX_PAUSE,
    MAX_SEED,
    MAX_SUMMARY,
    MIN_ENTRANTS,
    RULES,
    TOURNAMENT_GAMES,
)

SERVICE_START_GAME = "start_game"
SERVICE_DELETE_PLAYER = "delete_player"
SERVICE_EXPORT = "export"
SERVICE_START_TOURNAMENT = "start_tournament"
SERVICE_STOP_TOURNAMENT = "stop_tournament"
SERVICE_NEXT_TOURNAMENT_MATCH = "next_tournament_match"
SERVICE_CORRECT_DART = "correct_dart"
SERVICE_THROW_DART = "throw_dart"
SERVICE_NEXT_PLAYER = "next_player"
SERVICE_UNDO_VISIT = "undo_visit"


def _start_score(value: object) -> int:
    """0 for the game's start score, or a start score of 2 to 1001."""
    start = vol.Coerce(int)(value)
    if not valid_start(start):
        raise vol.Invalid("a start score is 0 or 2 to 1001")
    return int(start)


def _bot_level(value: object) -> int:
    """0 without the bot, or its 3-dart average of 20 to 120."""
    level = vol.Coerce(int)(value)
    if not valid_level(level):
        raise vol.Invalid("a bot level is 0 or 20 to 120")
    return int(level)


def _bed(value: object) -> dict[str, object]:
    """S1 to S20, D1 to D20, T1 to T20, 25, BULL or MISS, in any case."""
    dart = parse_bed(cv.string(value))
    if dart is None:
        raise vol.Invalid("a bed is S1 to T20, 25, BULL or MISS, for example T20")
    return dart


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
        vol.Optional("teams"): cv.boolean,
        vol.Optional("start_scores"): vol.All(
            cv.ensure_list, [_start_score], vol.Length(max=MAX_PLAYERS)
        ),
        vol.Optional("holes"): vol.All(vol.Coerce(int), vol.In(GOLF_HOLES)),
        vol.Optional("rounds"): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_ROUNDS)
        ),
        vol.Optional("bot_level"): _bot_level,
    }
)

CORRECT_DART_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("dart"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
        vol.Required("segment"): _bed,
    }
)
THROW_DART_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("segment"): _bed,
    }
)


START_TOURNAMENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("players"): vol.All(
            cv.ensure_list,
            [vol.All(cv.string, vol.Length(max=NAME_LENGTH))],
            vol.Length(min=MIN_ENTRANTS, max=MAX_ENTRANTS),
        ),
        vol.Optional("start_scores"): vol.All(
            cv.ensure_list, [_start_score], vol.Length(max=MAX_ENTRANTS)
        ),
        vol.Optional("format"): vol.All(cv.string, vol.In(FORMATS)),
        vol.Optional("game"): vol.All(cv.string, vol.In(TOURNAMENT_GAMES)),
        vol.Optional("legs"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_LEGS)),
        vol.Optional("sets"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SETS)),
        **{vol.Optional(rule): cv.boolean for rule in RULES},
        vol.Optional("third_place"): cv.boolean,
        vol.Optional("random_draw"): cv.boolean,
        vol.Optional("seed"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SEED)),
        vol.Optional("pause"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=MAX_PAUSE)
        ),
        vol.Optional("summary"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=MAX_SUMMARY)
        ),
    }
)

# Actions that only name the board.
BOARD_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})


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


def _check_players(
    game: str,
    names: list[str] | None,
    players: int,
    teams: bool = False,
    bot: bool = False,
) -> None:
    """Every player needs a name of their own, Killer two players and teams
    four players of X01 or a Cricket game; the bot takes a seat of its own."""
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
    count = len(names) if names else players
    if bot and (game.isdigit() or game in CRICKET_GAMES):
        if count >= MAX_PLAYERS:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="bot_seat"
            )
        count += 1
    if game == "killer" and count < 2:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="killer_players"
        )
    if teams and not (game.isdigit() or game in CRICKET_GAMES):
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="team_game"
        )
    if teams and count != TEAM_PLAYERS:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="team_players"
        )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def start_game(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        game: str = call.data["game"]
        names: list[str] | None = call.data.get("players")
        practice = coordinator.practice
        level: int = call.data.get("bot_level", practice.bot_level)
        _check_players(
            game,
            names,
            practice.humans,
            call.data.get("teams") is True,
            level > 0,
        )
        await coordinator.async_start_game(
            int(game) if game.isdigit() else game,
            names=names,
            legs=call.data.get("legs"),
            sets=call.data.get("sets"),
            double_out=call.data.get("double_out"),
            double_in=call.data.get("double_in"),
            bull_off=call.data.get("bull_off"),
            bull_off_distance=call.data.get("bull_off_distance"),
            teams=call.data.get("teams"),
            start_scores=call.data.get("start_scores"),
            holes=call.data.get("holes"),
            rounds=call.data.get("rounds"),
            bot_level=call.data.get("bot_level"),
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

    async def start_tournament(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        options = {
            key: value
            for key, value in call.data.items()
            if key != ATTR_CONFIG_ENTRY_ID
        }
        rules = {rule: options.pop(rule, None) for rule in RULES}
        await coordinator.async_start_tournament(rules=rules, **options)

    async def stop_tournament(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_stop_tournament()

    async def next_tournament_match(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_next_tournament_match()

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_TOURNAMENT,
        start_tournament,
        schema=START_TOURNAMENT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_TOURNAMENT, stop_tournament, schema=BOARD_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NEXT_TOURNAMENT_MATCH,
        next_tournament_match,
        schema=BOARD_SCHEMA,
    )

    async def correct_dart(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_correct_dart(call.data["dart"], call.data["segment"])

    async def throw_dart(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_throw_dart(call.data["segment"])

    async def next_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_next_player()

    async def undo_visit(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_undo_visit()

    for name, handler, schema in (
        (SERVICE_CORRECT_DART, correct_dart, CORRECT_DART_SCHEMA),
        (SERVICE_THROW_DART, throw_dart, THROW_DART_SCHEMA),
        (SERVICE_NEXT_PLAYER, next_player, BOARD_SCHEMA),
        (SERVICE_UNDO_VISIT, undo_visit, BOARD_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
