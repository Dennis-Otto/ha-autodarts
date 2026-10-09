"""A dartboard without Autodarts: set up without a board, every dart entered in
Home Assistant, with the games, the training and the statistics of a board."""

from datetime import timedelta

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.autodarts.config_flow import AutodartsConfigFlow
from custom_components.autodarts.diagnostics import async_get_config_entry_diagnostics
from custom_components.autodarts.local_coordinator import (
    MANUAL_STATE,
    AutodartsManualCoordinator,
)
from custom_components.autodarts.storage import storage_key

from .local_helpers import entity_summary, record

BOARD_ID = "manual_0123456789abcdef0123456789abcdef"
DATA = {
    "board_id": BOARD_ID,
    "manual_board": True,
    "local_only": True,
    "name": "Garage",
}


async def setup_manual(hass, **kwargs) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain="autodarts",
        version=2,
        unique_id=BOARD_ID,
        title="Autodarts (Garage)",
        data=DATA,
        **kwargs,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity(hass, platform: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        platform, "autodarts", f"{BOARD_ID}_{key}"
    )


def value(hass, platform: str, key: str) -> str:
    entity_id = entity(hass, platform, key)
    assert entity_id is not None
    return hass.states.get(entity_id).state


async def act(hass, service: str, **data) -> None:
    await hass.services.async_call("autodarts", service, data, blocking=True)
    await hass.async_block_till_done()


async def test_setup_offers_a_dartboard_without_autodarts(hass):
    result = await hass.config_entries.flow.async_init(
        "autodarts", context={"source": SOURCE_USER}
    )
    assert result["menu_options"][-1] == "manual"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    # The name is trimmed, and none is no name.
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"name": "   "}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": " Garage "}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Autodarts (Garage)"
    entry = result["result"]
    board_id = entry.data["board_id"]
    assert board_id.startswith("manual_") and len(board_id) == 39
    assert entry.unique_id == board_id
    assert entry.data == {
        "board_id": board_id,
        "manual_board": True,
        "local_only": True,
        "name": "Garage",
    }
    # Without a board, there is no bridge for online matches to set up.
    assert not AutodartsConfigFlow.async_supports_options_flow(entry)


