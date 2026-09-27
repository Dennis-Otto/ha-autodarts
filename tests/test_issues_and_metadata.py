"""Repair issues, translated states, entity metadata and quiet cloud logging."""

import logging
from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.coordinator import AutodartsDataUpdateCoordinator
from custom_components.autodarts.errors import AutodartsConnectionError
from custom_components.autodarts.local_coordinator import ISSUES

from .local_helpers import (
    CONFIG,
    STATE,
    entity_id,
    local_entry_data,
    mock_board,
    setup_local,
    setup_v2,
    state,
)


def issue(hass, name, entry):
    return ir.async_get(hass).async_get_issue("autodarts", f"{name}_{entry.entry_id}")


async def test_classic_board_manager_asks_to_update(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock)
    found = issue(hass, "board_manager_1", entry)
    assert found.severity == ir.IssueSeverity.WARNING
    assert found.translation_key == "board_manager_1"
    assert "headless-installation" in found.learn_more_url
    assert await hass.config_entries.async_remove(entry.entry_id)
    assert issue(hass, "board_manager_1", entry) is None


async def test_update_notice_appears_for_a_known_classic_board(hass, aioclient_mock):
    """Entries created by the setup store the generation, which never changes."""
    mock_board(aioclient_mock)
    data = {**local_entry_data(), "api_generation": 1}
    entry = MockConfigEntry(domain="autodarts", version=2, data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert issue(hass, "board_manager_1", entry) is not None
    # Issues are not kept across restarts, so every start reports it again.
    ir.async_delete_issue(hass, "autodarts", f"board_manager_1_{entry.entry_id}")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert issue(hass, "board_manager_1", entry) is not None


async def test_board_manager_2_has_no_update_notice(hass, aioclient_mock):
    entry = await setup_v2(hass, aioclient_mock)
    assert issue(hass, "board_manager_1", entry) is None


async def test_wrong_board_raises_and_clears_a_repair_issue(
    hass, aioclient_mock, freezer
):
    entry = await setup_local(hass, aioclient_mock)
    coordinator = entry.runtime_data.local
    other = deepcopy(CONFIG)
    other["auth"]["board_id"] = "another-board"
    aioclient_mock.clear_requests()
    mock_board(aioclient_mock, config=other)
    # Board Manager 1 reports its board ID with the settings, every 30 seconds.
    freezer.tick(timedelta(seconds=30))
    await coordinator.async_refresh()
    found = issue(hass, "wrong_board", entry)
    assert found.severity == ir.IssueSeverity.ERROR
    assert found.translation_placeholders == {"address": "http://192.0.2.10:3180"}
    assert state(hass, "switch", "detection") == "unavailable"

    aioclient_mock.clear_requests()
    mock_board(aioclient_mock)
    freezer.tick(timedelta(seconds=30))
    await coordinator.async_refresh()
    assert issue(hass, "wrong_board", entry) is None
    assert state(hass, "switch", "detection") == "off"


async def test_removing_the_entry_removes_every_repair_issue(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock)
    for name in ISSUES:
        ir.async_create_issue(
            hass,
            "autodarts",
            f"{name}_{entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=name,
        )
    assert await hass.config_entries.async_remove(entry.entry_id)
    assert all(issue(hass, name, entry) is None for name in ISSUES)


@pytest.mark.parametrize(
    "status,expected",
    [
        ("Takeout in progress", "takeout_in_progress"),
        ("Calibrating", "calibrating"),
        ("Throw", "throw"),
        ("Something new", "unknown"),
        (None, "unknown"),
    ],
)
async def test_detection_status_is_translatable(hass, aioclient_mock, status, expected):
    await setup_local(hass, aioclient_mock, state={**STATE, "status": status})
    assert state(hass, "sensor", "local_status") == expected
    options = hass.states.get(entity_id(hass, "sensor", "local_status")).attributes[
        "options"
    ]
    assert "takeout_in_progress" in options


async def test_entity_categories_and_classes(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock)
    registry = er.async_get(hass)

    def entry(platform, key):
        return registry.async_get(entity_id(hass, platform, key))

    for key in ("start", "stop", "reset"):
        assert entry("button", key).entity_category is None
    restart = entry("button", "restart")
    assert restart.entity_category == EntityCategory.CONFIG
    assert restart.original_device_class == ButtonDeviceClass.RESTART
    assert entry("binary_sensor", "cameras_active").original_device_class == "running"
    assert entry("binary_sensor", "calibrating").original_device_class == "running"
    darts = hass.states.get(entity_id(hass, "sensor", "training_darts"))
    assert darts.attributes["state_class"] == "total_increasing"
    assert "icon" not in darts.attributes


async def test_failed_match_reads_are_logged_once(hass, caplog):
    cloud = AsyncMock()
    cloud.get_board.return_value = {"id": "board-1", "matchId": "match-1"}
    cloud.get_match.side_effect = AutodartsConnectionError
    coordinator = AutodartsDataUpdateCoordinator(hass, cloud, "board-1")
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            await coordinator.async_refresh()
    assert coordinator.data["match"] is None
    assert caplog.text.count("Could not fetch the current match") == 1
    cloud.get_match.side_effect = None
    cloud.get_match.return_value = {"id": "match-1"}
    cloud.get_match_state.return_value = {"round": 2}
    await coordinator.async_refresh()
    assert coordinator.data["match"] == {
        "id": "match-1",
        "round": 2,
    }
    cloud.get_match.side_effect = AutodartsConnectionError
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        await coordinator.async_refresh()
    assert "Could not fetch the current match" in caplog.text


@pytest.mark.parametrize("match_id", [42, {"id": "match-1"}, ["match-1"]])
async def test_match_id_that_is_no_text_means_no_match(hass, match_id):
    cloud = AsyncMock()
    cloud.get_board.return_value = {"id": "board-1", "matchId": match_id}
    coordinator = AutodartsDataUpdateCoordinator(hass, cloud, "board-1")
    await coordinator.async_refresh()
    assert coordinator.data["match"] is None
    cloud.get_match.assert_not_called()


def test_cloud_match_values():
    from custom_components.autodarts import sensor

    match = {
        "variant": "X01",
        "round": 4,
        "turnScore": 81,
        "finished": False,
        "turns": [{"throws": [{}, {}, {}]}, {"throws": [{}]}, {}],
    }
    data = {
        "board": {"state": {"connected": True, "event": "Throw detected"}},
        "match": match,
    }
    assert sensor._get_board_status(data) == "connected"
    assert sensor._get_board_event(data) == "Throw detected"
    assert sensor._get_game_mode(data) == "X01"
    assert sensor._get_match_state(data) == "active"
    assert sensor._get_round(data) == 4
    assert sensor._get_visit_score(data) == 81
    assert sensor._get_darts_thrown(data) == 4
    assert sensor._get_match_state({"match": {**match, "finished": True}}) == "finished"
    assert sensor._get_darts_thrown({"match": {"turns": None}}) is None

    empty = {"board": {"status": "Offline"}}
    assert sensor._get_board_status(empty) == "disconnected"
    assert sensor._get_board_event(empty) == "Offline"
    assert sensor._get_match_state(empty) == "no_match"
    for value in (
        sensor._get_game_mode,
        sensor._get_round,
        sensor._get_visit_score,
        sensor._get_darts_thrown,
    ):
        assert value(empty) is None


async def test_training_average_is_unknown_without_darts(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock)
    assert state(hass, "sensor", "training_average") == "unknown"
    average = hass.states.get(entity_id(hass, "sensor", "training_average"))
    assert average.attributes["state_class"] == "measurement"
    darts = hass.states.get(entity_id(hass, "sensor", "training_darts"))
    assert darts.attributes["hits"] == {}


async def test_training_values_have_the_units_of_the_live_sensors(hass, aioclient_mock):
    await setup_local(hass, aioclient_mock)
    units = {
        key: hass.states.get(
            entity_id(hass, "sensor", f"training_{key}")
        ).attributes.get("unit_of_measurement")
        for key in ("darts", "triples", "points", "average", "visits", "scores_180")
    }
    assert units == {
        "darts": "darts",
        "triples": "darts",
        "points": "points",
        "average": "points",
        "visits": "visits",
        "scores_180": "visits",
    }
    started = hass.states.get(entity_id(hass, "sensor", "training_started"))
    assert "unit_of_measurement" not in started.attributes
