"""The bridge for online matches: Tools for Autodarts calls a webhook of Home Assistant."""

import json
import logging
import re
from copy import deepcopy
from http import HTTPStatus
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import State, callback
from homeassistant.core_config import async_process_ha_core_config
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.network import NoURLAvailableError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from custom_components.autodarts import event, online
from custom_components.autodarts.api import AutodartsConnectionError
from custom_components.autodarts.config_flow import AutodartsConfigFlow
from custom_components.autodarts.diagnostics import async_get_config_entry_diagnostics
from custom_components.autodarts.local_coordinator import EVENT_TYPES
from custom_components.autodarts.online import (
    EFFECT_TRIGGERS,
    MOMENTS,
    ONLINE_EVENT_TYPES,
    RATE_LIMITS,
    parse,
)
from custom_components.autodarts.runtime import AutodartsRuntimeData

from .local_helpers import (
    BRIDGE,
    WEBHOOK_ID,
    entity_id,
    entity_summary,
    entry_data,
    local_entry_data,
    mock_board,
    mock_cloud,
    setup_bridge,
)
from .local_helpers import WEBHOOK_PATH as PATH

ROOT = Path(__file__).parents[1]
SENSOR = "sensor.autodarts_board_online_bridge_last_event"
# State attributes of the event entity itself, not of an event.
ENTITY_ATTRIBUTES = {"event_types", "friendly_name", "icon"}


def record_events(hass) -> list[dict]:
    """The details of every board event from now on."""
    events: list[dict] = []

    @callback
    def collect(event) -> None:
        if (new := event.data["new_state"]) and "event_type" in new.attributes:
            events.append(
                {
                    key: value
                    for key, value in new.attributes.items()
                    if key not in ENTITY_ATTRIBUTES
                }
            )

    async_track_state_change_event(
        hass, entity_id(hass, "event", "board_events"), collect
    )
    return events


async def call(client, method: str = "GET", query: str = "", **kwargs):
    response = await client.request(method, f"{PATH}{query}", **kwargs)
    return response.status, await response.text()


# -- triggers ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("trigger", "player", "kind", "details"),
    [
        ("gameon", None, "online_game_on", {}),
        ("gameon", "Dennis", "online_game_on", {"name": "Dennis"}),
        ("bot_throw", None, "online_game_on", {}),
        ("busted", "Lea", "online_busted", {"name": "Lea"}),
        ("bulloff", None, "online_bull_off", {}),
        ("tournament_ready", None, "online_tournament_ready", {}),
        ("idle", None, "online_match_left", {}),
        ("gameshot", None, "online_game_shot", {}),
        ("gameshot+d10", None, "online_game_shot", {"segment": "D10"}),
        # A query string turns the "+" into a space.
        ("gameshot d10", None, "online_game_shot", {"segment": "D10"}),
        ("matchshot+bull", None, "online_match_shot", {"segment": "BULL"}),
        ("matchshot_dennis", "Lea", "online_match_shot", {"name": "dennis"}),
        ("gameshot_john doe", None, "online_game_shot", {"name": "john doe"}),
        ("180", None, "online_visit", {"score": 180}),
        ("0", None, "online_visit", {"score": 0}),
        # A plain number is always the score of a visit, 25 as well.
        ("25", None, "online_visit", {"score": 25}),
        ("range_100_140", None, "online_visit", {"score_min": 100, "score_max": 140}),
        ("100-180", None, "online_visit", {"score_min": 100, "score_max": 180}),
        (
            "t20_t20_t20",
            None,
            "online_visit",
            {"score": 180, "darts": 3, "segments": ["T20", "T20", "T20"]},
        ),
        (
            "s20_25_m5",
            None,
            "online_visit",
            {"score": 45, "darts": 3, "segments": ["S20", "25", "MISS"]},
        ),
        (
            "bull_d20_miss",
            None,
            "online_visit",
            {"score": 90, "darts": 3, "segments": ["BULL", "D20", "MISS"]},
        ),
        ("t20", None, "online_dart", {"segment": "T20", "score": 60}),
        ("d16", None, "online_dart", {"segment": "D16", "score": 32}),
        ("s5", None, "online_dart", {"segment": "S5", "score": 5}),
        ("s25", None, "online_dart", {"segment": "25", "score": 25}),
        ("bull", None, "online_dart", {"segment": "BULL", "score": 50}),
        ("outside", None, "online_dart", {"segment": "MISS", "score": 0}),
        ("m17", None, "online_dart", {"segment": "MISS", "score": 0}),
        ("miss", None, "online_dart", {"segment": "MISS", "score": 0}),
    ],
)
def test_triggers_of_tools_for_autodarts(trigger, player, kind, details):
    assert parse(trigger, player) == (
        kind,
        {"trigger": trigger, **({"name": player} if player else {}), **details},
    )


def test_triggers_are_normalized_and_other_boards_ignored():
    assert parse("  GameOn ") == ("online_game_on", {"trigger": "gameon"})
    assert parse("Gameshot   D10") == (
        "online_game_shot",
        {"trigger": "gameshot d10", "segment": "D10"},
    )
    assert parse("other") == ("", {"trigger": "other"})


