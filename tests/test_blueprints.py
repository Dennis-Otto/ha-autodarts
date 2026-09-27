"""The automation blueprints, run by Home Assistant's own automation engine."""

import asyncio
import itertools
import json
import re
import shutil
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, quote, urlsplit

import pytest
from homeassistant.components.blueprint import models
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import load_yaml
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
    get_scheduled_timer_handles,
)

from custom_components.autodarts.local_coordinator import EVENT_TYPES

from .local_helpers import BULL, S20, T20, board, entity_id, setup_bridge
from .local_helpers import WEBHOOK_PATH as ONLINE_BRIDGE

ROOT = Path(__file__).parents[1]
BLUEPRINTS = ROOT / "blueprints" / "automation" / "autodarts"
PATHS = sorted(BLUEPRINTS.glob("*.yaml"))
EVENTS = "event.autodarts_board_events"
SOURCE = "https://github.com/Dennis-Otto/ha-autodarts/blob/main/blueprints/automation/autodarts/"
IMPORT = re.compile(
    r"https://my\.home-assistant\.io/redirect/blueprint_import/\?blueprint_url=[^)\s\"']+"
)
# Attributes a blueprint reads from a board event.
READS = re.compile(r"(?:attributes|event)\.get\('(\w+)'|attributes\.(?!get\b)(\w+)")
S1 = ("S1", 1, 1)
D20 = ("D20", 20, 2)
MOMENTS = (
    "maximum",
    "high_finish",
    "bust",
    "leg",
    "match",
    "personal_best",
    "daily_goal",
    "bull_off",
    "achievement",
    "tournament",
)
# Consecutive events always get distinct timestamps, even with a frozen clock.
TICKS = itertools.count(1)


@pytest.fixture(autouse=True)
async def blueprint_folder(hass, tmp_path):
    """Serve the repository blueprints from a temporary configuration folder."""
    hass.config.config_dir = str(tmp_path)
    shutil.copytree(BLUEPRINTS, tmp_path / "blueprints" / "automation" / "autodarts")
    assert await async_setup_component(hass, "event", {})


async def automate_all(hass, instances: list[tuple[str, dict]]) -> None:
    configs = [
        {"use_blueprint": {"path": f"autodarts/{name}.yaml", "input": inputs}}
        for name, inputs in instances
    ]
    assert await async_setup_component(hass, "automation", {"automation": configs})
    await hass.async_block_till_done()
    automations = hass.states.async_all("automation")
    assert [state.state for state in automations] == ["on"] * len(configs), automations


async def automate(hass, name: str, inputs: dict) -> None:
    await automate_all(hass, [(name, inputs)])


def fire(hass, event_type: str, **attributes) -> None:
    hass.states.async_set(
        EVENTS,
        (dt_util.utcnow() + timedelta(microseconds=next(TICKS))).isoformat(
            timespec="microseconds"
        ),
        {"event_type": event_type, **attributes},
    )


async def fire_all(hass, events: list[tuple[str, dict]]) -> None:
    for kind, attributes in events:
        fire(hass, kind, **attributes)
        await hass.async_block_till_done()


async def until_waiting(hass, seconds: float) -> None:
    """Let a running automation reach a delay of the given length.

    async_block_till_done() would wait for the whole run, which never ends
    while the clock is frozen.
    """
    for _ in range(200):
        due = [
            handle.when() - hass.loop.time()
            for handle in get_scheduled_timer_handles(hass.loop)
        ]
        if any(seconds - 0.5 < left <= seconds for left in due):
            return
        await asyncio.sleep(0)
    raise AssertionError(f"no delay of {seconds} s started")


