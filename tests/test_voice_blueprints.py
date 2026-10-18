"""The voice blueprints with Home Assistant's own Assist, in process and in seconds:
every sentence the guides give as an example, with Home Assistant in each language
of the integration, reaches the action with the right data, and Assist says what the
action answers, also why it refused a sentence. Assist's own commands stay its own.
The end-to-end test says a few of them to a real Home Assistant as well."""

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
from homeassistant.helpers.intent import IntentResponseErrorCode
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.autodarts.const import LANGUAGES

from .local_helpers import automate_all
from .test_manual_board import setup_manual

pytestmark = pytest.mark.usefixtures("blueprint_folder")
NO_INTENT_MATCH = IntentResponseErrorCode.NO_INTENT_MATCH

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

# The same with Home Assistant in Spanish.
SPANISH = [
    (
        "Juega 501 para Alex y Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 con Alex y Sam.",
    ),
    (
        "Empieza 301 con Alex, Sam y Kim",
        "start_game",
        {"game": 301, "bot_level": 0, "players": ["Alex", "Sam", "Kim"]},
        "Game on: 301 con Alex, Sam y Kim.",
    ),
    (
        "Empieza quinientos uno",
        "start_game",
        {"game": 501, "bot_level": 0},
        "Game on: 501 con Alex, Sam y Kim.",
    ),
    (
        "Juega la partida Cricket para Alex y Sam",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: Cricket con Alex y Sam.",
    ),
    (
        "Juega una partida de Cricket para Alex",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex"]},
        "Game on: Cricket con Alex.",
    ),
    (
        "Juega una partida de Around the Clock",
        "start_game",
        {"game": "Around the Clock", "bot_level": 0},
        "Game on: Around the Clock con Alex.",
    ),
    (
        "Inicia la partida Entrenamiento de dobles",
        "start_game",
        {"game": "Entrenamiento de dobles", "bot_level": 0},
        "Game on: Entrenamiento de dobles con Alex.",
    ),
    (
        "Juega 501 para Alex contra el bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 con Alex y el bot.",
    ),
    (
        "Juega 501 para Alex y el bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 con Alex y el bot.",
    ),
    (
        "Juega la partida Cricket contra el bot",
        "start_game",
        {"game": "Cricket", "bot_level": 60},
        "Game on: Cricket con Alex y el bot.",
    ),
    (
        "Juega 501 contra el bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on: 501 con Alex y el bot.",
    ),
    (
        "Empieza 301 con Alex, Sam y el bot",
        "start_game",
        {"game": 301, "bot_level": 60, "players": ["Alex", "Sam"]},
        "Game on: 301 con Alex, Sam y el bot.",
    ),
    (
        "Juega 501 para Ann Bob Cid Dan Eve Fay Gus Hal Ida",
        "start_game",
        {
            "game": 501,
            "bot_level": 0,
            "players": ["Ann", "Bob", "Cid", "Dan", "Eve", "Fay", "Gus", "Hal", "Ida"],
        },
        "Este juego admite como máximo 4 jugadores; los juegos de fiesta, hasta ocho.",
    ),
    (
        f"Juega 501 para Alex y {LONG_NAME}",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", LONG_NAME]},
        f"«{LONG_NAME[:20]}…» es demasiado largo para un nombre de jugador, que tiene como máximo 20 caracteres.",
    ),
    (
        f"Juega la partida {LONG_GAME}",
        "start_game",
        {"game": LONG_GAME, "bot_level": 0},
        f"Ningún juego se llama «{LONG_GAME[:64]}…». Nombra uno de los juegos de práctica, como 501, Cricket o Around the Clock.",
    ),
    (
        "Juega 101 para Alex y Sam",
        "start_game",
        {"game": 101, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 101 con Alex y Sam.",
    ),
    (
        "Alex hace 61",
        "enter_visit",
        {"score": 61, "player": "Alex"},
        "61 para Alex, quedan 40. Sam, te quedan 101.",
    ),
    (
        "Sam tiene 100",
        "enter_visit",
        {"score": 100, "player": "Sam"},
        "Sin puntos: Sam sigue con 101. Alex, te quedan 40.",
    ),
    (
        "Cierre con dos dardos",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "¡Game shot, y el partido, Alex!",
    ),
    (
        "Juega 501 para Alex y Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 con Alex y Sam.",
    ),
    (
        "Alex hace 140",
        "enter_visit",
        {"score": 140, "player": "Alex"},
        "140 para Alex, quedan 361. Sam, te quedan 501.",
    ),
    (
        "Alex cierra",
        "enter_visit",
        {"checkout": True, "player": "Alex"},
        "Le toca a Sam, no a Alex.",
    ),
    (
        "140 puntos",
        "enter_visit",
        {"score": 140},
        "140 para Sam, quedan 361. Alex, te quedan 361.",
    ),
    (
        "ciento cuarenta",
        "enter_visit",
        {"score": 140},
        "140 para Alex, quedan 221. Sam, te quedan 361.",
    ),
    (
        "Game shot en tres dardos",
        "enter_visit",
        {"checkout": True, "darts": 3},
        "Ninguna tirada cierra 361 con estas reglas y dardos.",
    ),
    (
        "Checkout con 1 dardo",
        "enter_visit",
        {"checkout": True, "darts": 1},
        "Ninguna tirada cierra 361 con estas reglas y dardos.",
    ),
    ("Triple 20", "throw_dart", {"segment": "T20"}, "Triple 20, quedan 301."),
    ("Doble 16", "throw_dart", {"segment": "D16"}, "Doble 16, quedan 269."),
    ("Simple 5", "throw_dart", {"segment": "S5"}, "Simple 5, quedan 264."),
    ("Siguiente jugador", "next_player", {}, "Alex, te quedan 221."),
    ("Bull", "throw_dart", {"segment": "BULL"}, "Bull, quedan 171."),
    ("Bull simple", "throw_dart", {"segment": "25"}, "25, quedan 146."),
    ("Fallo", "throw_dart", {"segment": "MISS"}, "Fallo, quedan 146."),
    ("Siguiente jugador", "next_player", {}, "Sam, te quedan 264."),
    ("Deshacer", "undo_visit", {}, "Deshecho: 75 de Alex."),
    (
        "Tirada 100",
        "enter_visit",
        {"score": 100},
        "100 para Alex, quedan 121. Sam, te quedan 264.",
    ),
    (
        f"{LONG_NAME} hace 100",
        "enter_visit",
        {"score": 100, "player": LONG_NAME},
        f"«{LONG_NAME[:20]}…» es demasiado largo para un nombre de jugador, que tiene como máximo 20 caracteres.",
    ),
]

# The same with Home Assistant in French.
FRENCH = [
    (
        "Lance 501 pour Alex et Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on\xa0: 501 avec Alex et Sam.",
    ),
    (
        "Joue 301 avec Alex, Sam et Kim",
        "start_game",
        {"game": 301, "bot_level": 0, "players": ["Alex", "Sam", "Kim"]},
        "Game on\xa0: 301 avec Alex, Sam et Kim.",
    ),
    (
        "Lance cinq cent un",
        "start_game",
        {"game": 501, "bot_level": 0},
        "Game on\xa0: 501 avec Alex, Sam et Kim.",
    ),
    (
        "Lancez la partie Cricket pour Alex et Sam",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on\xa0: Cricket avec Alex et Sam.",
    ),
    (
        "Lance la partie Cricket pour Alex",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex"]},
        "Game on\xa0: Cricket avec Alex.",
    ),
    (
        "Joue une partie de Around the Clock",
        "start_game",
        {"game": "Around the Clock", "bot_level": 0},
        "Game on\xa0: Around the Clock avec Alex.",
    ),
    (
        "Lance la partie Entraînement aux doubles",
        "start_game",
        {"game": "Entraînement aux doubles", "bot_level": 0},
        "Game on\xa0: Entraînement aux doubles avec Alex.",
    ),
    (
        "Joue 501 pour Alex contre le bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on\xa0: 501 avec Alex et le bot.",
    ),
    (
        "Joue 501 pour Alex et le bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on\xa0: 501 avec Alex et le bot.",
    ),
    (
        "Joue la partie Cricket contre le bot",
        "start_game",
        {"game": "Cricket", "bot_level": 60},
        "Game on\xa0: Cricket avec Alex et le bot.",
    ),
    (
        "Joue 501 contre le bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on\xa0: 501 avec Alex et le bot.",
    ),
    (
        "Lance 301 avec Alex, Sam et le bot",
        "start_game",
        {"game": 301, "bot_level": 60, "players": ["Alex", "Sam"]},
        "Game on\xa0: 301 avec Alex, Sam et le bot.",
    ),
    (
        "Lance 501 pour Ann Bob Cid Dan Eve Fay Gus Hal Ida",
        "start_game",
        {
            "game": 501,
            "bot_level": 0,
            "players": ["Ann", "Bob", "Cid", "Dan", "Eve", "Fay", "Gus", "Hal", "Ida"],
        },
        "Ce jeu accepte 4 joueurs au maximum\xa0; les jeux de soirée jusqu'à huit.",
    ),
    (
        f"Lance 501 pour Alex et {LONG_NAME}",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", LONG_NAME]},
        f"«\xa0{LONG_NAME[:20]}…\xa0» est trop long pour un nom de joueur, qui compte au plus 20 caractères.",
    ),
    (
        f"Lance la partie {LONG_GAME}",
        "start_game",
        {"game": LONG_GAME, "bot_level": 0},
        f"Aucun jeu ne s'appelle «\xa0{LONG_GAME[:64]}…\xa0». Nommez un des jeux d'entraînement, par exemple 501, Cricket ou Around the Clock.",
    ),
    (
        "Lance 101 pour Alex et Sam",
        "start_game",
        {"game": 101, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on\xa0: 101 avec Alex et Sam.",
    ),
    (
        "Alex a 61 points",
        "enter_visit",
        {"score": 61, "player": "Alex"},
        "61 pour Alex, reste 40. Sam, il vous reste 101.",
    ),
    (
        "Sam fait 100",
        "enter_visit",
        {"score": 100, "player": "Sam"},
        "Aucun point\xa0: Sam reste à 101. Alex, il vous reste 40.",
    ),
    (
        "Checkout en deux fléchettes",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Game shot, et le match, Alex\xa0!",
    ),
    (
        "Lance 501 pour Alex et Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on\xa0: 501 avec Alex et Sam.",
    ),
    (
        "Alex a fait 140",
        "enter_visit",
        {"score": 140, "player": "Alex"},
        "140 pour Alex, reste 361. Sam, il vous reste 501.",
    ),
    (
        "Alex finit",
        "enter_visit",
        {"checkout": True, "player": "Alex"},
        "C'est à Sam de lancer, pas à Alex.",
    ),
    (
        "140 points",
        "enter_visit",
        {"score": 140},
        "140 pour Sam, reste 361. Alex, il vous reste 361.",
    ),
    (
        "cent quarante",
        "enter_visit",
        {"score": 140},
        "140 pour Alex, reste 221. Sam, il vous reste 361.",
    ),
    (
        "Game shot en trois fléchettes",
        "enter_visit",
        {"checkout": True, "darts": 3},
        "Aucune volée ne finit 361 avec ces règles et ces fléchettes.",
    ),
    (
        "Finish en 1 fléchette",
        "enter_visit",
        {"checkout": True, "darts": 1},
        "Aucune volée ne finit 361 avec ces règles et ces fléchettes.",
    ),
    ("Triple 20", "throw_dart", {"segment": "T20"}, "Triple 20, reste 301."),
    ("Double 16", "throw_dart", {"segment": "D16"}, "Double 16, reste 269."),
    ("Simple 5", "throw_dart", {"segment": "S5"}, "Simple 5, reste 264."),
    ("Joueur suivant", "next_player", {}, "Alex, il vous reste 221."),
    ("Bull", "throw_dart", {"segment": "BULL"}, "Bull, reste 171."),
    ("Simple bull", "throw_dart", {"segment": "25"}, "25, reste 146."),
    ("Raté", "throw_dart", {"segment": "MISS"}, "Raté, reste 146."),
    ("Joueur suivant", "next_player", {}, "Sam, il vous reste 264."),
    ("Annule la dernière volée", "undo_visit", {}, "Annulé\xa0: 75 de Alex."),
    (
        "Volée 100",
        "enter_visit",
        {"score": 100},
        "100 pour Alex, reste 121. Sam, il vous reste 264.",
    ),
    (
        f"{LONG_NAME} a fait 100",
        "enter_visit",
        {"score": 100, "player": LONG_NAME},
        f"«\xa0{LONG_NAME[:20]}…\xa0» est trop long pour un nom de joueur, qui compte au plus 20 caractères.",
    ),
]

# The same with Home Assistant in Dutch.
DUTCH = [
    (
        "Speel 501 voor Alex en Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 met Alex en Sam.",
    ),
    (
        "Start 301 met Alex, Sam en Kim",
        "start_game",
        {"game": 301, "bot_level": 0, "players": ["Alex", "Sam", "Kim"]},
        "Game on: 301 met Alex, Sam en Kim.",
    ),
    (
        "Start vijfhonderdeen",
        "start_game",
        {"game": 501, "bot_level": 0},
        "Game on: 501 met Alex, Sam en Kim.",
    ),
    (
        "Start het spel Cricket voor Alex en Sam",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: Cricket met Alex en Sam.",
    ),
    (
        "Speel het spel Cricket voor Alex",
        "start_game",
        {"game": "Cricket", "bot_level": 0, "players": ["Alex"]},
        "Game on: Cricket met Alex.",
    ),
    (
        "Speel een spel Around the Clock",
        "start_game",
        {"game": "Around the Clock", "bot_level": 0},
        "Game on: Around the Clock met Alex.",
    ),
    (
        "Start het spel Dubbeltraining",
        "start_game",
        {"game": "Dubbeltraining", "bot_level": 0},
        "Game on: Dubbeltraining met Alex.",
    ),
    (
        "Speel 501 voor Alex tegen de bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 met Alex en de bot.",
    ),
    (
        "Speel 501 voor Alex en de bot",
        "start_game",
        {"game": 501, "bot_level": 60, "players": ["Alex"]},
        "Game on: 501 met Alex en de bot.",
    ),
    (
        "Speel het spel Cricket tegen de bot",
        "start_game",
        {"game": "Cricket", "bot_level": 60},
        "Game on: Cricket met Alex en de bot.",
    ),
    (
        "Speel 501 tegen de bot",
        "start_game",
        {"game": 501, "bot_level": 60},
        "Game on: 501 met Alex en de bot.",
    ),
    (
        "Start 301 met Alex, Sam en de bot",
        "start_game",
        {"game": 301, "bot_level": 60, "players": ["Alex", "Sam"]},
        "Game on: 301 met Alex, Sam en de bot.",
    ),
    (
        "Speel 501 voor Ann Bob Cid Dan Eve Fay Gus Hal Ida",
        "start_game",
        {
            "game": 501,
            "bot_level": 0,
            "players": ["Ann", "Bob", "Cid", "Dan", "Eve", "Fay", "Gus", "Hal", "Ida"],
        },
        "Dit spel neemt maximaal 4 spelers; partyspellen tot acht.",
    ),
    (
        f"Speel 501 voor Alex en {LONG_NAME}",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", LONG_NAME]},
        f"‘{LONG_NAME[:20]}…’ is te lang voor een spelersnaam, die hoogstens 20 tekens heeft.",
    ),
    (
        f"Start het spel {LONG_GAME}",
        "start_game",
        {"game": LONG_GAME, "bot_level": 0},
        f"Geen spel heet ‘{LONG_GAME[:64]}…’. Noem een van de oefenspellen, zoals 501, Cricket of Around the Clock.",
    ),
    (
        "Speel 101 voor Alex en Sam",
        "start_game",
        {"game": 101, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 101 met Alex en Sam.",
    ),
    (
        "Alex heeft 61",
        "enter_visit",
        {"score": 61, "player": "Alex"},
        "61 voor Alex, nog 40. Sam, je hebt nog 101 nodig.",
    ),
    (
        "Sam gooit 100",
        "enter_visit",
        {"score": 100, "player": "Sam"},
        "Geen score: Sam blijft op 101. Alex, je hebt nog 40 nodig.",
    ),
    (
        "Uitgooi met twee darts",
        "enter_visit",
        {"checkout": True, "darts": 2},
        "Game shot, en de wedstrijd, Alex!",
    ),
    (
        "Speel 501 voor Alex en Sam",
        "start_game",
        {"game": 501, "bot_level": 0, "players": ["Alex", "Sam"]},
        "Game on: 501 met Alex en Sam.",
    ),
    (
        "Alex heeft 140",
        "enter_visit",
        {"score": 140, "player": "Alex"},
        "140 voor Alex, nog 361. Sam, je hebt nog 501 nodig.",
    ),
    (
        "Alex gooit uit",
        "enter_visit",
        {"checkout": True, "player": "Alex"},
        "Sam is aan de beurt, niet Alex.",
    ),
    (
        "140 punten",
        "enter_visit",
        {"score": 140},
        "140 voor Sam, nog 361. Alex, je hebt nog 361 nodig.",
    ),
    (
        "honderdveertig",
        "enter_visit",
        {"score": 140},
        "140 voor Alex, nog 221. Sam, je hebt nog 361 nodig.",
    ),
    (
        "Game shot in drie pijlen",
        "enter_visit",
        {"checkout": True, "darts": 3},
        "Geen beurt gooit 361 uit met deze regels en darts.",
    ),
    (
        "Checkout met 1 pijl",
        "enter_visit",
        {"checkout": True, "darts": 1},
        "Geen beurt gooit 361 uit met deze regels en darts.",
    ),
    ("Triple 20", "throw_dart", {"segment": "T20"}, "Triple 20, nog 301."),
    ("Dubbel 16", "throw_dart", {"segment": "D16"}, "Dubbel 16, nog 269."),
    ("Enkel 5", "throw_dart", {"segment": "S5"}, "Enkel 5, nog 264."),
    ("Volgende speler", "next_player", {}, "Alex, je hebt nog 221 nodig."),
    ("Bull", "throw_dart", {"segment": "BULL"}, "Bull, nog 171."),
    ("Enkel bull", "throw_dart", {"segment": "25"}, "25, nog 146."),
    ("Mis", "throw_dart", {"segment": "MISS"}, "Mis, nog 146."),
    ("Volgende speler", "next_player", {}, "Sam, je hebt nog 264 nodig."),
    ("Ongedaan maken", "undo_visit", {}, "Teruggenomen: 75 van Alex."),
    (
        "Beurt 100",
        "enter_visit",
        {"score": 100},
        "100 voor Alex, nog 121. Sam, je hebt nog 264 nodig.",
    ),
    (
        f"{LONG_NAME} heeft 100",
        "enter_visit",
        {"score": 100, "player": LONG_NAME},
        f"‘{LONG_NAME[:20]}…’ is te lang voor een spelersnaam, die hoogstens 20 tekens heeft.",
    ),
]
SPOKEN = {"en": ENGLISH, "de": GERMAN, "es": SPANISH, "fr": FRENCH, "nl": DUTCH}


async def say(hass, text: str) -> str:
    """What Assist answers to a sentence."""
    result = await conversation.async_converse(hass, text, None, Context())
    return result.response.speech["plain"]["speech"]


async def listen(hass, language: str):
    """Home Assistant in a language, with a board and both voice blueprints: the
    calls of actions, as Assist makes them."""
    # Assist reads the words of numbers in the language of Home Assistant.
    hass.config.language = language
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})
    await setup_manual(hass)
    await automate_all(
        hass, [("start_game_by_voice", {}), ("enter_darts_by_voice", {})]
    )
    return async_capture_events(hass, EVENT_CALL_SERVICE)


def actions(calls) -> list[tuple[str, dict]]:
    """The actions of the integration among the calls, with their data."""
    return [
        (call.data["service"], call.data["service_data"])
        for call in calls
        if call.data["domain"] == "autodarts"
    ]


def test_the_voice_blueprints_speak_every_language_of_the_integration():
    assert list(SPOKEN) == list(LANGUAGES)


@pytest.mark.parametrize("language", SPOKEN)
async def test_assist_runs_every_sentence_through_the_blueprints(
    hass, caplog, language
):
    """Each sentence reaches its action with the data the blueprint makes of it,
    and Assist answers what the action says: what started or was entered, or why
    it was refused, never "Done"."""
    calls = await listen(hass, language)
    for text, action, data, answer in SPOKEN[language]:
        calls.clear()
        said = await say(hass, text)
        assert (actions(calls), said) == ([(action, data)], answer), text
    # A refused sentence is no error of the automation, as one a schema refused was.
    assert not [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.ERROR
        and record.name.startswith("homeassistant.components.automation")
    ]


# Commands of Assist itself in each language, which the sentences of the blueprints
# leave to it: a timer, the time and "cancel", which Assist hears as "never mind".
OWN_COMMANDS = {
    "en": ["Start a timer for 5 minutes", "What time is it", "Never mind"],
    "de": ["Starte einen Timer für 5 Minuten", "Wie spät ist es", "Abbrechen"],
    "es": ["Inicia un temporizador de 5 minutos", "Qué hora es", "Cancelar"],
    "fr": ["Lance un minuteur de 5 minutes", "Quelle heure est-il", "Annuler"],
    "nl": ["Start een timer van 5 minuten", "Hoe laat is het", "Annuleer"],
}

# Commands for the volume, the heating or a light, with a number after a few words.
OTHER_DEVICES = {
    "en": ["Set the volume to 50", "Set the temperature to 21"],
    "de": ["Stelle die Lautstärke auf 50", "Stelle die Temperatur auf 21"],
    "es": ["Pon el volumen a 50", "Pon la temperatura a 21", "Sube el volumen a 30"],
    "fr": ["Mets le volume a 50", "Mets le volume à 50", "Règle la température à 21"],
    "nl": ["Zet het volume op 50", "Zet de temperatuur op 21"],
}


@pytest.mark.parametrize("language", SPOKEN)
async def test_assist_keeps_its_own_commands(hass, language):
    """Assist hears the sentences of the blueprints before its own commands, so they
    need a number or a word of darts: a timer stays a timer in every language."""
    calls = await listen(hass, language)
    for text in OWN_COMMANDS[language]:
        result = await conversation.async_converse(hass, text, None, Context())
        # Assist knew the command, and no action of the integration ran for it.
        assert result.response.error_code != NO_INTENT_MATCH, text
        assert not actions(calls), text
    # Commands for other devices that hold a number are not darts either, even when
    # Assist has no such device to act on.
    for text in OTHER_DEVICES[language]:
        await conversation.async_converse(hass, text, None, Context())
        assert not actions(calls), text


# Sentences of one's own: the blueprint knows the words that join the names and the
# articles before the bot in every language of the integration, also those its own
# sentences don't use, such as "un bot", "het bot" and "&".
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
    names only join them, and the bot at the end with any of its articles is the
    bot."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})
    await setup_manual(hass)
    await automate_all(hass, [("start_game_by_voice", {"sentences": OWN_SENTENCES})])
    calls = async_capture_events(hass, EVENT_CALL_SERVICE)
    for text, players, bot_level in OWN_LANGUAGES:
        calls.clear()
        said = await say(hass, text)
        others = " and ".join(players[1:] + ["the bot"] * (bot_level > 0))
        data = {"game": 501, "bot_level": bot_level, "players": players}
        assert (actions(calls), said) == (
            [("start_game", data)],
            f"Game on: 501 with {players[0]} and {others}.",
        ), text


# Where a guide gives sentences that need Home Assistant in another language.
OTHER_LANGUAGE = re.compile(
    r"- (?:with Home Assistant |mit Home Assistant )?(?:in|auf) (\w+)"
)
LANGUAGE_NAMES = {
    "English": "en",
    "Englisch": "en",
    "German": "de",
    "Deutsch": "de",
    "Spanish": "es",
    "Spanisch": "es",
    "French": "fr",
    "Französisch": "fr",
    "Dutch": "nl",
    "Niederländisch": "nl",
}
QUOTED = re.compile(r'"([^"]+)"|„([^“]+)“')


def _examples(page: str) -> dict[str, set[str]]:
    """The sentences a guide gives as examples for the voice blueprints, in the
    overview of the blueprints and under "Say for example", by the language
    Home Assistant needs for them."""
    text = (ROOT / "docs" / page).read_text(encoding="utf-8")
    own = "de" if page.endswith(".de.md") else "en"
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
    found: dict[str, set[str]] = {language: set() for language in SPOKEN}
    for line in [*rows, *"".join(lists).splitlines()]:
        other = OTHER_LANGUAGE.match(line)
        language = LANGUAGE_NAMES[other.group(1)] if other else own
        found[language] |= {first or second for first, second in QUOTED.findall(line)}
    return found


@pytest.mark.parametrize("page", ["automations.md", "automations.de.md"])
def test_every_example_of_the_guides_is_said_to_assist(page):
    """The guides give examples in every language of the integration, and no
    sentence that the test above leaves out, in the language Home Assistant needs
    for it."""
    for language, sentences in _examples(page).items():
        said = {text for text, *_ in SPOKEN[language]}
        assert sentences, language
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
