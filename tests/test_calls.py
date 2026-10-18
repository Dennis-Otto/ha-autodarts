"""The words of the callers and of the weekly report, in the language of Home
Assistant: what the board events bring for the blueprints."""

import pytest

from custom_components.autodarts.calls import Caller, speaks

# The defaults of the blueprints before the board events brought the words: the
# calls in English stay what they were.
ENGLISH = [
    ("bust", {"player": 1, "players": 2}, "No score"),
    (
        "turn_changed",
        {
            "player": 2,
            "name": "Sam",
            "players": 2,
            "remaining": 81,
            "checkout": "T15 D18",
        },
        "Sam, you require 81",
    ),
    (
        "turn_changed",
        {"player": 1, "players": 1, "remaining": 40, "checkout": "D20"},
        "You require 40",
    ),
    (
        "turn_changed",
        {
            "player": 2,
            "players": 2,
            "bot": True,
            "remaining": 141,
            "checkout": "T20 T7 D20",
        },
        "Bot, you require 141",
    ),
    (
        "turn_changed",
        {"player": 2, "players": 3, "name": None, "remaining": 32, "checkout": "D16"},
        "Player 2, you require 32",
    ),
    (
        "leg_won",
        {"player": 2, "name": "Sam", "players": 2},
        "Game shot, and the leg, Sam!",
    ),
    ("leg_won", {"player": 1, "players": 1}, "Game shot, and the leg!"),
    (
        "leg_won",
        {"player": 1, "name": "Alex", "players": 4, "team_name": "Alex & Kim"},
        "Game shot, and the leg, Alex & Kim!",
    ),
    (
        "leg_won",
        {"player": 2, "name": "Lea", "players": 2, "rounds": 10, "remaining": 32},
        "Round limit, and the leg, Lea!",
    ),
    ("leg_won", {"player": 1, "players": 1, "rounds": 10}, "Round limit, and the leg!"),
    (
        "match_won",
        {"player": 2, "name": "Sam", "players": 2},
        "Game shot, and the match, Sam!",
    ),
    ("match_won", {"player": 1, "players": 1}, "Game shot, and the match!"),
    (
        "match_won",
        {"player": 2, "name": "Lea", "players": 2, "rounds": 1},
        "Round limit, and the match, Lea!",
    ),
    (
        "match_won",
        {"player": 1, "players": 1, "rounds": 1},
        "Round limit, and the match!",
    ),
    ("visit_thrown", {"score": 180, "darts": 3}, "One hundred and eighty!"),
    ("visit_completed", {"score": 125, "darts": 3}, "125"),
    ("visit_completed", {"score": 0, "darts": 3}, "No score"),
    ("dart_detected", {"segment": "T20", "score": 60}, "Treble 20"),
    ("dart_detected", {"segment": "D16", "score": 32}, "Double 16"),
    ("dart_detected", {"segment": "S5", "score": 5}, "5"),
    ("dart_detected", {"segment": "25", "score": 25}, "25"),
    ("dart_detected", {"segment": "Bull", "score": 50}, "Bull"),
    ("dart_detected", {"segment": "M", "score": 0}, "Miss"),
]


async def caller(hass, language: str) -> Caller:
    hass.config.language = language
    loaded = Caller()
    await loaded.async_load(hass)
    return loaded


@pytest.mark.parametrize(("kind", "attributes", "call"), ENGLISH)
async def test_the_english_calls_are_those_the_blueprints_said(
    hass, kind, attributes, call
):
    assert (await caller(hass, "en")).words(kind, attributes) == {"call": call}


async def test_a_turn_calls_the_next_player_as_a_caller_does(hass):
    english = await caller(hass, "en")
    match = {"player": 2, "name": "Sam", "players": 2, "remaining": 169}
    setup = {"route": "T20 T20 S17", "leave": 32}
    assert english.call("turn_changed", {**match, "setup": setup}) == (
        "Sam, leave yourself 32"
    )
    assert english.call(
        "turn_changed", {"player": 1, "players": 1, "remaining": 169, "setup": setup}
    ) == ("Leave yourself 32")
    # Without a checkout or a setup: who throws in a match, nothing alone.
    assert english.call("turn_changed", {**match, "setup": None}) == "Sam to throw."
    assert english.call("turn_changed", {"player": 1, "players": 1}) == ""
    assert english.call("turn_changed", {**match, "bull_off": True}) == (
        "Sam, throw for the bull"
    )
    assert english.call("bull_off_won", match) == "Sam to throw first. Game on!"