async def pass_time(hass, freezer, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def listened(path: Path) -> set[str]:
    """The board events a blueprint triggers on."""
    return {
        kind
        for node in walk(load_yaml(path))
        if node.get("trigger") == "event.received"
        for kind in node["options"]["event_type"]
    }


def read_attributes(path: Path) -> set[str]:
    return {
        name or attribute
        for name, attribute in READS.findall(path.read_text(encoding="utf-8"))
    }


def spoken(calls) -> list[str]:
    return [str(call.data["message"]) for call in calls]


VOICE = {
    "board_events": EVENTS,
    "tts_engine": "tts.home_assistant_cloud",
    "speakers": ["media_player.dartroom"],
}


# -- every blueprint ------------------------------------------------------------


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_blueprint_metadata(path):
    blueprint = models.Blueprint(
        load_yaml(path), expected_domain="automation", schema=BLUEPRINT_SCHEMA
    )
    metadata = blueprint.metadata
    assert metadata["name"].startswith("Autodarts: ")
    assert metadata["source_url"] == SOURCE + path.name
    # The blueprints need the same Home Assistant as the integration.
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert metadata["homeassistant"]["min_version"] == hacs["homeassistant"]
    assert metadata["author"] == "Dennis Otto"
    # Every input explains itself in the blueprint editor.
    for key, entry in blueprint.inputs.items():
        assert entry and entry.get("description"), f"{path.stem}: {key}"


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_blueprints_listen_to_events_of_the_integration(path):
    assert listened(path) <= set(EVENT_TYPES)


@pytest.mark.parametrize(
    "document", ["README.md", "docs/automations.md", "docs/de/automationen.md"]
)
def test_documents_import_every_blueprint(document):
    """Each import button opens the blueprint file on the main branch."""
    text = (ROOT / document).read_text(encoding="utf-8")
    imported = set()
    for link in IMPORT.findall(text):
        encoded = link.split("blueprint_url=", 1)[1]
        (url,) = parse_qs(urlsplit(link).query)["blueprint_url"]
        # Fully encoded, as My Home Assistant expects it.
        assert encoded == quote(url, safe="")
        assert url.startswith(SOURCE), url
        imported.add(url.removeprefix(SOURCE))
    assert imported == {path.name for path in PATHS}


def photo_name(call) -> str:
    """The file a snapshot saves, without the folder and the moment it was taken."""
    folder, _, name = str(call.data["filename"]).rpartition("/")
    assert folder == "/media/autodarts/highlights", folder
    assert call.data["entity_id"] == ["camera.autodarts_board_camera_1"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_", name), name
    return name[20:]


PHOTO = {
    "board_events": EVENTS,
    "camera": "camera.autodarts_board_camera_1",
    "photo_actions": [
        {
            "action": "test.photo",
            "data": {"image": "{{ image }}", "message": "{{ message }}"},
        }
    ],
}


# -- the real board events -------------------------------------------------------


async def visit(hass, coordinator, *darts) -> None:
    """Throw dart by dart, then pull the darts."""
    for count in range(1, len(darts) + 1):
        coordinator.async_receive("state", board(*darts[:count]))
        await hass.async_block_till_done()
    coordinator.async_receive("state", board(*darts, event="Takeout started"))
    coordinator.async_receive("state", board(event="Takeout finished"))
    await hass.async_block_till_done()


async def test_blueprints_follow_the_real_board_events(
    hass, aioclient_mock, hass_client_no_auth
):
    """A practice match, free play and an online match on the board events."""
    entry = await setup_bridge(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = entity_id(hass, "event", "board_events")
    payloads: dict[str, set[str]] = defaultdict(set)

    @callback
    def collect(event) -> None:
        attributes = event.data["new_state"].attributes
        if kind := attributes.get("event_type"):
            payloads[kind].update(attributes)

    async def unchanged_board() -> dict:
        # A reconciliation read while the scenario waits finds the same board.
        return dict(coordinator.data["local"])

    async_track_state_change_event(hass, events, collect)
    speak = async_mock_service(hass, "tts", "speak")
    celebrate = async_mock_service(hass, "test", "celebrate")
    light = async_mock_service(hass, "test", "light")
    photos = async_mock_service(hass, "test", "photo")
    snapshots = async_mock_service(hass, "camera", "snapshot")
    switch_on = async_mock_service(hass, "switch", "turn_on")
    reports = async_mock_service(hass, "test", "report")
    voice = {**VOICE, "board_events": events}
    await automate_all(
        hass,
        [
            (
                "practice_caller",
                {
                    **voice,
                    "bull_off_turn_message": "{{ who }}, throw for the bull",
                    "bull_off_message": "{{ who }} to throw first. Game on!",
                },
            ),
            ("dart_caller", voice),
            (
                "visit_score",
                {
                    "board_events": events,
                    "celebration": [
                        {"action": "test.celebrate", "data": {"score": "{{ score }}"}}
                    ],
                },
            ),
            (
                "light_show",
                {
                    "board_events": events,
                    **{
                        f"{moment}_actions": [
                            {
                                "action": "test.light",
                                "data": {"moment": "{{ moment }}", "who": "{{ who }}"},
                            }
                        ]
                        for moment in MOMENTS
                    },
                    "online_matches": True,
                },
            ),
            (
                "training_session",
                {"board_events": events, "detection": "switch.detection"},
            ),
            # A visit crosses 100 points before its third dart, too.
            (
                "highlight_photo",
                {**PHOTO, "board_events": events, "minimum_score": 100},
            ),
            (
                "weekly_report",
                {
                    "board_events": events,
                    "notify_actions": [
                        {"action": "test.report", "data": {"message": "{{ message }}"}}
                    ],
                },
            ),
        ],
    )
    with patch.object(coordinator.client, "get_state", side_effect=unchanged_board):
        await coordinator.async_set_daily_goal(5)
        await coordinator.async_start_game(
            101, names=["Dennis", "Lea"], legs=1, sets=1, bull_off=True
        )
        await visit(hass, coordinator, BULL)
        await visit(hass, coordinator, S20)
        # 101 - 80 leaves 21: the third dart busts, and it is the fifth of the day.
        await visit(hass, coordinator, T20, S20, T20)
        await visit(hass, coordinator, T20, S1, D20)
        # A party game adds points and the next target to the turn.
        await coordinator.async_start_game("shanghai", names=["Dennis"])
        await visit(hass, coordinator, S1)
        await coordinator.async_play(0)
        await visit(hass, coordinator, T20, T20, T20)
        # A new session every morning keeps the board as it is.
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": entity_id(hass, "button", "reset_training")},
            blocking=True,
        )
        await hass.async_block_till_done()
        # The week ends now instead of on Monday.
        coordinator.reports.report.ends = dt_util.utcnow()
        await coordinator.reports._async_report(dt_util.utcnow())
        await hass.async_block_till_done()
        # A team match names the team of the player who checks out.
        await coordinator.async_start_game(
            101, names=["Dennis", "Lea", "Kim", "Sam"], bull_off=False, teams=True
        )
        await visit(hass, coordinator, T20, S1, D20)
    # Tools for Autodarts reports the moments of an online match; your own 180
    # comes from the board.
    client = await hass_client_no_auth()
    for query in (
        "event=busted&player=Lea",
        "event=gameshot_dennis",
        "event=matchshot",
        "event=180",
    ):
        assert (await client.get(f"{ONLINE_BRIDGE}?{query}")).status == 200
    await hass.async_block_till_done()

    assert spoken(speak) == [
        "Lea, throw for the bull",
        "Dennis to throw first. Game on! Dennis, you require 101",
        "No score",
        "Lea, you require 101",
        "Game shot, and the match, Lea!",
        # The dart caller waits for the end of the practice game.
        "One hundred and eighty!",
        "Game shot, and the match, Dennis & Kim!",
    ]
    assert [call.data for call in celebrate] == [{"score": 180}]
    assert [(call.data["moment"], call.data["who"]) for call in light] == [
        ("bull_off", "Dennis"),
        ("daily_goal", ""),
        ("bust", "Dennis"),
        ("personal_best", ""),
        ("match", "Lea"),
        # Lea's checkout of 101, first leg and first match unlock achievements.
        ("achievement", "Lea"),
        ("achievement", "Lea"),
        ("achievement", "Lea"),
        ("maximum", ""),
        ("personal_best", ""),
        ("match", "Dennis"),
        # Dennis checks out 101 for the team; the leg and the match count for Kim, too.
        ("achievement", "Dennis"),
        ("achievement", "Dennis"),
        ("achievement", "Dennis"),
        ("achievement", "Kim"),
        ("achievement", "Kim"),
        ("bust", "Lea"),
        ("leg", "dennis"),
        ("match", ""),
    ]
    assert not switch_on
    assert [call.data["message"] for call in photos] == [
        "140!",
        "Checkout 101 by Lea!",
        "180!",
        "Checkout 101 by Dennis!",
    ]
    assert [call.data["message"] for call in reports] == [
        "12 darts, 1 session. 3-dart average 123.0. Best visit 180, 1 × 180. "
        "Checkout rate 100.0 %. 1 day in a row. 2 new personal bests."
    ]
    # The gallery names each photo by the time, the player at the board and the score.
    assert [photo_name(call) for call in snapshots] == [
        "Dennis_140.jpg",
        "Lea_checkout-101.jpg",
        "180.jpg",
        "Dennis_checkout-101.jpg",
    ]

    # A round robin of three at 101, everybody winning once: the order of the
    # draw makes Dennis the winner, and the light show plays the tournament.
    with patch.object(coordinator.client, "get_state", side_effect=unchanged_board):
        await coordinator.async_start_tournament(
            players=["Dennis", "Lea", "Kim"],
            game="101",
            legs=1,
            sets=1,
            pause=0,
            rules={"bull_off": False},
        )
        for _ in range(3):
            await visit(hass, coordinator, T20, S1, D20)
            if coordinator.tournament.waiting:
                await coordinator.async_next_tournament_match()
    await hass.async_block_till_done()
    assert (light[-2].data["moment"], light[-1].data) == (
        "match",
        {"moment": "tournament", "who": "Dennis"},
    )

    # Whatever a blueprint reads is in the events it listens to.
    for path in PATHS:
        kinds = listened(path)
        if not kinds:
            continue
        assert kinds <= payloads.keys(), path.stem
        available = set().union(*(payloads[kind] for kind in kinds))
        assert read_attributes(path) <= available, path.stem


# -- celebrate a visit score -------------------------------------------------------


async def test_visit_score_runs_actions_for_high_visits_once(hass):
    calls = async_mock_service(hass, "test", "celebrate")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "visit_score",
        {
            "board_events": EVENTS,
            "minimum_score": 100,
            "celebration": [
                {
                    "action": "test.celebrate",
                    "data": {"score": "{{ score }}", "segments": "{{ segments }}"},
                }
            ],
        },
    )
    three = {"darts": 3, "segments": ["T20", "T20", "S20"], "game": None}
    await fire_all(
        hass,
        [
            ("dart_detected", {"score": 60, "segment": "T20", "dart_index": 3}),
            # With the third dart, not again when the darts are pulled.
            ("visit_thrown", {"score": 140, **three}),
            ("visit_completed", {"score": 140, **three, "thrown": True}),
            ("visit_thrown", {"score": 60, **three}),
            # A shorter visit counts when it completes.
            (
                "visit_completed",
                {"score": 120, "darts": 2, "segments": ["T20", "T20"], "thrown": False},
            ),
            # An older integration without visit_thrown.
            ("visit_completed", {"score": 100, **three}),
        ],
    )
    assert [call.data["score"] for call in calls] == [140, 120, 100]
    assert calls[0].data["segments"] == ["T20", "T20", "S20"]


# -- dart caller ---------------------------------------------------------------------


async def test_dart_caller_announces_visits_and_darts(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "dart_caller", {**VOICE, "call_each_dart": True})
    await fire_all(
        hass,
        [
            ("dart_detected", {"segment": "T20", "score": 60, "dart_index": 1}),
            ("dart_detected", {"segment": "S5", "score": 5, "dart_index": 2}),
            # The third dart is called with its visit.
            ("dart_detected", {"segment": "T20", "score": 60, "dart_index": 3}),
            ("visit_thrown", {"score": 125, "darts": 3, "game": None}),
            ("visit_completed", {"score": 125, "darts": 3, "thrown": True}),
            ("dart_detected", {"segment": "D16", "score": 32, "dart_index": 1}),
            ("dart_detected", {"segment": "M", "score": 0, "dart_index": 2}),
            ("visit_completed", {"score": 32, "darts": 2, "thrown": False}),
            ("dart_detected", {"segment": "Bull", "score": 50, "dart_index": 1}),
            ("dart_detected", {"segment": "25", "score": 25, "dart_index": 2}),
            ("visit_thrown", {"score": 180, "darts": 3, "segments": ["T20"] * 3}),
        ],
    )
    assert spoken(calls) == [
        "Treble 20",
        "5",
        "125",
        "Double 16",
        "Miss",
        "32",
        "Bull",
        "25",
        "One hundred and eighty!",
    ]
    assert calls[0].data["media_player_entity_id"] == ["media_player.dartroom"]
    assert calls[0].data["cache"] is True
    assert "language" not in calls[0].data and "options" not in calls[0].data


async def test_dart_caller_skips_darts_and_practice_games_by_default(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass, "dart_caller", {**VOICE, "visit_message": "{{ score }} points"}
    )
    await fire_all(
        hass,
        [
            ("dart_detected", {"segment": "T20", "score": 60, "dart_index": 1}),
            # The practice caller has the floor during a practice game.
            ("visit_thrown", {"score": 140, "darts": 3, "game": 501}),
            ("visit_thrown", {"score": 100, "darts": 3, "game": None}),
        ],
    )
    assert spoken(calls) == ["100 points"]


async def test_dart_caller_in_practice_games_with_its_own_voice(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "dart_caller",
        {
            **VOICE,
            "silent_in_practice_games": False,
            "language": "de-DE",
            "tts_options": {"voice": "KatjaNeural"},
            "visit_message": "{{ score }} Punkte",
            "maximum_message": "",
        },
    )
    await fire_all(
        hass,
        [
            ("visit_thrown", {"score": 140, "darts": 3, "game": "cricket"}),
            # An empty message stays silent.
            ("visit_thrown", {"score": 180, "darts": 3, "game": 501}),
        ],
    )
    assert spoken(calls) == ["140 Punkte"]
    assert calls[0].data["language"] == "de-DE"
    assert calls[0].data["options"] == {"voice": "KatjaNeural"}


# -- practice caller -------------------------------------------------------------------


async def test_practice_caller_calls_requirements_busts_and_game_shots(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "practice_caller", VOICE)
    match = {"game": 501, "players": 2}
    await fire_all(
        hass,
        [
            (
                "turn_changed",
                {
                    **match,
                    "player": 2,
                    "name": "Sam",
                    "remaining": 81,
                    "checkout": "T15 D18",
                },
            ),
            # No checkout possible and no turn message: silent.
            (
                "turn_changed",
                {
                    **match,
                    "player": 1,
                    "name": None,
                    "remaining": 321,
                    "checkout": None,
                },
            ),
            ("bust", {**match, "player": 1, "name": None, "remaining": 32}),
            (
                "leg_won",
                {**match, "player": 2, "name": "Sam", "darts": 15, "match": False},
            ),
            # The deciding leg leaves the call to the match.
            (
                "leg_won",
                {**match, "player": 2, "name": "Sam", "darts": 12, "match": True},
            ),
            ("match_won", {**match, "player": 2, "name": "Sam", "sets": 1}),
            (
                "turn_changed",
                {
                    "game": 501,
                    "players": 1,
                    "player": 1,
                    "name": None,
                    "remaining": 40,
                    "checkout": "D20",
                },
            ),
            (
                "leg_won",
                {"game": 501, "players": 1, "player": 1, "name": None, "match": False},
            ),
            # Cricket has no checkout: the next player stays silent.
            (
                "turn_changed",
                {
                    "game": "cricket",
                    "players": 2,
                    "player": 2,
                    "name": "Sam",
                    "remaining": None,
                    "checkout": None,
                    "points": 40,
                },
            ),
            ("leg_won", {"game": "cricket", "players": 2, "player": 2, "name": "Sam"}),
        ],
    )
    assert spoken(calls) == [
        "Sam, you require 81",
        "No score",
        "Game shot, and the leg, Sam!",
        "Game shot, and the match, Sam!",
        "You require 40",
        "Game shot, and the leg!",
        "Game shot, and the leg, Sam!",
    ]


async def test_practice_caller_names_the_team_of_a_team_match(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "practice_caller", VOICE)
    teams = {"game": 501, "players": 4, "player": 3, "name": "Kim", "team": 1}
    await fire_all(
        hass,
        [
            ("leg_won", {**teams, "team_name": "Alex & Kim", "match": False}),
            # Without both names, the player at the board is named.
            ("leg_won", {**teams, "team_name": None, "match": False}),
            ("match_won", {**teams, "team_name": "Alex & Kim"}),
        ],
    )
    assert spoken(calls) == [
        "Game shot, and the leg, Alex & Kim!",
        "Game shot, and the leg, Kim!",
        "Game shot, and the match, Alex & Kim!",
    ]


async def test_practice_caller_names_unnamed_players_in_its_language(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "practice_caller",
        {
            **VOICE,
            "turn_message": "{{ who }} ist dran{{ ', ' ~ target if target }}",
            "player_label": "Spieler",
            "language": "de-DE",
        },
    )
    party = {"game": "shanghai", "players": 3, "remaining": None, "checkout": None}
    await fire_all(
        hass,
        [
            ("turn_changed", {**party, "player": 3, "name": None, "target": "7"}),
            (
                "turn_changed",
                {
                    "game": 501,
                    "players": 3,
                    "player": 1,
                    "name": None,
                    "remaining": 501,
                    "checkout": None,
                },
            ),
            # Without its own message, a bull-off throw is the next player's turn.
            (
                "turn_changed",
                {**party, "game": 501, "player": 2, "name": None, "bull_off": True},
            ),
            # A won bull-off stays silent without its message.
            ("bull_off_won", {**party, "game": 501, "player": 2, "distance": 5.0}),
            (
                "turn_changed",
                {**party, "game": 501, "player": 2, "name": None, "remaining": 501},
            ),
        ],
    )
    assert spoken(calls) == [
        "Spieler 3 ist dran, 7",
        "Spieler 1 ist dran",
        "Spieler 2 ist dran",
        "Spieler 2 ist dran",
    ]
    assert calls[0].data["language"] == "de-DE"


async def test_practice_caller_calls_the_bull_off(hass):
    calls = async_mock_service(hass, "tts", "speak")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "practice_caller",
        {
            **VOICE,
            "bull_off_turn_message": "{{ who }}, throw for the bull",
            "bull_off_message": (
                "{{ who }} wins the bull with {{ hit }}"
                "{{ ', ' ~ distance ~ ' mm' if distance is number }}"
            ),
        },
    )
    match = {"game": 101, "players": 2, "remaining": None, "checkout": None}
    won = {**match, "player": 2, "name": "Lea", "hit": "S20"}
    await fire_all(
        hass,
        [
            ("turn_changed", {**match, "player": 2, "name": "Lea", "bull_off": True}),
            (
                "bull_off_won",
                {**match, "player": 1, "name": None, "hit": "BULL", "distance": 3.2},
            ),
            # The winner starts: one call for both.
            (
                "turn_changed",
                {
                    **match,
                    "player": 1,
                    "name": None,
                    "remaining": 101,
                    "checkout": "T17 BULL",
                },
            ),
            ("bull_off_won", {**won, "distance": 12.5}),
            ("turn_changed", {**match, "player": 2, "name": "Lea", "remaining": 501}),
            # A dart without a position has no distance, and nobody says "None".
            ("bull_off_won", {**won, "hit": "25", "distance": None}),
            ("turn_changed", {**match, "player": 2, "name": "Lea", "remaining": 501}),
        ],
    )
    assert spoken(calls) == [
        "Lea, throw for the bull",
        "Player 1 wins the bull with BULL, 3.2 mm Player 1, you require 101",
        "Lea wins the bull with S20, 12.5 mm",
        "Lea wins the bull with 25",
    ]


