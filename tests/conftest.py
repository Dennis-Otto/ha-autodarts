"""Home Assistant fixtures for Autodarts."""

import asyncio
import functools
import logging
import os
import re
import shutil
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.setup import async_setup_component
from hypothesis import settings
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension

import custom_components

# The HA test plugin preloads its own custom_components package.
custom_components.__path__.insert(
    0, str(Path(__file__).parents[1] / "custom_components")
)

# Property tests never fail on a slow machine; in CI they replay the same
# examples on every run, so a failure shows up again on a retry.
settings.register_profile("local", deadline=None)
settings.register_profile("ci", deadline=None, derandomize=True, print_blob=True)


def hypothesis_profile(environ: Mapping[str, str]) -> str:
    """The profile of the property tests: the same examples in every run in CI
    and under mutmut, which sets MUTANT_UNDER_TEST before it imports the tests,
    so that a mutant is killed or survives the same way on every machine."""
    return "ci" if environ.get("CI") or "MUTANT_UNDER_TEST" in environ else "local"


settings.load_profile(hypothesis_profile(os.environ))

# The modules of the integration, by the names they are imported with.
INTEGRATION = Path(__file__).parents[1] / "custom_components" / "autodarts"
MODULES = tuple(
    "custom_components.autodarts" + ("" if path.stem == "__init__" else f".{path.stem}")
    for path in sorted(INTEGRATION.glob("*.py"))
)


# How much longer a test may take under mutmut than its time limit allows.
MUTMUT_SLOWDOWN = 10


def pytest_collection_modifyitems(config, items):
    """Under mutmut the tests marked mutation_unsafe are skipped, and every test
    gets ten times its time limit.

    mutmut runs the tests in its copy of the repository, `mutants/`, which has no Git
    and holds every mutant in the code: a test that reads the code as text or asks
    Git fails there whatever the mutant. Every call of a function that mutmut
    changes passes its trampoline, which records the caller in the first run, so
    the slowest tests take several times as long; mutmut stops a mutant that hangs
    by a time limit of its own. mutmut sets MUTANT_UNDER_TEST in each of its runs,
    to an empty value in the run without a mutant.
    """
    if "MUTANT_UNDER_TEST" not in os.environ:
        return
    skip = pytest.mark.skip(reason="fails in mutmut's copy of the repository")
    for item in items:
        if item.get_closest_marker("mutation_unsafe"):
            item.add_marker(skip)
        limit = item.get_closest_marker("timeout")
        seconds = float(limit.args[0] if limit else config.getini("timeout") or 0)
        item.add_marker(pytest.mark.timeout(seconds * MUTMUT_SLOWDOWN), append=False)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    """A test that changes its parameters fails.

    Run again in the same process, it would get the changed ones: mutmut runs every
    test several times in its first process and forks the process of each mutant
    from it, and an IDE runs a failed test again.
    """
    callspec = getattr(item, "callspec", None)
    before = repr(callspec.params) if callspec else ""
    result = yield
    if callspec and repr(callspec.params) != before:
        pytest.fail(
            f"The test changed its parameters from {before} to {callspec.params!r}; "
            "change a copy of them instead.",
            pytrace=False,
        )
    return result


@functools.cache
def module_caches(module: ModuleType) -> tuple[Callable[..., Any], ...]:
    """The functions with a functools cache that a module defines, such as those
    of the checkouts."""
    return tuple(
        value
        for value in vars(module).values()
        if not isinstance(value, type)
        and callable(getattr(value, "cache_clear", None))
        and getattr(value, "__module__", None) == module.__name__
    )


def clear_integration_caches() -> None:
    """Empties the functools caches of every module of the integration loaded so far."""
    for name in MODULES:
        if (module := sys.modules.get(name)) is not None:
            for cached in module_caches(module):
                cached.cache_clear()


@pytest.fixture(autouse=True)
def fresh_caches():
    """Every test starts with the caches of the integration empty, as if it ran alone.

    mutmut runs the tests of a mutant in a process that it forks from the one that
    ran all the tests first: a result cached there, from the code without the mutant,
    would hide the mutant. And while that first run records which tests call a
    function, a test that finds its result in the cache would not count.
    """
    clear_integration_caches()


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Snapshots live in tests/__snapshots__, whichever pytest plugin loads last.

    syrupy and the HA test plugin both define this fixture with different folders;
    the plugins' load order follows the order of the installed packages on disk.
    """
    return snapshot.use_extension(AmberSnapshotExtension)


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


# Loggers of the integration, those Home Assistant reports its entities with,
# and those of the WebSocket commands and webhooks it offers, which answer a
# crashing handler with an error of their own.
WATCHED_LOGGERS = (
    "custom_components.autodarts",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components.websocket_api",
    "homeassistant.components.webhook",
)
# How the coordinators report a board or cloud that is away, once per outage.
UNAVAILABLE = re.compile(
    r"(Error fetching|Authentication failed while fetching) autodarts(_local)? data: "
)


# The log of a test whose errors pytest_runtest_teardown checks.
CHECKED_LOG = pytest.StashKey[pytest.LogCaptureFixture]()


@pytest.fixture(autouse=True)
def no_unexpected_errors(request, caplog):
    """An error in the log fails the test, unless it is marked expected_errors."""
    if not request.node.get_closest_marker("expected_errors"):
        request.node.stash[CHECKED_LOG] = caplog


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtest_teardown(item):
    """Checks the log once every fixture is torn down: hass last, which
    unloads the entries and stops Home Assistant.

    As the innermost wrapper, this runs while pytest still holds the records
    of the teardown.
    """
    yield
    caplog = item.stash.get(CHECKED_LOG, None)
    if caplog is None:
        return
    errors = [
        f"{when}: {record.name}: {record.getMessage()}"
        for when in ("setup", "call", "teardown")
        for record in caplog.get_records(when)
        if record.levelno >= logging.ERROR
        and record.name.startswith(WATCHED_LOGGERS)
        and not UNAVAILABLE.match(record.getMessage())
    ]
    assert not errors, errors


@pytest.fixture
async def blueprint_folder(hass, tmp_path):
    """Serve the repository blueprints from a temporary configuration folder."""
    from .local_helpers import BLUEPRINTS

    hass.config.config_dir = str(tmp_path)
    shutil.copytree(BLUEPRINTS, tmp_path / "blueprints" / "automation" / "autodarts")
    assert await async_setup_component(hass, "event", {})


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
