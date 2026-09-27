"""Tournaments in Home Assistant: actions, entities, the pause, events and restarts."""

import json
from datetime import timedelta

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.autodarts.const import DOMAIN

from .local_helpers import (
    S20,
    T20,
    board,
    entity_id,
    record,
    setup_local,
    state,
    switch,
)

D20 = ("D20", 20, 2)
S1 = ("S1", 1, 1)
CHECKOUT = (T20, S1, D20)
PLAYERS = ["Alex", "Sam", "Kim"]


async def throw(hass, coordinator, *darts, pull: bool = True) -> None:
    """Throw a visit dart by dart, then pull the darts."""
    for count in range(1, len(darts) + 1):
        coordinator.async_receive("state", board(*darts[:count]))
    if pull:
        coordinator.async_receive("state", board())
    await hass.async_block_till_done()


async def action(hass, service: str, **data) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)
    await hass.async_block_till_done()


async def press(hass, key: str) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id(hass, "button", key)}, blocking=True
    )
    await hass.async_block_till_done()


def tournament(hass):
    return hass.states.get(entity_id(hass, "sensor", "tournament"))


def fired(events, kind: str) -> list[dict]:
    return [attributes for event, attributes in events if event == kind]


async def pass_pause(hass, seconds: float = 11) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


async def test_a_round_robin_plays_through_with_pauses(hass, aioclient_mock, freezer):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = record(hass, coordinator)
    assert state(hass, "sensor", "tournament") == "no_tournament"
    assert tournament(hass).attributes["status"] is None

    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1, sets=1)
    started = fired(events, "tournament_started")
    assert started == [
        {
            "format": "round_robin",
            "game": 101,
            "matches": 3,
            "players": PLAYERS,
            "start_scores": [0, 0, 0],
            "legs_to_win": 1,
            "sets_to_win": 1,
            "seed": None,
            "source": "training",
        }
    ]
    assert state(hass, "sensor", "tournament") == "round_1"
    assert state(hass, "select", "practice_game") == "101"
    assert state(hass, "text", "practice_player_1") == "Kim"
    assert state(hass, "text", "practice_player_2") == "Sam"
    # The action keeps the players for the next tournament.
    assert state(hass, "text", "tournament_players") == "Alex, Sam, Kim"
    current = tournament(hass).attributes["current"]
    assert current["players"] == ["Kim", "Sam"] and current["match"] == 1

    await throw(hass, coordinator, S1, S1, S1)
    await throw(hass, coordinator, *CHECKOUT)
    finished = fired(events, "tournament_match_finished")
    assert len(finished) == 1
    assert finished[0]["winner"] == "Sam" and finished[0]["next"] == ["Alex", "Kim"]
    assert finished[0]["source"] == "websocket"
    attributes = tournament(hass).attributes
    assert attributes["status"] == "waiting" and attributes["next_at"]
    assert state(hass, "sensor", "tournament") == "round_2"

    # Darts during the pause start no new match.
    await throw(hass, coordinator, T20)
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["winner"] == 2
    # The pause ends while darts are on the board: the takeout starts the match.
    await throw(hass, coordinator, T20, pull=False)
    freezer.tick(timedelta(seconds=19))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "waiting"
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()
    assert tournament(hass).attributes["status"] == "playing"
    assert state(hass, "text", "practice_player_1") == "Alex"

    await throw(hass, coordinator, *CHECKOUT)
    # The pause ends with an empty board: the next match starts at once.
    freezer.tick(timedelta(seconds=19))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["current"]["players"] == ["Sam", "Alex"]
    await throw(hass, coordinator, S1, S1, S1)
    await throw(hass, coordinator, *CHECKOUT)
    assert fired(events, "tournament_finished") == [
        {
            "format": "round_robin",
            "game": 101,
            "matches": 3,
            "winner": "Alex",
            "runner_up": "Sam",
            "third": "Kim",
            "players": PLAYERS,
            "source": "websocket",
        }
    ]
    assert state(hass, "sensor", "tournament") == "finished"
    attributes = tournament(hass).attributes
    assert attributes["winner"] == "Alex"
    assert [row["name"] for row in attributes["standings"]] == ["Alex", "Sam", "Kim"]
    # Tournament matches go into the profiles and the head-to-head records.
    last = hass.states.get(entity_id(hass, "sensor", "last_match"))
    assert last.attributes["winner"] == "Alex"
    assert len(last.attributes["matches"]) == 3

    await press(hass, "tournament_stop")
    assert state(hass, "sensor", "tournament") == "no_tournament"