@pytest.mark.parametrize(
    ("trigger", "player", "name"),
    [
        # Lower case finds the trigger; the name keeps the case it was sent in.
        ("gameshot_Dennis", None, "Dennis"),
        ("MatchShot_John   Doe", None, "John Doe"),
        ("gameshot_Lea_2", "Sam", "Lea_2"),
        # Notifications and file names render a name again, so it never holds
        # the characters of a template, as no player name does.
        ("busted", "{{ 6*7 }}", "6*7"),
        ("gameshot_{% if 1 %}Kim", None, "if 1 Kim"),
        ("matchshot_#Lea", None, "Lea"),
        # Nothing left of the trigger's name: the player who was sent counts.
        ("gameshot_{}", "Sam", "Sam"),
        ("gameshot_%", None, None),
        ("gameon", "{#}", None),
        # As long as a name in the games, at most.
        ("gameshot_" + "x" * 30, None, "x" * 20),
    ],
)
def test_names_keep_their_case_and_lose_template_characters(trigger, player, name):
    moment = parse(trigger, player)
    assert moment is not None
    assert moment[1].get("name") == name
    assert moment[1]["trigger"] == " ".join(trigger.split()).lower()


@pytest.mark.parametrize(
    "trigger",
    [
        "181",
        "1800",
        "t21",
        "t25",
        "d25",
        "s0",
        "range_140_100",
        "range_100",
        "t20_t20",
        "t20_t20_t20_t20",
        "t20_outside_t20",
        "gameshot_",
        "gameshot+x",
        "gameshot+outside",
        "takeout",
        "board_started",
        "lobby_in",
        "dennis",
        "",
    ],
)
def test_unknown_triggers(trigger):
    assert parse(trigger) is None


def test_every_event_type_is_a_board_event_and_documented():
    assert set(MOMENTS.values()) <= set(ONLINE_EVENT_TYPES)
    assert EVENT_TYPES[-len(ONLINE_EVENT_TYPES) :] == ONLINE_EVENT_TYPES
    for document in ("docs/entities.md", "docs/entities.de.md"):
        text = (ROOT / document).read_text(encoding="utf-8")
        for kind in ONLINE_EVENT_TYPES:
            assert f"`{kind}`" in text, (document, kind)
    # Every ready-made effect is a trigger the bridge understands.
    assert all(parse(trigger) is not None for trigger in EFFECT_TRIGGERS)


# -- options -------------------------------------------------------------------


async def test_options_switch_the_bridge_on_and_show_the_address(hass, aioclient_mock):
    await async_process_ha_core_config(
        hass,
        {
            "internal_url": "http://homeassistant.lan:8123",
            "external_url": "https://darts.example.com",
        },
    )
    entry = await setup_bridge(hass, aioclient_mock, options={})
    assert entry.runtime_data.bridge is None
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", "autodarts", "board-1_online_bridge_last_event"
        )
        is None
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # A new address is offered once there is one.
    assert [str(key) for key in result["data_schema"].schema] == [
        "online_bridge",
        "online_bridge_remote",
    ]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"online_bridge": True, "online_bridge_remote": False}
    )
    assert result["step_id"] == "online_bridge"
    url = result["description_placeholders"]["url"]
    webhook_id = url.rsplit("/", 1)[1]
    assert re.fullmatch("[0-9a-f]{64}", webhook_id)
    # Only calls from the home network count, so the address is the internal one.
    assert url == f"http://homeassistant.lan:8123/api/webhook/{webhook_id}"
    effects = result["description_placeholders"]["effects"].split("\n")
    assert len(effects) == len(EFFECT_TRIGGERS)
    assert effects[0] == f"Home Assistant: gameon;URL;{url}?event=gameon;gameon"
    assert f"Home Assistant: 180;URL;{url}?event=180;180" in effects
    assert entry.options == {}

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {
        "online_bridge": True,
        "online_bridge_remote": False,
        "online_bridge_webhook_id": webhook_id,
    }
    # The options reload the entry, which opens the webhook and adds the sensor.
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.bridge is not None
    assert hass.states.get(SENSOR).state == "unknown"

    # Opening the options again shows the same address, with remote calls the
    # external https address.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert [str(key) for key in result["data_schema"].schema] == [
        "online_bridge",
        "online_bridge_remote",
        "online_bridge_new_address",
    ]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "online_bridge": True,
            "online_bridge_remote": True,
            "online_bridge_new_address": False,
        },
    )
    assert result["description_placeholders"]["url"] == (
        f"https://darts.example.com/api/webhook/{webhook_id}"
    )
    await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert entry.options["online_bridge_remote"] is True
    assert entry.runtime_data.bridge.remote is True

    # A new address replaces the old one.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "online_bridge": True,
            "online_bridge_remote": True,
            "online_bridge_new_address": True,
        },
    )
    await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    new_id = entry.options["online_bridge_webhook_id"]
    assert re.fullmatch("[0-9a-f]{64}", new_id) and new_id != webhook_id

    # Switched off, the bridge keeps its address for later and loses its sensor.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "online_bridge": False,
            "online_bridge_remote": False,
            "online_bridge_new_address": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {
        "online_bridge": False,
        "online_bridge_remote": False,
        "online_bridge_webhook_id": new_id,
    }
    assert entry.runtime_data.bridge is None
    assert hass.states.get(SENSOR) is None
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", "autodarts", "board-1_online_bridge_last_event"
        )
        is None
    )