# -- takeout, detection, alerts ----------------------------------------------------


async def test_takeout_actions(hass):
    started = async_mock_service(hass, "test", "started")
    finished = async_mock_service(hass, "test", "finished")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "takeout",
        {
            "board_events": EVENTS,
            "takeout_started": [{"action": "test.started"}],
            "takeout_finished": [{"action": "test.finished"}],
        },
    )
    fire(hass, "takeout_started")
    await hass.async_block_till_done()
    assert (len(started), len(finished)) == (1, 0)
    fire(hass, "takeout_finished")
    await hass.async_block_till_done()
    assert (len(started), len(finished)) == (1, 1)


async def test_detection_follows_presence(hass):
    turned_on = async_mock_service(hass, "switch", "turn_on")
    turned_off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set("binary_sensor.dartroom", "off")
    hass.states.async_set("switch.autodarts_detection", "off")
    await automate(
        hass,
        "auto_detection",
        {
            "presence": "binary_sensor.dartroom",
            "detection": "switch.autodarts_detection",
            "stop_after": {"minutes": 10},
        },
    )
    hass.states.async_set("binary_sensor.dartroom", "on")
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turned_on] == [
        ["switch.autodarts_detection"]
    ]
    hass.states.async_set("switch.autodarts_detection", "on")
    hass.states.async_set("binary_sensor.dartroom", "off")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()
    assert not turned_off
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=11))
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turned_off] == [
        ["switch.autodarts_detection"]
    ]