async def test_the_pause_waits_for_the_button_and_changes_at_once(
    hass, aioclient_mock, freezer
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id(hass, "number", "tournament_pause"), "value": 0},
        blocking=True,
    )
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1)
    with pytest.raises(ServiceValidationError) as error:
        await press(hass, "tournament_next_match")
    assert error.value.translation_key == "tournament_match_running"
    await throw(hass, coordinator, *CHECKOUT)
    assert tournament(hass).attributes["next_at"] is None
    await pass_pause(hass, 3600)
    assert tournament(hass).attributes["status"] == "waiting"
    # A pause set now counts from the end of the match and its summary.
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id(hass, "number", "tournament_pause"), "value": 30},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert tournament(hass).attributes["pause"] == 30
    assert tournament(hass).attributes["status"] == "waiting"
    freezer.tick(timedelta(seconds=39))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "playing"
    # The button starts the next match at once.
    await throw(hass, coordinator, *CHECKOUT)
    await press(hass, "tournament_next_match")
    assert tournament(hass).attributes["current"]["match"] == 3


async def test_a_timer_that_fires_early_waits_again(hass, aioclient_mock, freezer):
    # A frozen clock: however long the test takes, the pause is not over.
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1)
    await throw(hass, coordinator, *CHECKOUT)
    # The timer fires before the pause is over.
    coordinator._fixture_unsub()
    await coordinator._async_fixture_due(dt_util.utcnow())
    assert coordinator._fixture_unsub is not None
    assert tournament(hass).attributes["status"] == "waiting"
    await action(hass, "stop_tournament")
    assert coordinator._fixture_unsub is None


async def test_the_entities_set_the_next_tournament_up(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    registry = er.async_get(hass)
    for platform, key in (
        ("select", "tournament_format"),
        ("select", "tournament_game"),
        ("text", "tournament_players"),
        ("number", "tournament_pause"),
        ("number", "tournament_summary"),
        ("switch", "tournament_third_place"),
        ("switch", "tournament_random_draw"),
    ):
        entry_ = registry.async_get(entity_id(hass, platform, key))
        assert entry_.entity_category == er.EntityCategory.CONFIG, key
    assert state(hass, "select", "tournament_format") == "round_robin"
    assert state(hass, "select", "tournament_game") == "501"
    assert state(hass, "number", "tournament_pause") == "10"
    assert state(hass, "number", "tournament_summary") == "8"
    assert state(hass, "switch", "tournament_third_place") == "off"
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id(hass, "number", "tournament_summary"), "value": 12},
        blocking=True,
    )
    assert state(hass, "number", "tournament_summary") == "12"
    for key, option in (
        ("tournament_format", "knockout"),
        ("tournament_game", "cricket"),
    ):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id(hass, "select", key), "option": option},
            blocking=True,
        )
    await hass.services.async_call(
        "text",
        "set_value",
        {
            "entity_id": entity_id(hass, "text", "tournament_players"),
            "value": "Alex; Sam, Kim,Lea",
        },
        blocking=True,
    )
    await switch(hass, "tournament_third_place", True)
    await switch(hass, "tournament_random_draw", True)
    await switch(hass, "tournament_random_draw", False)
    assert state(hass, "text", "tournament_players") == "Alex, Sam, Kim, Lea"
    assert state(hass, "switch", "tournament_third_place") == "on"

    events = record(hass, coordinator)
    await press(hass, "tournament_start")
    assert fired(events, "tournament_started")[0]["format"] == "knockout"
    assert state(hass, "sensor", "tournament") == "semi_final"
    attributes = tournament(hass).attributes
    assert attributes["game"] == "cricket" and attributes["third_place"] is True
    assert [item["stage"] for item in attributes["bracket"]] == [
        "semi_final",
        "final",
        "third_place",
    ]
    assert state(hass, "select", "practice_game") == "cricket"
    await press(hass, "tournament_stop")
    with pytest.raises(ServiceValidationError) as error:
        await press(hass, "tournament_stop")
    assert error.value.translation_key == "no_tournament"


async def test_the_action_checks_its_players(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock, state=board())
    with pytest.raises(ServiceValidationError) as error:
        await action(hass, "start_tournament")
    assert error.value.translation_key == "tournament_players"
    with pytest.raises(ServiceValidationError) as error:
        await action(hass, "start_tournament", players=["Alex", "Sam", "ALEX"])
    assert error.value.translation_key == "duplicate_player"
    with pytest.raises(ServiceValidationError) as error:
        await action(hass, "next_tournament_match")
    assert error.value.translation_key == "no_tournament"
    assert state(hass, "sensor", "tournament") == "no_tournament"


