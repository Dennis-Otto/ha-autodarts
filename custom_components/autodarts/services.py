"""Actions of the integration: start a practice game or a tournament with one call,
correct and enter darts, pass the turn, undo a visit, and more."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

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
from homeassistant.helpers.service import (
    async_get_config_entry,
    async_register_admin_service,
)

from .bot import BOARD_MM, bed_name, segment_at, valid_level
from .const import DOMAIN
from .cricket import CRICKET_GAMES
from .export import EXPORT_CONTENTS, EXPORT_FORMATS, async_export
from .local_coordinator import AutodartsLocalCoordinator
from .manual import parse_bed
from .party import GOLF_HOLES, MAX_ROUNDS
from .positions import MAX_DISTANCE
from .practice import (
    GAME_OPTIONS,
    MAX_LEGS,
    MAX_PLAYERS,
    MAX_SETS,
    TEAM_PLAYERS,
    UNWINNABLE_START,
    PracticeGame,
    valid_start,
)
from .profiles import NAME_LENGTH, valid_name
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


# The longest bed name an error message repeats.
BED_ECHO = 20
# Numbers and beds are checked in the handlers, which explain a wrong value in
# the language of the user; the schemas only make them numbers and texts.
START_SCORES = vol.All(cv.ensure_list, [vol.Coerce(int)])
BED = vol.All(cv.string, vol.Length(min=1, max=255))


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
        vol.Optional("start_scores"): START_SCORES,
        vol.Optional("holes"): vol.All(vol.Coerce(int), vol.In(GOLF_HOLES)),
        vol.Optional("rounds"): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_ROUNDS)
        ),
        vol.Optional("bot_level"): vol.Coerce(int),
    }
)

# Where a dart is, as the board reports it: 1 is the outer edge of the double
# ring, and y points to the 20. The bed follows from it.
POSITION: dict[vol.Marker, Any] = {
    vol.Optional("x"): vol.Coerce(float),
    vol.Optional("y"): vol.Coerce(float),
}
CORRECT_DART_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("dart"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
        vol.Optional("segment"): BED,
        **POSITION,
    }
)
THROW_DART_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("segment"): BED,
        **POSITION,
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
        vol.Optional("start_scores"): START_SCORES,
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
        # Without a folder, the export goes to autodarts/exports of the media folder.
        vol.Optional("folder"): vol.All(cv.string, vol.Length(min=1, max=255)),
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


def _invalid(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


def _bed(value: str) -> dict[str, object]:
    """The dart in the named bed, or a translated error naming the bed."""
    dart = parse_bed(value)
    if dart is None:
        shown = "".join(
            char if char.isprintable() else "?" for char in value.strip()[:BED_ECHO]
        )
        raise _invalid("invalid_segment", segment=shown)
    return dart


def _position(data: Mapping[str, Any]) -> tuple[float, float] | None:
    """The position of an action, both coordinates or none, on the board or
    around it."""
    if "x" not in data and "y" not in data:
        return None
    x, y = data.get("x", math.nan), data.get("y", math.nan)
    if not all(math.isfinite(value) and abs(value) <= MAX_DISTANCE for value in (x, y)):
        raise _invalid("invalid_position", limit=f"{MAX_DISTANCE:g}")
    return x, y


def _dart_at(
    data: Mapping[str, Any],
) -> tuple[dict[str, object], tuple[float, float] | None]:
    """The dart of an action and where it is: the named bed, the bed at the
    position, or both when they agree."""
    position = _position(data)
    named = _bed(data["segment"]) if "segment" in data else None
    if position is None:
        if named is None:
            raise _invalid("no_bed")
        return named, None
    found = _bed(bed_name(*segment_at(position[0] * BOARD_MM, position[1] * BOARD_MM)))
    if named is not None and named["name"] != found["name"]:
        raise _invalid(
            "bed_position", segment=str(named["name"]), found=str(found["name"])
        )
    return found, position


def _check_names(names: list[str] | None) -> None:
    """Names without the characters no player name contains, such as { } % #,
    which templates of automations would run."""
    if not all(valid_name(name) for name in names or []):
        raise _invalid("invalid_player_name")


def _check_level(level: int) -> None:
    if not valid_level(level):
        raise _invalid("invalid_bot_level")


def _check_starts(
    starts: list[int] | None,
    seats: int,
    teams: bool = False,
    x01: bool = False,
    doubles: bool = False,
    current: list[int] | None = None,
) -> None:
    """Start scores of 0 or 2 to 1001, one per seat or, for teams, one per team;
    a start score of 3 cannot be won with double in and double out."""
    for start in starts or []:
        if not valid_start(start):
            raise _invalid("invalid_start_score")
    if starts is not None and teams and len(starts) > TEAM_PLAYERS // 2:
        raise _invalid("team_start_scores")
    if starts is not None and len(starts) > seats:
        raise _invalid(
            "too_many_start_scores", scores=str(len(starts)), players=str(seats)
        )
    # Unset start scores stay as they are; a team plays from its first player's.
    playing = (current or []) if starts is None else starts
    used = playing[: TEAM_PLAYERS // 2 if teams else seats]
    if x01 and doubles and UNWINNABLE_START in used:
        raise _invalid("unwinnable_start")


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


def _doubles(call: ServiceCall, practice: PracticeGame) -> bool:
    """Whether double in and double out both apply, as the call sets them or
    as they are."""
    return all(
        call.data.get(rule, getattr(practice, rule))
        for rule in ("double_in", "double_out")
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def start_game(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        game: str = call.data["game"]
        names: list[str] | None = call.data.get("players")
        practice = coordinator.practice
        level: int = call.data.get("bot_level", practice.bot_level)
        _check_names(names)
        _check_level(level)
        _check_players(
            game, names, practice.humans, call.data.get("teams") is True, level > 0
        )
        paired = game.isdigit() or game in CRICKET_GAMES
        # The bot's seat, after the players, has a start score, too.
        seats = (len(names) if names else practice.humans) + int(level > 0 and paired)
        _check_starts(
            call.data.get("start_scores"),
            seats,
            teams=paired
            and seats == TEAM_PLAYERS
            and bool(call.data.get("teams", practice.teams)),
            x01=game.isdigit(),
            current=list(practice.starts),
            doubles=_doubles(call, practice),
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
            call.data.get("folder"),
        )

    # Actions that forget or write out the players' data are for administrators;
    # automations and scripts, which run without a user, still use them.
    async_register_admin_service(
        hass, DOMAIN, SERVICE_DELETE_PLAYER, delete_player, schema=DELETE_PLAYER_SCHEMA
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_EXPORT,
        export,
        schema=EXPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def link_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        person: str = call.data["person"]
        _check_names([call.data["player"]])
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

    async_register_admin_service(
        hass, DOMAIN, SERVICE_LINK_PLAYER, link_player, schema=LINK_PLAYER_SCHEMA
    )
    async_register_admin_service(
        hass, DOMAIN, SERVICE_UNLINK_PLAYER, unlink_player, schema=UNLINK_PLAYER_SCHEMA
    )

    async def start_tournament(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        setup = coordinator.tournament.setup
        _check_names(call.data.get("players"))
        _check_starts(
            call.data.get("start_scores"),
            len(call.data.get("players", setup.players)),
            x01=str(call.data.get("game", setup.game)).isdigit(),
            doubles=_doubles(call, coordinator.practice),
        )
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
        dart, position = _dart_at(call.data)
        await coordinator.async_correct_dart(call.data["dart"], dart, position)

    async def throw_dart(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_throw_dart(*_dart_at(call.data))

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