async def test_board_alert_waits_for_the_grace_period(hass, freezer):
    alerts = async_mock_service(hass, "test", "alert")
    recoveries = async_mock_service(hass, "test", "recovered")
    hass.states.async_set("binary_sensor.board_connection", "on")
    hass.states.async_set("binary_sensor.camera_problem", "off")
    await automate(
        hass,
        "board_alert",
        {
            "connection": "binary_sensor.board_connection",
            "camera_problem": "binary_sensor.camera_problem",
            "alert_actions": [
                {"action": "test.alert", "data": {"problem": "{{ problem }}"}}
            ],
            "recovery_actions": [
                {
                    "action": "test.recovered",
                    "data": {
                        "problem": "{{ problem }}",
                        "recovered": "{{ recovered }}",
                    },
                }
            ],
        },
    )
    # A short restart neither alerts nor reports a recovery.
    hass.states.async_set("binary_sensor.board_connection", "off")
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=30))
    hass.states.async_set("binary_sensor.board_connection", "on")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=3))
    await hass.async_block_till_done()
    assert not alerts and not recoveries

    hass.states.async_set("binary_sensor.camera_problem", "on")
    await hass.async_block_till_done()
    await pass_time(hass, freezer, 180)
    assert [call.data for call in alerts] == [{"problem": "cameras"}]
    hass.states.async_set("binary_sensor.camera_problem", "off")
    await hass.async_block_till_done()
    assert [call.data for call in recoveries] == [
        {"problem": "cameras", "recovered": True}
    ]

    # A camera that fails while the board restarts is a problem, too.
    hass.states.async_set("binary_sensor.camera_problem", "unavailable")
    await hass.async_block_till_done()
    hass.states.async_set("binary_sensor.camera_problem", "on")
    await hass.async_block_till_done()
    await pass_time(hass, freezer, 180)
    assert [call.data for call in alerts][-1] == {"problem": "cameras"}
    assert len(alerts) == 2

    # A board that stays offline, and its all-clear.
    hass.states.async_set("binary_sensor.board_connection", "off")
    await hass.async_block_till_done()
    await pass_time(hass, freezer, 180)
    assert alerts[-1].data == {"problem": "offline"}
    hass.states.async_set("binary_sensor.board_connection", "on")
    await hass.async_block_till_done()
    assert recoveries[-1].data == {"problem": "offline", "recovered": True}
    assert (len(alerts), len(recoveries)) == (3, 2)


