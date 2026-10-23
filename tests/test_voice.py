"""Starting a game as a voice assistant hears it: games by their names, players as
their profiles spell them, and an answer in words to say."""

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError

from custom_components.homedarts.const import DOMAIN
from custom_components.homedarts.profiles import NAME_LENGTH
from custom_components.homedarts.services import GAME_TEXT
from custom_components.homedarts.voice import refusal

from .local_helpers import NOW, board, setup_local, state
from .test_manual_board import setup_manual


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
    assert entry.runtime_data.local.games.practice.game == 0


async def test_start_game_refuses_a_name_no_game_has(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock, state=board())
    with pytest.raises(vol.Invalid):
        await start(hass, game="")
    # A name longer than any game's, as a voice assistant may hear it, is
    # explained, with its beginning.
    with pytest.raises(ServiceValidationError) as error:
        await start(hass, game="x" * (GAME_TEXT + 1))
    assert error.value.translation_key == "unknown_game"
    assert error.value.translation_placeholders == {"game": "x" * GAME_TEXT + "…"}


async def test_a_known_player_keeps_the_spelling_of_the_profile(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.games.practice
    practice.profiles.visit("Anne-Marie", 60, now=NOW)
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


@pytest.mark.parametrize("language", ["de", "de-CH", "de_AT"])
async def test_the_answer_speaks_the_language_of_home_assistant(
    hass, aioclient_mock, language
):
    """Also in a regional language, such as German of Switzerland."""
    await setup_local(hass, aioclient_mock, state=board())
    hass.config.language = language
    answer = await start(hass, True, game="doubles", players=["Alex", "Sam"])
    assert answer["message"] == "Game on: Doppeltraining mit Alex und Sam."
    answer = await start(hass, True, game="501", players=["Alex"], bot_level=60)
    assert answer["message"] == "Game on: 501 mit Alex und dem Bot."
    answer = await start(hass, True, game="Golfball")
    assert answer == {
        "started": False,
        "message": "Kein Spiel heißt „Golfball“. Nenne eines der Übungsspiele, etwa 501, Cricket oder Around the Clock.",
    }


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"players": ["Ann", "Bob", "Cid", "Dan", "Eve"]},
            "This game takes 4 players at most; party games take up to eight.",
        ),
        (
            {"game": "killer", "players": [f"P{seat}" for seat in range(9)]},
            "This game takes 8 players at most; party games take up to eight.",
        ),
        (
            {"players": ["Alex", "x" * (NAME_LENGTH + 1)]},
            f'"{"x" * NAME_LENGTH}…" is too long for a player name, which has at'
            f" most {NAME_LENGTH} characters.",
        ),
        (
            {"game": "x" * 70},
            f'No game is called "{"x" * GAME_TEXT}…". Name one of the practice'
            " games, such as 501, Cricket or Around the Clock.",
        ),
        # Home Assistant's own refusal, for a board it does not know, in words.
        (
            {"config_entry_id": "unknown"},
            "Integration homedarts config entry with ID unknown was not found.",
        ),
    ],
)
async def test_what_a_voice_assistant_may_hear_wrongly_is_explained(
    hass, aioclient_mock, data, message
):
    """Too many players, a name or a game longer than any, or a board that is not
    there: the action says why in words, where a schema would have refused the call
    before it, and Assist would have answered "Done"."""
    entry = await setup_local(hass, aioclient_mock, state=board())
    answer = await start(hass, True, **{"game": "501", **data})
    assert answer == {"started": False, "message": message}
    assert entry.runtime_data.local.games.practice.game == 0


async def test_an_entry_for_a_name_longer_than_a_players_is_explained(hass):
    """A sentence taken apart wrongly may name a player with more words than a name
    has: the entry is refused with words to say."""
    entry = await setup_manual(hass)
    await start(hass, game="501", players=["Alex", "Sam"])
    for service, data in (
        ("enter_visit", {"score": 100}),
        ("throw_dart", {"segment": "T20"}),
    ):
        answer = await hass.services.async_call(
            DOMAIN,
            service,
            {**data, "player": " Alex, Sam and the bot "},
            blocking=True,
            return_response=True,
        )
        assert answer == {
            "entered": False,
            "message": '"Alex, Sam and the bo…" is too long for a player name, which'
            " has at most 20 characters.",
        }
    scores = entry.runtime_data.local.games.practice.snapshot()["scores"]
    assert [score["remaining"] for score in scores] == [501, 501]


async def test_a_named_entry_without_a_turn_says_why_itself(hass):
    """Without a game, or while the bot is up, a named entry is not checked against
    the player at the board: the entry itself says why it cannot go in."""
    await setup_manual(hass)
    named = {"score": 60, "player": "Alex"}
    answer = await hass.services.async_call(
        DOMAIN, "enter_visit", named, blocking=True, return_response=True
    )
    assert answer == {
        "entered": False,
        "message": "A visit's score can be entered while an X01 leg is played; in"
        " other games, and in the bull-off, enter its darts.",
    }
    await start(hass, game="301", players=["Alex"], bot_level=60)
    await hass.services.async_call(DOMAIN, "enter_visit", {"score": 60}, blocking=True)
    answer = await hass.services.async_call(
        DOMAIN, "enter_visit", named, blocking=True, return_response=True
    )
    assert answer == {
        "entered": False,
        "message": "The bot is at the board. Wait for its visit, or end it with "
        "Next player.",
    }


async def test_home_assistants_refusals_speak_its_language(hass, aioclient_mock):
    """A refusal of Home Assistant itself is said in its language, never as the key
    of its message."""
    await setup_local(hass, aioclient_mock, state=board())
    hass.config.language = "de"
    answer = await start(hass, True, game="501", config_entry_id="unknown")
    assert answer["message"] == (
        "Konfigurationseintrag mit ID unknown zur Integration homedarts wurde nicht"
        " gefunden."
    )
    answer = await hass.services.async_call(
        DOMAIN,
        "next_player",
        {"config_entry_id": "unknown"},
        blocking=True,
        return_response=True,
    )
    assert answer["passed"] is False
    assert answer["message"].startswith("Konfigurationseintrag mit ID unknown")


async def test_a_refusal_without_its_words_says_the_error(hass):
    """A message that Home Assistant has no words for, or whose placeholders are
    missing, is said as the error tells it."""
    assert await refusal(hass, ServiceValidationError("The board is busy.")) == (
        "The board is busy."
    )
    unknown = ServiceValidationError(
        translation_domain="homeassistant", translation_key="no_such_message"
    )
    assert await refusal(hass, unknown) == str(unknown)
    missing = ServiceValidationError(
        translation_domain="homeassistant",
        translation_key="service_config_entry_not_found",
    )
    assert await refusal(hass, missing) == str(missing)


async def test_asked_for_an_answer_a_wrong_call_says_why(hass, aioclient_mock):
    """A voice assistant says what was wrong instead of "Done"."""
    entry = await setup_local(hass, aioclient_mock, state=board())
    answer = await start(hass, True, game="killer", players=["Alex"])
    assert answer["started"] is False
    assert answer["message"] == "Killer needs at least two players."
    assert entry.runtime_data.local.games.practice.party is None
    # Without an answer asked for, the call fails as before.
    with pytest.raises(ServiceValidationError):
        await start(hass, game="killer", players=["Alex"])
