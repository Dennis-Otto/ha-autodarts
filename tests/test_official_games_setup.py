"""Bermuda, Round the World and Gotcha in Home Assistant: their rules as
configuration entities, the start_game action and the scoreboard."""

import pytest
import voluptuous as vol
from homeassistant.helpers import entity_registry as er

from custom_components.homedarts.const import DOMAIN

from .local_helpers import (
    T20,
    board,
    entity_id,
    setup_local,
    state,
    switch,
)
from .test_practice_setup import select_game, set_number, throw


async def test_the_rules_of_the_new_games_are_configuration_entities(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    practice = entry.runtime_data.local.games.practice
    registry = er.async_get(hass)
    for platform, key, value in (
        ("switch", "practice_bermuda_halve_on_miss", "on"),
        ("select", "practice_round_the_world_order", "ascending"),
        ("number", "practice_gotcha_target", "301"),
    ):
        assert state(hass, platform, key) == value
        entity = registry.async_get(entity_id(hass, platform, key))
        assert entity.entity_category == er.EntityCategory.CONFIG
    await select_game(hass, "bermuda")
    await switch(hass, "practice_bermuda_halve_on_miss", False)
    assert practice.party.kind == "bermuda" and not practice.party.halves
    await select_game(hass, "round_the_world")
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": entity_id(hass, "select", "practice_round_the_world_order"),
            "option": "descending",
        },
        blocking=True,
    )
    assert practice.party.order == "descending"
    assert state(hass, "sensor", "practice_target") == "20"
    await select_game(hass, "gotcha")
    await set_number(hass, "practice_gotcha_target", 501)
    assert practice.party.goal == 501
    assert state(hass, "number", "practice_gotcha_target") == "501"


async def test_start_game_plays_the_new_games_with_their_rules(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    practice = coordinator.games.practice
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {"game": "bermuda", "players": ["Alex", "Sam"], "halve_on_miss": False},
        blocking=True,
    )
    assert practice.party.kind == "bermuda" and not practice.bermuda_halve_on_miss
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["rounds"] == 13
    assert remaining.attributes["target"] == "12"
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {"game": "Round the World", "order": "random"},
        blocking=True,
    )
    assert practice.party.kind == "round_the_world"
    assert practice.round_the_world_order == "random"
    await hass.services.async_call(
        DOMAIN,
        "start_game",
        {
            "game": "gotcha",
            "players": ["Alex", "Sam", "Kim"],
            "target_score": "201",
            "out_mode": "straight",
        },
        blocking=True,
    )
    assert practice.party.goal == 201 and practice.party.out_mode == "straight"
    await throw(hass, coordinator, T20)
    remaining = hass.states.get(entity_id(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["game"] == "gotcha"
    assert remaining.attributes["scores"][0]["left"] == 141
    for wrong in ({"order": "sideways"}, {"target_score": 100}):
        with pytest.raises(vol.Invalid):
            await hass.services.async_call(
                DOMAIN, "start_game", {"game": "gotcha", **wrong}, blocking=True
            )