async def test_a_home_may_have_several_dartboards_without_autodarts(hass):
    for name in ("Garage", "Cellar"):
        result = await hass.config_entries.flow.async_init(
            "autodarts", context={"source": SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )
        flow = hass.config_entries.flow.async_progress()[0]["flow_id"]
        await hass.config_entries.flow.async_configure(flow, {"name": name})
        await hass.async_block_till_done()
    entries = hass.config_entries.async_entries("autodarts")
    assert [entry.title for entry in entries] == [
        "Autodarts (Garage)",
        "Autodarts (Cellar)",
    ]
    assert len({entry.unique_id for entry in entries}) == 2
    names = {
        device.name
        for entry in entries
        for device in dr.async_entries_for_config_entry(
            dr.async_get(hass), entry.entry_id
        )
    }
    assert names == {"Garage", "Cellar"}


async def test_a_dartboard_without_autodarts_has_the_entities_of_the_games(
    hass, aioclient_mock, snapshot
):
    entry = await setup_manual(hass)
    # Nothing is ever asked of a board.
    assert not aioclient_mock.mock_calls
    coordinator = entry.runtime_data.local
    assert isinstance(coordinator, AutodartsManualCoordinator)
    assert coordinator.manual_board and coordinator.update_interval is None
    assert entry.runtime_data.cloud is None and entry.runtime_data.bridge is None
    assert entity_summary(hass, entry) == snapshot
    assert value(hass, "sensor", "local_status") == "manual"
    assert value(hass, "sensor", "local_visit_score") == "0"
    assert value(hass, "switch", "training_session") == "on"
    # Every dart is entered by hand, so manual entry is on and cannot be turned off.
    assert coordinator.practice.manual_entry
    for platform, key in (
        ("switch", "practice_manual_entry"),
        ("switch", "detection"),
        ("switch", "free_stuck_takeout"),
        ("binary_sensor", "local_connected"),
        ("button", "calibrate"),
        ("select", "standby_minutes"),
        ("sensor", "correction_rate"),
        ("sensor", "num_throws"),
        ("sensor", "detection_fps"),
        ("camera", "camera_0"),
        ("update", "board_software"),
    ):
        assert entity(hass, platform, key) is None, key
    device = dr.async_get(hass).async_get_device_by_identifier(
        ("autodarts", BOARD_ID), entry.entry_id
    )
    assert device.name == "Garage"
    assert device.manufacturer is None
    assert device.configuration_url is None and device.sw_version is None
    # Time passes without a read of any board.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()
    assert not aioclient_mock.mock_calls
    assert value(hass, "sensor", "local_status") == "manual"


async def test_every_dart_is_entered_by_hand(hass):
    entry = await setup_manual(hass)
    coordinator = entry.runtime_data.local
    await act(hass, "start_game", game="501", players=["Alex", "Sam"])
    events = record(hass, coordinator)
    for bed in ("T20", "T20", "T20"):
        await act(hass, "throw_dart", segment=bed)
    assert value(hass, "sensor", "local_visit_score") == "180"
    assert value(hass, "sensor", "last_throw") == "T20"
    await act(hass, "next_player")
    assert value(hass, "sensor", "practice_remaining") == "501"
    remaining = hass.states.get(entity(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["name"] == "Sam"
    assert value(hass, "sensor", "training_darts") == "3"
    assert value(hass, "sensor", "training_scores_180") == "1"
    kinds = [kind for kind, _ in events]
    assert kinds.count("dart_detected") == 3
    assert "visit_thrown" in kinds and "visit_completed" in kinds
    completed = next(item for kind, item in events if kind == "visit_completed")
    assert completed["score"] == 180 and completed["manual"] is True
    # Sam passes.
    await act(hass, "next_player")
    remaining = hass.states.get(entity(hass, "sensor", "practice_remaining"))
    assert remaining.attributes["name"] == "Alex"
    # The board waits for darts; the status never changes by itself.
    assert value(hass, "sensor", "local_status") == "manual"
    assert coordinator.data["local"] == MANUAL_STATE


async def test_manual_entry_stays_on_after_a_restart(hass, hass_storage):
    # The store of a board that had manual entry off, before it lost its Autodarts.
    hass_storage[storage_key("manual-entry")] = {
        "version": 1,
        "minor_version": 3,
        "key": storage_key("manual-entry"),
        "data": {"practice": {"game": 301, "manual_entry": False}},
    }
    entry = await setup_manual(hass, entry_id="manual-entry")
    coordinator = entry.runtime_data.local
    assert coordinator.practice.manual_entry
    await act(hass, "throw_dart", segment="S20")
    await act(hass, "next_player")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data.local
    assert coordinator.practice.manual_entry
    assert value(hass, "sensor", "practice_remaining") == "281"
    assert value(hass, "sensor", "training_darts") == "1"
    # A refresh keeps the game as it is.
    await coordinator.async_refresh()
    assert value(hass, "sensor", "practice_remaining") == "281"


async def test_nothing_on_a_dartboard_without_autodarts_can_be_controlled(hass):
    entry = await setup_manual(hass)
    coordinator = entry.runtime_data.local
    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_recalibrate()
    assert error.value.translation_key == "no_board_manager"
    with pytest.raises(HomeAssistantError):
        assert coordinator.client
    assert coordinator._stream_task is None


async def test_diagnostics_of_a_dartboard_without_autodarts(hass):
    entry = await setup_manual(hass)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["connection"] == {"manual_board": True}
    assert diagnostics["local_available"] is True
    assert diagnostics["realtime_connected"] is False
    assert diagnostics["board_manager_generation"] is None


async def test_a_dartboard_without_autodarts_has_nothing_to_set_up_again(hass):
    entry = await setup_manual(hass)
    result = await hass.config_entries.flow.async_init(
        "autodarts",
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "manual_board"


async def test_removing_a_dartboard_without_autodarts_removes_its_training(
    hass, hass_storage
):
    entry = await setup_manual(hass)
    await act(hass, "start_game", game="301")
    await act(hass, "throw_dart", segment="S20")
    await act(hass, "next_player")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert storage_key(entry.entry_id) in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert storage_key(entry.entry_id) not in hass_storage
