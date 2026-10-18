"""Serve the bundled Lovelace card and load it on every dashboard, also on Cast."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import logging
import re
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from aiohttp import hdrs, web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import async_get_integration
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FRONTEND = Path(__file__).parent / "frontend"
CARD_URL = f"/{DOMAIN}/autodarts-card.js"
CARD_PATH = FRONTEND / "autodarts-card.js"
# The dashboard strategy alone, small enough to be registered before Home Assistant
# stops waiting for it; it loads the strategy of the card module.
STRATEGY_URL = f"/{DOMAIN}/autodarts-strategy.js"
STRATEGY_PATH = FRONTEND / "autodarts-strategy.js"
# Both modules by their address, the card first as the digest has always taken them.
MODULES = {CARD_URL: CARD_PATH, STRATEGY_URL: STRATEGY_PATH}
# A month, as Home Assistant sends its own static files; the tests compare the two.
CACHE_CONTROL = "public, max-age=2678400"
# One content coding of Accept-Encoding with its optional weight, a number from 0 to 1
# with up to three decimals (RFC 9110, sections 12.4.2 and 12.5.3).
_CODING = re.compile(
    r"\s*([\w!#$%&'*+.^`|~-]+)\s*(?:;\s*q\s*=\s*([01](?:\.\d{0,3})?)\s*)?",
    re.IGNORECASE,
)


@dataclass(slots=True)
class CardResources:
    """The addresses of both modules, which the dashboard resources keep for Cast."""

    urls: tuple[str, ...]
    # Boards are set up side by side; one at a time looks at the resources.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


CARD_RESOURCES: HassKey[CardResources] = HassKey(f"{DOMAIN}_card_resources")


async def async_register_card(hass: HomeAssistant) -> None:
    """Make custom:autodarts-card available without a manual dashboard resource."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    version = (await async_get_integration(hass, DOMAIN)).version
    modules, digest = await hass.async_add_executor_job(_load)
    # Version and content change the URLs, so browsers never keep a stale card. Both
    # modules carry the same query: the strategy imports the card by it.
    tag = f"{version}-{digest}"
    for url, (module, compressed) in modules.items():
        hass.http.register_view(ModuleView(url, module, compressed, tag))
    # The strategy comes first, so that it is there before the cards have loaded.
    urls = tuple(f"{url}?v={tag}" for url in (STRATEGY_URL, CARD_URL))
    for url in urls:
        add_extra_js_url(hass, url)
    hass.data[CARD_RESOURCES] = CardResources(urls)


async def async_add_card_resources(hass: HomeAssistant) -> None:
    """Keep both modules in the dashboard resources, at their current addresses.

    Home Assistant Cast shows a dashboard on a TV through Chromecast and loads only
    its resources, never the modules that the frontend adds to every page. A browser
    loads a resource and a module of the frontend at one address once. Resources in
    YAML are the user's own: the documentation names the lines for them.
    """
    if (card := hass.data.get(CARD_RESOURCES)) is None or (
        resources := _resources(hass)
    ) is None:
        return
    async with card.lock:
        try:
            # Home Assistant reads the resources on their first use.
            await resources.async_get_info()
            for url in card.urls:
                await _async_keep(resources, url)
        except HomeAssistantError as err:
            # Every browser still loads the cards; only Cast misses them.
            _LOGGER.warning("The cards are missing in the dashboard resources: %s", err)


async def async_remove_card_resources(hass: HomeAssistant) -> None:
    """Remove both modules from the dashboard resources, with the last board."""
    if (resources := _resources(hass)) is None:
        return
    try:
        await resources.async_get_info()
        for item in _ours(resources, *MODULES):
            await resources.async_delete_item(item["id"])
    except HomeAssistantError as err:
        _LOGGER.warning("The cards stay in the dashboard resources: %s", err)


