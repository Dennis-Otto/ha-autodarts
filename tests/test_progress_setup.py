"""Achievements, the players' progress and dart positions in Home Assistant."""

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.const import DOMAIN

from .local_helpers import (
    BULL,
    OUTER_BULL,
    T20,
    board,
    entity_id,
    local_entry_data,
    mock_board,
    record,
    setup_local,
    state,
    switch,
)
from .test_practice_setup import select_game

# Where the darts land: T20 slightly left of the centre of the bed, the bulls
# near the middle.
COORDS = {"T20": (-0.02, 0.6), "Bull": (0.01, 0.0), "25": (0.05, 0.05)}


def placed(*hits):
    """A board state whose darts carry positions."""
    state = board(*hits)
    for dart in state["throws"]:
        x, y = COORDS[dart["segment"]["name"]]
        dart["coords"] = {"x": x, "y": y}
    return state


async def throw(hass, coordinator, *darts) -> None:
    for count in range(1, len(darts) + 1):
        coordinator.async_receive("state", placed(*darts[:count]))
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()


def device_id(hass, entry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "board-1"), entry.entry_id
    )
    assert device is not None
    return device.id


async def positions(hass, client, **data) -> dict:
    await client.send_json_auto_id({"type": "autodarts/positions", **data})
    return await client.receive_json()


async def test_a_180_unlocks_an_achievement(hass, aioclient_mock, hass_ws_client):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = record(hass, coordinator)
    assert state(hass, "sensor", "achievements") == "0"
    assert state(hass, "switch", "achievements_enabled") == "on"
    coordinator.practice.set_name(0, "Alex")
    await select_game(hass, "501")
    await throw(hass, coordinator, T20, T20, T20)

    unlocked = [details for kind, details in events if kind == "achievement_unlocked"]
    assert unlocked == [
        {
            "player": 1,
            "name": "Alex",
            "achievement": "maximum",
            "tier": 1,
            "tiers": 3,
            "threshold": 1,
            "source": "websocket",
        }
    ]
    # It comes after the visit and the turn it belongs to.
    kinds = [kind for kind, _ in events]
    assert kinds.index("achievement_unlocked") > kinds.index("turn_changed")
    event = hass.states.get(entity_id(hass, "event", "board_events"))
    assert event.attributes["event_type"] == "achievement_unlocked"

    achievements = hass.states.get(entity_id(hass, "sensor", "achievements"))
    assert achievements.state == "1"
    assert achievements.attributes["unit_of_measurement"] == "badges"
    assert achievements.attributes["latest"]["achievement"] == "maximum"
    [alex] = achievements.attributes["players"]
    assert alex["badges"]["maximum"]["tier"] == 1
    assert achievements.attributes["catalogue"][0]["id"] == "maximum"

    profiles = hass.states.get(entity_id(hass, "sensor", "player_profiles"))
    [profile] = profiles.attributes["players"]
    assert profile["name"] == "Alex" and profile["maximums"] == 1
    assert profile["hits"] == {"T20": 3} and profile["streak"] == 1
    assert profile["trend"]["maximums"][-1] == 1
    assert profile["spread"] == []

    client = await hass_ws_client(hass)
    session = await positions(hass, client, device_id=device_id(hass, entry))
    assert session["success"] is True
    assert session["result"]["positions"] == [[-0.02, 0.6]] * 3
    player = await positions(
        hass, client, device_id=device_id(hass, entry), player="alex"
    )
    assert player["result"]["player"] == "Alex"
    assert len(player["result"]["positions"]) == 3


