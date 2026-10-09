"""Entering darts as a voice assistant hears them: the actions at the board answer
in words what a visit scored and left, a dart, who throws next and a visit taken
back, or why they refused, in the words of the scoreboard's caller."""

import pytest
from homeassistant.exceptions import ServiceValidationError

from .test_manual_board import act, setup_manual, value


async def say(hass, service: str, **data) -> dict:
    """The answer of an action asked for a response, as a voice assistant asks."""
    response = await hass.services.async_call(
        "autodarts", service, data, blocking=True, return_response=True
    )
    await hass.async_block_till_done()
    return response


async def test_a_visit_says_what_it_scored_and_who_throws_next(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="501", players=["Alex", "Sam"])
    assert await say(hass, "enter_visit", score=140) == {
        "entered": True,
        "message": "140 for Alex, 361 left. Sam, you require 501.",
    }
    assert value(hass, "sensor", "practice_remaining") == "501"


async def test_a_bust_says_the_score_stays(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="101", players=["Alex"])
    await act(hass, "enter_visit", score=61)
    # Alone at the board, Alex throws on; nobody else is named.
    answer = await say(hass, "enter_visit", score=45)
    assert answer["message"] == "No score: Alex stays at 40."
    answer = await say(hass, "enter_visit", score=0)
    assert answer["message"] == "0 for Alex, 40 left."


async def test_a_checkout_scores_what_is_left_and_wins_the_leg(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="101", players=["Alex", "Sam"], legs=2)
    await act(hass, "enter_visit", score=61)
    await act(hass, "enter_visit", score=26)
    answer = await say(hass, "enter_visit", checkout=True, darts=2)
    # Sam begins the next leg.
    assert answer["message"] == "Game shot, and the leg, Alex! Sam, you require 101."
    await act(hass, "enter_visit", score=60)
    await act(hass, "enter_visit", score=61)
    await act(hass, "enter_visit", score=41, player="Sam")
    answer = await say(hass, "enter_visit", checkout=True, player="alex")
    assert answer["message"] == "Game shot, and the match, Alex!"


@pytest.mark.parametrize(
    ("data", "key", "message"),
    [
        (
            {"checkout": True, "score": 50},
            "checkout_score",
            "A checkout scores what is left, 101, not 50.",
        ),
        (
            {},
            "visit_no_score",
            "Give the score of the visit, or checkout for a visit that checks out "
            "what is left.",
        ),
        (
            {"checkout": False},
            "visit_no_score",
            "Give the score of the visit, or checkout for a visit that checks out "
            "what is left.",
        ),
        (
            {"score": 60, "player": "Sam"},
            "not_their_turn",
            "It is Alex's turn, not Sam's.",
        ),
        (
            {"checkout": True, "darts": 1},
            "visit_impossible",
            "No visit scores 101 from 101 with these rules and darts. Check the score.",
        ),
    ],
)
async def test_a_wrong_visit_says_why(hass, data, key, message):
    await setup_manual(hass)
    await act(hass, "start_game", game="101", players=["Alex", "Sam"])
    assert await say(hass, "enter_visit", **data) == {
        "entered": False,
        "message": message,
    }
    # Without a response, the action fails as any other.
    with pytest.raises(ServiceValidationError) as error:
        await act(hass, "enter_visit", **data)
    assert error.value.translation_key == key
    assert value(hass, "sensor", "practice_remaining") == "101"


async def test_a_dart_says_its_bed_and_what_is_left(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="501", players=["Alex", "Sam"])
    spoken = []
    for segment in ("T20", "SB", "MISS"):
        spoken.append((await say(hass, "throw_dart", segment=segment))["message"])
    assert spoken == ["Triple 20, 441 left.", "25, 416 left.", "Miss, 416 left."]
    assert await say(hass, "next_player") == {
        "passed": True,
        "message": "Sam, you require 501.",
    }
    answer = await say(hass, "throw_dart", segment="D16", player="Sam")
    assert answer["message"] == "Double 16, 469 left."
    answer = await say(hass, "throw_dart", segment="BULL", player="Alex")
    assert answer == {"entered": False, "message": "It is Sam's turn, not Alex's."}


async def test_a_dart_says_a_bust_and_the_game_shot(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="101", players=["Alex", "Sam"])
    await act(hass, "enter_visit", score=61)
    await act(hass, "enter_visit", score=60)
    answer = await say(hass, "throw_dart", segment="T20")
    assert answer["message"] == "Triple 20: no score!"
    await act(hass, "next_player")
    await act(hass, "enter_visit", score=0)
    # The game shot counts once the visit ends, as the next player is called.
    answer = await say(hass, "throw_dart", segment="D20")
    assert answer["message"] == "Double 20. Game shot!"
    answer = await say(hass, "next_player")
    assert answer["message"] == "Game shot, and the match, Alex!"


async def test_the_next_player_after_a_game_shot_says_the_leg(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="101", players=["Alex", "Sam"], legs=2)
    await act(hass, "enter_visit", score=61)
    await act(hass, "enter_visit", score=60)
    await act(hass, "throw_dart", segment="D20")
    answer = await say(hass, "next_player")
    assert answer["message"] == "Game shot, and the leg, Alex! Sam, you require 101."


async def test_a_dart_of_cricket_says_its_bed_and_the_next_player(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="cricket", players=["Alex", "Sam"])
    answer = await say(hass, "throw_dart", segment="T20")
    assert answer["message"] == "Triple 20."
    answer = await say(hass, "next_player")
    assert answer["message"] == "Sam to throw."


async def test_an_undone_visit_says_whose_and_how_many_points(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="501", players=["Alex", "Sam"])
    await act(hass, "enter_visit", score=140)
    assert await say(hass, "undo_visit") == {
        "undone": True,
        "message": "Taken back: 140 of Alex.",
    }
    answer = await say(hass, "undo_visit")
    assert answer["undone"] is False


async def test_players_without_a_name_and_the_bot_are_named(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="301", players=["Alex"], bot_level=60)
    answer = await say(hass, "enter_visit", score=60)
    assert answer["message"] == "60 for Alex, 241 left. The bot, you require 301."
    answer = await say(hass, "enter_visit", score=60)
    assert answer == {
        "entered": False,
        "message": "The bot is at the board. Wait for its visit, or end it with "
        "Next player.",
    }
    # The next player ends the bot's visit.
    answer = await say(hass, "next_player")
    assert answer["message"] == "Alex, you require 241."


async def test_a_player_without_a_name_is_named_by_their_seat(hass):
    await setup_manual(hass)
    await act(hass, "start_game", game="301")
    answer = await say(hass, "enter_visit", score=60, player="Alex")
    assert answer["message"] == "It is Player 1's turn, not Alex's."
    answer = await say(hass, "enter_visit", score=60)
    assert answer["message"] == "60 for Player 1, 241 left."


async def test_the_answers_speak_the_language_of_home_assistant(hass):
    await setup_manual(hass)
    hass.config.language = "de"
    await act(hass, "start_game", game="501", players=["Alex", "Sam"])
    answer = await say(hass, "enter_visit", score=140)
    assert answer["message"] == "140 für Alex, noch 361. Sam, du brauchst 501."
    answer = await say(hass, "throw_dart", segment="D16")
    assert answer["message"] == "Doppel 16, noch 469."
    answer = await say(hass, "enter_visit", score=60, player="Alex")
    assert answer["message"] == "Sam ist dran, nicht Alex."
