"""Device grant and token rotation tests at the HTTP boundary."""

import asyncio
import time
from dataclasses import replace
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.autodarts.api import (
    API_BASE,
    DEVICE_CODE_URL,
    DEVICE_TOKEN_URL,
    REFRESH_URL,
    AutodartsAuthError,
    AutodartsCloudClient,
    AutodartsConnectionError,
    DeviceAuthorization,
    request_device_code,
    wait_for_device_token,
)

CLIENT_ID = "registered-test-client"
TOKEN = {
    "access_token": "test-access",
    "refresh_token": "test-refresh",
    "expires_in": 900,
}
DEVICE = {
    "device_code": "private-test-device-code",
    "user_code": "ABCD-EFGH",
    "verification_uri": "https://auth.autodarts.io/link",
    "verification_uri_complete": "https://auth.autodarts.io/link?user_code=ABCD-EFGH",
    "expires_in": 600,
    "interval": 5,
}


def grant():
    return DeviceAuthorization(
        DEVICE["device_code"],
        DEVICE["user_code"],
        DEVICE["verification_uri"],
        DEVICE["verification_uri_complete"],
        time.monotonic() + 600,
        5,
    )


async def test_device_request(hass, aioclient_mock):
    aioclient_mock.post(DEVICE_CODE_URL, json=DEVICE)
    device = await request_device_code(async_get_clientsession(hass), CLIENT_ID)
    assert device.user_code == "ABCD-EFGH"
    assert device.interval == 5
    assert DEVICE["device_code"] not in repr(device)
    assert aioclient_mock.mock_calls[0][2] == {"client_id": CLIENT_ID}


@pytest.mark.parametrize("code", ["invalid_client", "unauthorized_client"])
async def test_unregistered_client(hass, aioclient_mock, code):
    aioclient_mock.post(DEVICE_CODE_URL, status=400, json={"error": code})
    with pytest.raises(AutodartsAuthError, match=code):
        await request_device_code(async_get_clientsession(hass), CLIENT_ID)


async def test_pending_and_slow_down(hass):
    sleep = AsyncMock()
    with patch(
        "custom_components.autodarts.api._auth_request", new_callable=AsyncMock
    ) as request:
        request.side_effect = [
            AutodartsAuthError("authorization_pending"),
            AutodartsAuthError("slow_down"),
            TOKEN,
        ]
        token = await wait_for_device_token(
            async_get_clientsession(hass), CLIENT_ID, grant(), sleep
        )
    assert [c.args[0] for c in sleep.call_args_list] == [5, 5, 10]
    assert token["refresh_token"] == TOKEN["refresh_token"]
    assert request.call_args.args[1] == DEVICE_TOKEN_URL
    assert (
        request.call_args.args[2]["grant_type"]
        == "urn:ietf:params:oauth:grant-type:device_code"
    )
    assert request.call_args.args[2]["device_code"] == DEVICE["device_code"]


@pytest.mark.parametrize("code", ["access_denied", "expired_token", "invalid_client"])
async def test_terminal_device_errors(hass, code):
    with patch(
        "custom_components.autodarts.api._auth_request",
        side_effect=AutodartsAuthError(code),
    ) as request:
        with pytest.raises(AutodartsAuthError, match=code):
            await wait_for_device_token(
                async_get_clientsession(hass), CLIENT_ID, grant(), AsyncMock()
            )
    assert request.call_count == 1


async def test_expired_code_never_polled(hass):
    with patch("custom_components.autodarts.api._auth_request") as request:
        with pytest.raises(AutodartsAuthError, match="expired_token"):
            await wait_for_device_token(
                async_get_clientsession(hass),
                CLIENT_ID,
                replace(grant(), expires_at=time.monotonic() - 1),
            )
    request.assert_not_called()


async def test_outage_backs_off_and_recovers(hass):
    sleep = AsyncMock()
    with patch(
        "custom_components.autodarts.api._auth_request",
        side_effect=[AutodartsConnectionError(), TOKEN],
    ):
        await wait_for_device_token(
            async_get_clientsession(hass), CLIENT_ID, grant(), sleep
        )
    assert [c.args[0] for c in sleep.call_args_list] == [5, 10]


