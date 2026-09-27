"""Home Assistant fixtures for Autodarts."""

import asyncio
import logging
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from hypothesis import settings
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components

# The HA test plugin preloads its own custom_components package.
custom_components.__path__.insert(
    0, str(Path(__file__).parents[1] / "custom_components")
)

# Property tests never fail on a slow machine; in CI they replay the same
# examples on every run, so a failure shows up again on a retry.
settings.register_profile("local", deadline=None)
settings.register_profile("ci", deadline=None, derandomize=True, print_blob=True)
settings.load_profile("ci" if os.environ.get("CI") else "local")


@pytest.fixture(autouse=True)
def custom_integration(enable_custom_integrations):
    """Enable discovery of the real integration from this repository."""


@pytest.fixture(autouse=True)
def local_stream():
    """No external sockets in tests; stream-specific tests override this source."""

    async def idle_stream(self):
        await asyncio.Future()
        yield  # pragma: no cover

    with patch(
        "custom_components.autodarts.local_api.AutodartsLocalClient.events", idle_stream
    ):
        yield


@pytest.fixture
def cloud_link():
    """Offer the cloud link, as once Autodarts has issued a client ID."""
    with patch("custom_components.autodarts.const.CLOUD_LINK_AVAILABLE", True):
        yield


# Loggers of the integration, and those Home Assistant reports its entities with.
WATCHED_LOGGERS = (
    "custom_components.autodarts",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
)
# How the coordinators report a board or cloud that is away, once per outage.
UNAVAILABLE = re.compile(
    r"(Error fetching|Authentication failed while fetching) autodarts(_local)? data: "
)


@pytest.fixture(autouse=True)
def no_unexpected_errors(request, caplog):
    """An error in the log fails the test, unless it is marked expected_errors."""
    yield
    if request.node.get_closest_marker("expected_errors"):
        return
    errors = [
        f"{record.name}: {record.getMessage()}"
        for when in ("setup", "call")
        for record in caplog.get_records(when)
        if record.levelno >= logging.ERROR
        and record.name.startswith(WATCHED_LOGGERS)
        and not UNAVAILABLE.match(record.getMessage())
    ]
    assert not errors, errors


@pytest.fixture
async def client(hass, aioclient_mock):
    """A client for the board at the address of local_entry_data."""
    from custom_components.autodarts.local_api import AutodartsLocalClient

    return AutodartsLocalClient("192.0.2.10", 3180, async_get_clientsession(hass))


@pytest.fixture
async def two_boards(hass, aioclient_mock):
    """Two boards in one home, each with its own ID, address and cameras."""
    from .local_helpers import (
        SECOND_BASE,
        board,
        local_entry_data,
        mock_board,
        second_board_config,
    )

    mock_board(aioclient_mock, state=board())
    mock_board(
        aioclient_mock, state=board(), config=second_board_config(), base=SECOND_BASE
    )
    entries = []
    for board_id, host in (("board-1", "192.0.2.10"), ("board-2", "192.0.2.20")):
        entry = MockConfigEntry(
            domain="autodarts",
            version=2,
            unique_id=board_id,
            title=f"Autodarts ({host})",
            data=local_entry_data(board_id, host),
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)
    return entries