async def test_a_new_address_replaces_the_old_one_when_switching_off(
    hass, aioclient_mock
):
    """Whoever knows a leaked address can never use it again."""
    entry = await setup_bridge(hass, aioclient_mock)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "online_bridge": False,
            "online_bridge_remote": False,
            "online_bridge_new_address": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    new_id = entry.options["online_bridge_webhook_id"]
    assert re.fullmatch("[0-9a-f]{64}", new_id) and new_id != WEBHOOK_ID
    assert entry.options["online_bridge"] is False


async def test_only_an_entry_with_a_local_board_has_options(hass, aioclient_mock):
    """The bridge delivers moments as events of the local board."""
    local = await setup_bridge(hass, aioclient_mock, options={})
    cloud = MockConfigEntry(
        domain="autodarts",
        version=2,
        data={"board_id": "board-2", "local_only": False},
    )
    cloud.add_to_hass(hass)
    assert AutodartsConfigFlow.async_supports_options_flow(local)
    assert not AutodartsConfigFlow.async_supports_options_flow(cloud)
    assert local.supports_options and not cloud.supports_options


async def test_address_without_the_configured_urls(hass):
    # Remote calls without an external https address use the home network.
    with patch.object(
        online, "get_url", side_effect=[NoURLAvailableError, "http://192.0.2.5:8123"]
    ):
        assert online.bridge_url(hass, WEBHOOK_ID, True) == (
            f"http://192.0.2.5:8123{PATH}"
        )
    with patch.object(online, "get_url", side_effect=NoURLAvailableError):
        assert online.bridge_url(hass, WEBHOOK_ID, False) == (
            f"http://homeassistant.local:8123{PATH}"
        )


# -- calls ---------------------------------------------------------------------


async def test_calls_become_board_events(
    hass, aioclient_mock, hass_client_no_auth, caplog
):
    caplog.set_level(logging.DEBUG, logger="custom_components.autodarts")
    entry = await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_client_no_auth()
    plain = {"Content-Type": "text/plain;charset=UTF-8"}

    # An effect of type URL, and one whose "+" was not encoded.
    assert await call(client, query="?event=180") == (HTTPStatus.OK, "ok")
    assert await call(client, query="?event=gameshot+d10&player=Dennis") == (
        HTTPStatus.OK,
        "ok",
    )
    # An effect of type JSON API sends its JSON as text/plain.
    assert await call(
        client, "POST", data='{"event": "busted", "player": "Lea"}', headers=plain
    ) == (HTTPStatus.OK, "ok")
    assert await call(client, "POST", data='{"event": 140, "other": [1]}') == (
        HTTPStatus.OK,
        "ok",
    )
    assert await call(client, "POST", data="event=t20_t20_t20&player=Sam") == (
        HTTPStatus.OK,
        "ok",
    )
    # A bare trigger or a JSON string, with the player in the address.
    assert await call(client, "POST", "?player=Sam", data="matchshot") == (
        HTTPStatus.OK,
        "ok",
    )
    assert await call(client, "POST", data='"bull"') == (HTTPStatus.OK, "ok")
    # A POST without a body reads the address.
    assert await call(client, "POST", "?event=idle") == (HTTPStatus.OK, "ok")
    # A moment on another board is no event.
    assert await call(client, query="?event=other") == (HTTPStatus.OK, "ignored")
    # Home Assistant answers HEAD requests itself, so websites can check the URL.
    assert (await call(client, "HEAD"))[0] == HTTPStatus.OK
    await hass.async_block_till_done()

    assert events == [
        {
            "event_type": "online_visit",
            "trigger": "180",
            "score": 180,
            "source": "online",
        },
        {
            "event_type": "online_game_shot",
            "trigger": "gameshot d10",
            "segment": "D10",
            "name": "Dennis",
            "source": "online",
        },
        {
            "event_type": "online_busted",
            "trigger": "busted",
            "name": "Lea",
            "source": "online",
        },
        {
            "event_type": "online_visit",
            "trigger": "140",
            "score": 140,
            "source": "online",
        },
        {
            "event_type": "online_visit",
            "trigger": "t20_t20_t20",
            "name": "Sam",
            "score": 180,
            "darts": 3,
            "segments": ["T20", "T20", "T20"],
            "source": "online",
        },
        {
            "event_type": "online_match_shot",
            "trigger": "matchshot",
            "name": "Sam",
            "source": "online",
        },
        {
            "event_type": "online_dart",
            "trigger": "bull",
            "segment": "BULL",
            "score": 50,
            "source": "online",
        },
        {"event_type": "online_match_left", "trigger": "idle", "source": "online"},
    ]
    sensor = hass.states.get(SENSOR)
    assert dt_util.parse_datetime(sensor.state) is not None
    assert sensor.attributes["trigger"] == "idle"
    assert sensor.attributes["event_type"] == "online_match_left"
    assert sensor.attributes["device_class"] == "timestamp"
    assert er.async_get(hass).async_get(SENSOR).entity_category == "diagnostic"

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert WEBHOOK_ID not in json.dumps(diagnostics, default=str)
    assert diagnostics["online_bridge"] == {
        "enabled": True,
        "remote": False,
        "events": 8,
        "ignored": 1,
        "invalid": 0,
        "limited": 0,
        "last_event": sensor.state,
        "last_event_type": "online_match_left",
    }
    assert not [
        record
        for record in caplog.records
        if record.name.startswith("custom_components.autodarts")
        and WEBHOOK_ID in record.getMessage()
    ]