async def test_cancellation_stops_polling(hass):
    with patch("custom_components.autodarts.api._auth_request") as request:
        task = asyncio.create_task(
            wait_for_device_token(async_get_clientsession(hass), CLIENT_ID, grant())
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    request.assert_not_called()


async def test_refresh_persisted_even_when_following_request_fails(
    hass, aioclient_mock
):
    aioclient_mock.post(REFRESH_URL, json=TOKEN)
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/board-1", status=503)
    persisted = Mock()
    cloud = AutodartsCloudClient(
        async_get_clientsession(hass),
        {
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "expires_at": 0,
        },
        CLIENT_ID,
        persisted,
    )
    with pytest.raises(AutodartsConnectionError):
        await cloud.get_board("board-1")
    assert persisted.call_args.args[0]["refresh_token"] == "test-refresh"
    assert aioclient_mock.mock_calls[0][2] == {
        "client_id": CLIENT_ID,
        "refresh_token": "old-refresh",
    }
    assert aioclient_mock.mock_calls[1][3] == {"Authorization": "Bearer test-access"}


async def test_concurrent_refresh_only_consumes_token_once(hass, aioclient_mock):
    aioclient_mock.post(REFRESH_URL, json=TOKEN)
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/board-1", json={"id": "board-1"})
    cloud = AutodartsCloudClient(
        async_get_clientsession(hass),
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": 0,
        },
        CLIENT_ID,
    )
    await asyncio.gather(cloud.get_board("board-1"), cloud.get_board("board-1"))
    assert sum(str(call[1]) == REFRESH_URL for call in aioclient_mock.mock_calls) == 1


async def test_rejected_access_token_is_refreshed_once(hass):
    def response(status):
        result = Mock()
        result.status = status
        result.json = AsyncMock(return_value={"id": "board-1"})
        context = AsyncMock()
        context.__aenter__.return_value = result
        return context

    session = Mock(spec=aiohttp.ClientSession, closed=False)
    session.get.side_effect = [response(401), response(200)]
    cloud = AutodartsCloudClient(
        session,
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": time.time() + 900,
        },
        CLIENT_ID,
    )
    with patch(
        "custom_components.autodarts.api._auth_request", return_value=TOKEN
    ) as refresh:
        assert await cloud.get_board("board-1") == {"id": "board-1"}
    refresh.assert_awaited_once()
    assert session.get.call_count == 2


async def test_repeated_401_requires_reauth(hass, aioclient_mock):
    aioclient_mock.post(REFRESH_URL, json=TOKEN)
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/board-1", status=401)
    cloud = AutodartsCloudClient(
        async_get_clientsession(hass),
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": time.time() + 900,
        },
        CLIENT_ID,
    )
    with pytest.raises(AutodartsAuthError, match="invalid_token"):
        await cloud.get_board("board-1")
    assert aioclient_mock.call_count == 3


@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {**DEVICE, "interval": 0},
        {**DEVICE, "expires_in": -1},
        {**DEVICE, "interval": True},
        {**DEVICE, "expires_in": "600"},
    ],
)
async def test_malformed_device_response(hass, aioclient_mock, body):
    aioclient_mock.post(DEVICE_CODE_URL, json=body)
    with pytest.raises(AutodartsConnectionError):
        await request_device_code(async_get_clientsession(hass), CLIENT_ID)


@pytest.mark.parametrize(
    "answer",
    [
        {"exc": aiohttp.ClientConnectionError()},
        {"exc": TimeoutError()},
        {"text": "<html>maintenance</html>"},
    ],
)
async def test_unreachable_or_garbled_auth_service(hass, aioclient_mock, answer):
    aioclient_mock.post(DEVICE_CODE_URL, **answer)
    with pytest.raises(AutodartsConnectionError, match="Could not contact"):
        await request_device_code(async_get_clientsession(hass), CLIENT_ID)


async def test_code_expiring_while_pending_stops_polling(hass):
    with patch(
        "custom_components.autodarts.api._auth_request",
        side_effect=AutodartsAuthError("authorization_pending"),
    ) as request:
        with pytest.raises(AutodartsAuthError, match="expired_token"):
            await wait_for_device_token(
                async_get_clientsession(hass),
                CLIENT_ID,
                replace(grant(), expires_at=time.monotonic() + 0.05, interval=0.01),
            )
    assert request.call_count >= 1


async def test_parallel_rejections_refresh_the_token_once(hass):
    def response(headers):
        result = Mock()
        result.status = 401 if headers["Authorization"] == "Bearer old" else 200
        result.json = AsyncMock(return_value={"id": "board-1"})

        async def arrive():
            # Both requests are on the way before either learns of the rejection.
            await asyncio.sleep(0)
            return result

        context = AsyncMock()
        context.__aenter__.side_effect = arrive
        return context

    session = Mock(spec=aiohttp.ClientSession, closed=False)
    session.get.side_effect = lambda url, headers: response(headers)
    cloud = AutodartsCloudClient(
        session,
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": time.time() + 900,
        },
        CLIENT_ID,
    )
    with patch(
        "custom_components.autodarts.api._auth_request", return_value=TOKEN
    ) as refresh:
        assert await asyncio.gather(
            cloud.get_board("board-1"), cloud.get_board("board-1")
        ) == [{"id": "board-1"}, {"id": "board-1"}]
    refresh.assert_awaited_once()
    assert session.get.call_count == 4


