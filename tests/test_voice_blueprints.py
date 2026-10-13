"""The voice blueprints with Home Assistant's own Assist, in process and in seconds:
every sentence the guides give as an example, with Home Assistant in English and in
German, reaches the action with the right data, and Assist says what the action
answers, also why it refused a sentence. The end-to-end test says a few of them to
a real Home Assistant as well."""

import importlib.util
import logging
import re
from importlib.metadata import version
from pathlib import Path

import pytest
from homeassistant.components import conversation
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import Context
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_capture_events

from .local_helpers import automate_all
from .test_manual_board import setup_manual

pytestmark = pytest.mark.usefixtures("blueprint_folder")

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pin_assist", ROOT / "scripts" / "pin_assist.py"
)
pin_assist = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pin_assist)
# A game's name that no voice assistant hears: 70 characters.
LONG_GAME = "Around the Clock and the longest name of a game anyone ever thought of"
# A name longer than a player's, as Assist hears a sentence it took apart wrongly.
LONG_NAME = "Maximilianalexandrina"

# What is said to Assist with Home Assistant in English, in order, the action it
# runs with its data, and what Assist answers.
ENGLISH = [
    # Starting a game.
    (
        "Start 501 for Alex and Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 with Alex and Sam.",
    ),
    (
        "Play 301 with Alex, Sam and Kim",
        "start_game",
        {"game": 301, "bot_level": 0, "players": ["Alex", "Sam", "Kim"]},
        "Game on: 301 with Alex, Sam and Kim.",
    ),
    (
        "Start five hundred one",
        "start_game",
        {"game": 501, "bot_level": 0},
        "Game on: 501 with Alex, Sam and Kim.",
    ),
    (
        "Start the game Cricket for Alex and Sam",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: Cricket with Alex and Sam.",
    ),
    (
        "Start the game Cricket for Alex",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex"]},
        "Game on: Cricket with Alex.",
    ),
    (
        "Play a game of Around the Clock",
        "start_game",
        {"game": "Around the Clock", "bot_level": 0},
        "Game on: Around the Clock with Alex.",
    ),
    (
        "Start the game Doubles training",
        "start_game",
        {"game": "Doubles training", "bot_level": 0},
        "Game on: Doubles training with Alex.",
    ),
    (
        "Start 501 for Alex against the bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 with Alex and the bot.",
    ),
    (
        "Play the game Cricket against the bot",
        "start_game",
        {"game": "Cricket", "bot_level": 60},
        "Game on: Cricket with Alex and the bot.",
    ),
    (
        "Play 501 against the bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on: 501 with Alex and the bot.",
    ),
    # The bot at the end of the players is the bot, never a player.
    (
        "Play 501 for Alex and the bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 with Alex and the bot.",
    ),
    (
        "Start 301 for Alex, Sam and bot",
        "start_game",
        {"game": 301, "bot_level": 60, "players": ["Alex", "Sam"]},
        "Game on: 301 with Alex, Sam and the bot.",
    ),
    (
        "Play 501 for the bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on: 501 with Alex, Sam and the bot.",
    ),
    # What the action refuses, Assist explains.
    (
        "Start 501 for Ann Bob Cid Dan Eve Fay Gus Hal Ida",
        "start_game",
        {
            "game": 501,
            "bot_level": 0,
            "players": ["Ann", "Bob", "Cid", "Dan", "Eve", "Fay", "Gus", "Hal", "Ida"],
        },
        "This game takes 4 players at most; party games take up to eight.",
    ),
    (
        f"Start 501 for Alex and {LONG_NAME}",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", LONG_NAME]},
        f'"{LONG_NAME[:20]}…" is too long for a player name, which has at most 20'
        " characters.",
    ),
    (
        f"Start the game {LONG_GAME}",
        "start_game",
        {"game": LONG_GAME, "bot_level": 0},
        f'No game is called "{LONG_GAME[:64]}…". Name one of the practice games,'
        " such as 501, Cricket or Around the Clock.",
    ),
    # Entering darts.
    (
        "Start 101 for Alex and Sam",
        "start_game",
        {"game": 101, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 101 with Alex and Sam.",
    ),
    (
        "Alex has 61",
        "enter_visit",
        {"score": 61, "player": "Alex"},
        "61 for Alex, 40 left. Sam, you require 101.",
    ),
    (
        "Sam scored 100",
        "enter_visit",
        {"score": 100, "player": "Sam"},
        "No score: Sam stays at 101. Alex, you require 40.",
    ),
    (
        "Checkout with two darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Game shot, and the match, Alex!",
    ),
    (
        "Start 501 for Alex and Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 with Alex and Sam.",
    ),
    (
        "Alex has 140",
        "enter_visit",
        {"score": 140, "player": "Alex"},
        "140 for Alex, 361 left. Sam, you require 501.",
    ),
    (
        "Alex checks out",
        "enter_visit",
        {"checkout": True, "player": "Alex"},
        "It is Sam's turn, not Alex's.",
    ),
    (
        "140 points",
        "enter_visit",
        {"score": 140},
        "140 for Sam, 361 left. Alex, you require 361.",
    ),
    (
        "one hundred forty",
        "enter_visit",
        {"score": 140},
        "140 for Alex, 221 left. Sam, you require 361.",
    ),
    (
        "Game shot in three darts",
        "enter_visit",
        {"checkout": True, "darts": 3},
        "No visit checks out 361 with these rules and darts.",
    ),
    # Digits work in every language.
    (
        "Checkout with 2 darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "No visit checks out 361 with these rules and darts.",
    ),
    (
        "Checkout mit 2 Darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "No visit checks out 361 with these rules and darts.",
    ),
    ("Triple 20", "throw_dart", {"segment": "T20"}, "Triple 20, 301 left."),
    ("Double 16", "throw_dart", {"segment": "D16"}, "Double 16, 269 left."),
    ("Single 5", "throw_dart", {"segment": "S5"}, "Single 5, 264 left."),
    ("Next player", "next_player", {}, "Alex, you require 221."),
    ("Bull", "throw_dart", {"segment": "BULL"}, "Bull, 171 left."),
    ("Single bull", "throw_dart", {"segment": "25"}, "25, 146 left."),
    ("Miss", "throw_dart", {"segment": "MISS"}, "Miss, 146 left."),
    ("Next player", "next_player", {}, "Sam, you require 264."),
    ("Undo", "undo_visit", {}, "Taken back: 75 of Alex."),
    (
        f"{LONG_NAME} has 100",
        "enter_visit",
        {"score": 100, "player": LONG_NAME},
        f'"{LONG_NAME[:20]}…" is too long for a player name, which has at most 20'
        " characters.",
    ),
]

# The same with Home Assistant in German.
GERMAN = [
    (
        "Starte 501 für Alex und Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 mit Alex und Sam.",
    ),
    (
        "Spiele 301 mit Alex, Sam und Kim",
        "start_game",
        {"game": 301, "bot_level": 0, "players": ["Alex", "Sam", "Kim"]},
        "Game on: 301 mit Alex, Sam und Kim.",
    ),
    (
        "Starte fünfhunderteins",
        "start_game",
        {"game": 501, "bot_level": 0},
        "Game on: 501 mit Alex, Sam und Kim.",
    ),
    (
        "Starte das Spiel Cricket für Alex und Sam",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: Cricket mit Alex und Sam.",
    ),
    (
        "Starte das Spiel Cricket für Alex",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex"]},
        "Game on: Cricket mit Alex.",
    ),
    (
        "Spiele das Spiel Around the Clock",
        "start_game",
        {"game": "Around the Clock", "bot_level": 0},
        "Game on: Around the Clock mit Alex.",
    ),
    (
        "Starte das Spiel Doppeltraining",
        "start_game",
        {"game": "Doppeltraining", "bot_level": 0},
        "Game on: Doppeltraining mit Alex.",
    ),
    (
        "Starte 501 für Alex gegen den Bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 mit Alex und dem Bot.",
    ),
    (
        "Spiele 501 für Alex gegen den Bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 mit Alex und dem Bot.",
    ),
    (
        "Spiele das Spiel Cricket gegen den Bot",
        "start_game",
        {"game": "Cricket", "bot_level": 60},
        "Game on: Cricket mit Alex und dem Bot.",
    ),
    (
        "Spiele 501 gegen den Bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on: 501 mit Alex und dem Bot.",
    ),
    (
        "Spiele 501 für Alex und den Bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 mit Alex und dem Bot.",
    ),
    (
        "Starte 301 mit Alex, Sam und dem Bot",
        "start_game",
        {"game": 301, "bot_level": 60, "players": ["Alex", "Sam"]},
        "Game on: 301 mit Alex, Sam und dem Bot.",
    ),
    (
        "Starte 501 für Ann Bob Cid Dan Eve Fay Gus Hal Ida",
        "start_game",
        {
            "game": 501,
            "bot_level": 0,
            "players": ["Ann", "Bob", "Cid", "Dan", "Eve", "Fay", "Gus", "Hal", "Ida"],
        },
        "Dieses Spiel nimmt höchstens 4 Spieler; Partyspiele bis zu acht.",
    ),
    (
        f"Starte 501 für Alex und {LONG_NAME}",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", LONG_NAME]},
        f"„{LONG_NAME[:20]}…“ ist zu lang für einen Spielernamen, der höchstens 20"
        " Zeichen hat.",
    ),
    (
        f"Starte das Spiel {LONG_GAME}",
        "start_game",
        {"game": LONG_GAME, "bot_level": 0},
        f"Kein Spiel heißt „{LONG_GAME[:64]}…“. Nenne eines der Übungsspiele, etwa"
        " 501, Cricket oder Around the Clock.",
    ),
    (
        "Starte 101 für Alex und Sam",
        "start_game",
        {"game": 101, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 101 mit Alex und Sam.",
    ),
    (
        "Alex hat 61",
        "enter_visit",
        {"score": 61, "player": "Alex"},
        "61 für Alex, noch 40. Sam, du brauchst 101.",
    ),
    (
        "Sam wirft 100",
        "enter_visit",
        {"score": 100, "player": "Sam"},
        "Überworfen: Sam bleibt bei 101. Alex, du brauchst 40.",
    ),
    (
        "Checkout mit zwei Darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Game shot, und das Match, Alex!",
    ),
    (
        "Starte 501 für Alex und Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 mit Alex und Sam.",
    ),
    (
        "Alex hat 140",
        "enter_visit",
        {"score": 140, "player": "Alex"},
        "140 für Alex, noch 361. Sam, du brauchst 501.",
    ),
    (
        "Alex checkt",
        "enter_visit",
        {"checkout": True, "player": "Alex"},
        "Sam ist dran, nicht Alex.",
    ),
    (
        "140 Punkte",
        "enter_visit",
        {"score": 140},
        "140 für Sam, noch 361. Alex, du brauchst 361.",
    ),
    (
        "einhundertvierzig",
        "enter_visit",
        {"score": 140},
        "140 für Alex, noch 221. Sam, du brauchst 361.",
    ),
    (
        "Game Shot in drei Darts",
        "enter_visit",
        {"checkout": True, "darts": 3},
        "Keine Aufnahme checkt 361 mit diesen Regeln und Darts aus.",
    ),
    (
        "Checkout mit 2 Darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Keine Aufnahme checkt 361 mit diesen Regeln und Darts aus.",
    ),
    (
        "Checkout with 2 darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Keine Aufnahme checkt 361 mit diesen Regeln und Darts aus.",
    ),
    ("Triple 20", "throw_dart", {"segment": "T20"}, "Triple 20, noch 301."),
    ("Doppel 16", "throw_dart", {"segment": "D16"}, "Doppel 16, noch 269."),
    ("Single 5", "throw_dart", {"segment": "S5"}, "Single 5, noch 264."),
    ("Nächster Spieler", "next_player", {}, "Alex, du brauchst 221."),
    ("Bull", "throw_dart", {"segment": "BULL"}, "Bull, noch 171."),
    ("Single Bull", "throw_dart", {"segment": "25"}, "25, noch 146."),
    ("Fehlwurf", "throw_dart", {"segment": "MISS"}, "Fehlwurf, noch 146."),
    ("Nächster Spieler", "next_player", {}, "Sam, du brauchst 264."),
    ("Rückgängig", "undo_visit", {}, "Zurückgenommen: 75 von Alex."),
    (
        "Aufnahme 100",
        "enter_visit",
        {"score": 100},
        "100 für Alex, noch 121. Sam, du brauchst 264.",
    ),
    (
        f"{LONG_NAME} hat 100",
        "enter_visit",
        {"score": 100, "player": LONG_NAME},
        f"„{LONG_NAME[:20]}…“ ist zu lang für einen Spielernamen, der höchstens 20"
        " Zeichen hat.",
    ),
]

SPOKEN = {"en": ENGLISH, "de": GERMAN}


async def say(hass, text: str) -> str:
    """What Assist answers to a sentence."""
    result = await conversation.async_converse(hass, text, None, Context())
    return result.response.speech["plain"]["speech"]


@pytest.mark.parametrize("language", SPOKEN)
async def test_assist_runs_every_sentence_through_the_blueprints(
    hass, caplog, language
):
    """Each sentence reaches its action with the data the blueprint makes of it,
    and Assist answers what the action says: what started or was entered, or why
    it was refused, never "Done"."""
    # Assist reads the words of numbers in the language of Home Assistant.
    hass.config.language = language
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})
    await setup_manual(hass)
    await automate_all(
        hass, [("start_game_by_voice", {}), ("enter_darts_by_voice", {})]
    )
    calls = async_capture_events(hass, EVENT_CALL_SERVICE)
    for text, action, data, answer in SPOKEN[language]:
        calls.clear()
        said = await say(hass, text)
        made = [
            (call.data["service"], call.data["service_data"])
            for call in calls
            if call.data["domain"] == "autodarts"
        ]
        assert (made, said) == ([(action, data)], answer), text
    # A refused sentence is no error of the automation, as one a schema refused was.
    assert not [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.ERROR
        and record.name.startswith("homeassistant.components.automation")
    ]