async def test_names_are_spelled_as_the_players_profile_spells_them(
    hass, aioclient_mock, hass_client_no_auth
):
    entry = await setup_bridge(hass, aioclient_mock)
    entry.runtime_data.local.games.practice.profiles.visit("Dennis", 60)
    events = record_events(hass)
    client = await hass_client_no_auth()
    for query in (
        "?event=gameshot_dennis",
        "?event=busted&player=DENNIS",
        "?event=matchshot_Kim",
        "?event=gameon&player=%7B%7B%206*7%20%7D%7D",
    ):
        assert await call(client, query=query) == (HTTPStatus.OK, "ok")
    await hass.async_block_till_done()
    assert [event["name"] for event in events] == ["Dennis", "Dennis", "Kim", "6*7"]
    assert events[0]["trigger"] == "gameshot_dennis"


@pytest.mark.parametrize(
    ("method", "query", "body", "status", "answer"),
    [
        ("GET", "", None, HTTPStatus.BAD_REQUEST, "event missing"),
        ("GET", "?event=%20", None, HTTPStatus.BAD_REQUEST, "event missing"),
        ("GET", "?event=" + "1" * 65, None, HTTPStatus.BAD_REQUEST, "invalid event"),
        ("GET", "?event=game%01on", None, HTTPStatus.BAD_REQUEST, "invalid event"),
        (
            "GET",
            "?event=180&player=" + "x" * 51,
            None,
            HTTPStatus.BAD_REQUEST,
            "invalid player",
        ),
        (
            "POST",
            "",
            r'{"event": "180", "player": "a\u0007b"}',
            HTTPStatus.BAD_REQUEST,
            "invalid player",
        ),
        (
            "GET",
            "?event=180&x=" + "1" * 1024,
            None,
            HTTPStatus.REQUEST_URI_TOO_LONG,
            "address too long",
        ),
        ("POST", "", "{nope", HTTPStatus.BAD_REQUEST, "invalid JSON"),
        ("POST", "", "[180]", HTTPStatus.BAD_REQUEST, "invalid JSON"),
        ("POST", "", '{"event": true}', HTTPStatus.BAD_REQUEST, "invalid event"),
        ("POST", "", '{"event": ["x"]}', HTTPStatus.BAD_REQUEST, "invalid event"),
        ("POST", "", '{"player": 1.5}', HTTPStatus.BAD_REQUEST, "invalid player"),
        ("POST", "", b"\xff\xfe", HTTPStatus.BAD_REQUEST, "invalid text"),
        ("POST", "", "a=1&" * 11, HTTPStatus.BAD_REQUEST, "invalid fields"),
        (
            "POST",
            "",
            "event=180&x=" + "1" * 1024,
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "body too large",
        ),
        ("POST", "", "  ", HTTPStatus.BAD_REQUEST, "event missing"),
    ],
)
async def test_invalid_calls_are_refused(
    hass, aioclient_mock, hass_client_no_auth, method, query, body, status, answer
):
    entry = await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_client_no_auth()
    assert await call(client, method, query, data=body) == (status, answer)
    await hass.async_block_till_done()
    assert not events
    assert entry.runtime_data.bridge.counts["invalid"] == 1
    assert hass.states.get(SENSOR).state == "unknown"


async def test_unknown_triggers_are_explained_once(
    hass, aioclient_mock, hass_client_no_auth, caplog
):
    caplog.set_level(logging.DEBUG, logger="custom_components.autodarts")
    await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_client_no_auth()
    for trigger in ("takeout", "lobby_in"):
        assert await call(client, query=f"?event={trigger}") == (
            HTTPStatus.BAD_REQUEST,
            "unknown event",
        )
    assert not events
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.autodarts.online"
        and record.levelno == logging.WARNING
    ]
    assert warnings == [
        "The online bridge ignored the unknown event 'takeout'; the documentation "
        "lists the triggers of Tools for Autodarts it understands"
    ]
    assert "Online bridge ignored the unknown event 'lobby_in'" in caplog.text


