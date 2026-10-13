"""How the browser test waits for the cards, instead of sleeping for a fixed time.

A card draws itself at once and then fills in what Home Assistant sends over its
websocket, such as positions, profiles and trends. A page is settled when every card
has drawn itself, no request of the frontend waits for its answer, the websocket was
quiet for a moment, no animation of a card is running, and the browser has drawn two
frames since. browser.py waits for that, and for the states that a move at the board
sets, so that it checks a page as soon as it is ready and never too early; the
screenshot tool can use the same helpers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

# Milliseconds without a frame of the websocket before a page counts as settled:
# longer than the gaps between the frames of one update of Home Assistant.
QUIET = 100
# How often a page checks what it waits for, in milliseconds.
POLL = 50

# Counts the requests of the frontend on Home Assistant's websocket that wait for their
# answer, and notes when the last frame went or came. Added to every page before its
# scripts run, so it wraps the socket the frontend opens. Home Assistant answers a
# request with a result, and a ping with a pong, under the request's id; it may put
# several answers into one frame as a list.
WS_PROBE = """
(() => {
  if (window.__ws) return;
  const Native = window.WebSocket;
  const ws = { sockets: new Set(), last: performance.now() };
  ws.waiting = () => [...ws.sockets].flatMap((socket) => [...socket.__waiting.values()]);
  window.__ws = ws;
  window.WebSocket = class extends Native {
    constructor(...args) {
      super(...args);
      this.__waiting = new Map();
      ws.sockets.add(this);
      // A socket that closes answers nothing more; its frontend asks again on a new one.
      this.addEventListener('close', () => ws.sockets.delete(this));
      this.addEventListener('message', (event) => {
        ws.last = performance.now();
        try {
          for (const message of [].concat(JSON.parse(event.data))) {
            if (message.type === 'result' || message.type === 'pong') this.__waiting.delete(message.id);
          }
        } catch (error) {}
      });
    }
    send(data) {
      ws.last = performance.now();
      try {
        const message = JSON.parse(data);
        if (message.id !== undefined) this.__waiting.set(message.id, message.type);
      } catch (error) {}
      return super.send(data);
    }
  };
})();
"""
# Whether every card on the page has drawn itself.
CARDS_DRAWN = """
() => {
  const cards = [];
  (function collect(root) {
    root.querySelectorAll('*').forEach((el) => {
      if (el.tagName.startsWith('AUTODARTS-') && !el.tagName.endsWith('-EDITOR')) cards.push(el);
      if (el.shadowRoot) collect(el.shadowRoot);
    });
  })(document);
  return cards.length > 0 && cards.every((card) => card.shadowRoot?.querySelector('ha-card'));
}
"""
# Whether no request waits for its answer and no frame came for the given milliseconds.
WEBSOCKET_QUIET = """
(quiet) => Boolean(window.__ws) && window.__ws.waiting().length === 0
  && performance.now() - window.__ws.last > quiet
"""
# What still waits for its answer, for the message of a page that does not settle.
WEBSOCKET_WAITING = "() => window.__ws ? window.__ws.waiting() : 'no websocket probe'"
# The animations and transitions that run and end, in the cards ("cards") or anywhere on
# the page ("page"), by their names. Endless ones, such as the pulse of the latest dart,
# never end and don't count.
ANIMATIONS = """
(scope) => {
  const roots = scope === 'page' ? [document] : [];
  (function collect(root, inCard) {
    root.querySelectorAll('*').forEach((el) => {
      const card = inCard || el.tagName.startsWith('AUTODARTS-');
      if (el.shadowRoot) {
        if (card || scope === 'page') roots.push(el.shadowRoot);
        collect(el.shadowRoot, card);
      }
    });
  })(document, false);
  return [...new Set(roots.flatMap((root) => root.getAnimations()))]
    .filter((animation) => animation.playState === 'running'
      && Number.isFinite(animation.effect?.getComputedTiming().endTime))
    .map((animation) => animation.animationName || animation.transitionProperty || 'animation');
}
"""
# Two frames: the browser has laid out and drawn what the last change brought.
FRAMES = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
# Opens a path within the app, as its links do, and notes the cards shown before, which
# leave the page once the new view replaces them.
NAVIGATE = """
(path) => {
  if (location.pathname === path) return;
  const cards = [];
  (function collect(root) {
    root.querySelectorAll('*').forEach((el) => {
      if (el.tagName.startsWith('AUTODARTS-')) cards.push(el);
      if (el.shadowRoot) collect(el.shadowRoot);
    });
  })(document);
  window.__shownBefore = cards;
  history.pushState(null, '', path);
  window.dispatchEvent(new CustomEvent('location-changed', { detail: { replace: false } }));
}
"""
# Whether the view of the path replaced the one before and its cards have drawn.
SHOWN = f"""
(path) => location.pathname === path
  && (window.__shownBefore ?? []).every((card) => !card.isConnected)
  && ({CARDS_DRAWN})()