async def test_expired_token_without_refresh_token_requires_reauth(
    hass, aioclient_mock
):
    cloud = AutodartsCloudClient(
        async_get_clientsession(hass),
        {"access_token": "old", "expires_at": 0},
        CLIENT_ID,
    )
    with pytest.raises(AutodartsAuthError, match="invalid_grant"):
        await cloud.get_board("board-1")
    assert aioclient_mock.call_count == 0


def fresh_client(hass) -> AutodartsCloudClient:
    return AutodartsCloudClient(
        async_get_clientsession(hass),
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": time.time() + 900,
        },
        CLIENT_ID,
    )


async def test_forbidden_board_is_not_retried(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/board-1", status=403)
    with pytest.raises(AutodartsAuthError, match="access_denied"):
        await fresh_client(hass).get_board("board-1")
    assert aioclient_mock.call_count == 1


async def test_boards_of_the_account(hass, aioclient_mock):
    boards = [{"id": "board-1", "name": "Living room"}, {"id": "board-2"}]
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/", json=boards)
    assert await fresh_client(hass).get_boards() == boards
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": "Bearer access"}


@pytest.mark.parametrize(
    "body", [{"id": "board-1"}, ["board-1"], [{"id": 1}], [{"name": "no id"}]]
)
async def test_malformed_board_list_is_rejected(hass, aioclient_mock, body):
    aioclient_mock.get(f"{API_BASE}/bs/v0/boards/", json=body)
    with pytest.raises(AutodartsConnectionError, match="Invalid boards response"):
        await fresh_client(hass).get_boards()


@pytest.mark.parametrize(
    "status,body,error",
    [
        (400, {"error": "invalid_grant"}, AutodartsAuthError),
        (503, {}, AutodartsConnectionError),
        (200, {"access_token": "incomplete"}, AutodartsConnectionError),
    ],
)
async def test_refresh_failure(hass, aioclient_mock, status, body, error):
    aioclient_mock.post(REFRESH_URL, status=status, json=body)
    cloud = AutodartsCloudClient(
        async_get_clientsession(hass),
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_at": 0,
        },
        CLIENT_ID,
    )
    with pytest.raises(error):
        await cloud.get_board("board-1")
    assert cloud.token["refresh_token"] == "old-refresh"


@pytest.mark.parametrize("method", ["get_board", "get_match", "get_match_state"])
async def test_cloud_objects_must_be_objects(method):
    result = Mock()
    result.status = 200
    result.json = AsyncMock(return_value=["not", "an", "object"])
    context = AsyncMock()
    context.__aenter__.return_value = result
    session = Mock(spec=aiohttp.ClientSession, closed=False)
    session.get.return_value = context
    fresh = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_at": time.time() + 900,
    }
    cloud = AutodartsCloudClient(session, fresh, CLIENT_ID)
    with pytest.raises(AutodartsConnectionError, match="Invalid Autodarts response"):
        await getattr(cloud, method)("id-1")


@pytest.mark.parametrize(
    "method,identifier,path",
    [
        ("get_board", "../../users/me", "/bs/v0/boards/..%2F..%2Fusers%2Fme"),
        ("get_match", "m 1?x", "/gs/v0/matches/m%201%3Fx"),
        ("get_match_state", "m#1", "/gs/v0/matches/m%231/state"),
    ],
)
async def test_identifiers_stay_one_path_segment(
    hass, aioclient_mock, method, identifier, path
):
    aioclient_mock.get(f"{API_BASE}{path}", json={"id": "x"})
    assert await getattr(fresh_client(hass), method)(identifier) == {"id": "x"}
    assert aioclient_mock.mock_calls[0][1].raw_path == path


@pytest.mark.parametrize("identifier", ["", None, 7])
async def test_missing_identifiers_send_nothing(hass, aioclient_mock, identifier):
    with pytest.raises(AutodartsConnectionError, match="Invalid identifier"):
        await fresh_client(hass).get_match(identifier)
    assert not aioclient_mock.mock_calls


async def test_requests_after_home_assistant_closed_its_session_are_lost_connections():
    """Home Assistant closes its shared session last when it stops (#107)."""
    session = aiohttp.ClientSession()
    await session.close()
    with pytest.raises(AutodartsConnectionError, match="closed its HTTP session"):
        await request_device_code(session, CLIENT_ID)
    fresh = {"access_token": "a", "refresh_token": "r", "expires_at": time.time() + 900}
    with pytest.raises(AutodartsConnectionError, match="closed its HTTP session"):
        await AutodartsCloudClient(session, fresh, CLIENT_ID).get_boards()