async def test_calls_beyond_the_rate_limit_are_refused(
    hass, aioclient_mock, hass_client_no_auth
):
    entry = await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_client_no_auth()
    per_second = RATE_LIMITS[0][1]
    with patch.object(online, "monotonic", return_value=100.0):
        for _ in range(per_second):
            assert await call(client, query="?event=t20") == (HTTPStatus.OK, "ok")
        assert await call(client, query="?event=t20") == (
            HTTPStatus.TOO_MANY_REQUESTS,
            "too many calls",
        )
    # A second later, the bridge accepts calls again.
    with patch.object(online, "monotonic", return_value=101.0):
        assert await call(client, query="?event=t20") == (HTTPStatus.OK, "ok")
    await hass.async_block_till_done()
    assert len(events) == per_second + 1
    assert entry.runtime_data.bridge.counts["limited"] == 1


async def test_a_minute_of_calls_is_limited_too(
    hass, aioclient_mock, hass_client_no_auth
):
    """A leaked address cannot keep the recorder and the lights busy for long."""
    entry = await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_client_no_auth()
    (_, per_second), (minute, per_minute) = RATE_LIMITS
    # Always fewer calls than the limit per second, until the minute is full.
    spacing = 1.0 / (per_second - 1)
    moments = [100.0 + index * spacing for index in range(per_minute)]
    for moment in moments:
        with patch.object(online, "monotonic", return_value=moment):
            assert await call(client, query="?event=t20") == (HTTPStatus.OK, "ok")
    later = moments[-1] + 1.0
    assert later - moments[0] < minute
    with patch.object(online, "monotonic", return_value=later):
        assert await call(client, query="?event=t20") == (
            HTTPStatus.TOO_MANY_REQUESTS,
            "too many calls",
        )
    # Once the first call is a minute old, the next one is welcome.
    with patch.object(online, "monotonic", return_value=moments[0] + minute):
        assert await call(client, query="?event=t20") == (HTTPStatus.OK, "ok")
    await hass.async_block_till_done()
    assert len(events) == per_minute + 1
    assert entry.runtime_data.bridge.counts["limited"] == 1


async def test_calls_over_the_websocket_api(hass, aioclient_mock, hass_ws_client):
    """Home Assistant's own test call passes a request with a different reader."""
    await setup_bridge(hass, aioclient_mock)
    events = record_events(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "webhook/handle",
            "webhook_id": WEBHOOK_ID,
            "method": "POST",
            "body": '{"event": "busted"}',
        }
    )
    result = (await client.receive_json())["result"]
    assert (result["status"], result["body"]) == (HTTPStatus.OK, "ok")
    await hass.async_block_till_done()
    assert [event["event_type"] for event in events] == ["online_busted"]


@pytest.mark.parametrize(("remote", "answer"), [(False, ""), (True, "ok")])
async def test_calls_from_outside_the_home_network(
    hass, aioclient_mock, hass_client_no_auth, remote, answer
):
    """Home Assistant refuses them silently unless remote calls are allowed."""
    await setup_bridge(
        hass, aioclient_mock, options={**BRIDGE, "online_bridge_remote": remote}
    )
    events = record_events(hass)
    client = await hass_client_no_auth()
    with patch(
        "homeassistant.components.webhook.network_util.is_local", return_value=False
    ):
        assert await call(client, query="?event=180") == (HTTPStatus.OK, answer)
    await hass.async_block_till_done()
    assert len(events) == (1 if remote else 0)


async def test_a_switched_off_or_unloaded_bridge_does_not_answer(
    hass, aioclient_mock, hass_client_no_auth
):
    # Home Assistant's default configuration loads webhooks.
    assert await async_setup_component(hass, "webhook", {})
    entry = await setup_bridge(
        hass, aioclient_mock, options={**BRIDGE, "online_bridge": False}
    )
    assert entry.runtime_data.bridge is None
    assert hass.states.get(SENSOR) is None
    events = record_events(hass)
    client = await hass_client_no_auth()
    # Home Assistant answers every unknown address alike, so it gives nothing away.
    assert await call(client, query="?event=180") == (HTTPStatus.OK, "")
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["online_bridge"] == {"enabled": False}

    hass.config_entries.async_update_entry(entry, options=BRIDGE)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    events = record_events(hass)
    assert await call(client, query="?event=180") == (HTTPStatus.OK, "ok")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await call(client, query="?event=180") == (HTTPStatus.OK, "")
    assert len(events) == 1


async def test_sensor_remembers_the_last_event_across_restarts(hass, aioclient_mock):
    mock_restore_cache(
        hass,
        [
            State(
                SENSOR,
                "2026-09-26T20:15:00+00:00",
                {"trigger": "180", "event_type": "online_visit"},
            )
        ],
    )
    entry = await setup_bridge(hass, aioclient_mock)
    sensor = hass.states.get(SENSOR)
    assert sensor.state == "2026-09-26T20:15:00+00:00"
    assert sensor.attributes["trigger"] == "180"
    assert sensor.attributes["event_type"] == "online_visit"
    bridge = entry.runtime_data.bridge
    assert bridge.diagnostics()["last_event"] == "2026-09-26T20:15:00+00:00"

    # A newer moment is never replaced by an older one.
    bridge.restore(dt_util.utcnow(), "busted", "online_busted")
    assert bridge.last_trigger == "180"


