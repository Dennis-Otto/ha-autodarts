"""The dashboard card: dart details for the board view and automatic loading."""

import gzip
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.setup import async_setup_component
from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.card import (
    CARD_PATH,
    CARD_URL,
    STRATEGY_PATH,
    STRATEGY_URL,
    _accepts_gzip,
    async_register_card,
)
from custom_components.autodarts.sensor import AutodartsVisitSensor

from .local_helpers import STATE, entity_id, setup_local

MANIFEST = Path(__file__).parents[1] / "custom_components/autodarts/manifest.json"


def dart(name, number, multiplier, bed, x=None, y=None):
    result = {
        "segment": {
            "name": name,
            "number": number,
            "multiplier": multiplier,
            "bed": bed,
        }
    }
    if x is not None:
        result["coords"] = {"x": x, "y": y}
    return result


def visit(*darts, **changes):
    return {
        **STATE,
        "running": True,
        "status": "Throw",
        "numThrows": len(darts),
        "throws": list(darts),
        **changes,
    }


def throws(hass):
    return hass.states.get(entity_id(hass, "sensor", "local_visit_score")).attributes[
        "throws"
    ]


async def test_visit_sensor_reports_beds_and_positions(hass, aioclient_mock):
    await setup_local(
        hass,
        aioclient_mock,
        state=visit(
            dart("T20", 20, 3, "Triple", 0.012345, 0.61239),
            dart("S5", 5, 1, "SingleOuter", -0.28, 0.7),
            dart("Bull", 25, 2, "Double"),
        ),
    )
    assert (
        hass.states.get(entity_id(hass, "sensor", "local_visit_score")).state == "115"
    )
    assert throws(hass) == [
        {
            "segment": "T20",
            "number": 20,
            "multiplier": 3,
            "score": 60,
            "bed": "Triple",
            "x": 0.012,
            "y": 0.612,
        },
        {
            "segment": "S5",
            "number": 5,
            "multiplier": 1,
            "score": 5,
            "bed": "SingleOuter",
            "x": -0.28,
            "y": 0.7,
        },
        {
            "segment": "Bull",
            "number": 25,
            "multiplier": 2,
            "score": 50,
            "bed": "Double",
        },
    ]


async def test_camera_jitter_keeps_positions_until_a_dart_changes(hass, aioclient_mock):
    entry = await setup_local(
        hass, aioclient_mock, state=visit(dart("T20", 20, 3, "Triple", 0.01, 0.6))
    )
    coordinator = entry.runtime_data.local
    first = hass.states.get(entity_id(hass, "sensor", "local_visit_score"))
    coordinator.async_receive(
        "state", visit(dart("T20", 20, 3, "Triple", 0.013, 0.602))
    )
    await hass.async_block_till_done()
    steady = hass.states.get(entity_id(hass, "sensor", "local_visit_score"))
    assert steady.attributes["throws"][0]["x"] == 0.01
    assert steady.last_updated == first.last_updated

    coordinator.async_receive(
        "state",
        visit(
            dart("S20", 20, 1, "SingleOuter", 0.02, 0.75),
            dart("D1", 1, 2, "Double", 0.3, 0.93),
        ),
    )
    await hass.async_block_till_done()
    assert [(item["segment"], item["x"]) for item in throws(hass)] == [
        ("S20", 0.02),
        ("D1", 0.3),
    ]