"""
# The states of Autodarts entities by their translation keys, from the frontend.
STATES = """
(keys) => {
  const hass = document.querySelector('home-assistant')?.hass;
  return Object.fromEntries(keys.map((key) => {
    const entity = Object.values(hass?.entities ?? {}).find(
      (item) => item.platform === 'autodarts' && item.translation_key === key
    );
    return [key, entity ? hass.states[entity.entity_id]?.state ?? null : null];
  }));
}
"""
# Whether the frontend shows these states of Autodarts entities.
STATES_ARE = f"""
(expected) => {{
  const states = ({STATES})(Object.keys(expected));
  return Object.entries(expected).every(([key, value]) => states[key] === value);
}}
"""


class Unsettled(AssertionError):
    """A page that did not reach what the test waits for."""


def probe(target: Page | BrowserContext) -> None:
    """Follow the websocket of every page of a context, or of one page, from its load."""
    target.add_init_script(WS_PROBE)


def wait_for(
    pages: Iterable[Page], expression: str, arg: object = None, timeout: int = 15000
) -> None:
    """Wait until a page function returns something true on every page."""
    for page in pages:
        page.wait_for_function(expression, arg=arg, timeout=timeout, polling=POLL)


def show(pages: Page | Iterable[Page], url: str) -> None:
    """Open a view on every page at once, until its cards have drawn: loaded on a page
    that shows nothing of Home Assistant yet, and within the app on one that does, as
    its links do. That keeps the frontend and its websocket, and takes a tenth of a
    second instead of a load of the whole app."""
    pages = [pages] if isinstance(pages, Page) else list(pages)
    target = urlsplit(url)
    for page in pages:
        if urlsplit(page.url).netloc == target.netloc:
            page.evaluate(NAVIGATE, target.path)
        else:
            # Only until the page is there: its cards are what the next lines wait for.
            page.goto(url, wait_until="commit")
    for page in pages:
        try:
            page.wait_for_function(SHOWN, arg=target.path, timeout=30000, polling=POLL)
        except PlaywrightTimeout as error:
            raise Unsettled(
                f"{page.url}: the view of {target.path} did not replace the one before"
                " or its cards did not draw"
            ) from error


def settle(*pages: Page, scope: str = "cards") -> None:
    """Wait until every page is settled: its cards drawn, its websocket quiet, the
    animations of its cards (or with scope "page", of the whole page) ended, and two
    frames drawn since."""
    wait_for(pages, CARDS_DRAWN, timeout=30000)
    for page in pages:
        try:
            page.wait_for_function(
                WEBSOCKET_QUIET, arg=QUIET, timeout=15000, polling=POLL
            )
        except PlaywrightTimeout as error:
            waiting = page.evaluate(WEBSOCKET_WAITING)
            raise Unsettled(
                f"{page.url}: the websocket does not get quiet; waiting for {waiting}"
            ) from error
    for page in pages:
        try:
            page.wait_for_function(
                f"() => ({ANIMATIONS})({scope!r}).length === 0",
                timeout=15000,
                polling=POLL,
            )
        except PlaywrightTimeout as error:
            running = page.evaluate(ANIMATIONS, scope)
            raise Unsettled(f"{page.url}: animations do not end: {running}") from error
    for page in pages:
        page.evaluate(FRAMES)


def expect_state(pages: Iterable[Page], expected: Mapping[str, str]) -> None:
    """Wait until every page shows these states of Autodarts entities, by their
    translation keys, such as {"num_throws": "2"} after the second dart of a visit."""
    for page in pages:
        try:
            page.wait_for_function(
                STATES_ARE, arg=dict(expected), timeout=15000, polling=POLL
            )
        except PlaywrightTimeout as error:
            shown = page.evaluate(STATES, list(expected))
            raise Unsettled(
                f"{page.url}: expected {dict(expected)}, the page shows {shown}"
            ) from error
