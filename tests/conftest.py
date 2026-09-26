"""Home Assistant fixtures for Autodarts."""

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import settings

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
