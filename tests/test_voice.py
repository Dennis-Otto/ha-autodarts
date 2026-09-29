"""Starting a game as a voice assistant hears it: games by their names, players as
their profiles spell them, and an answer in words to say."""

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError

from custom_components.autodarts.const import DOMAIN
from custom_components.autodarts.services import GAME_TEXT

from .local_helpers import board, setup_local, state


async def start(hass, respond: bool = False, **data):
    return await hass.services.async_call(
        DOMAIN, "start_game", data, blocking=True, return_response=respond
    )


@pytest.mark.parametrize(
    ("spoken", "game"),
    [
        ("Around the Clock", "around_the_clock"),
        ("around-the-clock", "around_the_clock"),
        ("Cricket", "cricket"),
        ("Bob's 27", "bobs_27"),
        ("Bobs 27", "bobs_27"),
        ("Halve it", "halve_it"),
        # A name in another language of the integration.
        ("Doppeltraining", "doubles"),
        ("Checkout-Training", "checkout"),
        # The beginning of a name, where it fits one game alone.
        ("Cut Throat", "cut_throat"),
        ("121", "checkout_121"),
        ("JDC", "jdc_challenge"),
        # A spoken number is a number.
        (501, "501"),
        (101, "101"),
    ],
)
async def test_start_game_knows_a_game_by_its_name(hass, aioclient_mock, spoken, game):
    await setup_local(hass, aioclient_mock, state=board())
    await start(hass, game=spoken)
    await hass.async_block_till_done()
    assert state(hass, "select", "practice_game") == game


@pytest.mark.parametrize(
    "spoken",
    [
        "Golfball",
        "401",
        # Too short, or the beginning of several games.
        "cr",
        "check",
    ],
)
async def test_start_game_explains_an_unknown_game(hass, aioclient_mock, spoken):
    entry = await setup_local(hass, aioclient_mock, state=board())
    with pytest.raises(ServiceValidationError) as error:
        await start(hass, game=spoken)
    assert error.value.translation_key == "unknown_game"
    assert error.value.translation_placeholders == {"game": spoken}
    assert entry.runtime_data.local.practice.game == 0


async def test_start_game_refuses_a_name_no_game_has(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock, state=board())
    for game in ("", "x" * (GAME_TEXT + 1)):
        with pytest.raises(vol.Invalid):
            await start(hass, game=game)


async def test_a_known_player_keeps_the_spelling_of_the_profile(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.practice
    practice.profiles.visit("Anne-Marie", 60)
    await start(hass, game="501", players=["anne-marie", "sam"])
    # A new name stays as it was said.
    assert practice.names[:2] == ["Anne-Marie", "sam"]


async def test_asked_for_an_answer_the_action_tells_what_started(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock, state=board())
    # Without names, the game alone.
    answer = await start(hass, True, game="around_the_clock")
    assert answer["players"] == [] and answer["message"] == "Game on: Around the Clock."
    answer = await start(hass, True, game="501", players=["Alex", "Sam", "Kim"])
    assert answer == {
        "started": True,
        "game": "501",
        "players": ["Alex", "Sam", "Kim"],
        "bot": False,
        "message": "Game on: 501 with Alex, Sam and Kim.",
    }
    answer = await start(hass, True, game="Cricket", players=["Alex"], bot_level=60)
    assert answer["bot"] is True
    assert answer["message"] == "Game on: Cricket with Alex and the bot."
    answer = await start(hass, True, game="around the clock", players=["Alex"])
    assert answer["message"] == "Game on: Around the Clock with Alex."
    # Without a response asked for, the action answers nothing.
    assert await start(hass, game="301") is None


async def test_the_answer_speaks_the_language_of_home_assistant(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock, state=board())
    hass.config.language = "de"
    answer = await start(hass, True, game="doubles", players=["Alex", "Sam"])
    assert answer["message"] == "Game on: Doppeltraining mit Alex und Sam."
    answer = await start(hass, True, game="501", players=["Alex"], bot_level=60)
    assert answer["message"] == "Game on: 501 mit Alex und dem Bot."
    answer = await start(hass, True, game="Golfball")
    assert answer == {
        "started": False,
        "message": "Kein Spiel heißt „Golfball“. Nenne eines der Übungsspiele, etwa 501, Cricket oder Around the Clock.",
    }


async def test_asked_for_an_answer_a_wrong_call_says_why(hass, aioclient_mock):
    """A voice assistant says what was wrong instead of "Done"."""
    entry = await setup_local(hass, aioclient_mock, state=board())
    answer = await start(hass, True, game="killer", players=["Alex"])
    assert answer["started"] is False
    assert answer["message"] == "Killer needs at least two players."
    assert entry.runtime_data.local.practice.party is None
    # Without an answer asked for, the call fails as before.
    with pytest.raises(ServiceValidationError):
        await start(hass, game="killer", players=["Alex"])