def test_restore_keeps_only_valid_values():
    bridge = object.__new__(online.OnlineBridge)
    bridge.last_event = None
    bridge.restore(None, "180", "online_visit")
    assert bridge.last_event is None
    moment = dt_util.utcnow()
    bridge.restore(moment, 180, None)
    assert (bridge.last_event, bridge.last_trigger, bridge.last_event_type) == (
        moment,
        None,
        None,
    )


async def test_sensor_after_a_restart_without_an_event(hass, aioclient_mock):
    mock_restore_cache(hass, [State(SENSOR, "unknown", {})])
    await setup_bridge(hass, aioclient_mock)
    assert hass.states.get(SENSOR).state == "unknown"


async def test_no_bridge_without_the_board_or_webhooks(hass, aioclient_mock):
    # A cloud-only entry has no board events to deliver the moments.
    entry = MockConfigEntry(domain="autodarts", data=local_entry_data(), options=BRIDGE)
    assert await online.async_setup_bridge(hass, entry, None) is None
    with patch.object(online, "async_setup_component", return_value=False):
        loaded = await setup_bridge(hass, aioclient_mock)
    assert loaded.runtime_data.bridge is None


async def test_entities_and_diagnostics_of_the_bridge(
    hass, aioclient_mock, hass_client, snapshot: SnapshotAssertion
):
    """The bridge adds one diagnostic sensor; diagnostics keep the address secret."""
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await setup_bridge(hass, aioclient_mock)
    added = {
        unique_id: summary
        for unique_id, summary in entity_summary(hass, entry).items()
        if "online" in unique_id
    }
    assert added == snapshot
    client = await hass_client()
    assert (await client.get(f"{PATH}?event=busted")).status == HTTPStatus.OK
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert WEBHOOK_ID not in json.dumps(diagnostics)
    assert diagnostics["online_bridge"] == snapshot(exclude=props("last_event"))


# -- moments from the cloud ----------------------------------------------------

LEA = {"name": "Lea", "boardId": "board-1"}
# The opponent of an online match, at another board.
SAM = {"name": "Sam", "boardId": "board-2"}


def throw(number: int, multiplier: int) -> dict:
    return {"segment": {"number": number, "multiplier": multiplier}}


T20, S20, D16, BULL, MISS = (
    throw(20, 3),
    throw(20, 1),
    throw(16, 2),
    throw(25, 2),
    throw(0, 0),
)
BULL_OFF = {"variant": "Bull-off", "players": [LEA, SAM], "player": 0}


def match_state(player=0, *darts, players=(LEA, SAM), **changes) -> dict:
    """The state of an X01 match as the cloud reports it, in the first round."""
    return {
        "variant": "X01",
        "players": list(players),
        "player": player,
        "set": 1,
        "leg": 1,
        "round": 1,
        "turns": [{"points": 0, "busted": False, "throws": list(darts)}],
        "gameWinner": -1,
        "winner": -1,
        **changes,
    }


def visit(*darts, points, **turn) -> list[dict]:
    """The turns of a match whose current visit has these darts."""
    return [{"points": points, "busted": False, "throws": list(darts), **turn}]


def read(state=None, match_id="match-1") -> dict:
    """The data of the cloud coordinator: the board, in a match with its state."""
    board = {"id": "board-1", "matchId": match_id} if match_id else {"id": "board-1"}
    return {"board": board, "match": state, "local": {}}


@pytest.mark.parametrize(
    ("number", "multiplier", "trigger", "segment"),
    [
        (20, 3, "t20", "T20"),
        (16, 2, "d16", "D16"),
        (5, 1, "s5", "S5"),
        (25, 1, "s25", "25"),
        (25, 2, "bull", "BULL"),
        # Beside the 17, off the board, and a bull without a ring.
        (17, 0, "m17", "MISS"),
        (0, 0, "miss", "MISS"),
        (25, 0, "miss", "MISS"),
    ],
)
def test_darts_of_the_cloud_are_named_as_tools_for_autodarts_names_them(
    number, multiplier, trigger, segment
):
    assert online.throw_trigger(throw(number, multiplier)) == trigger
    assert parse(trigger) == (
        "online_dart",
        {"trigger": trigger, "segment": segment, "score": number * multiplier},
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {"segment": "T20"},
        {"segment": {"number": "20", "multiplier": 3}},
        {"segment": {"number": 20, "multiplier": True}},
        {"segment": {"number": 21, "multiplier": 1}},
        {"segment": {"number": 20, "multiplier": 4}},
        {"segment": {"number": 25, "multiplier": 3}},
    ],
)
def test_malformed_darts_of_the_cloud_are_skipped(value):
    assert online.throw_trigger(value) is None


