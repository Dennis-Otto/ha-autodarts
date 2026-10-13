"""Serve the bundled Lovelace card and load it on every dashboard."""

from __future__ import annotations

import gzip
import hashlib
import re
from http import HTTPStatus
from pathlib import Path

from aiohttp import hdrs, web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.http.static import CACHE_HEADER
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
# One content coding of Accept-Encoding with its optional weight, a number from 0 to 1
# with up to three decimals (RFC 9110, sections 12.4.2 and 12.5.3).
_CODING = re.compile(
    r"\s*([\w!#$%&'*+.^`|~-]+)\s*(?:;\s*q\s*=\s*([01](?:\.\d{0,3})?)\s*)?",
    re.IGNORECASE,
)


async def async_register_card(hass: HomeAssistant) -> None:
    """Make custom:autodarts-card available without a manual dashboard resource."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    version = (await async_get_integration(hass, DOMAIN)).version
    card, compressed, digest = await hass.async_add_executor_job(_load)
    # Version and content change the URLs, so browsers never keep a stale card. Both
    # modules carry the same query: the strategy imports the card by it.
    tag = f"{version}-{digest}"
    hass.http.register_view(CardModuleView(card, compressed, tag))
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STRATEGY_URL, str(STRATEGY_PATH), cache_headers=True)]
    )
    query = f"?v={tag}"
    add_extra_js_url(hass, f"{STRATEGY_URL}{query}")
    add_extra_js_url(hass, f"{CARD_URL}{query}")


class CardModuleView(HomeAssistantView):
    """The card module, compressed for every browser that accepts gzip.

    Home Assistant sends a static file as it is on disk. The cards are more than half
    a megabyte of text, which gzip makes a quarter of that; a phone on slow Wi-Fi
    downloads them on its first visit and after every update.
    """

    url = CARD_URL
    name = f"{DOMAIN}:card"
    # Like every other frontend file: the dashboards load it before anyone logs in.
    requires_auth = False

    def __init__(self, card: bytes, compressed: bytes, tag: str) -> None:
        self._card = card
        self._compressed = compressed
        self._tag = tag
        # The headers of the static files; the weak tag stands for both encodings, as
        # the content is the same, and lets a browser revalidate its copy for free.
        self._headers = {
            hdrs.CACHE_CONTROL: CACHE_HEADER,
            hdrs.ETAG: f'W/"{tag}"',
            hdrs.VARY: hdrs.ACCEPT_ENCODING,
        }

    async def get(self, request: web.Request) -> web.Response:
        if any(tag.value in ("*", self._tag) for tag in request.if_none_match or ()):
            return web.Response(status=HTTPStatus.NOT_MODIFIED, headers=self._headers)
        if _accepts_gzip(request.headers.get(hdrs.ACCEPT_ENCODING, "")):
            return web.Response(
                body=self._compressed,
                content_type="text/javascript",
                charset="utf-8",
                headers={**self._headers, hdrs.CONTENT_ENCODING: "gzip"},
            )
        return web.Response(
            body=self._card,
            content_type="text/javascript",
            charset="utf-8",
            headers=self._headers,
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


def _load() -> tuple[bytes, bytes, str]:
    """Read the card module, compress it and digest both modules."""
    card = CARD_PATH.read_bytes()
    content = hashlib.sha256(card + STRATEGY_PATH.read_bytes())
    # Without a time stamp the same module always compresses to the same bytes.
    return card, gzip.compress(card, compresslevel=9, mtime=0), content.hexdigest()[:8]
