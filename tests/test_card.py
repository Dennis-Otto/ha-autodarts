"""The dashboard card: dart details for the board view and automatic loading."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.setup import async_setup_component

from custom_components.autodarts.card import CARD_PATH, CARD_URL, async_register_card
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


async def test_invalid_darts_are_not_exposed(hass, aioclient_mock):
    await setup_local(
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


async def test_visit_without_darts_and_positions_stay_out_of_history(
    hass, aioclient_mock
):
    await setup_local(hass, aioclient_mock, state=deepcopy(STATE))
    assert throws(hass) == []
    # Live positions change with every dart and are not useful in the recorder.
    assert "throws" in AutodartsVisitSensor._unrecorded_attributes


async def test_card_is_served_and_loaded_on_dashboards(hass):
    hass.config.components.add("frontend")
    hass.http = Mock(async_register_static_paths=AsyncMock())
    with patch("custom_components.autodarts.card.add_extra_js_url") as add_js:
        await async_register_card(hass)
    (config,) = hass.http.async_register_static_paths.call_args.args[0]
    assert (config.url_path, config.path, config.cache_headers) == (
        CARD_URL,
        str(CARD_PATH),
        True,
    )
    assert CARD_PATH.is_file()
    version = json.loads(MANIFEST.read_text())["version"]
    digest = hashlib.sha256(CARD_PATH.read_bytes()).hexdigest()[:8]
    add_js.assert_called_once_with(hass, f"{CARD_URL}?v={version}-{digest}")


async def test_card_is_skipped_without_web_frontend(hass):
    hass.http = Mock(async_register_static_paths=AsyncMock())
    with patch("custom_components.autodarts.card.add_extra_js_url") as add_js:
        assert await async_setup_component(hass, "autodarts", {})
    hass.http.async_register_static_paths.assert_not_called()
    add_js.assert_not_called()
