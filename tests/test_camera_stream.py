"""Live camera streams: relayed from Board Manager 2, snapshots everywhere else."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.autodarts.camera import AutodartsCamera
from custom_components.autodarts.errors import AutodartsConnectionError

from .local_helpers import BASE
from .test_board_manager_2 import setup_v2
from .test_local_setup import entity_id, setup_local

MJPEG = "multipart/x-mixed-replace; boundary=frame"
FRAME = b"--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg\r\n"
SNAPSHOTS = "homeassistant.components.camera.Camera.handle_async_mjpeg_stream"


async def test_board_manager_2_relays_the_live_stream(
    hass, aioclient_mock, hass_client
):
    entry = await setup_v2(hass, aioclient_mock)
    camera = entity_id(hass, "camera", "camera_0")
    er.async_get(hass).async_update_entity(camera, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    aioclient_mock.get(
        f"{BASE}/api/streams/cams/0", content=FRAME, headers={"Content-Type": MJPEG}
    )
    client = await hass_client()
    response = await client.get(f"/api/camera_proxy_stream/{camera}")
    assert response.status == 200
    assert response.headers["Content-Type"] == MJPEG
    assert await response.read() == FRAME
    streams = [call for call in aioclient_mock.mock_calls if "streams" in str(call[1])]
    assert [(call[0], call[1].path) for call in streams] == [
        ("GET", "/api/streams/cams/0")
    ]


@pytest.mark.parametrize(
    ("status", "headers"),
    [(404, {}), (200, {"Content-Type": "text/html"})],
)
async def test_a_missing_stream_falls_back_to_snapshots(
    hass, aioclient_mock, status, headers
):
    entry = await setup_v2(hass, aioclient_mock)
    aioclient_mock.get(
        f"{BASE}/api/streams/cams/1", status=status, text="none", headers=headers
    )
    client = entry.runtime_data.local.client
    with pytest.raises(AutodartsConnectionError, match="No camera stream"):
        await client.open_camera_stream(1)
    camera = AutodartsCamera(entry.runtime_data.local, 1)
    with patch(SNAPSHOTS, return_value=None) as snapshots:
        assert await camera.handle_async_mjpeg_stream(object()) is None
    snapshots.assert_called_once()


@pytest.mark.parametrize(
    "error", [aiohttp.ClientConnectionError("refused"), TimeoutError()]
)
async def test_an_unreachable_stream_falls_back_to_snapshots(
    hass, aioclient_mock, error
):
    entry = await setup_v2(hass, aioclient_mock)
    aioclient_mock.get(f"{BASE}/api/streams/cams/2", exc=error)
    client = entry.runtime_data.local.client
    with pytest.raises(AutodartsConnectionError, match="Unable to open"):
        await client.open_camera_stream(2)
    camera = AutodartsCamera(entry.runtime_data.local, 2)
    with patch(SNAPSHOTS, return_value=None) as snapshots:
        assert await camera.handle_async_mjpeg_stream(object()) is None
    snapshots.assert_called_once()


async def test_board_manager_1_sends_snapshots_without_asking(hass, aioclient_mock):
    entry = await setup_local(hass, aioclient_mock)
    camera = AutodartsCamera(entry.runtime_data.local, 0)
    aioclient_mock.clear_requests()
    with patch(SNAPSHOTS, return_value=None) as snapshots:
        await camera.handle_async_mjpeg_stream(object())
    snapshots.assert_called_once()
    assert not aioclient_mock.mock_calls


async def test_live_viewers_per_camera_are_capped(hass, aioclient_mock):
    """A third viewer gets snapshots, which spares the board PC."""
    entry = await setup_v2(hass, aioclient_mock)
    coordinator = entry.runtime_data.local
    camera = AutodartsCamera(coordinator, 0)
    release = asyncio.Event()

    async def relay(hass, request, stream, content_type):
        await release.wait()
        return "live"

    stream = Mock(headers={"Content-Type": MJPEG})
    with (
        patch.object(
            coordinator.client, "open_camera_stream", AsyncMock(return_value=stream)
        ) as opened,
        patch("custom_components.autodarts.camera.async_aiohttp_proxy_stream", relay),
        patch(SNAPSHOTS, return_value="snapshots") as snapshots,
    ):
        viewers = [
            hass.async_create_task(camera.handle_async_mjpeg_stream(object()))
            for _ in range(2)
        ]
        for _ in range(5):
            await asyncio.sleep(0)
        assert await camera.handle_async_mjpeg_stream(object()) == "snapshots"
        release.set()
        assert await asyncio.gather(*viewers) == ["live", "live"]
        # Viewers that left free their places.
        assert await camera.handle_async_mjpeg_stream(object()) == "live"
    assert opened.call_count == 3
    assert snapshots.call_count == 1
    assert stream.close.call_count == 3
