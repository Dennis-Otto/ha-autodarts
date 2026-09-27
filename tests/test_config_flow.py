"""Exercise the real Home Assistant config-flow manager."""

import asyncio
import time
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.autodarts.api import (
    AutodartsAuthError,
    AutodartsConnectionError,
    DeviceAuthorization,
)

# Valid for a day, so that neither a long test run nor a frozen clock ends them.
DEVICE = DeviceAuthorization(
    "private-device",
    "ABCD-EFGH",
    "https://auth.autodarts.io/link",
    "https://auth.autodarts.io/link?user_code=ABCD-EFGH",
    time.monotonic() + 86400,
    5,
)
TOKEN = {
    "access_token": "test-access",
    "refresh_token": "test-refresh",
    "expires_at": time.time() + 86400,
}
BOARD = {"id": "board-1", "name": "My Board"}
CLIENT_ID = "registered-test-client"


async def start_link(hass, result, future):
    with (
        patch(
            "custom_components.autodarts.config_flow.request_device_code",
            return_value=DEVICE,
        ),
        patch(
            "custom_components.autodarts.config_flow.wait_for_device_token",
            side_effect=lambda *args: future,
        ) as wait,
    ):
        # AsyncMock side_effect must await the future, rather than returning it.
        async def wait_for_approval(*args):
            return await future

        wait.side_effect = wait_for_approval
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"client_id": CLIENT_ID}
        )
        await asyncio.sleep(0)
    assert result["type"] == FlowResultType.SHOW_PROGRESS
    assert result["description_placeholders"]["user_code"] == "ABCD-EFGH"
    assert "private-device" not in str(result)
    return result


async def complete_link(hass, result, future, boards):
    future.set_result(TOKEN)
    await hass.async_block_till_done()
    with (
        patch(
            "custom_components.autodarts.config_flow.AutodartsCloudClient.get_boards",
            return_value=boards,
        ),
        patch("custom_components.autodarts.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
        await hass.async_block_till_done()
    return result


@pytest.mark.usefixtures("cloud_link")
async def test_device_login_creates_board_entry(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "board_id": "board-1",
        "client_id": CLIENT_ID,
        "token": TOKEN,
    }
    assert result["result"].unique_id == "board-1"


@pytest.mark.usefixtures("cloud_link")
async def test_multiple_boards(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    result = await complete_link(
        hass, result, future, [BOARD, {"id": "board-2", "name": "Second"}]
    )
    assert result["step_id"] == "board"
    with patch("custom_components.autodarts.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"board_id": "board-2"}
        )
        await hass.async_block_till_done()
    assert result["data"]["board_id"] == "board-2"


@pytest.mark.parametrize(
    "boards,reason", [([], "no_boards"), ([BOARD], "already_configured")]
)
@pytest.mark.usefixtures("cloud_link")
async def test_no_boards_and_legacy_duplicates(hass, boards, reason):
    if reason == "already_configured":
        entry = MockConfigEntry(
            domain="autodarts", version=2, data={"board_id": "board-1", "token": TOKEN}
        )
        entry.add_to_hass(hass)
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, boards)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == reason


@pytest.mark.parametrize(
    "boards,reason",
    [([BOARD], "reauth_successful"), ([{"id": "other"}], "wrong_account")],
)
async def test_legacy_reauth_preserves_entry_and_local_settings(hass, boards, reason):
    data = {
        "board_id": "board-1",
        "token": {"access_token": "legacy"},
        "host": "192.0.2.10",
        "port": 3180,
    }
    entry = MockConfigEntry(
        domain="autodarts", version=2, title="Original board", data=data
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "autodarts",
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, boards)
    assert result["reason"] == reason
    assert len(hass.config_entries.async_entries("autodarts")) == 1
    assert entry.title == "Original board"
    assert entry.data["host"] == "192.0.2.10"
    assert entry.data["port"] == 3180
    if reason == "reauth_successful":
        assert entry.data["token"] == TOKEN
        assert entry.data["client_id"] == CLIENT_ID
    else:
        assert entry.data == data


@pytest.mark.parametrize(
    "error,translation",
    [
        (AutodartsAuthError("unauthorized_client"), "invalid_client"),
        (AutodartsConnectionError(), "cannot_connect"),
    ],
)
@pytest.mark.usefixtures("cloud_link")
async def test_code_request_errors(hass, error, translation):
    result = await init_cloud_flow(hass)
    with patch(
        "custom_components.autodarts.config_flow.request_device_code", side_effect=error
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"client_id": CLIENT_ID}
        )
    assert result["step_id"] == "cloud"
    assert result["errors"] == {"base": translation}
    # Once the code request works, the same flow links the account.
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("cloud_link")
@pytest.mark.parametrize("code", ["expired_token", "access_denied"])
async def test_device_error_can_restart(hass, code):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    future.set_exception(AutodartsAuthError(code))
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "auth_retry"
    assert result["errors"] == {"base": code}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "cloud"
    future = asyncio.get_running_loop().create_future()
    result = await start_link(hass, result, future)
    result = await complete_link(hass, result, future, [BOARD])
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("cloud_link")
async def test_abort_cancels_device_polling(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    hass.config_entries.flow.async_abort(result["flow_id"])
    await hass.async_block_till_done()
    assert future.cancelled()


@pytest.mark.usefixtures("cloud_link")
async def test_board_outage_retries_without_new_device_code(hass):
    future = asyncio.get_running_loop().create_future()
    result = await init_cloud_flow(hass)
    result = await start_link(hass, result, future)
    future.set_result(TOKEN)
    await hass.async_block_till_done()
    with patch(
        "custom_components.autodarts.config_flow.AutodartsCloudClient.get_boards",
        side_effect=AutodartsConnectionError(),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["step_id"] == "boards"
    assert result["errors"] == {"base": "cannot_connect"}
    with (
        patch(
            "custom_components.autodarts.config_flow.AutodartsCloudClient.get_boards",
            return_value=[BOARD],
        ),
        patch("custom_components.autodarts.config_flow.request_device_code") as request,
        patch("custom_components.autodarts.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    request.assert_not_called()
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("cloud_link")
async def test_setup_requests_registered_client_id(hass):
    """Do not send users to the retired Keycloak client/redirect flow."""
    result = await init_cloud_flow(hass)
    assert result["step_id"] == "cloud"
    assert "client_id" in result["data_schema"].schema


async def init_cloud_flow(hass):
    result = await hass.config_entries.flow.async_init(
        "autodarts", context={"source": SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "cloud"}
    )