async def test_a_dart_that_moved_in_its_bed_is_drawn_at_its_new_spot(
    hass, aioclient_mock
):
    """Only camera jitter keeps a position: a reading farther away than about
    1.7 mm, or a dart that takes another dart's place, is drawn where it is."""
    first = dart("T20", 20, 3, "Triple", 0.01, 0.6)
    second = dart("T20", 20, 3, "Triple", 0.05, 0.62)
    entry = await setup_local(hass, aioclient_mock, state=visit(first, second))
    coordinator = entry.runtime_data.local
    # The board takes the first dart back; the second is now the first.
    coordinator.async_receive("state", visit(second))
    await hass.async_block_till_done()
    assert [(item["x"], item["y"]) for item in throws(hass)] == [(0.05, 0.62)]
    # The camera sees the dart 2 mm away: it moved.
    moved = dart("T20", 20, 3, "Triple", 0.05, 0.632)
    coordinator.async_receive("state", visit(moved))
    await hass.async_block_till_done()
    assert [(item["x"], item["y"]) for item in throws(hass)] == [(0.05, 0.632)]
    # A reading without a position shows none instead of the last one.
    coordinator.async_receive("state", visit(dart("T20", 20, 3, "Triple")))
    await hass.async_block_till_done()
    assert "x" not in throws(hass)[0]
    coordinator.async_receive("state", visit(second))
    await hass.async_block_till_done()
    assert [(item["x"], item["y"]) for item in throws(hass)] == [(0.05, 0.62)]


async def test_invalid_darts_are_not_exposed(hass, aioclient_mock):
    entry = await setup_local(
        hass,
        aioclient_mock,
        state=visit(
            dart("T20", 20, 3, "Unknown", float("nan"), 0.5),
            {"segment": {"name": "S5", "number": "5", "multiplier": 1}},
            {"segment": None},
            "garbage",
            {"segment": {"number": 5, "multiplier": 1}, "coords": {"x": True, "y": 1}},
        ),
    )
    assert throws(hass) == [
        {"segment": "T20", "number": 20, "multiplier": 3, "score": 60, "bed": None},
        {"segment": None, "number": 5, "multiplier": 1, "score": 5, "bed": None},
    ]
    # A bed that is no text, as a proxy might send it, is no bed either, and
    # the sensors keep updating without an error in the log.
    entry.runtime_data.local.async_receive(
        "state",
        visit(dart("S5", 5, 1, ["Single"]), dart("D1", 1, 2, {"bed": "Double"})),
    )
    await hass.async_block_till_done()
    assert [(item["segment"], item["bed"]) for item in throws(hass)] == [
        ("S5", None),
        ("D1", None),
    ]
    assert hass.states.get(entity_id(hass, "sensor", "last_throw")).state == "D1"
    assert hass.states.get(entity_id(hass, "sensor", "last_throw_score")).state == "2"


async def test_visit_without_darts_and_positions_stay_out_of_history(
    hass, aioclient_mock
):
    await setup_local(hass, aioclient_mock, state=deepcopy(STATE))
    assert throws(hass) == []
    # Live positions change with every dart and are not useful in the recorder.
    assert "throws" in AutodartsVisitSensor._unrecorded_attributes


def tag():
    """Version and digest of both modules, as in their addresses."""
    version = json.loads(MANIFEST.read_text())["version"]
    content = CARD_PATH.read_bytes() + STRATEGY_PATH.read_bytes()
    return f"{version}-{hashlib.sha256(content).hexdigest()[:8]}"


async def serve_card(hass, hass_client_no_auth):
    """Register the card as Home Assistant does and return a client without a login."""
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")
    with patch("custom_components.autodarts.card.add_extra_js_url") as add_js:
        await async_register_card(hass)
    return await hass_client_no_auth(), add_js


def assert_cached(response):
    # A month, as Home Assistant's own frontend files; the address changes with every
    # version and content.
    assert response.headers["Cache-Control"] == "public, max-age=2678400"
    assert response.headers["ETag"] == f'W/"{tag()}"'
    assert response.headers["Vary"] == "Accept-Encoding"


