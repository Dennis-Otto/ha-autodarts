"""Actions of the integration: start a practice game or a tournament with one call,
correct and enter darts, pass the turn, undo a visit, and more."""

from __future__ import annotations

import math
import re
from collections.abc import Awaitable, Callable, Mapping
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
from homeassistant.helpers.translation import async_get_translations

from .bot import BOARD_MM, bed_name, segment_at, valid_level
from .const import DOMAIN
from .cricket import CRICKET_GAMES
from .export import EXPORT_CONTENTS, EXPORT_FORMATS, async_export
from .local_coordinator import AutodartsLocalCoordinator
from .manual import parse_bed
from .party import GOLF_HOLES, MAX_ROUNDS, PARTY_GAMES
from .positions import MAX_DISTANCE
from .practice import (
    GAME_OPTIONS,
    MAX_LEGS,
    MAX_PLAYERS,
    MAX_SETS,
    PARTY_PLAYERS,
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
from .voice import Turn, passed, spoken, undone
from .voice import dart as dart_said
from .voice import name as voice_name
from .voice import visit as visit_said

SERVICE_START_GAME = "start_game"
SERVICE_DELETE_PLAYER = "delete_player"
SERVICE_EXPORT = "export"
SERVICE_START_TOURNAMENT = "start_tournament"
SERVICE_STOP_TOURNAMENT = "stop_tournament"
SERVICE_NEXT_TOURNAMENT_MATCH = "next_tournament_match"
SERVICE_CORRECT_DART = "correct_dart"
SERVICE_THROW_DART = "throw_dart"
SERVICE_ENTER_VISIT = "enter_visit"
SERVICE_NEXT_PLAYER = "next_player"
SERVICE_UNDO_VISIT = "undo_visit"


# The longest bed name an error message repeats.
BED_ECHO = 20
# Numbers and beds are checked in the handlers, which explain a wrong value in
# the language of the user; the schemas only make them numbers and texts.
START_SCORES = vol.All(cv.ensure_list, [vol.Coerce(int)])
BED = vol.All(cv.string, vol.Length(min=1, max=255))


# The languages of the integration: a game's name in any of them names the game.
LANGUAGES = ("en", "de", "es", "fr", "nl")
# A game's name as a voice assistant hears it is never longer.
GAME_TEXT = 64

START_GAME_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("game"): vol.All(
            vol.Coerce(str), vol.Length(min=1, max=GAME_TEXT)
        ),
        vol.Optional("players"): vol.All(
            cv.ensure_list,
            [vol.All(cv.string, vol.Length(max=NAME_LENGTH))],
            vol.Length(min=1, max=PARTY_PLAYERS),
        ),
        vol.Optional("legs"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_LEGS)),
        vol.Optional("sets"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_SETS)),
        vol.Optional("double_out"): cv.boolean,
        vol.Optional("double_in"): cv.boolean,
        vol.Optional("bull_off"): cv.boolean,
        vol.Optional("bull_off_distance"): cv.boolean,
        vol.Optional("teams"): cv.boolean,
        vol.Optional("three_in_a_bed"): cv.boolean,
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
# The player an entry is for, as a voice assistant names them: the action refuses
# the entry while another player is at the board.
TURN: dict[vol.Marker, Any] = {
    vol.Optional("player"): vol.All(
        cv.string, vol.Strip, vol.Length(min=1, max=NAME_LENGTH)
    ),
}
THROW_DART_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("segment"): BED,
        **POSITION,
        **TURN,
    }
)


# An X01 visit by its score, or as the checkout of what the player has left: the
# darts it took and those at a double.
ENTER_VISIT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("score"): vol.All(vol.Coerce(int), vol.Range(min=0, max=180)),
        vol.Optional("checkout"): cv.boolean,
        **TURN,
        vol.Optional("darts"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
        vol.Optional("darts_at_double"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3)
        ),
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


def _plain(text: str) -> str:
    """A name as it is spoken: without case, spaces and punctuation."""
    return re.sub(r"[\W_]+", "", text.casefold())


