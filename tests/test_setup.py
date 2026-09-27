"""Exercise setup, credential persistence and reauthentication in Home Assistant."""

import logging
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts import async_setup_entry
from custom_components.autodarts.api import (
    API_BASE,
    REFRESH_URL,
    AutodartsAuthError,
    AutodartsConnectionError,
)
from custom_components.autodarts.coordinator import AutodartsDataUpdateCoordinator

from .local_helpers import entity_summary, entry_data


@pytest.mark.usefixtures("cloud_link")
async def test_old_entry_requests_reauthentication(hass):
    data = entry_data()
    del data["client_id"]
    entry = MockConfigEntry(domain="autodarts", version=2, data=data)
    entry.add_to_hass(hass)
    with pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


async def test_setup_refreshes_persists_and_loads_sensors(
    hass, aioclient_mock, snapshot
):
    entry = MockConfigEntry(domain="autodarts", version=2, data=entry_data())
    entry.add_to_hass(hass)
    aioclient_mock.post(
        REFRESH_URL,
        json={"access_token": "new", "refresh_token": "rotated", "expires_in": 900},
    )
    aioclient_mock.get(
        f"{API_BASE}/bs/v0/boards/board-1",
        json={"id": "board-1", "name": "My Board", "state": {"connected": True}},
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    assert entry.data["token"]["refresh_token"] == "rotated"
    # Without a local board, the cloud provides the match entities.
    assert entity_summary(hass, entry) == snapshot
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_rotated_refresh_token_saved_before_board_outage(hass, aioclient_mock):
    entry = MockConfigEntry(domain="autodarts", version=2, data=entry_data())
    entry.add_to_hass(hass)
    aioclient_mock.post(
        REFRESH_URL,
        json={"access_token": "new", "refresh_token": "rotated", "expires_in": 900},
    )
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/board-1", status=503)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.data["token"]["refresh_token"] == "rotated"
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_revoked_refresh_triggers_reauth(hass, aioclient_mock):
    entry = MockConfigEntry(domain="autodarts", version=2, data=entry_data())
    entry.add_to_hass(hass)
    aioclient_mock.post(REFRESH_URL, status=400, json={"error": "invalid_grant"})
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(
        flow["context"].get("entry_id") == entry.entry_id
        and flow["step_id"] == "reauth_confirm"
        for flow in flows
    )


@pytest.mark.parametrize("method", ["get_board", "get_match", "get_match_state"])
async def test_auth_errors_from_all_cloud_reads_require_reauth(hass, method):
    cloud = AsyncMock()
    cloud.get_board.return_value = {"id": "board-1", "matchId": "match-1"}
    cloud.get_match.return_value = {"id": "match-1"}
    cloud.get_match_state.return_value = {"round": 1}
    getattr(cloud, method).side_effect = AutodartsAuthError("invalid_token")
    coordinator = AutodartsDataUpdateCoordinator(hass, cloud, "board-1")
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert isinstance(coordinator.last_exception, ConfigEntryAuthFailed)


async def test_cloud_is_polled_quickly_only_during_a_match(hass):
    cloud = AsyncMock()
    cloud.get_board.return_value = {"id": "board-1"}
    coordinator = AutodartsDataUpdateCoordinator(hass, cloud, "board-1")
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=60)
    cloud.get_board.return_value = {"id": "board-1", "matchId": "match-1"}
    cloud.get_match.return_value = {"id": "match-1"}
    cloud.get_match_state.return_value = {"round": 1}
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=5)


async def test_match_without_its_live_state_is_still_shown(hass, caplog):
    cloud = AsyncMock()
    cloud.get_board.return_value = {"id": "board-1", "matchId": "match-1"}
    cloud.get_match.return_value = {"id": "match-1", "variant": "X01"}
    cloud.get_match_state.side_effect = AutodartsConnectionError
    coordinator = AutodartsDataUpdateCoordinator(hass, cloud, "board-1")
    with caplog.at_level(logging.DEBUG):
        await coordinator.async_refresh()
    assert coordinator.data["match"] == {"id": "match-1", "variant": "X01"}
    assert "Could not fetch match state for match-1" in caplog.text
    assert "Could not fetch the current match" not in caplog.text
