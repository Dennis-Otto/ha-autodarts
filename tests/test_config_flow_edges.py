"""Less common config-flow paths: errors, token refresh and optional fields."""

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.api import (
    AutodartsAuthError,
    AutodartsCloudClient,
    AutodartsConnectionError,
)

from .local_helpers import mock_board
from .test_config_flow import (
    BOARD,
    CLIENT_ID,
    DEVICE,
    TOKEN,
    complete_link,
    init_cloud_flow,
    start_link,
)
from .test_local_flow import open_local

GET_BOARDS = "custom_components.autodarts.config_flow.AutodartsCloudClient.get_boards"


async def link_with(hass, result, user_input):
    """Start linking with a custom cloud form and an approval that never ends."""
    future = asyncio.get_running_loop().create_future()

    async def wait_for_approval(*args):
        return await future

    with (
        patch(
            "custom_components.autodarts.config_flow.request_device_code",
            return_value=DEVICE,
        ),
        patch(
            "custom_components.autodarts.config_flow.wait_for_device_token",
            side_effect=wait_for_approval,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
        await asyncio.sleep(0)
    return result, future


async def test_local_board_without_version_is_added(hass, aioclient_mock):
    mock_board(aioclient_mock, version="unknown")
    result = await open_local(hass)
    with patch("custom_components.autodarts.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.0.2.10", "port": 3180}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "api_generation" not in result["data"]


@pytest.mark.usefixtures("cloud_link")
async def test_cloud_form_rejects_an_invalid_board_address(hass):
    result = await init_cloud_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"client_id": CLIENT_ID, "host": "http://bad host/"}
    )
    assert result["step_id"] == "cloud"
    assert result["errors"] == {"host": "invalid_host"}
    result, future = await link_with(
        hass, result, {"client_id": CLIENT_ID, "host": "192.0.2.10"}
    )
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "192.0.2.10"


@pytest.mark.usefixtures("cloud_link")
async def test_cloud_entry_can_include_the_local_board(hass):
    result = await init_cloud_flow(hass)
    result, future = await link_with(
        hass, result, {"client_id": CLIENT_ID, "host": " Board.LAN ", "port": 3181}
    )
    assert result["type"] == FlowResultType.SHOW_PROGRESS
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "board.lan"
    assert result["data"]["port"] == 3181


@pytest.mark.usefixtures("cloud_link")
async def test_unexpected_login_error_and_lost_connection(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    future.set_exception(AutodartsAuthError("server_error"))
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    future.set_exception(AutodartsConnectionError())
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "auth_retry"
    assert result["errors"] == {"base": "cannot_connect"}
    await relink(hass, result)


@pytest.mark.usefixtures("cloud_link")
async def test_rejected_token_while_listing_boards_asks_to_retry(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    future.set_result(TOKEN)
    await hass.async_block_till_done()
    with patch(GET_BOARDS, side_effect=AutodartsAuthError("invalid_grant")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "auth_retry"
    assert result["errors"] == {"base": "invalid_auth"}
    await relink(hass, result)


async def relink(hass, result):
    """After a failed login, linking again creates the entry."""
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "cloud"
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("cloud_link")
async def test_token_refreshed_while_listing_boards_is_stored(hass):
    refreshed = {**TOKEN, "access_token": "refreshed"}
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    future.set_result(TOKEN)
    await hass.async_block_till_done()

    class RefreshingClient(AutodartsCloudClient):
        async def get_boards(self):
            self._on_token_update(refreshed)
            return [BOARD]

    with (
        patch(
            "custom_components.autodarts.config_flow.AutodartsCloudClient",
            RefreshingClient,
        ),
        patch("custom_components.autodarts.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done()
    assert result["data"]["token"] == refreshed


async def test_cloud_only_reauth_can_restart_linking(hass):
    entry = MockConfigEntry(
        domain="autodarts",
        version=2,
        unique_id="board-1",
        data={"board_id": "board-1", "token": TOKEN, "client_id": CLIENT_ID},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "autodarts",
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    future.set_exception(AutodartsAuthError("expired_token"))
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "auth_retry"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "reauth_confirm"

    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, [BOARD])
    assert result["reason"] == "reauth_successful"
    assert "host" not in entry.data
    assert entry.data["token"] == TOKEN