def test_a_match_from_the_cloud_becomes_the_triggers_of_the_bridge():
    moments = online.CloudMoments("board-1")
    # Nothing read yet, then a board without a match.
    assert moments.update(None) == []
    assert moments.update(read(match_id=None)) == []
    assert moments.update(read(BULL_OFF)) == [("bulloff", None)]
    assert moments.update(read(BULL_OFF)) == []
    assert moments.update(read(match_state(0, T20))) == [
        ("gameon", "Lea"),
        ("t20", "Lea"),
    ]
    # Every poll reports only what is new, and a full visit its score.
    full = read(match_state(turns=visit(T20, T20, S20, points=140)))
    assert moments.update(full) == [("t20", "Lea"), ("s20", "Lea"), ("140", "Lea")]
    assert moments.update(full) == []
    # The visit of the opponent at another board is not this board's.
    opponent = match_state(1, turns=visit(S20, S20, S20, points=60))
    assert moments.update(read(opponent)) == []
    bust = match_state(round=2, turns=visit(T20, T20, points=0, busted=True))
    assert moments.update(read(bust)) == [
        ("gameon", "Lea"),
        ("t20", "Lea"),
        ("t20", "Lea"),
        ("busted", "Lea"),
    ]
    leg = read(match_state(0, T20, D16, round=3, gameWinner=0))
    assert moments.update(leg) == [
        ("gameon", "Lea"),
        ("t20", "Lea"),
        ("d16", "Lea"),
        ("gameshot+d16", "Lea"),
    ]
    assert moments.update(leg) == []
    # The opponent wins the second leg, which this board does not celebrate.
    assert moments.update(read(match_state(1, D16, leg=2, gameWinner=1))) == []
    # The last leg is the match.
    won = read(match_state(0, BULL, leg=3, gameWinner=0, winner=0))
    assert moments.update(won) == [
        ("gameon", "Lea"),
        ("bull", "Lea"),
        ("matchshot+bull", "Lea"),
    ]
    assert moments.update(read(match_id=None)) == [("idle", None)]
    assert moments.update(read(match_id=None)) == []


def test_a_match_that_ran_before_home_assistant_watched_counts_from_then_on():
    moments = online.CloudMoments("board-1")
    # Its state cannot be read at first, and the first state is only noted.
    assert moments.update(read(None)) == []
    assert moments.update(read(match_state(0, T20, gameWinner=0))) == []
    assert moments.update(read(match_state(0, T20, T20))) == [("t20", "Lea")]
    # Another match without leaving the first one starts anew, without "idle".
    other = read(match_state(0, T20, T20), match_id="match-2")
    assert moments.update(other) == [
        ("gameon", "Lea"),
        ("t20", "Lea"),
        ("t20", "Lea"),
    ]


GAME_ON = ("gameon", "Lea")


@pytest.mark.parametrize(
    ("state", "moments"),
    [
        # A bot and a guest have no board of their own: they throw at this one.
        (
            match_state(0, T20, players=[{"name": "Bot", "cpuPPR": 60}]),
            [("gameon", "Bot"), ("t20", "Bot")],
        ),
        (match_state(0, players=[{"boardId": ""}]), [("gameon", None)]),
        (match_state(0, T20, players=["Lea"]), [("gameon", None), ("t20", None)]),
        # A malformed dart keeps its place, and a visit needs its score.
        (
            match_state(0, MISS, {}, T20),
            [GAME_ON, ("miss", "Lea"), ("t20", "Lea"), ("0", "Lea")],
        ),
        (
            match_state(turns=visit(T20, T20, T20, points=181)),
            [GAME_ON, ("t20", "Lea"), ("t20", "Lea"), ("t20", "Lea")],
        ),
        (
            match_state(turns=visit(T20, T20, T20, points=None)),
            [GAME_ON, ("t20", "Lea"), ("t20", "Lea"), ("t20", "Lea")],
        ),
        (match_state(turns=[{"throws": "T20"}]), [GAME_ON]),
        # A leg won with another player's dart, or with one that cannot be read.
        (match_state(1, S20, gameWinner=0), [("gameshot", "Lea")]),
        (
            match_state(0, T20, {}, gameWinner=0),
            [GAME_ON, ("t20", "Lea"), ("gameshot", "Lea")],
        ),
        (match_state(0, gameWinner=0), [GAME_ON, ("gameshot", "Lea")]),
        (match_state(0, gameWinner=5, winner="Lea"), [GAME_ON]),
        # States the integration cannot follow.
        ({**match_state(), "players": "Lea"}, []),
        (match_state(player=None), []),
        (match_state(player=2), []),
        (match_state(turns=[]), []),
        (match_state(turns=["T20"]), []),
        (match_state(turns=None), []),
    ],
)
def test_the_cloud_moments_of_unusual_states(state, moments):
    cloud = online.CloudMoments("board-1")
    assert cloud.update(read(match_id=None)) == []
    assert cloud.update(read(state)) == moments


def test_a_board_without_data_has_no_match():
    moments = online.CloudMoments("board-1")
    assert moments.update({"board": None, "match": match_state()}) == []
    assert moments.update({"board": {"matchId": 7}, "match": match_state()}) == []