# -- training ------------------------------------------------------------------------


REPORT = {
    "darts_sensor": "sensor.autodarts_training_darts",
    "average_sensor": "sensor.autodarts_training_average",
    "highest_sensor": "sensor.autodarts_training_highest",
    "maximum_sensor": "sensor.autodarts_training_scores_180",
    "report_actions": [{"action": "test.report", "data": {"message": "{{ summary }}"}}],
}


def training_totals(hass, darts: str) -> None:
    for key, value in (
        ("darts", darts),
        ("average", "57.349"),
        ("highest", "140"),
        ("scores_180", "1"),
    ):
        hass.states.async_set(f"sensor.autodarts_training_{key}", value)


async def report_at(hass, freezer, day: str) -> None:
    freezer.move_to(f"2026-09-{day} 21:00:00+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_training_report(hass, freezer):
    reports = async_mock_service(hass, "test", "report")
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-09-26 20:59:00+02:00")
    training_totals(hass, "30")
    await automate(hass, "training_report", REPORT)
    await report_at(hass, freezer, "26")
    assert [call.data["message"] for call in reports] == [
        "30 darts, 3-dart average 57.3, highest visit 140, 1 × 180."
    ]

    # No report without training.
    hass.states.async_set("sensor.autodarts_training_darts", "0")
    await report_at(hass, freezer, "27")
    assert len(reports) == 1
    # Turning the automation off cancels the timer for the next day.
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )


async def test_training_report_skips_days_without_darts(hass, freezer):
    """A finished session keeps its totals; the board's darts today decide."""
    reports = async_mock_service(hass, "test", "report")
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-09-26 20:59:00+02:00")
    config_entry = MockConfigEntry(domain="autodarts")
    config_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers={("autodarts", "board-1")}
    )
    for key in ("training_darts", "darts_today"):
        er.async_get(hass).async_get_or_create(
            "sensor",
            "autodarts",
            f"board-1_{key}",
            config_entry=config_entry,
            device_id=device.id,
            suggested_object_id=f"autodarts_{key}",
        )
    training_totals(hass, "30")
    today = "sensor.autodarts_darts_today"
    hass.states.async_set(today, "12", {"goal": 0, "goal_reached": False})
    await automate(hass, "training_report", {**REPORT, "minimum_darts": 10})
    await report_at(hass, freezer, "26")
    assert [call.data["message"] for call in reports] == [
        "30 darts, 3-dart average 57.3, highest visit 140, 1 × 180."
    ]
    # The next day the session still shows 30 darts, but none were thrown.
    hass.states.async_set(today, "0", {"goal": 0, "goal_reached": False})
    await report_at(hass, freezer, "27")
    # Too few darts for the minimum.
    hass.states.async_set(today, "5", {"goal": 0, "goal_reached": False})
    await report_at(hass, freezer, "28")
    assert len(reports) == 1
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )


SESSION = {
    "board_events": EVENTS,
    "detection": "switch.autodarts_board_detection",
    "calibration": "button.autodarts_board_calibrate",
}


async def test_training_session_prepares_and_tidies_up_the_board(hass, freezer):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    press = async_mock_service(hass, "button", "press")
    light = async_mock_service(hass, "test", "light")
    report = async_mock_service(hass, "test", "report")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "training_session",
        {
            **SESSION,
            "calibration_delay": {"seconds": 5},
            "session_started": [{"action": "test.light"}],
            "session_ended": [
                {
                    "action": "test.report",
                    "data": {
                        "reason": "{{ reason }}",
                        "darts": "{{ darts }}",
                        "average": "{{ average }}",
                        "minutes": "{{ duration_minutes }}",
                    },
                }
            ],
        },
    )
    fire(hass, "session_started", started="2026-09-26T18:00:00+00:00", reason="manual")
    # The cameras get time to open before the calibration.
    await until_waiting(hass, 5)
    assert len(light) == 1
    assert turn_on[0].data["entity_id"] == ["switch.autodarts_board_detection"]
    assert not press
    await pass_time(hass, freezer, 5)
    assert press[0].data["entity_id"] == ["button.autodarts_board_calibrate"]

    fire(
        hass,
        "session_ended",
        reason="idle",
        darts=30,
        average=48.5,
        duration_minutes=20.0,
    )
    await hass.async_block_till_done()
    assert turn_off[0].data["entity_id"] == ["switch.autodarts_board_detection"]
    assert report[0].data == {
        "reason": "idle",
        "darts": 30,
        "average": 48.5,
        "minutes": 20.0,
    }


async def test_training_session_without_board_controls_only_runs_actions(hass):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    press = async_mock_service(hass, "button", "press")
    light = async_mock_service(hass, "test", "light")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "training_session",
        {"board_events": EVENTS, "session_started": [{"action": "test.light"}]},
    )
    fire(hass, "session_started", started="2026-09-26T18:00:00+00:00")
    await hass.async_block_till_done()
    fire(hass, "session_ended", reason="manual", darts=0)
    await hass.async_block_till_done()
    assert len(light) == 1
    assert not turn_on and not press


async def test_training_session_started_by_a_dart_skips_the_calibration(hass):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    press = async_mock_service(hass, "button", "press")
    hass.states.async_set(EVENTS, "unknown")
    # Saved before the wait became a duration: plain seconds keep working.
    await automate(hass, "training_session", {**SESSION, "calibration_delay": 0})
    fire(
        hass,
        "session_started",
        started="2026-09-26T18:00:00+00:00",
        reason="first_dart",
    )
    await hass.async_block_till_done()
    assert turn_on[0].data["entity_id"] == ["switch.autodarts_board_detection"]
    # The dart that started the session is still in the board.
    assert not press


async def test_training_session_keeps_the_board_for_a_new_session(hass):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    light = async_mock_service(hass, "test", "light")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "training_session",
        {
            **SESSION,
            "calibration": [],
            "session_started": [{"action": "test.light"}],
            "session_ended": [{"action": "test.light"}],
        },
    )
    fire(hass, "session_ended", reason="new_session", darts=12)
    fire(hass, "session_started", reason="new_session")
    await hass.async_block_till_done()
    assert not turn_on and not turn_off and not light


async def test_training_session_routine_for_a_new_session_on_request(hass):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "training_session",
        {**SESSION, "calibration": [], "run_for_new_session": True},
    )
    fire(hass, "session_ended", reason="new_session", darts=12)
    await hass.async_block_till_done()
    fire(hass, "session_started", reason="new_session")
    await hass.async_block_till_done()
    assert len(turn_off) == 1 and len(turn_on) == 1


async def test_training_session_prepares_the_board_despite_a_failing_action(hass):
    turn_on = async_mock_service(hass, "switch", "turn_on")
    async_mock_service(
        hass, "test", "light", raise_exception=HomeAssistantError("light offline")
    )
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "training_session",
        {
            **SESSION,
            "calibration": [],
            "session_started": [{"action": "test.light"}],
        },
    )
    fire(hass, "session_started", reason="manual")
    await hass.async_block_till_done()
    assert turn_on[0].data["entity_id"] == ["switch.autodarts_board_detection"]


# -- highlight photo ---------------------------------------------------------------------


async def test_highlight_photo_for_a_180_and_a_checkout(hass):
    photos = async_mock_service(hass, "test", "photo")
    snapshots = async_mock_service(hass, "camera", "snapshot")
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "highlight_photo", PHOTO)
    fire(hass, "visit_thrown", score=140, darts=3)
    fire(hass, "visit_thrown", score=180, darts=3, name="Alex/Bee_2")
    # The photo waits a moment for a leg won by the same dart.
    await hass.async_block_till_done()
    assert [call.data for call in photos] == [
        {
            "image": "/api/camera_proxy/camera.autodarts_board_camera_1",
            "message": "180!",
        }
    ]
    fire(hass, "leg_won", game=501, players=2, player=2, name="Sam", checkout=121)
    await hass.async_block_till_done()
    assert photos[-1].data["message"] == "Checkout 121 by Sam!"
    # A Cricket leg has no checkout to show.
    fire(hass, "leg_won", game="cricket", players=2, player=1, name="Lea", mpr=2.4)
    await hass.async_block_till_done()
    assert len(photos) == 2
    # Characters a file name cannot have, and the separator, leave the player's name.
    assert [photo_name(call) for call in snapshots] == [
        "Alex Bee 2_180.jpg",
        "Sam_checkout-121.jpg",
    ]