async def test_the_german_calls(hass):
    german = await caller(hass, "de")
    match = {"player": 2, "name": "Lea", "players": 2}
    said = [
        german.call(kind, attributes)
        for kind, attributes in [
            ("turn_changed", {**match, "remaining": 101, "checkout": "T20 S1 D20"}),
            (
                "turn_changed",
                {"player": 1, "players": 1, "remaining": 40, "checkout": "D20"},
            ),
            ("turn_changed", {**match, "setup": {"leave": 32, "route": "T20 T20 S17"}}),
            ("turn_changed", {**match, "bot": True}),
            ("turn_changed", {**match, "bull_off": True}),
            ("bull_off_won", match),
            ("bust", match),
            ("leg_won", {**match, "players": 3, "name": None, "player": 3}),
            ("match_won", match),
            ("match_won", {**match, "rounds": 1}),
            ("visit_thrown", {"score": 180}),
            ("visit_completed", {"score": 0}),
            ("dart_detected", {"segment": "T19", "score": 57}),
            ("dart_detected", {"segment": "D8", "score": 16}),
            ("dart_detected", {"segment": "M", "score": 0}),
        ]
    ]
    assert said == [
        "Lea, du brauchst 101",
        "Du brauchst 40",
        "Lea, stell dir die 32",
        "Bot ist dran.",
        "Lea, dein Wurf aufs Bull",
        "Lea beginnt. Game on!",
        "Überworfen",
        "Game shot, und das Leg, Spieler 3!",
        "Game shot, und das Match, Lea!",
        "Rundenlimit, und das Match, Lea!",
        "Einhundertachtzig!",
        "Keine Punkte",
        "Triple 19",
        "Doppel 8",
        "Fehlwurf",
    ]


@pytest.mark.parametrize(
    ("language", "spoken"),
    [
        ("en", "en"),
        ("en-GB", "en"),
        ("de-CH", "de"),
        ("es-419", "es"),
        ("fr_CA", "fr"),
        ("NL", "nl"),
        ("pt-BR", "en"),
    ],
)
async def test_a_regional_language_speaks_its_language(hass, language, spoken):
    assert speaks(language) == spoken
    assert (await caller(hass, language)).language == spoken


async def test_other_events_bring_no_words(hass):
    english = await caller(hass, "en")
    assert english.words("takeout_started", {}) == {}
    assert english.words("dart_corrected", {"segment": "T20", "score": 60}) == {}
    # Before the words are loaded, no event brings any; the blueprints then say
    # their own.
    assert Caller().words("bust", {"player": 1}) == {}
    assert Caller().words("weekly_report", {"darts": 3}) == {}


WEEK = {
    "darts": 312,
    "visits": 104,
    "sessions": 3,
    "training_minutes": 95,
    "average": 54.25,
    "average_change": 2.14,
    "highest_visit": 140,
    "scores_180": 1,
    "checkout_rate": 31.25,
    "streak": 4,
    "personal_bests": [{"record": "highest_visit"}, {"record": "fewest_darts_501"}],
}
QUIET = {
    **WEEK,
    "darts": 10,
    "sessions": 1,
    "training_minutes": 3,
    "average": 20.0,
    "average_change": -3.25,
    "highest_visit": None,
    "scores_180": 0,
    "checkout_rate": None,
    "streak": 1,
    "personal_bests": [],
}


async def test_the_english_summary_is_the_one_the_blueprint_wrote(hass):
    english = await caller(hass, "en")
    assert english.words("weekly_report", WEEK) == {
        "title": "Your darts week",
        "summary": "312 darts in 95 minutes at the board, 3 sessions. "
        "3-dart average 54.2 (+2.1 on the week before). Best visit 140, 1 × 180. "
        "Checkout rate 31.2 %. 4 days in a row. 2 new personal bests.",
    }
    assert english.summary(QUIET) == (
        "10 darts in 3 minutes at the board, 1 session. "
        "3-dart average 20.0 (-3.2 on the week before). 1 day in a row."
    )
    assert english.summary({**QUIET, "darts": 12, "average": None, "sessions": 0}) == (
        "12 darts in 3 minutes at the board. 1 day in a row."
    )
    assert english.summary(
        {
            **QUIET,
            "darts": 30,
            "training_minutes": 1,
            "average_change": None,
            "highest_visit": 60,
            "streak": 0,
            "personal_bests": [{"record": "doubles"}],
        }
    ) == (
        "30 darts in 1 minute at the board, 1 session. "
        "3-dart average 20.0. Best visit 60. 1 new personal best."
    )
    # A week of darts without a session, with every value missing.
    assert english.summary({"darts": 3, "sessions": 2, "average_change": 0}) == (
        "3 darts, 2 sessions."
    )


async def test_the_summary_writes_the_numbers_of_its_language(hass):
    german = await caller(hass, "de")
    assert german.words("weekly_report", WEEK) == {
        "title": "Deine Dartwoche",
        "summary": "312 Darts in 95 Minuten am Board, 3 Sessions. "
        "3-Dart-Average 54,2 (+2,1 zur Vorwoche). Beste Aufnahme 140, 1 × 180. "
        "Checkout-Quote 31,2 %. 4 Tage in Folge. 2 neue Bestleistungen.",
    }
    assert german.summary(QUIET) == (
        "10 Darts in 3 Minuten am Board, 1 Session. "
        "3-Dart-Average 20,0 (-3,2 zur Vorwoche). 1 Tag in Folge."
    )
    french = await caller(hass, "fr")
    assert french.summary({**QUIET, "personal_bests": [{}], "training_minutes": 0}) == (
        "10 fléchettes, 1 session. Moyenne 3 fléchettes 20,0 (-3,2 par rapport à la "
        "semaine précédente). 1 jour d'affilée. 1 nouveau record personnel."
    )
