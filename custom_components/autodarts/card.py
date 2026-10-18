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

# Every file of the cards: the two modules that Home Assistant loads and the texts
# that the card module imports, one module per language in text/.
FRONTEND = Path(__file__).parent / "frontend"
CARD = "autodarts-card.js"
CARD_PATH = FRONTEND / CARD
# The dashboard strategy alone, small enough to be registered before Home Assistant
# stops waiting for it; it loads the strategy of the card module.
STRATEGY = "autodarts-strategy.js"
STRATEGY_PATH = FRONTEND / STRATEGY
# Both modules at their addresses without a version, which resources in YAML name.
CARD_URL = f"/{DOMAIN}/{CARD}"
STRATEGY_URL = f"/{DOMAIN}/{STRATEGY}"
# The path of a module of the cards in a resource, at any version or none.
_MODULE_PATH = re.compile(
    rf"/{DOMAIN}/(?:[^/]+/)?({re.escape(CARD)}|{re.escape(STRATEGY)})"
)
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
    """The address of each module, which the dashboard resources keep for Cast."""

    urls: dict[str, str]
    # Boards are set up side by side; one at a time looks at the resources.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


CARD_RESOURCES: HassKey[CardResources] = HassKey(f"{DOMAIN}_card_resources")


async def async_register_card(hass: HomeAssistant) -> None:
    """Make custom:autodarts-card available without a manual dashboard resource."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    version = (await async_get_integration(hass, DOMAIN)).version
    files, digest = await hass.async_add_executor_job(_load)
    # Version and content change the addresses, so browsers never keep a stale card.
    # The whole folder has the version in its address: the relative imports of a
    # module, of the card by the strategy and of the texts by the card, keep it.
    tag = f"{version}-{digest}"
    for name, (content, compressed) in files.items():
        hass.http.register_view(FileView(name, content, compressed, tag))
    # The strategy comes first, so that it is there before the cards have loaded.
    urls = {name: versioned(tag, name) for name in (STRATEGY, CARD)}
    for url in urls.values():
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
            for module, url in card.urls.items():
                await _async_keep(resources, module, url)
        except HomeAssistantError as err:
            # Every browser still loads the cards; only Cast misses them.
            _LOGGER.warning("The cards are missing in the dashboard resources: %s", err)


async def async_remove_card_resources(hass: HomeAssistant) -> None:
    """Remove both modules from the dashboard resources, with the last board."""
    if (resources := _resources(hass)) is None:
        return
    try:
        await resources.async_get_info()
        for item in _ours(resources, CARD, STRATEGY):
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


def versioned(tag: str, name: str) -> str:
    """The address of a file of the cards in the folder of this version."""
    return f"/{DOMAIN}/{tag}/{name}"


def _ours(resources: ResourceStorageCollection, *modules: str) -> list[dict[str, Any]]:
    """The resources of these modules, at any version or none, whatever their query."""
    return [item for item in resources.async_items() if _module(item["url"]) in modules]


def _module(url: str) -> str | None:
    """The module of the cards that a resource loads, or None for any other.

    Home Assistant takes any text as the address of a resource, so a typo in the
    resource of another card must not stop the boards from setting up.
    """
    try:
        path = urlsplit(url).path
    except ValueError:
        return None
    return match[1] if (match := _MODULE_PATH.fullmatch(path)) else None


async def _async_keep(
    resources: ResourceStorageCollection, module: str, url: str
) -> None:
    """One resource of the module at this address: added, brought up to date, the
    rest gone."""
    found = _ours(resources, module)
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


class FileView(HomeAssistantView):
    """A file of the cards, compressed for every browser that accepts gzip.

    Home Assistant sends a static file as it is on disk. The cards are more than half
    a megabyte of text, which gzip makes a quarter of that; a phone on slow Wi-Fi
    downloads them on its first visit and after every update.

    The file is served in the folder of any version, such as
    /autodarts/1.16.0-0123abcd/text/de.js, and without one, at /autodarts/text/de.js.
    The folder of a version that has gone serves today's file, as a page that Home
    Assistant sent before an update still asks for it; its imports, relative to it,
    then come from the same folder and are of today too.
    """

    # Like every other frontend file: the dashboards load it before anyone logs in.
    requires_auth = False

    def __init__(self, name: str, content: bytes, compressed: bytes, tag: str) -> None:
        self.url = f"/{DOMAIN}/{name}"
        self.extra_urls = [versioned("{version}", name)]
        # The name says which file this is; Home Assistant gives it to no route.
        self.name = f"{DOMAIN}:{name}"
        self._content = content
        self._compressed = compressed
        self._tag = tag

    def _headers(self, version: str | None) -> dict[str, str]:
        """The headers of the static files in the folder of this version.

        The weak tag stands for both encodings, as the content is the same, and lets a
        browser revalidate its copy for free. Any other address, such as the one of a
        resource in YAML without the version, is revalidated on every load, so that a
        browser never keeps an old file there.
        """
        current = version == self._tag
        return {
            hdrs.CACHE_CONTROL: CACHE_CONTROL if current else "no-cache",
            hdrs.ETAG: f'W/"{self._tag}"',
            hdrs.VARY: hdrs.ACCEPT_ENCODING,
        }

    async def get(
        self, request: web.Request, version: str | None = None
    ) -> web.Response:
        headers = self._headers(version)
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
            body=self._content,
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
    """Read every file of the cards, compress each and digest them together.

    The files go into the digest by their path in the folder, so a change of any of
    them, such as a text of one language, moves every address to a new folder.
    """
    files = {
        path.relative_to(FRONTEND).as_posix(): path.read_bytes()
        for path in FRONTEND.rglob("*.js")
    }
    names = sorted(files)
    content = hashlib.sha256(b"".join(files[name] for name in names))
    # Without a time stamp the same file always compresses to the same bytes.
    return {
        name: (files[name], gzip.compress(files[name], compresslevel=9, mtime=0))
        for name in names
    }, content.hexdigest()[:8]