async def test_card_is_served_and_loaded_on_dashboards(hass, hass_client_no_auth):
    client, add_js = await serve_card(hass, hass_client_no_auth)
    # The strategy comes first and imports the card by the same query.
    assert [call.args for call in add_js.call_args_list] == [
        (hass, f"{STRATEGY_URL}?v={tag()}"),
        (hass, f"{CARD_URL}?v={tag()}"),
    ]
    response = await client.get(f"{STRATEGY_URL}?v={tag()}")
    assert response.status == 200
    # Home Assistant's own header for static files, which the card module copies.
    static_cache_control = response.headers["Cache-Control"]
    assert static_cache_control == "public, max-age=2678400"
    assert await response.read() == STRATEGY_PATH.read_bytes()

    # Every browser accepts gzip, as the test client does: a quarter of the module.
    response = await client.get(f"{CARD_URL}?v={tag()}", auto_decompress=False)
    assert response.status == 200
    assert response.headers["Content-Type"] == "text/javascript; charset=utf-8"
    assert response.headers["Content-Encoding"] == "gzip"
    assert_cached(response)
    assert response.headers["Cache-Control"] == static_cache_control
    sent = await response.read()
    assert gzip.decompress(sent) == CARD_PATH.read_bytes()
    assert len(sent) < CARD_PATH.stat().st_size * 0.3


@pytest.mark.parametrize(
    "headers",
    [
        {"Accept-Encoding": "identity"},
        {"Accept-Encoding": "br;q=1.0, gzip;q=0"},
        {},
    ],
    ids=["identity", "gzip refused", "no Accept-Encoding"],
)
async def test_card_is_plain_for_clients_without_gzip(
    hass, hass_client_no_auth, headers
):
    client, _ = await serve_card(hass, hass_client_no_auth)
    response = await client.get(
        CARD_URL,
        headers=headers,
        skip_auto_headers=[] if headers else ["Accept-Encoding"],
        auto_decompress=False,
    )
    assert response.status == 200
    assert response.headers["Content-Type"] == "text/javascript; charset=utf-8"
    assert "Content-Encoding" not in response.headers
    assert_cached(response)
    assert await response.read() == CARD_PATH.read_bytes()


async def test_a_browser_keeps_its_copy_of_the_card(hass, hass_client_no_auth):
    client, _ = await serve_card(hass, hass_client_no_auth)
    # A browser asks again after a month, Safari also on every reload.
    for known in (f'W/"{tag()}"', f'"{tag()}"', f'"0.1.0-00000000", W/"{tag()}"', "*"):
        response = await client.get(CARD_URL, headers={"If-None-Match": known})
        assert response.status == 304
        assert_cached(response)
        assert await response.read() == b""
    # A copy of another version gets the module served now.
    response = await client.get(CARD_URL, headers={"If-None-Match": 'W/"0.1.0-0"'})
    assert response.status == 200
    assert await response.read() == CARD_PATH.read_bytes()


@pytest.mark.parametrize(
    ("accept_encoding", "gzip_accepted"),
    [
        ("gzip, deflate, br, zstd", True),
        ("GZIP", True),
        ("br;q=1.0, gzip;q=0.8, *;q=0.1", True),
        ("gzip ; Q = 0.001", True),
        ("x-gzip", True),
        ("*", True),
        ("deflate, *;q=0.5", True),
        ("", False),
        ("identity", False),
        ("br, zstd", False),
        ("gzip;q=0", False),
        ("gzip;q=0.000, *", False),
        ("*;q=0", False),
        ("gzip;q=high", False),
        ("gzip;q=2", False),
        ("gzipped", False),
    ],
)
def test_accept_encoding_is_read_with_its_weights(accept_encoding, gzip_accepted):
    assert _accepts_gzip(accept_encoding) is gzip_accepted


@given(st.text())
def test_the_first_weight_of_gzip_counts(rest):
    assert _accepts_gzip(f"gzip, {rest}")
    assert not _accepts_gzip(f"gzip;q=0, {rest}")


async def test_card_is_skipped_without_web_frontend(hass):
    hass.http = Mock(async_register_static_paths=AsyncMock())
    with patch("custom_components.autodarts.card.add_extra_js_url") as add_js:
        assert await async_setup_component(hass, "autodarts", {})
    hass.http.async_register_static_paths.assert_not_called()
    hass.http.register_view.assert_not_called()
    add_js.assert_not_called()
