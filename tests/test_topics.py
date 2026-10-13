"""The topics of a board's readings, and what the coordinator takes from Home
Assistant's DataUpdateCoordinator."""

import ast
import logging
from pathlib import Path

import pytest
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.autodarts.topics import BoardTopics, Topic

from .local_helpers import setup_local, written

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "autodarts"
# The methods that Home Assistant documents for a coordinator to override.
HOOKS = {"_async_setup", "_async_update_data"}


def test_a_topic_calls_only_its_own_listeners_until_they_leave():
    topics = BoardTopics()
    calls = []
    leave = topics.async_add_listener(Topic.MOTION, lambda: calls.append("motion"))
    topics.async_add_listener(Topic.TELEMETRY, lambda: calls.append("telemetry"))
    topics.async_publish(Topic.MOTION)
    assert calls == ["motion"]
    leave()
    # Leaving twice changes nothing more.
    leave()
    topics.async_publish(Topic.MOTION)
    # A topic nobody listens to.
    topics.async_publish(Topic.CAMERA_STATE)
    assert calls == ["motion"]
    topics.async_publish(Topic.TELEMETRY)
    assert calls == ["motion", "telemetry"]


async def test_an_unloaded_board_leaves_no_listener_of_its_readings(
    hass, aioclient_mock
):
    entry = await setup_local(hass, aioclient_mock)
    coordinator = entry.runtime_data.local
    assert await hass.config_entries.async_unload(entry.entry_id)
    with written(hass) as entities:
        for topic in Topic:
            coordinator.topics.async_publish(topic)
        await hass.async_block_till_done()
    assert not entities


def members(node: ast.AST) -> str | None:
    """The member that a node of the code reads, writes or defines."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    return None


# Reads the code as text, which holds every mutant in mutmut's copy.
@pytest.mark.mutation_unsafe
async def test_the_coordinators_use_only_what_home_assistant_offers_them(hass):
    """A private member of DataUpdateCoordinator may change with any release of
    Home Assistant; reading or overriding one could make every board
    unavailable after an update."""
    probe = DataUpdateCoordinator(
        hass, logging.getLogger(__name__), config_entry=None, name="probe"
    )
    private = {
        name
        for name in (*vars(probe), *dir(DataUpdateCoordinator))
        if name.startswith("_") and not name.startswith("__")
    } - HOOKS
    assert {"_listeners", "_shutdown_requested", "_async_refresh"} <= private
    used = sorted(
        f"{path.name}:{node.lineno} {members(node)}"
        for path in INTEGRATION.glob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if members(node) in private
    )
    assert not used