def _resources(hass: HomeAssistant) -> ResourceStorageCollection | None:
    """The dashboard resources that Home Assistant keeps, not those of YAML."""
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is not None and isinstance(
        lovelace.resources, ResourceStorageCollection
    ):
        return lovelace.resources
    return None


def _ours(resources: ResourceStorageCollection, *paths: str) -> list[dict[str, Any]]:
    """The resources of these modules by their path, whatever their query."""
    return [
        item for item in resources.async_items() if urlsplit(item["url"]).path in paths
    ]


async def _async_keep(resources: ResourceStorageCollection, url: str) -> None:
    """One module resource at this address: added, brought up to date, the rest gone."""
    found = _ours(resources, urlsplit(url).path)
    if not found:
        await resources.async_create_item({"res_type": "module", "url": url})
        return
    first, *others = found
    if first["url"] != url or first["type"] != "module":
        await resources.async_update_item(
            first["id"], {"res_type": "module", "url": url}
        )
    for item in others:
        await resources.async_delete_item(item["id"])


class ModuleView(HomeAssistantView):
    """A module of the cards, compressed for every browser that accepts gzip.

    Home Assistant sends a static file as it is on disk. The cards are more than half
    a megabyte of text, which gzip makes a quarter of that; a phone on slow Wi-Fi
    downloads them on its first visit and after every update.
    """

    # Like every other frontend file: the dashboards load it before anyone logs in.
    requires_auth = False

    def __init__(self, url: str, module: bytes, compressed: bytes, tag: str) -> None:
        self.url = url
        self.name = f"{DOMAIN}:{Path(url).stem}"
        self._module = module
        self._compressed = compressed
        self._tag = tag

    def _headers(self, request: web.Request) -> dict[str, str]:
        """The headers of the static files for the address of this version.

        The weak tag stands for both encodings, as the content is the same, and lets a
        browser revalidate its copy for free. Any other address, such as the one of a
        resource in YAML without the version, is revalidated on every load, so that a
        browser never keeps an old module there.
        """
        current = request.query.get("v") == self._tag
        return {
            hdrs.CACHE_CONTROL: CACHE_CONTROL if current else "no-cache",
            hdrs.ETAG: f'W/"{self._tag}"',
            hdrs.VARY: hdrs.ACCEPT_ENCODING,
        }

    async def get(self, request: web.Request) -> web.Response:
        headers = self._headers(request)
        if any(tag.value in ("*", self._tag) for tag in request.if_none_match or ()):
            return web.Response(status=HTTPStatus.NOT_MODIFIED, headers=headers)
        if _accepts_gzip(request.headers.get(hdrs.ACCEPT_ENCODING, "")):
            return web.Response(
                body=self._compressed,
                content_type="text/javascript",
                charset="utf-8",
                headers={**headers, hdrs.CONTENT_ENCODING: "gzip"},
            )
        return web.Response(
            body=self._module,
            content_type="text/javascript",
            charset="utf-8",
            headers=headers,
        )


def _accepts_gzip(accept_encoding: str) -> bool:
    """Whether a request takes gzip, by name or as `*`, with a weight above 0.

    A coding named more than once counts the first time; a malformed one not at all.
    """
    weights: dict[str, float] = {}
    for item in accept_encoding.split(","):
        if coding := _CODING.fullmatch(item):
            weights.setdefault(coding[1].lower(), float(coding[2] or 1))
    # RFC 9110 counts x-gzip as gzip.
    weight = weights.get("gzip", weights.get("x-gzip", weights.get("*", 0.0)))
    return weight > 0


def _load() -> tuple[dict[str, tuple[bytes, bytes]], str]:
    """Read both modules, compress each and digest them together."""
    modules = {url: path.read_bytes() for url, path in MODULES.items()}
    content = hashlib.sha256(b"".join(modules.values()))
    # Without a time stamp the same module always compresses to the same bytes.
    return {
        url: (module, gzip.compress(module, compresslevel=9, mtime=0))
        for url, module in modules.items()
    }, content.hexdigest()[:8]
