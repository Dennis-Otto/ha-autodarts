"""Serve the bundled Lovelace card and load it on every dashboard."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

FRONTEND = Path(__file__).parent / "frontend"
CARD_URL = f"/{DOMAIN}/autodarts-card.js"
CARD_PATH = FRONTEND / "autodarts-card.js"
# The dashboard strategy alone, small enough to be registered before Home Assistant
# stops waiting for it; it loads the strategy of the card module.
STRATEGY_URL = f"/{DOMAIN}/autodarts-strategy.js"
STRATEGY_PATH = FRONTEND / "autodarts-strategy.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Make custom:autodarts-card available without a manual dashboard resource."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    version = (await async_get_integration(hass, DOMAIN)).version
    digest = await hass.async_add_executor_job(_digest)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True),
            StaticPathConfig(STRATEGY_URL, str(STRATEGY_PATH), cache_headers=True),
        ]
    )
    # Version and content change the URLs, so browsers never keep a stale card. Both
    # modules carry the same query: the strategy imports the card by it.
    query = f"?v={version}-{digest}"
    add_extra_js_url(hass, f"{STRATEGY_URL}{query}")
    add_extra_js_url(hass, f"{CARD_URL}{query}")


def _digest() -> str:
    content = hashlib.sha256()
    for path in (CARD_PATH, STRATEGY_PATH):
        content.update(path.read_bytes())
    return content.hexdigest()[:8]