async def test_highlight_photo_of_a_checkout_by_the_third_dart(hass):
    """The visit and the leg arrive together; the leg gets one photo."""
    photos = async_mock_service(hass, "test", "photo")
    snapshots = async_mock_service(hass, "camera", "snapshot")
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "highlight_photo", {**PHOTO, "minimum_score": 100})
    fire(hass, "visit_thrown", score=170, darts=3)
    fire(hass, "leg_won", game=501, players=1, player=1, name=None, checkout=170)
    await hass.async_block_till_done()
    assert [call.data["message"] for call in photos] == ["Checkout 170!"]
    assert [photo_name(call) for call in snapshots] == ["checkout-170.jpg"]


async def test_highlight_photo_can_skip_checkouts_and_lower_the_score(hass):
    photos = async_mock_service(hass, "test", "photo")
    async_mock_service(hass, "camera", "snapshot")
    hass.states.async_set(EVENTS, "unknown")
    # Saved before the visit came from the board events: the old input is ignored.
    await automate(
        hass,
        "highlight_photo",
        {
            **PHOTO,
            "visit_score": "sensor.autodarts_board_detected_visit_score",
            "minimum_score": 140,
            "checkouts": False,
        },
    )
    fire(hass, "visit_thrown", score=140, darts=3)
    await hass.async_block_till_done()
    fire(hass, "leg_won", game=501, players=1, player=1, name=None, checkout=40)
    await hass.async_block_till_done()
    assert [call.data["message"] for call in photos] == ["140!"]


async def test_highlight_photo_gallery_folder_and_saving_can_change(hass):
    photos = async_mock_service(hass, "test", "photo")
    snapshots = async_mock_service(hass, "camera", "snapshot")
    hass.states.async_set(EVENTS, "unknown")
    await automate_all(
        hass,
        [
            (
                "highlight_photo",
                {
                    **PHOTO,
                    "gallery_folder": " /config/media/darts/ ",
                    "checkouts": False,
                },
            ),
            # Only the gallery, without actions of its own.
            (
                "highlight_photo",
                {
                    "board_events": EVENTS,
                    "camera": "camera.autodarts_board_camera_2",
                    "minimum_score": 100,
                },
            ),
            ("highlight_photo", {**PHOTO, "save_photo": False, "minimum_score": 120}),
        ],
    )
    fire(hass, "visit_thrown", score=180, darts=3, name="Lea")
    await hass.async_block_till_done()
    folders = sorted(
        (str(call.data["filename"]).rsplit("/", 1)[0], call.data["entity_id"])
        for call in snapshots
    )
    assert folders == [
        ("/config/media/darts", ["camera.autodarts_board_camera_1"]),
        ("/media/autodarts/highlights", ["camera.autodarts_board_camera_2"]),
    ]
    assert all(
        str(call.data["filename"]).endswith("_Lea_180.jpg") for call in snapshots
    )
    assert len(photos) == 2


async def test_a_photo_that_cannot_be_saved_is_still_sent(hass):
    photos = async_mock_service(hass, "test", "photo")

    async def refuse(call) -> None:
        raise HomeAssistantError("Cannot write, no access to path")

    hass.services.async_register("camera", "snapshot", refuse)
    hass.states.async_set(EVENTS, "unknown")
    await automate(hass, "highlight_photo", PHOTO)
    fire(hass, "visit_thrown", score=180, darts=3)
    await hass.async_block_till_done()
    assert [call.data["message"] for call in photos] == ["180!"]


# -- light show ------------------------------------------------------------------------


def moment_actions(action: str = "test.light") -> dict:
    return {
        f"{moment}_actions": [
            {
                "action": action,
                "data": {
                    "moment": "{{ moment }}",
                    "who": "{{ who }}",
                    "score": "{{ score }}",
                    "checkout": "{{ checkout }}",
                },
            }
        ]
        for moment in (*MOMENTS, "takeout", "board_clear")
    }


async def test_light_show_moments(hass):
    light = async_mock_service(hass, "test", "light")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "light_show",
        {"board_events": EVENTS, **moment_actions(), "high_finish_minimum": 100},
    )
    x01 = {"game": 501, "players": 2}
    await fire_all(
        hass,
        [
            ("visit_thrown", {"score": 140, "darts": 3}),
            ("visit_thrown", {"score": 180, "darts": 3}),
            ("visit_completed", {"score": 180, "darts": 3, "thrown": True}),
            # An older integration announces the 180 when the darts are pulled.
            ("visit_completed", {"score": 180, "darts": 3}),
            ("takeout_started", {}),
            ("takeout_finished", {}),
            ("bust", {**x01, "player": 1, "name": "Dennis", "remaining": 32}),
            ("leg_won", {**x01, "player": 2, "name": None, "checkout": 40}),
            ("leg_won", {**x01, "player": 1, "name": "Dennis", "checkout": 121}),
            # A Cricket leg is a won leg without a checkout.
            ("leg_won", {"game": "cricket", "players": 1, "player": 1, "name": None}),
            # The deciding leg leaves the stage to the match.
            ("leg_won", {**x01, "player": 2, "name": "Lea", "match": True}),
            ("match_won", {**x01, "player": 2, "name": "Lea"}),
            ("personal_best", {"record": "highest_visit", "value": 180}),
            ("daily_goal_reached", {"goal": 100, "darts": 100, "streak": 3}),
            ("bull_off_won", {**x01, "player": 2, "name": None, "distance": 4.1}),
            (
                "achievement_unlocked",
                {"player": 1, "name": "Dennis", "achievement": "maximum", "tier": 1},
            ),
            ("turn_changed", {**x01, "player": 2, "name": None}),
            # The tournament's winner after the final.
            ("tournament_match_finished", {"winner": "Lea", "loser": "Dennis"}),
            ("tournament_finished", {"winner": "Lea", "runner_up": "Dennis"}),
        ],
    )
    assert [
        (
            call.data["moment"],
            call.data["who"],
            call.data["score"],
            call.data["checkout"],
        )
        for call in light
    ] == [
        ("maximum", "", 180, 0),
        ("maximum", "", 180, 0),
        ("takeout", "", 0, 0),
        ("board_clear", "", 0, 0),
        ("bust", "Dennis", 0, 0),
        ("leg", "Player 2", 0, 40),
        ("high_finish", "Dennis", 0, 121),
        ("leg", "", 0, 0),
        ("match", "Lea", 0, 0),
        ("personal_best", "", 0, 0),
        ("daily_goal", "", 0, 0),
        ("bull_off", "Player 2", 0, 0),
        ("achievement", "Dennis", 0, 0),
        ("tournament", "Lea", 0, 0),
    ]