async def test_the_action_sets_rules_draw_and_pause(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await action(
        hass,
        "start_tournament",
        players=["Alex", "Sam", "Kim", "Lea", "Max"],
        format="knockout",
        game="301",
        legs=2,
        sets=2,
        double_out=False,
        double_in=True,
        bull_off=True,
        bull_off_distance=True,
        third_place=True,
        seed=11,
        pause=0,
        summary=3,
    )
    attributes = tournament(hass).attributes
    assert attributes["seed"] == 11 and attributes["pause"] == 0
    assert attributes["summary"] == 3
    assert sorted(attributes["players"]) == ["Alex", "Kim", "Lea", "Max", "Sam"]
    assert (attributes["legs_to_win"], attributes["sets_to_win"]) == (2, 2)
    practice = coordinator.practice
    assert practice.game == 301 and practice.double_in and not practice.double_out
    assert practice.bull_off and practice.bulling is not None
    assert state(hass, "switch", "tournament_third_place") == "on"
    assert state(hass, "number", "tournament_pause") == "0"


async def test_a_tournament_survives_a_restart(
    hass, aioclient_mock, hass_storage, freezer
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1)
    await throw(hass, coordinator, *CHECKOUT)
    assert coordinator.practice.hold
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass_storage[f"autodarts.{entry.entry_id}.training"]["data"]["tournament"]
    coordinator = entry.runtime_data.local
    assert coordinator.practice.hold
    assert state(hass, "sensor", "tournament") == "round_2"
    assert tournament(hass).attributes["status"] == "waiting"
    # The pause ended while Home Assistant was stopped: the match starts now.
    freezer.tick(timedelta(seconds=60))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "playing"
    await throw(hass, coordinator, S20)
    assert coordinator.practice.players[0].remaining == 81


async def test_diagnostics_count_the_tournament_without_names(
    hass, aioclient_mock, hass_client
):
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await setup_local(hass, aioclient_mock, state=board())
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1)
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diagnostics["tournament"] == {
        "format": "round_robin",
        "game": "101",
        "players": 3,
        "third_place": False,
        "random_draw": False,
        "pause": 10,
        "summary": 8,
        "running": {
            "format": "round_robin",
            "game": "101",
            "status": "playing",
            "players": 3,
            "matches_played": 0,
            "matches_total": 3,
        },
    }
    text = json.dumps(diagnostics)
    for name in PLAYERS:
        assert name not in text


async def test_another_game_in_the_pause_is_played_to_its_end(
    hass, aioclient_mock, freezer
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await action(hass, "start_tournament", players=PLAYERS, game="101", legs=1)
    await throw(hass, coordinator, *CHECKOUT)
    # Somebody plays a game of their own during the pause.
    await action(hass, "start_game", game="301", players=["Tom"])
    freezer.tick(timedelta(seconds=19))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "waiting"
    assert coordinator.practice.kind == 301
    await throw(hass, coordinator, T20)
    assert tournament(hass).attributes["status"] == "waiting"
    # A training game makes no way by itself either; ending the game does.
    await action(hass, "start_game", game="doubles")
    freezer.tick(timedelta(seconds=1))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "waiting"
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id(hass, "select", "practice_game"), "option": "off"},
        blocking=True,
    )
    freezer.tick(timedelta(seconds=5))
    await pass_pause(hass, 0)
    assert tournament(hass).attributes["status"] == "playing"
    assert coordinator._fixture_unsub is None
    assert state(hass, "text", "practice_player_1") == "Alex"


async def test_the_action_takes_start_scores_for_a_handicap(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    await action(
        hass,
        "start_tournament",
        players=PLAYERS,
        game="501",
        start_scores=[501, 301, 0],
        legs=1,
    )
    assert tournament(hass).attributes["start_scores"] == [501, 301, 0]
    # Kim against Sam: Sam starts from 301.
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert [score["remaining"] for score in remaining.attributes["scores"]] == [
        501,
        301,
    ]
    assert entry.runtime_data.local.practice.starts == [0, 301, 0, 0]
    with pytest.raises(vol.Invalid):
        await action(hass, "start_tournament", players=PLAYERS, start_scores=[1])
