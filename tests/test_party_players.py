"""Party games for up to eight players; X01 and the Cricket games stay at four."""

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.practice import (
    MAX_PLAYERS,
    PARTY_PLAYERS,
    PracticeGame,
    valid_settings,
)

from .local_helpers import board, setup_local, state, throw
from .test_practice_setup import select_game, set_number

NAMES = ["Alex", "Sam", "Kim", "Lea", "Mia", "Leo", "Zoe", "Ben"]


def test_party_games_seat_eight_and_the_other_games_four():
    game = PracticeGame()
    # Before a game is chosen, a party may gather.
    assert game.seats == PARTY_PLAYERS
    game.set_players(8)
    assert game.humans == 8
    game.play("killer")
    assert game.seats == PARTY_PLAYERS and len(game.players) == 8
    assert len(game.snapshot()["scores"]) == 8
    # X01, the Cricket games and the training games keep four seats.
    for kind in (501, "cricket", "around_the_clock"):
        game.play(kind)
        assert game.seats == MAX_PLAYERS and game.humans == 4, kind
    game.play("shanghai", 8)
    assert len(game.players) == 8


def test_eight_players_take_turns_and_win_a_party_game():
    game = PracticeGame()
    game.set_players(8)
    game.play("count_up")
    game.set_rounds(count_up_rounds=1)
    for index, name in enumerate(NAMES):
        game.set_name(index, name)
    events = throw(game, "T20")
    for _ in range(7):
        events += throw(game, "S1")
    won = [details for kind, details in events if kind == "leg_won"]
    assert won and won[0]["name"] == "Alex" and won[0]["players"] == 8
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.names == NAMES and len(restored.players) == 8


def test_settings_of_four_names_from_before_come_back_with_eight():
    saved = {
        "players": 2,
        "names": ["Alex", "Sam", "", ""],
        "starts": [0, 0, 0, 0],
        "bot_level": 0,
        "legs_to_win": 1,
        "sets_to_win": 1,
        "double_out": True,
        "double_in": False,
        "bull_off": False,
        "bull_off_distance": False,
    }
    assert valid_settings(saved)["names"] == ["Alex", "Sam"] + [""] * 6
    assert valid_settings({**saved, "names": NAMES})["names"] == NAMES
    assert valid_settings({**saved, "names": [*NAMES, "Max"]}) is None
    assert valid_settings({**saved, "names": ["Alex"]}) is None
    assert valid_settings({**saved, "players": 9}) is None


async def test_eight_named_players_start_killer_and_x01_refuses_a_fifth(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.practice
    await hass.services.async_call(
        DOMAIN, "start_game", {"game": "killer", "players": NAMES}, blocking=True
    )
    await hass.async_block_till_done()
    assert practice.party.kind == "killer" and practice.names == NAMES
    assert state(hass, "number", "practice_players") == "8"
    assert state(hass, "text", "practice_player_8") == "Ben"
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN, "start_game", {"game": "501", "players": NAMES[:5]}, blocking=True
        )
    assert error.value.translation_key == "too_many_players"
    assert error.value.translation_placeholders == {"count": "4"}
    # Without names, X01 takes the first four of the party.
    await hass.services.async_call(DOMAIN, "start_game", {"game": "501"}, blocking=True)
    assert practice.game == 501 and practice.humans == 4
    # The bot needs a seat of its own, which four players leave none of.
    await hass.services.async_call(
        DOMAIN, "start_game", {"game": "shanghai", "players": NAMES}, blocking=True
    )
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN, "start_game", {"game": "501", "bot_level": 60}, blocking=True
        )
    assert error.value.translation_key == "bot_seat"


async def test_the_players_number_takes_eight_for_party_games_only(
    hass, aioclient_mock
):
    await setup_local(hass, aioclient_mock, state=board())
    await select_game(hass, "halve_it")
    await set_number(hass, "practice_players", 8)
    assert state(hass, "number", "practice_players") == "8"
    await select_game(hass, "501")
    assert state(hass, "number", "practice_players") == "4"
    with pytest.raises(ServiceValidationError) as error:
        await set_number(hass, "practice_players", 5)
    assert error.value.translation_key == "too_many_players"