# Sentences of one's own in French, Spanish and Dutch, as the guides suggest for
# those languages: the blueprint knows their words that join the names and their
# articles before the bot.
OWN_SENTENCES = [
    "(joue|juega|speel) {101..1001,100:game} (pour|para|voor) {players}",
]
OWN_LANGUAGES = [
    ("joue 501 pour Alex et le bot", ["Alex"], 60),
    ("joue 501 pour Alex et un bot", ["Alex"], 60),
    ("juega 501 para Alex y el bot", ["Alex"], 60),
    ("juega 501 para Alex y un bot", ["Alex"], 60),
    ("speel 501 voor Alex en de bot", ["Alex"], 60),
    ("speel 501 voor Alex en een bot", ["Alex"], 60),
    ("speel 501 voor Alex en het bot", ["Alex"], 60),
    ("speel 501 voor Alex & bot", ["Alex"], 60),
    ("joue 501 pour Alex et Sam", ["Alex", "Sam"], 0),
    ("juega 501 para Alex y Sam", ["Alex", "Sam"], 0),
    ("speel 501 voor Alex en Sam", ["Alex", "Sam"], 0),
    ("speel 501 voor Alex & Sam", ["Alex", "Sam"], 0),
]


async def test_the_bot_and_the_names_in_sentences_of_ones_own(hass):
    """In sentences of one's own, the French, Spanish and Dutch words that join the
    names only join them, and the bot at the end with its article is the bot."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})
    await setup_manual(hass)
    await automate_all(hass, [("start_game_by_voice", {"sentences": OWN_SENTENCES})])
    calls = async_capture_events(hass, EVENT_CALL_SERVICE)
    for text, players, bot_level in OWN_LANGUAGES:
        calls.clear()
        said = await say(hass, text)
        made = [
            call.data["service_data"]
            for call in calls
            if call.data["domain"] == "autodarts"
        ]
        others = " and ".join(players[1:] + ["the bot"] * (bot_level > 0))
        assert (made, said) == (
            [{"game": 501, "bot_level": bot_level, "players": players}],
            f"Game on: 501 with {players[0]} and {others}.",
        ), text


# Where a guide gives sentences that need Home Assistant in the other language.
OTHER_LANGUAGE = re.compile(
    r"- (?:with Home Assistant )?in German|- (?:mit Home Assistant )?auf Englisch"
)
QUOTED = re.compile(r'"([^"]+)"|„([^“]+)“')


def _examples(page: str) -> dict[str, set[str]]:
    """The sentences a guide gives as examples for the voice blueprints, in the
    overview of the blueprints and under "Say for example", by the language
    Home Assistant needs for them."""
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")
    own, other = ("de", "en") if page.endswith(".de.md") else ("en", "de")
    # The text of a row, without the alt text of its import button.
    rows = re.findall(
        r"^\| \*\*(?:Start a game|Enter darts) by voice\*\* \| (.*?) \| \[!\[",
        text,
        re.M,
    )
    lists = re.findall(
        r"^(?:Say for example|Sag zum Beispiel):\n\n((?:- .*\n)+)", text, re.M
    )
    assert len(rows) == len(lists) == 2, page
    found: dict[str, set[str]] = {own: set(), other: set()}
    for line in [*rows, *"".join(lists).splitlines()]:
        language = other if OTHER_LANGUAGE.match(line) else own
        found[language] |= {first or second for first, second in QUOTED.findall(line)}
    return found


@pytest.mark.parametrize("page", ["automations.md", "automations.de.md"])
def test_every_example_of_the_guides_is_said_to_assist(page):
    """The guides give no sentence that the test above leaves out, in the language
    Home Assistant needs for it."""
    for language, sentences in _examples(page).items():
        said = {text for text, *_ in SPOKEN[language]}
        assert sentences <= said, (language, sorted(sentences - said))


def test_assist_has_the_versions_of_home_assistant():
    """Assist runs in the tests with the packages Home Assistant installs for it:
    those of the conversation manifest of the Home Assistant the test plugin pins.
    When the test plugin brings a new Home Assistant, scripts/pin_assist.py pins
    them again."""
    wanted = pin_assist.manifest_pins()
    pinned = dict(
        re.findall(
            r"^([\w.-]+)==(\S+)$",
            (ROOT / "requirements-test.in").read_text(encoding="utf-8"),
            re.M,
        )
    )
    lines = "\n".join(f"{name}=={pin}" for name, pin in sorted(wanted.items()))
    assert {name: pinned.get(name) for name in wanted} == wanted, (
        f"Home Assistant {HA_VERSION} installs these for Assist:\n{lines}\nRun"
        " python scripts/pin_assist.py, which pins them in requirements-test.in and"
        " compiles requirements-test.txt again."
    )
    assert {name: version(name) for name in wanted} == wanted, (
        "Install requirements-test.txt again: pip install --require-hashes -r"
        " requirements-test.txt"
    )