async def test_light_show_restores_the_lights_and_pauses_the_detection(hass, freezer):
    light = async_mock_service(hass, "test", "light")
    snapshot = async_mock_service(hass, "scene", "create")
    restore = async_mock_service(hass, "scene", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    turn_on = async_mock_service(hass, "switch", "turn_on")
    detection = "switch.autodarts_board_detection"
    hass.states.async_set(EVENTS, "unknown")
    hass.states.async_set(detection, "on")
    await automate(
        hass,
        "light_show",
        {
            "board_events": EVENTS,
            **moment_actions(),
            "effect_moments": ["maximum", "bust"],
            "restore_lights": ["light.wled", "light.dartroom"],
            "effect_duration": {"seconds": 8},
            "pause_detection": True,
            "detection": detection,
        },
    )
    fire(hass, "visit_thrown", score=180, darts=3)
    await until_waiting(hass, 8)
    automation = hass.states.async_all("automation")[0].entity_id
    scene = automation.replace("automation.", "autodarts_light_show_")
    assert [call.data for call in snapshot] == [
        {"scene_id": scene, "snapshot_entities": ["light.wled", "light.dartroom"]}
    ]
    assert [call.data["entity_id"] for call in turn_off] == [[detection]]
    assert len(light) == 1 and not restore and not turn_on
    hass.states.async_set(detection, "off")
    await pass_time(hass, freezer, 8)
    assert [call.data["entity_id"] for call in restore] == [[f"scene.{scene}"]]
    assert [call.data["entity_id"] for call in turn_on] == [[detection]]

    # Takeout and board clear set a look of their own, at once, and so does
    # a moment without an effect.
    fire(hass, "takeout_started")
    await hass.async_block_till_done()
    fire(hass, "leg_won", game=501, players=1, player=1, name=None, checkout=40)
    await hass.async_block_till_done()
    assert len(light) == 3 and len(snapshot) == 1 and len(turn_off) == 1

    # A detection that was off stays off.
    fire(hass, "bust", game=501, players=1, player=1, name=None, remaining=40)
    await until_waiting(hass, 8)
    await pass_time(hass, freezer, 8)
    assert len(snapshot) == 2 and len(restore) == 2
    assert len(turn_off) == 1 and len(turn_on) == 1


async def test_light_show_restores_the_lights_after_a_failing_effect(hass, freezer):
    async_mock_service(
        hass, "test", "light", raise_exception=HomeAssistantError("WLED offline")
    )
    async_mock_service(hass, "scene", "create")
    restore = async_mock_service(hass, "scene", "turn_on")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "light_show",
        {
            "board_events": EVENTS,
            **moment_actions(),
            "effect_moments": ["match"],
            "restore_lights": ["light.wled"],
            "effect_duration": {"seconds": 5},
        },
    )
    fire(hass, "match_won", game=501, players=2, player=1, name="Lea")
    await until_waiting(hass, 5)
    await pass_time(hass, freezer, 5)
    assert len(restore) == 1


async def test_light_show_without_restore_plays_moments_at_once(hass):
    light = async_mock_service(hass, "test", "light")
    snapshot = async_mock_service(hass, "scene", "create")
    hass.states.async_set(EVENTS, "unknown")
    await automate(
        hass,
        "light_show",
        {"board_events": EVENTS, "maximum_actions": [{"action": "test.light"}]},
    )
    # Moments without actions stay dark.
    await fire_all(
        hass,
        [
            ("bust", {"game": 501, "players": 1, "player": 1, "remaining": 40}),
            ("visit_thrown", {"score": 180, "darts": 3}),
            ("visit_thrown", {"score": 180, "darts": 3}),
        ],
    )
    assert len(light) == 2 and not snapshot


async def test_light_show_reacts_to_online_matches_when_asked(hass):
    light = async_mock_service(hass, "test", "light")
    online = async_mock_service(hass, "test", "online")
    hass.states.async_set(EVENTS, "unknown")
    await automate_all(
        hass,
        [
            ("light_show", {"board_events": EVENTS, **moment_actions()}),
            (
                "light_show",
                {
                    "board_events": EVENTS,
                    **moment_actions("test.online"),
                    "online_matches": True,
                },
            ),
        ],
    )
    await fire_all(
        hass,
        [
            ("online_busted", {"trigger": "busted", "source": "online"}),
            (
                "online_game_shot",
                {"trigger": "gameshot+d10", "segment": "D10", "source": "online"},
            ),
            (
                "online_match_shot",
                {"trigger": "matchshot_dennis", "name": "dennis", "source": "online"},
            ),
            # Your own 180 comes from the board, and only once.
            ("online_visit", {"trigger": "180", "score": 180, "source": "online"}),
        ],
    )
    # Off by default: an online match stays dark.
    assert not light
    assert [(call.data["moment"], call.data["who"]) for call in online] == [
        ("bust", ""),
        ("leg", ""),
        ("match", "dennis"),
    ]