async def setup_cloud(hass, aioclient_mock, *, local=True, options=None):
    """A board linked to the cloud, in the network unless local is False."""
    if local:
        mock_board(aioclient_mock)
    mock_cloud(aioclient_mock)
    data = {**entry_data(), **local_entry_data(), "local_only": False}
    entry = MockConfigEntry(
        domain="autodarts",
        version=2,
        data=data if local else entry_data(),
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.cloud is not None
    return entry


async def poll(hass, cloud, state=None) -> None:
    """One poll of the cloud coordinator, which finds the board in a match with
    this state or, without one, in no match."""
    client = cloud.cloud
    data = read(deepcopy(state), "match-1" if state is not None else None)
    with (
        patch.object(client, "get_board", AsyncMock(return_value=data["board"])),
        patch.object(client, "get_match", AsyncMock(return_value={"id": "match-1"})),
        patch.object(client, "get_match_state", AsyncMock(return_value=data["match"])),
    ):
        await cloud.async_refresh()
    await hass.async_block_till_done()


def cloud_event(event_type: str, trigger: str, **details) -> dict:
    return {"event_type": event_type, "trigger": trigger, **details, "source": "cloud"}


@pytest.mark.usefixtures("cloud_link")
async def test_cloud_matches_bring_the_board_events_of_the_bridge(hass, aioclient_mock):
    """Without the browser extension, the moments of a match come from the cloud
    as the same board events, for the light show and every automation."""
    entry = await setup_cloud(hass, aioclient_mock)
    entry.runtime_data.local.games.practice.profiles.visit("Dennis", 60)
    cloud = entry.runtime_data.cloud
    events = record_events(hass)
    players = [{"name": "dennis", "boardId": "board-1"}, SAM]
    await poll(hass, cloud, {**BULL_OFF, "players": players})
    full = visit(T20, S20, D16, points=112)
    await poll(hass, cloud, match_state(players=players, turns=full))
    await poll(hass, cloud, match_state(1, S20, players=players))
    won = match_state(0, D16, players=players, round=2, gameWinner=0, winner=0)
    await poll(hass, cloud, won)
    await poll(hass, cloud)
    # As the player's profile spells the name, as with the bridge.
    name = {"name": "Dennis"}
    assert events == [
        cloud_event("online_bull_off", "bulloff"),
        cloud_event("online_game_on", "gameon", **name),
        cloud_event("online_dart", "t20", segment="T20", score=60, **name),
        cloud_event("online_dart", "s20", segment="S20", score=20, **name),
        cloud_event("online_dart", "d16", segment="D16", score=32, **name),
        cloud_event("online_visit", "112", score=112, **name),
        cloud_event("online_game_on", "gameon", **name),
        cloud_event("online_dart", "d16", segment="D16", score=32, **name),
        cloud_event("online_match_shot", "matchshot+d16", segment="D16", **name),
        cloud_event("online_match_left", "idle"),
    ]
    # An unloaded board stops following the cloud.
    assert await hass.config_entries.async_unload(entry.entry_id)
    with patch.object(online, "async_dispatcher_send") as send:
        await poll(hass, cloud, match_state(0, T20, players=players))
    send.assert_not_called()


@pytest.mark.usefixtures("cloud_link")
async def test_the_bridge_alone_reports_online_moments_when_it_is_switched_on(
    hass, aioclient_mock
):
    """The bridge is faster than a poll, and both would report every moment twice."""
    entry = await setup_cloud(hass, aioclient_mock, options=BRIDGE)
    assert entry.runtime_data.bridge is not None
    events = record_events(hass)
    await poll(hass, entry.runtime_data.cloud, match_state(0, T20))
    assert events == []


@pytest.mark.usefixtures("cloud_link")
async def test_a_board_only_the_cloud_reaches_has_the_online_events(
    hass, aioclient_mock
):
    """Lens or Autodarts X without a Board Manager in the network: the events
    entity carries the moments of their online matches."""
    entry = await setup_cloud(hass, aioclient_mock, local=False)
    assert entry.runtime_data.local is None
    event = entity_id(hass, "event", "board_events")
    assert hass.states.get(event).attributes["event_types"] == ONLINE_EVENT_TYPES
    events = record_events(hass)
    await poll(
        hass,
        entry.runtime_data.cloud,
        match_state(0, T20, players=[{"name": "dennis"}]),
    )
    # Without the profiles of a board, the name stays as Autodarts spells it.
    assert events == [
        cloud_event("online_game_on", "gameon", name="dennis"),
        cloud_event("online_dart", "t20", segment="T20", score=60, name="dennis"),
    ]
    # The entity stays while the cloud is away.
    with patch.object(
        entry.runtime_data.cloud.cloud,
        "get_board",
        AsyncMock(side_effect=AutodartsConnectionError("away")),
    ):
        await entry.runtime_data.cloud.async_refresh()
    await hass.async_block_till_done()
    assert not entry.runtime_data.cloud.last_update_success
    assert hass.states.get(event).state != "unavailable"


async def test_no_events_entity_for_an_entry_without_a_board(hass):
    """Setup stops before the platforms when neither the network nor the cloud
    reaches the board; the events entity needs one of them."""
    added = Mock()
    await event.async_setup_entry(
        hass, Mock(runtime_data=AutodartsRuntimeData()), added
    )
    added.assert_not_called()