async def test_achievements_can_be_turned_off(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    events = record(hass, coordinator)
    coordinator.practice.set_name(0, "Alex")
    await select_game(hass, "501")
    await switch(hass, "achievements_enabled", False)
    assert state(hass, "switch", "achievements_enabled") == "off"
    await throw(hass, coordinator, OUTER_BULL, BULL, OUTER_BULL)
    assert "achievement_unlocked" not in [kind for kind, _ in events]
    assert state(hass, "sensor", "achievements") == "0"
    # Turned on again, what was reached meanwhile unlocks quietly.
    await switch(hass, "achievements_enabled", True)
    assert "achievement_unlocked" not in [kind for kind, _ in events]
    assert state(hass, "sensor", "achievements") == "1"


async def test_progress_survives_a_restart_and_leaves_with_the_player(
    hass, aioclient_mock, hass_storage
):
    mock_board(aioclient_mock, state=board())
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data=local_entry_data(), entry_id="progress-entry"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data.local
    coordinator.practice.set_name(0, "Alex")
    await select_game(hass, "501")
    await throw(hass, coordinator, T20, T20, T20)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    saved = hass_storage["autodarts.progress-entry.training"]["data"]["progress"]
    assert saved["players"][0]["counters"]["maximums"] == 1
    coordinator = entry.runtime_data.local
    assert coordinator.progress.players["alex"].counters["maximums"] == 1
    assert state(hass, "sensor", "achievements") == "1"
    assert len(coordinator.progress.session) == 3

    # A new training session starts its positions from zero.
    await switch(hass, "training_session", False)
    await switch(hass, "training_session", True)
    assert len(coordinator.progress.session) == 0

    await hass.services.async_call(
        DOMAIN, "delete_player", {"name": "ALEX"}, blocking=True
    )
    await hass.async_block_till_done()
    assert coordinator.progress.players == {}
    assert state(hass, "sensor", "achievements") == "0"


async def test_positions_need_a_loaded_board(hass, aioclient_mock, hass_ws_client):
    entry = await setup_local(hass, aioclient_mock, state=board())
    client = await hass_ws_client(hass)
    unknown = await positions(hass, client, device_id="nothing")
    assert unknown["success"] is False
    assert unknown["error"]["code"] == "not_found"
    other = MockConfigEntry(domain="demo")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("demo", "lamp")}
    )
    foreign = await positions(hass, client, device_id=device.id)
    assert (foreign["success"], foreign["error"]["code"]) == (False, "not_found")
    board_device = device_id(hass, entry)
    assert (await positions(hass, client, device_id=board_device))["success"] is True
    assert await hass.config_entries.async_unload(entry.entry_id)
    unloaded = await positions(hass, client, device_id=board_device)
    assert (unloaded["success"], unloaded["error"]["code"]) == (False, "not_found")


async def test_corrected_darts_are_logged_only_where_the_correction_puts_them(
    hass, aioclient_mock, hass_ws_client
):
    entry = await setup_local(hass, aioclient_mock, state=board())
    coordinator = entry.runtime_data.local
    coordinator.practice.set_name(0, "Alex")
    await select_game(hass, "501")
    coordinator.async_receive("state", placed(T20))
    coordinator.async_receive("state", placed(T20, T20))
    await hass.async_block_till_done()
    # The board read a treble 20 where a single 20 is: the spot it saw is wrong too.
    await hass.services.async_call(
        DOMAIN, "correct_dart", {"dart": 2, "segment": "S20"}, blocking=True
    )
    coordinator.async_receive("state", placed(T20, T20, T20))
    await hass.async_block_till_done()
    # The third dart is corrected with the spot where it is; the bed follows from it.
    await hass.services.async_call(
        DOMAIN, "correct_dart", {"dart": 3, "x": 0.0, "y": 0.8}, blocking=True
    )
    await hass.async_block_till_done()
    visit = hass.states.get(entity_id(hass, "sensor", "local_visit_score"))
    assert [
        (dart["segment"], dart.get("x"), dart.get("y"))
        for dart in visit.attributes["throws"]
    ] == [("T20", -0.02, 0.6), ("S20", None, None), ("S20", 0.0, 0.8)]
    assert visit.state == "100"
    coordinator.async_receive("state", board())
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    device = device_id(hass, entry)
    logged = [[-0.02, 0.6], [0.0, 0.8]]
    session = await positions(hass, client, device_id=device)
    assert session["result"]["positions"] == logged
    player = await positions(hass, client, device_id=device, player="Alex")
    assert player["result"]["positions"] == logged

    # An undone visit comes back with the positions it had.
    await hass.services.async_call(DOMAIN, "undo_visit", {}, blocking=True)
    await hass.async_block_till_done()
    visit = hass.states.get(entity_id(hass, "sensor", "local_visit_score"))
    assert [
        (dart["segment"], dart.get("x")) for dart in visit.attributes["throws"]
    ] == [("T20", -0.02), ("S20", None), ("S20", 0.0)]
    assert len(coordinator.progress.session) == 0
