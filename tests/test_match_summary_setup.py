"""The match summary, states that stay as written and double out in Home Assistant."""

import json

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.autodarts.const import DOMAIN

from .local_helpers import T20, board, entity_id, record, setup_local, state, switch

D20 = ("D20", 20, 2)
S1 = ("S1", 1, 1)


async def start_game(hass, **fields) -> None:
    await hass.services.async_call(DOMAIN, "start_game", fields, blocking=True)
    await hass.async_block_till_done()


async def throw(hass, coordinator, *darts) -> None:
    """Throw a visit dart by dart, then pull the darts."""
    for count in range(1, len(darts) + 1):
        coordinator.async_receive("state", board(*darts[:count]))
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()


async def test_a_finished_match_shows_its_summary_and_announces_it(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = record(hass, coordinator)
    await start_game(hass, game="101", players=["Alex", "Sam"], legs=2)
    sensor = entity_id(hass, "sensor", "practice_remaining")
    await throw(hass, coordinator, T20, S1, D20)
    first = hass.states.get(sensor)
    assert first.attributes["summary"] is None and len(first.attributes["legs"]) == 1
    # Sam wins the second leg, Alex the third and the match.
    await throw(hass, coordinator, T20, S1, D20)
    # A state Home Assistant wrote keeps its attributes.
    assert len(first.attributes["legs"]) == 1
    await throw(hass, coordinator, T20, S1, D20)
    attributes = hass.states.get(sensor).attributes
    summary = attributes["summary"]
    assert attributes["winner"] == 1 and summary["winner"] == 1
    assert (summary["game"], summary["legs_to_win"], summary["sets_to_win"]) == (
        101,
        2,
        1,
    )
    assert [
        (player["name"], player["legs"], player["darts"], player["average"])
        for player in summary["players"]
    ] == [("Alex", 2, 6, 101.0), ("Sam", 1, 3, 101.0)]
    alex = summary["players"][0]
    assert (alex["highest_checkout"], alex["best_leg"], alex["checkout_rate"]) == (
        101,
        3,
        100.0,
    )
    won = [details for kind, details in events if kind == "match_won"]
    assert len(won) == 1 and won[0]["summary"] == summary["players"]
    # The store keeps the summary for a restart.
    assert coordinator.practice.stored()["summary"]["players"] == summary["players"]


async def test_double_out_switched_during_a_leg_applies_from_the_next(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start_game(hass, game="301", double_out=False)
    await throw(hass, coordinator, T20)
    await switch(hass, "practice_double_out", True)
    sensor = entity_id(hass, "sensor", "practice_remaining")
    assert state(hass, "switch", "practice_double_out") == "on"
    assert hass.states.get(sensor).attributes["double_out"] is False
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id(hass, "button", "practice_new_leg")},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(sensor).attributes["double_out"] is True
    # A new game takes the rule it asks for at once.
    await throw(hass, coordinator, T20)
    await start_game(hass, game="301", double_out=False)
    assert coordinator.practice.double_out is False
    assert state(hass, "switch", "practice_double_out") == "off"


async def test_diagnostics_leave_the_names_of_the_summary_out(
    hass, aioclient_mock, hass_client
):
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    await start_game(hass, game="101", players=["Alexandra", "Samuel"])
    await throw(hass, coordinator, T20, S1, D20)
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    summary = diagnostics["local"]["practice"]["summary"]
    assert [player["name"] for player in summary["players"]] == ["**REDACTED**"] * 2
    assert "Alexandra" not in json.dumps(diagnostics)