async def _game_key(hass: HomeAssistant, game: str) -> str:
    """The game an action names: its key, such as 501 or around_the_clock, or its
    name in a language of the integration as a voice assistant hears it, such as
    "Around the Clock", "Bobs 27" or "Doppeltraining". The beginning of a name
    is enough where it fits one game alone, such as "Cut Throat"."""
    if game in GAME_OPTIONS:
        return game
    names = {key: {_plain(key)} for key in GAME_OPTIONS}
    for language in LANGUAGES:
        texts = await async_get_translations(hass, language, "entity", {DOMAIN})
        for key in GAME_OPTIONS:
            # Home Assistant fills a missing translation with the English one.
            name = texts[f"component.{DOMAIN}.entity.select.practice_game.state.{key}"]
            names[key].add(_plain(name))
    wanted = _plain(game)
    same = {key for key, spoken in names.items() if wanted in spoken}
    begun = {
        key
        for key, spoken in names.items()
        if len(wanted) >= 3 and any(name.startswith(wanted) for name in spoken)
    }
    for found in (same, begun):
        if len(found) == 1:
            return found.pop()
    raise _invalid("unknown_game", game=game)


async def _game_on(hass: HomeAssistant, key: str, practice: PracticeGame) -> str:
    """What a voice assistant says when a game starts: the game and who plays it."""
    texts = await async_get_translations(hass, hass.config.language, "entity", {DOMAIN})
    game = texts.get(f"component.{DOMAIN}.entity.select.practice_game.state.{key}", key)
    players = [name for name in practice.names[: practice.humans] if name]
    if practice.bot_seat is not None:
        players.append(await spoken(hass, "voice_bot"))
    if not players:
        return await spoken(hass, "voice_game_on_alone", game=game)
    conjunction = await spoken(hass, "voice_and")
    last = f" {conjunction} "
    together = last.join(
        [", ".join(players[:-1]), players[-1]] if len(players) > 1 else players
    )
    return await spoken(hass, "voice_game_on", game=game, players=together)


async def _check_turn(
    hass: HomeAssistant, practice: PracticeGame, player: str | None
) -> None:
    """An entry for a named player only while they are at the board, as a voice
    assistant may hear the wrong one; without a game, the entry says why itself."""
    if player is None or practice.kind is None or practice.bot_up:
        return
    who = practice.thrower
    if who is None or _plain(who) != _plain(player):
        raise _invalid(
            "not_their_turn",
            player=player,
            name=await voice_name(hass, practice, practice.current),
        )


def _visit_score(data: Mapping[str, Any], practice: PracticeGame) -> int:
    """The score of a visit an action enters: its score, or for a checkout what the
    player has left."""
    score: int | None = data.get("score")
    if not data.get("checkout"):
        if score is None:
            raise _invalid("visit_no_score")
        return score
    player = practice.players[practice.current] if practice.players else None
    remaining = player.remaining if player is not None and practice.game else 0
    if score is not None and score != remaining:
        raise _invalid("checkout_score", score=str(score), remaining=str(remaining))
    return remaining


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
    """Every player needs a name of their own, party games take eight players
    and the others four, Killer needs two players and teams four players of X01
    or a Cricket game; the bot takes a seat of its own."""
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
    seats = PARTY_PLAYERS if game in PARTY_GAMES else MAX_PLAYERS
    if names and len(names) > seats:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="too_many_players",
            translation_placeholders={"count": str(seats)},
        )
    count = len(names) if names else min(players, seats)
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
    async def start_game(call: ServiceCall) -> ServiceResponse:
        """Start a game. Asked for a response, as by a voice assistant, the action
        answers what started or what was wrong in words to say, instead of failing."""
        try:
            key = await _start_game(call)
        except ServiceValidationError as error:
            if not call.return_response:
                raise
            placeholders = error.translation_placeholders or {}
            message = await spoken(hass, str(error.translation_key), **placeholders)
            return {"started": False, "message": message}
        if not call.return_response:
            return None
        practice = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID)).practice
        return {
            "started": True,
            "game": key,
            "players": [name for name in practice.names[: practice.humans] if name],
            "bot": practice.bot_seat is not None,
            "message": await _game_on(hass, key, practice),
        }

    async def _start_game(call: ServiceCall) -> str:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        game = await _game_key(hass, call.data["game"])
        practice = coordinator.practice
        # A name a player already has keeps its spelling, as a voice may lower it.
        names: list[str] | None = (
            [practice.profiles.spelled(name) for name in call.data["players"]]
            if call.data.get("players")
            else None
        )
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
            three_in_a_bed=call.data.get("three_in_a_bed"),
            start_scores=call.data.get("start_scores"),
            holes=call.data.get("holes"),
            rounds=call.data.get("rounds"),
            bot_level=call.data.get("bot_level"),
        )
        return game

    async def delete_player(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        if not await coordinator.async_delete_player(call.data["name"]):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_player",
                translation_placeholders={"name": call.data["name"]},
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_GAME,
        start_game,
        schema=START_GAME_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
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

    async def answered(
        call: ServiceCall, done: str, act: Callable[[bool], Awaitable[str | None]]
    ) -> ServiceResponse:
        """Run an action at the board. Asked for a response, as by a voice assistant,
        it answers what happened or what was wrong in words to say, instead of
        failing."""
        try:
            message = await act(call.return_response)
        except ServiceValidationError as error:
            if not call.return_response:
                raise
            placeholders = error.translation_placeholders or {}
            message = await spoken(hass, str(error.translation_key), **placeholders)
            return {done: False, "message": message}
        return {done: True, "message": message} if call.return_response else None

    async def throw_dart(call: ServiceCall) -> ServiceResponse:
        async def act(answer: bool) -> str | None:
            coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
            practice = coordinator.practice
            await _check_turn(hass, practice, call.data.get("player"))
            bed, position = _dart_at(call.data)
            await coordinator.async_throw_dart(bed, position)
            return await dart_said(hass, practice, str(bed["name"])) if answer else None

        return await answered(call, "entered", act)

    async def enter_visit(call: ServiceCall) -> ServiceResponse:
        async def act(answer: bool) -> str | None:
            coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
            practice = coordinator.practice
            await _check_turn(hass, practice, call.data.get("player"))
            score = _visit_score(call.data, practice)
            turn = Turn.of(practice)
            await coordinator.async_enter_visit(
                score, call.data.get("darts"), call.data.get("darts_at_double")
            )
            return await visit_said(hass, practice, turn, score) if answer else None

        return await answered(call, "entered", act)

    async def next_player(call: ServiceCall) -> ServiceResponse:
        async def act(answer: bool) -> str | None:
            coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
            turn = Turn.of(coordinator.practice)
            await coordinator.async_next_player()
            return await passed(hass, coordinator.practice, turn) if answer else None

        return await answered(call, "passed", act)

    async def undo_visit(call: ServiceCall) -> ServiceResponse:
        async def act(answer: bool) -> str | None:
            coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
            await coordinator.async_undo_visit()
            if not answer:
                return None
            score = sum(
                dart["number"] * dart["multiplier"]
                for dart in coordinator.training.visit()
            )
            return await undone(hass, coordinator.practice, score)

        return await answered(call, "undone", act)

    hass.services.async_register(
        DOMAIN, SERVICE_CORRECT_DART, correct_dart, schema=CORRECT_DART_SCHEMA
    )
    for name, handler, schema in (
        (SERVICE_THROW_DART, throw_dart, THROW_DART_SCHEMA),
        (SERVICE_ENTER_VISIT, enter_visit, ENTER_VISIT_SCHEMA),
        (SERVICE_NEXT_PLAYER, next_player, BOARD_SCHEMA),
        (SERVICE_UNDO_VISIT, undo_visit, BOARD_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN,
            name,
            handler,
            schema=schema,
            supports_response=SupportsResponse.OPTIONAL,
        )
