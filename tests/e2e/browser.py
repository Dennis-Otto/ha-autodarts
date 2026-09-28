"""Verify the dashboard cards in a real browser against the demo instance.

Runs in the Playwright container on the demo's Compose network (see browser.sh).
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

HA = "http://homeassistant:8123"
BOARD = "http://board-mock:3180"
LOADS = 5
# Board Manager generation of the demo board, passed on by browser.sh.
GENERATION = int(os.environ.get("BOARD_MANAGER", "1"))
# Writable folder for screenshots of a failed step, mounted by browser.sh.
ARTIFACTS = os.environ.get("BROWSER_ARTIFACTS", "")
# Steps to run instead of all, comma-separated, each a step's name or its beginning,
# such as "touch screens" or "correcting" while working on a screen; browser.sh passes
# BROWSER_STEPS on.
ONLY = {
    name.strip()
    for name in os.environ.get("BROWSER_STEPS", "").split(",")
    if name.strip()
}
# The integration as mounted by browser.sh, for the texts every language expects.
INTEGRATION = Path(__file__).resolve().parents[2] / "custom_components" / "autodarts"


def find(tag: str) -> str:
    """A page function returning every card element with this tag, in shadow roots too."""
    return f"""
() => {{
  const cards = [];
  (function collect(root) {{
    root.querySelectorAll('{tag}').forEach((card) => cards.push(card));
    root.querySelectorAll('*').forEach((el) => el.shadowRoot && collect(el.shadowRoot));
  }})(document);
  return cards;
}}
"""


CARDS = find("autodarts-card")
TRAINING_CARDS = find("autodarts-training-card")
STATUS_CARDS = find("autodarts-status-card")
SCOREBOARD_CARDS = find("autodarts-scoreboard-card")
PLAYERS_CARDS = find("autodarts-players-card")
DOUBLES_CARDS = find("autodarts-doubles-card")
LEADERBOARD_CARDS = find("autodarts-leaderboard-card")
FORM_EDITORS = find("hui-form-editor")
SCOREBOARD_STATE = f"""
() => {{
  const root = ({SCOREBOARD_CARDS})()[0].shadowRoot;
  const text = (selector) => root.querySelector(selector)?.textContent ?? null;
  return {{
    title: text('.title'),
    banner: root.querySelector('.banner').hidden ? null : text('.banner'),
    players: [...root.querySelectorAll('.player')].map((el) => [
      el.querySelector('.name').textContent,
      el.querySelector('.big').textContent,
      el.classList.contains('active'),
    ]),
    route: [...root.querySelectorAll('.main .bed')].map((el) => el.textContent),
    big: text('.single .big'),
    cricket: [...root.querySelectorAll('.cricket tr')].map((row) =>
      [...row.children].map((cell) => cell.textContent)
    ),
    darts: [...root.querySelectorAll('.visit .segment')].map((el) => el.textContent),
    scorecard: [...root.querySelectorAll('.scorecard tbody tr')].map((row) =>
      [...row.children].map((cell) => cell.textContent)
    ),
    summary: [...root.querySelectorAll('.summary tr')].map((row) =>
      [...row.children].map((cell) => cell.textContent)
    ),
    sum: text('.sum .value'),
    full: root.querySelector('.scoreboard').classList.contains('full'),
  }};
}}
"""
RENDERED = f"() => ({CARDS})().filter((card) => card.shadowRoot?.querySelector('.board svg')).length"
CARD_STATE = f"""
() => {{
  const card = ({CARDS})()[0];
  const root = card.shadowRoot;
  return {{
    score: root.querySelector('.score').textContent,
    slots: [...root.querySelectorAll('.slot .segment')].map((el) => el.textContent),
    latest: [...root.querySelectorAll('.slot')].findIndex((el) => el.classList.contains('latest')),
    hits: root.querySelectorAll('.hits .hit').length,
    darts: root.querySelectorAll('.darts .dart').length,
    blinking: root.querySelector('.hits').classList.contains('blink'),
    status: root.querySelector('.pill').textContent,
    toggle: root.querySelector('[data-action="toggle"]').textContent,
    numbers: root.querySelectorAll('.numbers text').length,
    beds: root.querySelectorAll('.face path').length,
    recent: [...root.querySelectorAll('.recent-visit')].map((el) => el.textContent),
  }};
}}
"""
PRACTICE_STATE = f"""
() => {{
  const root = ({CARDS})()[0].shadowRoot;
  return {{
    hidden: root.querySelector('.practice').hidden,
    title: root.querySelector('.practice-title').textContent,
    remaining: root.querySelector('.practice-remaining').textContent,
    route: [...root.querySelectorAll('.practice-route .bed')].map((el) => el.textContent),
    aim: root.querySelectorAll('.aim path').length,
    meta: root.querySelector('.practice-meta').textContent,
    scores: [...root.querySelectorAll('.player-score')].map((el) => [
      el.querySelector('.who').textContent,
      el.querySelector('.rest').textContent,
      el.classList.contains('active'),
    ]),
    grid: [...root.querySelectorAll('.practice .cricket tr')].map((row) =>
      [...row.children].map((cell) => cell.textContent)
    ),
  }};
}}
"""
T20 = {
    "segment": {"name": "T20", "number": 20, "multiplier": 3, "bed": "Triple"},
    "coords": {"x": 0.035, "y": 0.608},
}
T1 = {
    "segment": {"name": "T1", "number": 1, "multiplier": 3, "bed": "Triple"},
    "coords": {"x": 0.187, "y": 0.576},
}
SINGLE_1 = {
    "segment": {"name": "S1", "number": 1, "multiplier": 1, "bed": "SingleOuter"},
    "coords": {"x": 0.25, "y": 0.72},
}
DOUBLE_20 = {
    "segment": {"name": "D20", "number": 20, "multiplier": 2, "bed": "Double"},
    "coords": {"x": 0.002, "y": 0.972},
}
# A single 20 in the outer single bed, where a treble 20 could be read.
SINGLE_20 = {
    "segment": {"name": "S20", "number": 20, "multiplier": 1, "bed": "SingleOuter"},
    "coords": {"x": 0.01, "y": 0.8},
}
# 101 in one visit: 60, 1 and the double 20.
CHECKOUT_101 = [
    T20,
    {
        "segment": {"name": "S1", "number": 1, "multiplier": 1, "bed": "SingleOuter"},
        "coords": {"x": 0.244, "y": 0.751},
    },
    {
        "segment": {"name": "D20", "number": 20, "multiplier": 2, "bed": "Double"},
        "coords": {"x": 0.0, "y": 0.976},
    },
]
# Calls a service for an Autodarts entity through the logged-in frontend.
CALL_SERVICE = """
async ([domain, service, key, data]) => {
  const hass = document.querySelector('home-assistant').hass;
  const entity = Object.values(hass.entities).find(
    (item) => item.platform === 'autodarts' && item.translation_key === key
  );
  await hass.callService(domain, service, { entity_id: entity.entity_id, ...data });
}
"""
# The state of an Autodarts entity by its translation key.
STATE_OF = """
(key) => {
  const hass = document.querySelector('home-assistant').hass;
  const entity = Object.values(hass.entities).find(
    (item) => item.platform === 'autodarts' && item.translation_key === key
  );
  return hass.states[entity.entity_id].state;
}
"""
# Names a practice player; the four name fields share one translation key.
SET_NAME = """
async ([index, name]) => {
  const hass = document.querySelector('home-assistant').hass;
  const ids = Object.values(hass.entities)
    .filter((item) => item.platform === 'autodarts' && item.translation_key === 'practice_player')
    .map((item) => item.entity_id)
    .sort();
  await hass.callService('text', 'set_value', { entity_id: ids[index], value: name });
}
"""
TRAINING_STATE = f"""
() => {{
  const root = ({TRAINING_CARDS})()[0].shadowRoot;
  const text = (selector) => root.querySelector(selector)?.textContent;
  return {{
    average: text('.average'),
    darts: text('[data-total="darts"]'),
    visits: text('[data-total="visits"]'),
    heat: root.querySelectorAll('.heat-layer path').length,
    top: [...root.querySelectorAll('.top-row .key')].map((el) => el.textContent),
    history: root.querySelectorAll('.history-chart .visit-bar:not(.empty)').length,
    highest: root.querySelector('[data-tile="highest"] .value')?.textContent,
    sessions: [...root.querySelectorAll('.session-table tbody tr')].map(
      (row) => [...row.children].slice(2).map((cell) => cell.textContent)
    ),
    session: text('[data-action="session"]'),
    state: text('.session-state'),
  }};
}}
"""
STATUS_STATE = f"""
() => {{
  const root = ({STATUS_CARDS})()[0].shadowRoot;
  return {{
    cameras: root.querySelectorAll('.camera').length,
    version: root.querySelector('.version')?.textContent,
    update: root.querySelector('.update-badge')?.textContent,
    detection: root.querySelector('.toggle')?.getAttribute('aria-checked'),
    chips: root.querySelectorAll('.chip').length,
    system: !root.querySelector('.system-tile')?.hidden,
    info: root.querySelector('.system-info')?.hidden ? '' : root.querySelector('.system-info')?.textContent,
  }};
}}
"""


# Records page errors with their text; Playwright reports some only as "Object".
CAPTURE_ERRORS = r"""
window.__pageErrors = [];
window.addEventListener("error", (event) => {
  window.__pageErrors.push(`${event.message} (${event.filename || "page"})`);
});
window.addEventListener("unhandledrejection", (event) => {
  let reason = event.reason;
  try {
    reason = JSON.stringify(reason, Object.getOwnPropertyNames(reason ?? {}));
  } catch (error) {
    reason = String(reason);
  }
  window.__pageErrors.push(`unhandled rejection: ${reason}`);
});
"""
# A browser notice, not an error: the sections view re-measures itself after the
# card's text wraps differently at the final column width (a few pixels).
BENIGN = ("ResizeObserver loop completed with undelivered notifications",)


class BrowserFailure(AssertionError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise BrowserFailure(message)


def board_requests() -> dict:
    with urllib.request.urlopen(f"{BOARD}/control/requests", timeout=10) as response:
        return json.load(response)


def control(changes: dict) -> None:
    request = urllib.request.Request(
        f"{BOARD}/control/state",
        data=json.dumps(changes).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=10).read()


def open_view(
    browser: Browser,
    view: str,
    cards: str,
    ready: str,
    scheme: str = "dark",
    locale: str = "en-US",
) -> tuple[Page, list[str]]:
    page = browser.new_page(
        locale=locale, viewport={"width": 1280, "height": 820}, color_scheme=scheme
    )
    problems: list[str] = []
    page.add_init_script(CAPTURE_ERRORS)
    page.on(
        "console",
        lambda message: (
            message.type == "error"
            and "autodarts" in message.text.lower()
            and problems.append(f"console: {message.text}")
        ),
    )
    page.goto(f"{HA}/autodarts-demo/{view}")
    page.wait_for_function(
        f"() => ({cards})().some((card) => card.shadowRoot?.querySelector('{ready}'))",
        timeout=30000,
    )
    return page, problems


def open_board(
    browser: Browser, scheme: str = "dark", locale: str = "en-US"
) -> tuple[Page, list[str]]:
    return open_view(browser, "board", CARDS, ".board svg", scheme, locale)


def page_errors(page: Page, problems: list[str]) -> list[str]:
    """Console errors from the card plus every page error except known notices."""
    recorded = page.evaluate("window.__pageErrors || []")
    return problems + [
        error for error in recorded if not any(text in error for text in BENIGN)
    ]


def fresh_loads(browser: Browser) -> None:
    # Home Assistant boots in parallel with the card module; every load must register it.
    for attempt in range(LOADS):
        page, problems = open_board(browser)
        check(page.evaluate(RENDERED) == 1, f"Load {attempt + 1}: card not rendered")
        errors = page_errors(page, problems)
        check(not errors, f"Load {attempt + 1}: {errors}")
        page.close()


def visit(browser: Browser) -> None:
    page, problems = open_board(browser)
    state = page.evaluate(CARD_STATE)
    expected = {
        "score": "115",
        "slots": ["T20", "S5", "Bull"],
        "latest": 2,
        "hits": 3,
        "darts": 3,
        "blinking": True,
        "status": "Remove your darts",
        "toggle": "Stop detection",
        "numbers": 20,
        "beds": 80,
        # The last completed visits, newest first.
        "recent": ["90", "112", "102", "125", "81"],
    }
    check(state == expected, f"Card state {state} != {expected}")

    commands = len(board_requests()["commands"])
    page.locator("autodarts-card button[data-action='toggle']").click()
    page.wait_for_function(
        f"() => ({CARD_STATE})().toggle === 'Start detection'", timeout=15000
    )
    new = board_requests()["commands"][commands:]
    check(
        [(c["method"], c["path"]) for c in new] == [("PUT", "/api/stop")],
        f"Stop sent {new}",
    )
    page.locator("autodarts-card button[data-action='toggle']").click()
    page.wait_for_function(
        f"() => ({CARD_STATE})().toggle === 'Stop detection'", timeout=15000
    )

    # Discarding detected darts needs a second tap within a few seconds.
    commands = len(board_requests()["commands"])
    reset = page.locator("autodarts-card button[data-action='reset']")
    reset.click()
    check(reset.text_content() == "Confirm?", "Reset did not ask for confirmation")
    check(
        len(board_requests()["commands"]) == commands, "Reset ran without confirmation"
    )
    reset.click()
    page.wait_for_function(f"() => ({CARD_STATE})().score === '0'", timeout=15000)
    new = board_requests()["commands"][commands:]
    check(
        [(c["method"], c["path"]) for c in new] == [("POST", "/api/reset")],
        f"Reset sent {new}",
    )
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def practice(browser: Browser) -> None:
    """A practice leg counts down and shows the route and the bed to aim at."""
    page, problems = open_board(browser)
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "301"}]
    )
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().remaining === '301'", timeout=15000
    )
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": [T20] * count})
    control({"status": "Takeout in progress", "event": "Takeout started"})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().remaining === '121'", timeout=15000
    )
    state = page.evaluate(PRACTICE_STATE)
    expected = {
        "hidden": False,
        "title": "Practice 301",
        "remaining": "121",
        "route": ["T20", "25", "D18"],
        "aim": 1,
    }
    check(
        {key: state[key] for key in expected} == expected and not state["scores"],
        f"Practice state {state} != {expected}",
    )

    # Two players: the scoreboard follows the turn after the darts are pulled.
    page.evaluate(SET_NAME, [0, "Alex"])
    page.evaluate(SET_NAME, [1, "Sam"])
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": 2}]
    )
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().scores.length === 2", timeout=15000
    )
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": [T20] * count})
    control({"status": "Takeout in progress", "event": "Takeout started"})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().meta === 'Sam to throw'", timeout=15000
    )
    scores = page.evaluate(PRACTICE_STATE)["scores"]
    check(
        scores == [["Alex", "121", False], ["Sam", "301", True]],
        f"Scoreboard {scores}",
    )

    # Cricket: marks on the chalkboard, points while the other needs the 20.
    page.evaluate(
        CALL_SERVICE,
        ["select", "select_option", "practice_game", {"option": "cricket"}],
    )
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().title === 'Cricket'", timeout=15000
    )
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": [T20] * count})
    control({"status": "Takeout in progress", "event": "Takeout started"})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().meta === 'Sam to throw'", timeout=15000
    )
    state = page.evaluate(PRACTICE_STATE)
    grid = state["grid"]
    check(
        grid[0][1:] == ["Alex", "Sam"]
        and grid[1] == ["20", "Ⓧ", ""]
        and ["Points", "120", "0"] in grid
        and state["remaining"] == "0"
        and state["route"] == ["T20"]
        and state["aim"] == 1,
        f"Cricket state {state}",
    )

    # Shanghai: the round, the number to hit and every player's points.
    page.evaluate(
        CALL_SERVICE,
        ["select", "select_option", "practice_game", {"option": "shanghai"}],
    )
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().title === 'Shanghai'", timeout=15000
    )
    single_one = {
        "segment": {"name": "S1", "number": 1, "multiplier": 1, "bed": "SingleOuter"},
        "coords": {"x": 0.25, "y": 0.72},
    }
    control({"event": "Throw detected", "throws": [single_one]})
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().remaining === '1'", timeout=15000
    )
    state = page.evaluate(PRACTICE_STATE)
    check(
        state["route"] == ["1"]
        and state["meta"].startswith("Round 1/7")
        and state["aim"] == 4,
        f"Shanghai state {state}",
    )
    control({"status": "Takeout in progress", "event": "Takeout started"})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": 1}]
    )

    # Around the Clock: the next number and all of its beds to aim at.
    page.evaluate(
        CALL_SERVICE,
        ["select", "select_option", "practice_game", {"option": "around_the_clock"}],
    )
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().title === 'Around the Clock'", timeout=15000
    )
    one = {
        "segment": {"name": "S1", "number": 1, "multiplier": 1, "bed": "SingleOuter"},
        "coords": {"x": 0.25, "y": 0.72},
    }
    control({"event": "Throw detected", "throws": [one]})
    page.wait_for_function(
        f"() => ({PRACTICE_STATE})().remaining === '2'", timeout=15000
    )
    state = page.evaluate(PRACTICE_STATE)
    check(
        state["aim"] == 4 and " · 1 darts · " in state["meta"],
        f"Around the Clock state {state}",
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    page.wait_for_function(f"() => ({PRACTICE_STATE})().hidden", timeout=15000)
    check(page.evaluate(PRACTICE_STATE)["aim"] == 0, "Aim still shown without a game")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def progress(browser: Browser) -> None:
    """Badges, trends, the positions heatmap and the leaderboard after the practice games."""
    page, problems = open_view(browser, "players", PLAYERS_CARDS, ".profile")
    page.wait_for_function(
        f"() => ({PLAYERS_CARDS})()[0].shadowRoot.querySelector('.badges-section:not([hidden])')",
        timeout=15000,
    )
    earned = page.evaluate(
        f"() => [...({PLAYERS_CARDS})()[0].shadowRoot.querySelectorAll('.badge:not(.locked)')]"
        ".map((badge) => badge.dataset.badge)"
    )
    # Alex threw a 180 in 301 and nine marks in Cricket.
    check("maximum" in earned and "cricket_nine" in earned, f"Earned badges {earned}")
    trends = page.evaluate(
        f"() => ({PLAYERS_CARDS})()[0].shadowRoot.querySelectorAll('.trend-player').length"
    )
    check(trends >= 1, f"Trends of {trends} players")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()

    page, problems = open_view(browser, "training", TRAINING_CARDS, ".heat-layer")
    page.locator("autodarts-training-card button[data-mode='positions']").click()
    page.wait_for_function(
        f"() => ({TRAINING_CARDS})()[0].shadowRoot.querySelectorAll('.heat-layer .position').length > 0",
        timeout=15000,
    )
    page.locator("autodarts-training-card button[data-source='Alex']").click()
    page.wait_for_function(
        f"() => ({TRAINING_CARDS})()[0].shadowRoot"
        ".querySelector('button[data-source=\"Alex\"]').getAttribute('aria-pressed') === 'true'",
        timeout=15000,
    )
    page.wait_for_function(
        f"() => ({TRAINING_CARDS})()[0].shadowRoot.querySelectorAll('.heat-layer .position').length > 0",
        timeout=15000,
    )
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()

    page, problems = open_view(browser, "leaderboard", LEADERBOARD_CARDS, ".record")
    leader = page.evaluate(
        f"() => ({LEADERBOARD_CARDS})()[0].shadowRoot"
        ".querySelector('[data-record=\"maximums\"] .record-leader .who')?.textContent"
    )
    check(leader == "Alex", f"Most 180s: {leader}")
    page.locator("autodarts-leaderboard-card button[data-period='week']").click()
    pressed = page.evaluate(
        f"() => ({LEADERBOARD_CARDS})()[0].shadowRoot"
        ".querySelector('[data-period=\"week\"]').getAttribute('aria-pressed')"
    )
    check(pressed == "true", "The period did not switch")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def training(browser: Browser) -> None:
    page, problems = open_view(browser, "training", TRAINING_CARDS, ".heat-layer path")
    # The history of completed visits is loaded from the recorder.
    try:
        page.wait_for_function(
            f"() => ({TRAINING_STATE})().history === 5", timeout=15000
        )
    except PlaywrightTimeout:
        pass  # The comparison below reports what the card shows instead.
    state = page.evaluate(TRAINING_STATE)
    # Demo visits: 81, 125, 102, 112 and 90 points, plus 115 in progress.
    expected = {
        "average": "104.2",
        "darts": "18",
        "visits": "6",
        "heat": 11,
        "top": ["S20", "T20", "Bull", "S5", "25"],
        "history": 5,
        "highest": "125",
        # Darts, average and best visit of the two earlier sessions, newest first.
        "sessions": [["9", "86.0", "97"], ["6", "83.0", "140"]],
        "session": "End session",
        "state": "Session running",
    }
    check(state == expected, f"Training card state {state} != {expected}")

    # Ending a session needs a second tap; starting one does not.
    toggle = page.locator("autodarts-training-card button[data-action='session']")
    toggle.click()
    check(toggle.text_content() == "Confirm?", "Ending did not ask for confirmation")
    toggle.click()
    page.wait_for_function(
        f"() => ({TRAINING_STATE})().session === 'Start session'", timeout=30000
    )
    ended = page.evaluate(TRAINING_STATE)
    check(ended["state"].startswith("Session ended"), f"Session state {ended}")
    check(len(ended["sessions"]) == 3, f"Ended session missing: {ended['sessions']}")
    toggle.click()
    page.wait_for_function(f"() => ({TRAINING_STATE})().darts === '0'", timeout=30000)
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def status(browser: Browser) -> None:
    page, problems = open_view(browser, "status", STATUS_CARDS, ".camera")
    state = page.evaluate(STATUS_STATE)
    check(state["cameras"] == 3, f"Status card cameras: {state}")
    check(state["version"].startswith("Version "), f"Status card version: {state}")
    check(state["detection"] == "true", f"Status card detection: {state}")
    check(state["chips"] == 3, f"Status card connections: {state}")
    # Board Manager 2 describes its PC; the classic Board Manager does not.
    expected_info = (
        "Debian 13 · Intel Core i3-9100T · Detection 2.0.0" if GENERATION >= 2 else ""
    )
    check(state["info"] == expected_info, f"Status card board PC: {state}")

    commands = len(board_requests()["commands"])
    toggle = page.locator("autodarts-status-card .toggle")
    toggle.click()
    page.wait_for_function(
        f"() => ({STATUS_STATE})().detection === 'false'", timeout=15000
    )
    new = board_requests()["commands"][commands:]
    check(
        [(c["method"], c["path"]) for c in new] == [("PUT", "/api/stop")],
        f"Stop sent {new}",
    )
    toggle.click()
    page.wait_for_function(
        f"() => ({STATUS_STATE})().detection === 'true'", timeout=15000
    )

    # Restarting the Board Manager needs a second tap.
    restart = page.locator("autodarts-status-card button[data-action='restart']")
    commands = len(board_requests()["commands"])
    restart.click()
    check(restart.text_content() == "Confirm?", "Restart did not ask for confirmation")
    check(
        len(board_requests()["commands"]) == commands,
        "Restart ran without confirmation",
    )
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def scoreboard(browser: Browser) -> None:
    """The scoreboard view follows the visit, an X01 match, Cricket and a training game."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 800})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-auto/scoreboard")
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})().some((card) => card.shadowRoot?.querySelector('.main'))",
        timeout=30000,
    )

    def wait(condition: str) -> dict:
        page.wait_for_function(
            f"() => {{ const state = ({SCOREBOARD_STATE})(); return {condition}; }}",
            timeout=15000,
        )
        return page.evaluate(SCOREBOARD_STATE)

    def takeout() -> None:
        control({"status": "Takeout in progress", "event": "Takeout started"})
        control({"status": "Throw", "event": "Takeout finished", "throws": []})

    def game(option: str) -> None:
        page.evaluate(
            CALL_SERVICE,
            ["select", "select_option", "practice_game", {"option": option}],
        )

    # Between games, the visit score is the big number.
    takeout()
    control({"event": "Throw detected", "throws": [T20]})
    state = wait("state.big === '60'")
    check(
        state["full"] and state["darts"] == ["T20", "–", "–"] and state["sum"] is None,
        f"Scoreboard between games {state}",
    )
    takeout()

    # An X01 match: every player's score, the player at the board and the route.
    page.evaluate(SET_NAME, [0, "Alex"])
    page.evaluate(SET_NAME, [1, "Sam"])
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": 2}]
    )
    game("501")
    state = wait("state.players.length === 2")
    check(state["title"] == "Practice 501", f"Scoreboard title {state}")
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": [T20] * count})
    state = wait("state.sum === '180'")
    check(
        state["players"][0] == ["Alex", "321", True] and state["darts"][2] == "T20",
        f"Scoreboard during the visit {state}",
    )
    takeout()
    state = wait("state.players[1][2]")
    check(
        state["players"] == [["Alex", "321", False], ["Sam", "501", True]],
        f"Scoreboard after the turn {state}",
    )

    # The match ends with its summary; the next dart starts the next match.
    page.evaluate(CALL_SERVICE, ["number", "set_value", "practice_legs", {"value": 1}])
    game("101")
    state = wait("state.players.length === 2 && state.players[0][1] === '101'")
    throws = [T20, SINGLE_1, DOUBLE_20]
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": throws[:count]})
    takeout()
    state = wait("state.summary.length > 0")
    check(
        state["banner"] == "Alex wins the match!"
        # The winner is also named for screen readers.
        and state["summary"][0] == ["Match summary", "Alex Winner", "Sam"]
        and state["summary"][1] == ["Legs", "1", "0"]
        and ["3-dart avg.", "101.0", "–"] in state["summary"]
        and not state["players"],
        f"Scoreboard summary {state}",
    )
    control({"event": "Throw detected", "throws": [T20]})
    state = wait("state.summary.length === 0")
    check(state["banner"] is None, f"Scoreboard after the summary {state}")
    takeout()

    # Cricket: the chalkboard with both players.
    game("cricket")
    state = wait("state.title === 'Cricket'")
    check(
        state["cricket"][0] == ["T20", "Alex", "Sam"] and state["route"] == ["T20"],
        f"Scoreboard in Cricket {state}",
    )

    # A training game: the target is the big number.
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": 1}]
    )
    game("around_the_clock")
    state = wait("state.title === 'Around the Clock'")
    check(state["big"] == "1", f"Scoreboard in Around the Clock {state}")
    game("off")
    wait("state.big !== null && state.title !== 'Around the Clock'")
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


# Calls an action of the integration through the logged-in frontend.
CALL_ACTION = """
async ([service, data]) => {
  const hass = document.querySelector('home-assistant').hass;
  await hass.callService('autodarts', service, data);
}
"""


def play_comfort(browser: Browser) -> None:
    """A tap corrects a dart, the keypad enters one and passes, the bot throws, and
    the last visit comes back."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 1000})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-demo/keypad")
    card = page.locator("autodarts-scoreboard-card")
    card.locator(".main").wait_for(timeout=30000)
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_bot_delay", {"value": 0.5}]
    )
    page.evaluate(CALL_SERVICE, ["switch", "turn_on", "practice_manual_entry"])
    page.evaluate(
        CALL_ACTION,
        ["start_game", {"game": "301", "players": ["Alex"], "bot_level": 120}],
    )
    card.locator(".pad").wait_for(timeout=15000)
    names = card.locator(".player .name").all_text_contents()
    check(names == ["Alex", "Bot Level 120"], f"Players against the bot {names}")
    title = card.locator(".pad .section-label").text_content()
    check(title == "Enter a dart", f"Keypad title {title!r}")

    # The board reads a single 20; a tap on the dart puts it into the treble.
    control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
    card.locator("[data-dart='2']").click()
    title = card.locator(".pad .section-label").text_content()
    check(title == "Correct dart 2", f"Pad title {title!r}")
    card.locator("[data-pad='multiplier'][data-value='3']").click()
    card.locator(".pad-number[data-value='T20']").click()
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.sum .value')?.textContent === '120'",
        timeout=15000,
    )
    # The third dart entered by hand, then the next player with a second tap.
    card.locator("[data-pad='multiplier'][data-value='3']").click()
    card.locator(".pad-number[data-value='T20']").click()
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.sum .value')?.textContent === '180'",
        timeout=15000,
    )
    card.locator("[data-pad='next']").click()
    label = card.locator("[data-pad='next']").text_content()
    check(label == "Confirm?", f"Next player asks for a second tap: {label!r}")
    card.locator("[data-pad='next']").click()

    # The bot throws, and Alex is up again; the undo takes both visits back.
    page.wait_for_function(
        f"""() => {{
          const root = ({SCOREBOARD_CARDS})()[0].shadowRoot;
          const tiles = [...root.querySelectorAll('.player')];
          return tiles[0].classList.contains('active') && tiles[1].querySelector('.big').textContent !== '301';
        }}""",
        timeout=20000,
    )
    card.locator("[data-pad='undo']").click()
    card.locator("[data-pad='undo']").click()
    page.wait_for_function(
        f"""() => {{
          const root = ({SCOREBOARD_CARDS})()[0].shadowRoot;
          const values = [...root.querySelectorAll('.player .big')].map((el) => el.textContent);
          return values[0] === '121' && values[1] === '301';
        }}""",
        timeout=15000,
    )
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_bot_level", {"value": 0}]
    )
    page.evaluate(CALL_SERVICE, ["switch", "turn_off", "practice_manual_entry"])
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


def lobby(browser: Browser) -> None:
    """A game is chosen and started on the scoreboard, and ended there again."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 800})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-auto/scoreboard")
    card = "autodarts-scoreboard-card"
    page.locator(f"{card} .main").wait_for(timeout=30000)
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    page.locator(f"{card} .lobby-cta").click()
    page.locator(f"{card} .lobby").wait_for(timeout=15000)
    title = page.locator(f"{card} .title").text_content()
    check(title == "New game", f"Lobby title {title!r}")
    players = page.locator(f"{card} .lobby-player .who")
    # The screen starts with the players the board has; start from nobody.
    while players.count():
        page.locator(f"{card} .lobby-player [data-lobby='remove']").first.click()
    # Players at home come first: Alex and Sam are home, Kim is out.
    suggested = page.locator(f"{card} .suggestion:not(.guest)").all_text_contents()
    check(
        suggested[:3] == ["Alex⌂", "Sam⌂", "Kim"],
        f"Suggestions {suggested}",
    )
    page.locator(f"{card} .game[data-value='cricket']").click()
    page.locator(f"{card} .suggestion", has_text="Sam").click()
    name = page.locator(f"{card} .lobby-name")
    name.fill("Robin")
    name.press("Enter")
    page.locator(f"{card} .suggestion", has_text="Alex").click()
    check(
        players.all_text_contents() == ["Sam", "Robin", "Alex"],
        f"Players {players.all_text_contents()}",
    )
    page.locator(f"{card} [data-lobby='up'][data-value='2']").click()
    page.locator(f"{card} [data-lobby='up'][data-value='1']").click()
    page.locator(f"{card} [data-lobby='remove'][data-value='2']").click()
    page.locator(f"{card} [data-lobby='legs'][data-value='1']").click()
    check(
        players.all_text_contents() == ["Alex", "Sam"],
        f"Players {players.all_text_contents()}",
    )
    pictures = page.locator(f"{card} .lobby-player .avatar").count()
    check(pictures == 2, f"{pictures} pictures of linked players")
    page.locator(f"{card} .lobby .start").click()

    # The scoreboard shows the game it started, with the pictures of the players.
    page.wait_for_function(
        f"() => ({SCOREBOARD_STATE})().title === 'Cricket'", timeout=15000
    )
    state = page.evaluate(SCOREBOARD_STATE)
    check(state["cricket"][0][1:] == ["Alex", "Sam"], f"Scoreboard {state}")
    heads = page.locator(f"{card} .cricket thead .avatar").count()
    check(heads == 2, f"{heads} pictures on the chalkboard")
    legs = page.evaluate(STATE_OF, "practice_legs")
    check(legs in ("2", "2.0"), f"Legs per set {legs!r}")

    # During a game the header opens the screen; ending the game needs a second tap.
    page.locator(f"{card} .lobby-toggle").click()
    end = page.locator(f"{card} [data-lobby='end']")
    end.click()
    check(end.text_content() == "Confirm?", "Ending did not ask for confirmation")
    end.click()
    page.wait_for_function(
        f"() => !({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector(\"[data-lobby='end']\")",
        timeout=15000,
    )
    page.locator(f"{card} [data-lobby='close']").click()
    page.locator(f"{card} .lobby-cta").wait_for(timeout=15000)
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


def more_games(browser: Browser) -> None:
    """A team match, Tactics and Golf on the scoreboard."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 800})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-auto/scoreboard")
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})().some((card) => card.shadowRoot?.querySelector('.main'))",
        timeout=30000,
    )

    def wait(condition: str) -> dict:
        page.wait_for_function(
            f"() => {{ const state = ({SCOREBOARD_STATE})(); return {condition}; }}",
            timeout=15000,
        )
        return page.evaluate(SCOREBOARD_STATE)

    def takeout() -> None:
        control({"status": "Takeout in progress", "event": "Takeout started"})
        control({"status": "Throw", "event": "Takeout finished", "throws": []})

    def call(domain: str, service: str, key: str, **data) -> None:
        page.evaluate(CALL_SERVICE, [domain, service, key, data])

    takeout()
    for index, name in enumerate(("Alex", "Sam", "Kim", "Lea")):
        page.evaluate(SET_NAME, [index, name])
    call("number", "set_value", "practice_players", value=4)
    call("switch", "turn_on", "practice_teams")
    call("select", "select_option", "practice_game", option="301")
    state = wait("state.players.length === 2")
    check(
        state["players"] == [["Alex & Kim", "301", True], ["Sam & Lea", "301", False]],
        f"Scoreboard of a team match {state}",
    )
    control({"event": "Throw detected", "throws": [T20]})
    takeout()
    state = wait("state.players[1][2]")
    check(
        state["players"] == [["Alex & Kim", "241", False], ["Sam & Lea", "301", True]],
        f"Scoreboard after the first team visit {state}",
    )
    call("switch", "turn_off", "practice_teams")
    call("number", "set_value", "practice_players", value=2)

    call("select", "select_option", "practice_game", option="tactics")
    state = wait("state.title === 'Tactics'")
    numbers = [row[0] for row in state["cricket"][1:13]]
    check(
        numbers == [*(str(number) for number in range(20, 9, -1)), "Bull"],
        f"Scoreboard in Tactics {state}",
    )

    call("select", "select_option", "practice_game", option="golf")
    state = wait("state.title === 'Golf' && state.scorecard.length === 2")
    control({"event": "Throw detected", "throws": [T1]})
    takeout()
    # A treble is two strokes.
    state = wait("state.scorecard[0][1] === '2'")
    check(
        state["scorecard"][0][0] == "Alex" and state["scorecard"][0][-1] == "2",
        f"Scorecard of Golf {state}",
    )
    call("number", "set_value", "practice_players", value=1)
    call("select", "select_option", "practice_game", option="off")
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


def tournament(browser: Browser) -> None:
    """A round robin started on the new game screen, played, shown and stopped."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 800})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-demo/tournament")
    card = "autodarts-scoreboard-card"
    page.locator(f"{card} .main").wait_for(timeout=30000)
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    page.locator(f"{card} .main .lobby-cta").click()
    page.locator(f"{card} [data-lobby='mode'][data-value='tournament']").click()
    groups = page.locator(f"{card} .lobby-group .section-label").all_text_contents()
    check(groups == ["X01", "Cricket"], f"Tournament games {groups}")
    players = page.locator(f"{card} .lobby-player .who")
    while players.count():
        page.locator(f"{card} .lobby-player [data-lobby='remove']").first.click()
    for name in ("Alex", "Sam", "Kim"):
        page.locator(f"{card} .suggestion", has_text=name).click()
    page.locator(f"{card} .game", has_text="101").click()
    fewer = page.locator(f"{card} [data-lobby='legs'][data-value='-1']")
    while not fewer.is_disabled():
        fewer.click()
    start = page.locator(f"{card} .lobby .start")
    check(start.text_content() == "Start tournament", "No tournament to start")
    start.click()

    # Kim and Sam open the round robin; its round is in the match view.
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.meta')"
        ".textContent.startsWith('Tournament · Round 1 · Match 1 of 3')",
        timeout=15000,
    )
    state = page.evaluate(SCOREBOARD_STATE)
    check(
        [player[0] for player in state["players"]] == ["Kim", "Sam"],
        f"First match {state}",
    )
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": CHECKOUT_101[:count]})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})

    # After the summary of the match (8 seconds), the table with the next match.
    page.locator(f"{card} .standings").wait_for(timeout=15000)
    rows = page.locator(f"{card} .standings tbody .who").all_text_contents()
    check(rows == ["Kim", "Alex", "Sam"], f"Table {rows}")
    pairing = page.locator(f"{card} .pairing").text_content()
    check(pairing == "AlexvsKim", f"Next match {pairing!r}")
    page.locator(f"{card} .start-next").click()
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.meta')"
        ".textContent.startsWith('Tournament · Round 2 · Match 2 of 3')",
        timeout=15000,
    )

    # Ending the game stops the tournament too.
    page.locator(f"{card} .lobby-toggle").click()
    end = page.locator(f"{card} [data-lobby='end']")
    check(end.text_content() == "Stop tournament", f"End button {end.text_content()}")
    end.click()
    end.click()
    page.wait_for_function(
        f"() => !({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector(\"[data-lobby='end']\")",
        timeout=15000,
    )
    stage = page.evaluate(STATE_OF, "tournament")
    check(stage == "no_tournament", f"Tournament after stopping: {stage}")
    page.locator(f"{card} [data-lobby='close']").click()
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


# The landscape tablet at the board that the scoreboard screens are built for.
TABLET = {"width": 800, "height": 480}
# Controls the card sizes for a finger; each is at least 44 px high, the keys of the
# pad at least 40 px, so that the pad fits beside the scores of a short screen.
FINGER_TARGETS = ".lobby-cta, .lobby button, .pad button, .undo-only, .start-next"
PAD_KEYS = ".pad button"
# The width of the scoreboard against its room, and every control that is smaller
# than the card means it to be: finger targets, and whatever has a minimum size of
# 44 px or more in the card's style.
TABLET_LAYOUT = f"""
() => {{
  const card = ({SCOREBOARD_CARDS})()[0];
  const root = card.shadowRoot;
  const frame = root.querySelector('ha-card');
  const small = [];
  let targets = 0;
  for (const el of root.querySelectorAll('button, input, {FINGER_TARGETS}')) {{
    if (!el.getClientRects().length) continue;
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    const finger = el.matches('{FINGER_TARGETS}');
    if (finger) targets += 1;
    const high = finger || parseFloat(style.minHeight) >= 44;
    const wide = parseFloat(style.minWidth) >= 44;
    const least = el.matches('{PAD_KEYS}') ? 39.5 : 43.5;
    if ((high && box.height < least) || (wide && box.width < 43.5)) {{
      const name = `${{el.className || el.tagName.toLowerCase()}} "${{el.textContent.trim()}}"`;
      small.push(`${{name}} ${{Math.round(box.width)}}x${{Math.round(box.height)}}`);
    }}
  }}
  return {{
    width: frame.scrollWidth,
    room: frame.clientWidth,
    right: Math.round(card.getBoundingClientRect().right),
    viewport: innerWidth,
    targets,
    small,
  }};
}}
"""
# The fitted scoreboard: its height against the screen and its own room, where the
# start of the new game screen sits, and the pad beside the scores.
TABLET_FIT = f"""
() => {{
  const card = ({SCOREBOARD_CARDS})()[0];
  const root = card.shadowRoot;
  const frame = root.querySelector('ha-card');
  const box = (selector) => {{
    const el = root.querySelector(selector);
    if (!el || !el.getClientRects().length) return null;
    const rect = el.getBoundingClientRect();
    return {{ top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right }};
  }};
  const actions = root.querySelector('.lobby-actions');
  return {{
    bottom: Math.round(card.getBoundingClientRect().bottom),
    screen: innerHeight,
    height: frame.scrollHeight,
    room: frame.clientHeight,
    sticky: actions ? getComputedStyle(actions).position : null,
    actions: box('.lobby-actions'),
    main: box('.scoreboard > .main'),
    pad: box('.scoreboard > .pad-area'),
    beside: !!root.querySelector('.scoreboard.full.with-pad'),
  }};
}}
"""


def tablet_screen(browser: Browser) -> None:
    """The new game screen, scoreboard, keypad and tournament on an 800 x 480 tablet:
    nothing wider than the screen, targets for a finger, and idle mode without motion."""
    page = browser.new_page(locale="en-US", viewport=TABLET)
    page.add_init_script(CAPTURE_ERRORS)
    card = "autodarts-scoreboard-card"

    def fits(screen: str, targets: bool = True) -> None:
        layout = page.evaluate(TABLET_LAYOUT)
        check(
            layout["width"] <= layout["room"] + 1
            and layout["right"] <= layout["viewport"] + 1,
            f"{screen} is wider than the tablet: {layout}",
        )
        check(not targets or layout["targets"], f"{screen} has no targets: {layout}")
        check(not layout["small"], f"{screen}: targets below 44 px {layout['small']}")

    def fills(screen: str) -> None:
        """A full-height scoreboard is one screen high and needs no scrolling."""
        fit = page.evaluate(TABLET_FIT)
        check(
            fit["bottom"] <= fit["screen"] + 1 and fit["height"] <= fit["room"] + 1,
            f"{screen} is higher than the tablet: {fit}",
        )

    def open_screen(view: str) -> None:
        errors = page_errors(page, [])
        check(not errors, f"Console problems: {errors}")
        page.goto(f"{HA}/autodarts-demo/{view}")
        page.locator(f"{card} .main").wait_for(timeout=30000)

    def game_off() -> None:
        page.evaluate(
            CALL_SERVICE,
            ["select", "select_option", "practice_game", {"option": "off"}],
        )
        control({"status": "Throw", "event": "Takeout finished", "throws": []})

    def end_game() -> None:
        page.locator(f"{card} .lobby-toggle").click()
        end = page.locator(f"{card} [data-lobby='end']")
        end.click()
        end.click()
        page.wait_for_function(
            f"() => !({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector(\"[data-lobby='end']\")",
            timeout=15000,
        )
        page.locator(f"{card} [data-lobby='close']").click()

    def choose(names: tuple[str, ...], game: str) -> None:
        players = page.locator(f"{card} .lobby-player .who")
        while players.count():
            page.locator(f"{card} .lobby-player [data-lobby='remove']").first.click()
        for name in names:
            page.locator(f"{card} .suggestion", has_text=name).click()
        page.locator(f"{card} .game", has_text=game).first.click()

    # Between games, then the new game screen and an X01 match it starts.
    page.goto(f"{HA}/autodarts-demo/tournament")
    page.locator(f"{card} .main").wait_for(timeout=30000)
    game_off()
    page.locator(f"{card} .lobby-cta").wait_for(timeout=15000)
    fits("The scoreboard between games")
    page.locator(f"{card} .lobby-cta").click()
    page.locator(f"{card} .lobby").wait_for(timeout=15000)
    fits("The new game screen")
    # The start stays at the bottom of the screen while the choices scroll.
    fit = page.evaluate(TABLET_FIT)
    actions = fit["actions"]
    check(
        fit["sticky"] == "sticky"
        and actions is not None
        and 0 <= actions["top"]
        and actions["bottom"] <= fit["screen"] + 1,
        f"The start of the new game screen is out of reach: {fit}",
    )
    choose(("Alex", "Sam"), "501")
    page.locator(f"{card} .lobby .start").click()
    page.wait_for_function(
        f"() => ({SCOREBOARD_STATE})().players.length === 2", timeout=15000
    )
    control({"event": "Throw detected", "throws": [T20]})
    page.wait_for_function(
        f"() => ({SCOREBOARD_STATE})().darts[0] === 'T20'", timeout=15000
    )
    fits("The scoreboard of a match", targets=False)
    fills("The scoreboard of a match")
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    end_game()

    # The keypad for darts entered by hand.
    open_screen("keypad")
    page.evaluate(CALL_SERVICE, ["switch", "turn_on", "practice_manual_entry"])
    page.evaluate(
        CALL_ACTION, ["start_game", {"game": "301", "players": ["Alex", "Sam"]}]
    )
    page.locator(f"{card} .pad").wait_for(timeout=15000)
    fits("The keypad")
    fills("The keypad")
    # In landscape, the pad sits beside the scores instead of below them.
    fit = page.evaluate(TABLET_FIT)
    main, pad = fit["main"], fit["pad"]
    check(
        fit["beside"]
        and main is not None
        and pad is not None
        and pad["left"] >= main["right"] - 1
        and pad["top"] < main["bottom"],
        f"The pad is not beside the scores: {fit}",
    )
    page.evaluate(CALL_SERVICE, ["switch", "turn_off", "practice_manual_entry"])
    game_off()

    # A round robin: its setup, a match and the table with the next match.
    open_screen("tournament")
    page.locator(f"{card} .main .lobby-cta").click()
    page.locator(f"{card} [data-lobby='mode'][data-value='tournament']").click()
    choose(("Alex", "Sam", "Kim"), "101")
    fewer = page.locator(f"{card} [data-lobby='legs'][data-value='-1']")
    while not fewer.is_disabled():
        fewer.click()
    fits("The tournament setup")
    page.locator(f"{card} .lobby .start").click()
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.meta')"
        ".textContent.startsWith('Tournament · Round 1')",
        timeout=15000,
    )
    fits("A tournament match", targets=False)
    for count in range(1, 4):
        control({"event": "Throw detected", "throws": CHECKOUT_101[:count]})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    # The table follows the eight seconds of the match summary.
    page.locator(f"{card} .standings").wait_for(timeout=30000)
    page.locator(f"{card} .start-next").wait_for(timeout=15000)
    fits("The tournament table")
    end_game()
    stage = page.evaluate(STATE_OF, "tournament")
    check(stage == "no_tournament", f"Tournament after stopping: {stage}")
    game_off()

    # Idle mode after ten seconds, without its fade for a device that asks for less
    # motion; a tap brings the scoreboard back.
    page.emulate_media(reduced_motion="reduce")
    open_screen("idle")
    panel = page.locator(f"{card} .idle-panel")
    panel.wait_for(timeout=60000)
    motion = panel.evaluate(
        "(el) => [matchMedia('(prefers-reduced-motion: reduce)').matches,"
        " getComputedStyle(el).animationName]"
    )
    check(motion == [True, "none"], f"Idle mode with reduced motion: {motion}")
    fits("Idle mode", targets=False)
    panel.click()
    panel.wait_for(state="detached", timeout=15000)
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


# Touch screens as players use them: the companion app on an iPhone passes the status
# bar and the home indicator on as safe areas (top, bottom), a small Android phone shows
# the dashboard in its browser, an iPhone on its side keeps the home indicator below, and
# a 24 inch touch monitor stands beside the board, as many players have it.
TOUCH_SCREENS = (
    ("iPhone", {"width": 393, "height": 852}, (59, 34)),
    ("small Android phone", {"width": 360, "height": 640}, (0, 0)),
    ("iPhone in landscape", {"width": 852, "height": 393}, (0, 21)),
    ("24-inch touch monitor", {"width": 1920, "height": 1080}, (0, 0)),
)
# Four players whose long names have to fit a phone.
LONG_NAMES = ["Maximilian", "Anneliese-Charlotte", "Bartholomäus", "Konstantin"]


def phone_style(top: int, bottom: int) -> str:
    """Home Assistant's safe areas as the companion app sets them, and a theme whose
    cards are see-through, as glass themes make them."""
    return f"""
const style = document.createElement('style');
style.textContent = `html {{
  --app-safe-area-inset-top: {top}px !important;
  --app-safe-area-inset-bottom: {bottom}px !important;
  --ha-card-background: rgba(60, 64, 80, 0.35) !important;
}}`;
// The script runs before the page has an element to hold the style.
const add = () => document.documentElement.append(style);
if (document.documentElement) add();
else document.addEventListener('DOMContentLoaded', add, {{ once: true }});
"""


# The room a phone leaves: above the home indicator, the scoreboard's own height.
PHONE_FIT = f"""
() => {{
  const card = ({SCOREBOARD_CARDS})()[0];
  const frame = card.shadowRoot.querySelector('ha-card');
  const inset = getComputedStyle(document.documentElement).getPropertyValue('--safe-area-inset-bottom');
  return {{
    bottom: Math.round(card.getBoundingClientRect().bottom),
    free: innerHeight - (parseFloat(inset) || 0),
    height: frame.scrollHeight,
    room: frame.clientHeight,
  }};
}}
"""
# The start bar of the new game screen: whether it stays at the bottom, covers what
# scrolls beneath it with a background of its own, spans the card and keeps the start
# above the home indicator.
START_BAR = f"""
() => {{
  const root = ({SCOREBOARD_CARDS})()[0].shadowRoot;
  const bar = root.querySelector('.lobby-actions');
  const style = getComputedStyle(bar);
  const frame = root.querySelector('ha-card').getBoundingClientRect();
  const box = bar.getBoundingClientRect();
  const start = root.querySelector('.lobby .start').getBoundingClientRect();
  const inset = getComputedStyle(document.documentElement).getPropertyValue('--safe-area-inset-bottom');
  return {{
    sticky: style.position,
    layers: style.backgroundImage,
    base: style.backgroundColor,
    edges: [Math.round(box.left - frame.left), Math.round(frame.right - box.right)],
    start: [Math.round(start.top), Math.round(start.bottom)],
    free: innerHeight - (parseFloat(inset) || 0),
    buttons: [...bar.querySelectorAll('button')].map((el) => el.dataset.lobby),
    hints: root.querySelectorAll('.lobby-hint').length,
  }};
}}
"""
# Every card on the page against the width of the phone, and names cut short.
PHONE_WIDTH = """
() => {
  const cards = [];
  (function collect(root) {
    root.querySelectorAll('*').forEach((el) => {
      if (el.tagName.startsWith('AUTODARTS-') && el.shadowRoot) cards.push(el);
      if (el.shadowRoot) collect(el.shadowRoot);
    });
  })(document);
  const wide = [];
  const cut = [];
  for (const card of cards) {
    const frame = card.shadowRoot.querySelector('ha-card');
    if (!frame) continue;
    if (frame.scrollWidth > frame.clientWidth + 1 || card.getBoundingClientRect().right > innerWidth + 1) {
      wide.push(`${card.tagName.toLowerCase()} ${frame.scrollWidth}/${frame.clientWidth}`);
    }
    for (const el of card.shadowRoot.querySelectorAll('.tile .name')) {
      if (el.scrollWidth > el.clientWidth + 1) cut.push(el.textContent);
    }
  }
  return { cards: cards.length, wide, cut };
}
"""
# The middle of the treble 20 and a spot in the single 20 beside it, in millimetres
# from the bull with y up, as positions count.
TREBLE_20_SPOT = (0, 102)
SINGLE_20_SPOT = (15, 60)
# The part of the board to tap in sight, and where the board is on the screen.
BOARD_VIEW = """
(el) => {
  const [x, y, size] = el.getAttribute('viewBox').split(' ').map(Number);
  const rect = el.getBoundingClientRect();
  return { x, y, size, left: rect.left, top: rect.top, width: rect.width, height: rect.height };
}
"""
LOUPE_SHOWN = (
    f"() => !({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.loupe').hidden"
)


# What spoils the pad with its board: a key that something else covers where a
# finger taps it, and a board that draws beyond its box when zoomed in, over the keys
# and past the edge of the card.
PAD_PROBLEMS = f"""
() => {{
  const root = ({SCOREBOARD_CARDS})()[0].shadowRoot;
  const covered = [...root.querySelectorAll('.pad button')]
    .filter((key) => {{
      const rect = key.getBoundingClientRect();
      const hit = root.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return rect.width > 0 && !key.contains(hit);
    }})
    .map((key) => `covered: ${{key.textContent.trim()}}`);
  const board = root.querySelector('.pad-board');
  const overflow = board && getComputedStyle(board).overflow;
  return [...covered, ...(board && !['hidden', 'clip'].includes(overflow) ? [`board drawn beyond its box: ${{overflow}}`] : [])];
}}
"""


def board_point(view: dict, spot: tuple[float, float]) -> tuple[float, float]:
    """Where a spot of the board in millimetres is on the screen, zoomed in or not."""
    scale = min(view["width"], view["height"]) / view["size"]
    middle_x = view["x"] + view["size"] / 2
    middle_y = view["y"] + view["size"] / 2
    return (
        view["left"] + view["width"] / 2 + (spot[0] - middle_x) * scale,
        view["top"] + view["height"] / 2 + (-spot[1] - middle_y) * scale,
    )


def fingers(page: Page, *moves: list[tuple[float, float]]) -> bool:
    """Fingers on the touch screen, each from its first point to its last, as the
    browser gets them from a real screen; whether the loupe showed on the way. They
    rest on their last points before they let go, as a finger does that reads the
    loupe: one that leaves still moving flings, and the next tap only stops the fling."""
    session = page.context.new_cdp_session(page)

    def send(kind: str, points: list[tuple[float, float]]) -> None:
        session.send(
            "Input.dispatchTouchEvent",
            {
                "type": kind,
                "touchPoints": [
                    {"x": x, "y": y, "id": index} for index, (x, y) in enumerate(points)
                ],
            },
        )

    send("touchStart", [move[0] for move in moves])
    send("touchMove", [move[-1] for move in moves])
    shown = bool(page.evaluate(LOUPE_SHOWN))
    page.wait_for_timeout(120)
    send("touchEnd", [])
    session.detach()
    return shown


def touch_screens(browser: Browser) -> None:
    """The scoreboard, the new game screen, the keypad and the training card on phones
    and a touch monitor, driven by taps, in German with its long words."""
    for device, size, insets in TOUCH_SCREENS:
        touch_screen(browser, device, size, insets)


def touch_screen(
    browser: Browser, device: str, size: dict[str, int], insets: tuple[int, int]
) -> None:
    phone = size["width"] < 1000
    context = browser.new_context(
        locale="de-DE",
        viewport=size,
        device_scale_factor=3 if phone else 1,
        is_mobile=phone,
        has_touch=True,
    )
    page = context.new_page()
    page.add_init_script(CAPTURE_ERRORS)
    page.add_init_script(phone_style(*insets))
    card = "autodarts-scoreboard-card"

    def fits(screen: str, targets: bool = True, high: bool = True) -> None:
        """Nothing wider than the screen, every control big enough for a finger, and a
        scoreboard one screen high above the home indicator; the new game screen
        scrolls instead."""
        layout = page.evaluate(TABLET_LAYOUT)
        check(
            layout["width"] <= layout["room"] + 1
            and layout["right"] <= layout["viewport"] + 1,
            f"{device}: {screen} is wider than the screen: {layout}",
        )
        check(not targets or layout["targets"], f"{device}: {screen} has no targets")
        check(
            not layout["small"],
            f"{device}: {screen}: targets below 44 px {layout['small']}",
        )
        fit = page.evaluate(PHONE_FIT)
        check(
            not high
            or (fit["bottom"] <= fit["free"] + 1 and fit["height"] <= fit["room"] + 1),
            f"{device}: {screen} runs below the screen: {fit}",
        )

    def start_bar(screen: str, buttons: list[str]) -> None:
        bar = page.evaluate(START_BAR)
        check(bar["sticky"] == "sticky", f"{device}: {screen}: the bar scrolls away")
        # The card's colour over the page's: nothing shines through a see-through card.
        check(
            "gradient" in bar["layers"] and not bar["base"].startswith("rgba("),
            f"{device}: {screen}: the bar shows what scrolls beneath it: {bar}",
        )
        check(
            max(bar["edges"]) <= 1,
            f"{device}: {screen}: the bar does not span the card: {bar}",
        )
        check(
            bar["start"][0] >= 0 and bar["start"][1] <= bar["free"] + 1,
            f"{device}: {screen}: the start is out of reach: {bar}",
        )
        check(
            bar["buttons"] == buttons, f"{device}: {screen}: buttons {bar['buttons']}"
        )

    def wide(view: str) -> None:
        state = page.evaluate(PHONE_WIDTH)
        check(state["cards"], f"{device}: no cards in the {view} view")
        check(
            not state["wide"], f"{device}: {view} view wider than the screen: {state}"
        )
        check(not state["cut"], f"{device}: {view} view cuts names short: {state}")

    def wait_players(count: int) -> None:
        page.wait_for_function(
            f"() => ({SCOREBOARD_STATE})().players.length === {count}", timeout=15000
        )

    def game_off() -> None:
        page.evaluate(
            CALL_SERVICE,
            ["select", "select_option", "practice_game", {"option": "off"}],
        )
        control({"status": "Throw", "event": "Takeout finished", "throws": []})

    page.goto(f"{HA}/autodarts-auto/scoreboard")
    page.locator(f"{card} .main").wait_for(timeout=30000)
    game_off()
    page.locator(f"{card} .lobby-cta").wait_for(timeout=15000)
    fits("the scoreboard between games")

    # The new game screen with the detection stopped, as at the board after a break:
    # its hint and the start stay above the home indicator on a bar of their own, and
    # every game can be tapped, none hides beneath the bar.
    control({"running": False, "status": "Stopped", "event": "Stopped"})
    page.locator(f"{card} .lobby-cta").tap()
    page.locator(f"{card} .lobby").wait_for(timeout=15000)
    page.locator(f"{card} .lobby-hint").first.wait_for(timeout=15000)
    fits("the new game screen", high=False)
    start_bar("the new game screen", ["close", "start"])
    games = page.locator(f"{card} .lobby .game")
    for index in range(games.count()):
        games.nth(index).tap()
        pressed = games.nth(index).get_attribute("aria-pressed")
        check(pressed == "true", f"{device}: game {index} not chosen by a tap")
    players = page.locator(f"{card} .lobby-player [data-lobby='remove']")
    while players.count():
        players.first.tap()
    for name in ("Alex", "Sam"):
        page.locator(f"{card} .suggestion", has_text=name).tap()
    page.locator(f"{card} .lobby .game", has_text="301").first.tap()
    page.locator(f"{card} .lobby .start").tap()
    wait_players(2)
    control({"event": "Throw detected", "throws": [T20]})
    fits("a match of two", targets=False)

    # A running game adds its end to the bar; two taps end it.
    page.locator(f"{card} .lobby-toggle").tap()
    page.locator(f"{card} .lobby").wait_for(timeout=15000)
    start_bar("the new game screen during a game", ["end", "close", "start"])
    end = page.locator(f"{card} [data-lobby='end']")
    end.tap()
    end.tap()
    page.wait_for_function(
        f"() => !({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector(\"[data-lobby='end']\")",
        timeout=15000,
    )
    page.locator(f"{card} [data-lobby='close']").tap()
    control({"status": "Throw", "event": "Takeout finished", "throws": []})

    # Four players with long names, in X01 and in Cricket.
    for game in ("501", "cricket"):
        page.evaluate(
            CALL_ACTION, ["start_game", {"game": game, "players": LONG_NAMES}]
        )
        if game == "501":
            wait_players(4)
        else:
            page.locator(f"{card} .cricket").wait_for(timeout=15000)
        control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
        fits(f"four players with long names in {game}", targets=False)
        control({"status": "Throw", "event": "Takeout finished", "throws": []})
    game_off()

    # The keypad and its board, which opens whole for darts entered by hand: two
    # fingers zoom in, and a finger slides with the loupe from the single 20 to the
    # treble 20 and enters it where it lets go. The keypad is a choice of the card; the
    # demo's keypad view has it.
    page.goto(f"{HA}/autodarts-demo/keypad")
    page.locator(f"{card} .main").wait_for(timeout=30000)
    page.evaluate(CALL_SERVICE, ["switch", "turn_on", "practice_manual_entry"])
    page.evaluate(CALL_ACTION, ["start_game", {"game": "301", "players": ["Alex"]}])
    page.locator(f"{card} .pad").wait_for(timeout=15000)
    fits("the keypad")
    page.locator(f"{card} [data-pad='board']").tap()
    board = page.locator(f"{card} .pad-board")
    board.wait_for(timeout=15000)
    fits("the board to tap")
    view = board.evaluate(BOARD_VIEW)
    check(view["size"] == 460, f"{device}: the keypad's board opens zoomed in: {view}")
    middle = board_point(view, (0, 0))
    fingers(
        page,
        [(middle[0] - 20, middle[1]), (middle[0] - 40, middle[1])],
        [(middle[0] + 20, middle[1]), (middle[0] + 40, middle[1])],
    )
    zoomed = board.evaluate(BOARD_VIEW)
    check(zoomed["size"] < 300, f"{device}: two fingers did not zoom in: {zoomed}")
    problems = page.evaluate(PAD_PROBLEMS)
    check(not problems, f"{device}: the board zoomed in spoils the pad: {problems}")
    shown = fingers(
        page, [board_point(zoomed, SINGLE_20_SPOT), board_point(zoomed, TREBLE_20_SPOT)]
    )
    check(shown, f"{device}: no loupe while aiming")
    page.wait_for_function(
        f"() => ({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.sum .value')?.textContent === '60'",
        timeout=15000,
    )
    page.evaluate(CALL_SERVICE, ["switch", "turn_off", "practice_manual_entry"])
    game_off()

    # A dart the board read wrong: on a small screen its board opens zoomed in on where the
    # board saw it, and a tap on the treble 20 corrects it.
    page.evaluate(CALL_ACTION, ["start_game", {"game": "301", "players": ["Alex"]}])
    control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
    # The game has booked both darts before a finger picks the second one.
    page.wait_for_function(
        f"""() => {{
          const state = ({SCOREBOARD_STATE})();
          return state.darts.join() === 'T20,S20,–' && state.players[0]?.[1] === '221';
        }}""",
        timeout=15000,
    )
    page.locator(f"{card} [data-dart='2']").tap()
    board.wait_for(timeout=15000)
    view = board.evaluate(BOARD_VIEW)
    # A small screen: a narrow card, or a low screen as a phone on its side.
    small = min(size["width"], size["height"]) < 600
    check(
        (view["size"] < 460) == small,
        f"{device}: the board of a correction opens {view['size']} mm wide",
    )
    problems = page.evaluate(PAD_PROBLEMS)
    check(
        not problems, f"{device}: the board of a correction spoils the pad: {problems}"
    )
    x, y = board_point(view, TREBLE_20_SPOT)
    page.touchscreen.tap(x, y)
    page.wait_for_function(
        f"() => ({SCOREBOARD_STATE})().darts[1] === 'T20'", timeout=15000
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    game_off()

    # The other views: every card as wide as the screen, the tiles' names whole.
    for view in ("live", "training", "players"):
        page.goto(f"{HA}/autodarts-auto/{view}")
        page.wait_for_function(
            "() => document.querySelector('home-assistant')?.hass",
            timeout=30000,
        )
        page.wait_for_timeout(1500)
        wide(view)
    errors = page_errors(page, [])
    check(not errors, f"{device}: console problems: {errors}")
    context.close()


# Every size a dashboard is opened on, in both orientations: its viewport, the safe
# areas at the top and the bottom, and whether it is a touch screen.
SCREENS = (
    ("small phone", {"width": 360, "height": 640}, (0, 0), True),
    ("small phone on its side", {"width": 640, "height": 360}, (0, 0), True),
    ("iPhone", {"width": 393, "height": 852}, (59, 34), True),
    ("iPhone on its side", {"width": 852, "height": 393}, (0, 21), True),
    ("tablet", {"width": 768, "height": 1024}, (24, 20), True),
    ("tablet on its side", {"width": 1024, "height": 768}, (24, 20), True),
    ("laptop", {"width": 1280, "height": 800}, (0, 0), False),
    # Many players have a 24 or 27 inch touch screen beside the board.
    ("24-inch touch monitor", {"width": 1920, "height": 1080}, (0, 0), True),
    ("27-inch touch monitor", {"width": 2560, "height": 1440}, (0, 0), True),
)
# The views of the generated dashboard; those of the demo dashboard are read from it.
AUTO_VIEWS = ("live", "scoreboard", "training", "players", "board")
DEMO_VIEWS = """
async () => {
  const hass = document.querySelector('home-assistant').hass;
  const config = await hass.callWS({ type: 'lovelace/config', url_path: 'autodarts-demo' });
  return config.views.map((view) => view.path);
}
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
# What a player would see as broken on this screen, card by card: a card wider than the
# screen, text cut short or cut off, text on top of other text or running over the edge
# of its tile or button, text too small to read, a control too small for a finger on a
# touch screen, and a full-height scoreboard running below the screen.
# Text beneath a bar that stays in place is hidden by it and does not count as covered.
LAYOUT_PROBLEMS = """
(touch) => {
  const cards = [];
  (function collect(root) {
    root.querySelectorAll('*').forEach((el) => {
      if (el.tagName.startsWith('AUTODARTS-') && !el.tagName.endsWith('-EDITOR') && el.shadowRoot) cards.push(el);
      if (el.shadowRoot) collect(el.shadowRoot);
    });
  })(document);
  const problems = [];
  const inset = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue('--safe-area-inset-bottom')
  ) || 0;
  // Shown on the screen: not hidden, and not only for screen readers.
  const shown = (el, frame) => {
    for (let e = el; e && e !== frame.parentNode; e = e.parentElement) {
      if (e.hidden) return false;
      const style = getComputedStyle(e);
      if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
      if (style.clipPath === 'inset(50%)') return false;
    }
    return true;
  };
  const within = (a, b) => ({
    left: Math.max(a.left, b.left), top: Math.max(a.top, b.top),
    right: Math.min(a.right, b.right), bottom: Math.min(a.bottom, b.bottom),
  });
  const area = (r) => Math.max(0, r.right - r.left) * Math.max(0, r.bottom - r.top);
  const words = (el) => el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 40);
  // The tile or button a text sits in: the nearest element with a frame or a fill that
  // shows; a button plain as text has no edge to run over.
  const boxOf = (el, frame) => {
    for (let e = el; e && e !== frame; e = e.parentElement) {
      const style = getComputedStyle(e);
      const fill = style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent';
      const border = parseFloat(style.borderLeftWidth) > 0 && style.borderLeftStyle !== 'none'
        && !style.borderLeftColor.endsWith(', 0)') && style.borderLeftColor !== 'transparent';
      if (border || fill) return e;
    }
    return null;
  };
  for (const card of cards) {
    const root = card.shadowRoot;
    const frame = root.querySelector('ha-card');
    if (!frame) continue;
    const box = card.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) continue;
    const label = card.tagName.toLowerCase();
    if (frame.scrollWidth > frame.clientWidth + 1 || box.right > innerWidth + 1 || box.left < -1) {
      problems.push(`${label} is wider than the screen (${frame.scrollWidth}/${frame.clientWidth}, right ${Math.round(box.right)} of ${innerWidth})`);
    }
    // The part of a text the overflow of its element and their ancestors leaves visible,
    // and whether one cuts it off without letting it scroll.
    // Glyph boxes stand a little above and below a tight line; only a text cut at its
    // side or a line lost as a whole counts.
    const clip = (el, rect) => {
      let visible = rect;
      let cut = false;
      for (let e = el; e && e !== frame.parentNode; e = e.parentElement) {
        const style = getComputedStyle(e);
        if (style.overflowX === 'visible' && style.overflowY === 'visible') continue;
        const next = within(visible, e.getBoundingClientRect());
        const scrolls = /auto|scroll/.test(style.overflowX + style.overflowY);
        const narrower = next.right - next.left < visible.right - visible.left - 2;
        const lower = next.bottom - next.top < (visible.bottom - visible.top) * 0.6;
        if (!scrolls && (narrower || lower)) cut = true;
        visible = next;
      }
      return { visible, cut };
    };
    const texts = [];
    const range = document.createRange();
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const el = node.parentElement;
      if (!el || !node.textContent.trim() || el.closest('svg, style, script')) continue;
      if (!shown(el, frame)) continue;
      const style = getComputedStyle(el);
      // Text only for screen readers.
      if (style.clipPath === 'inset(50%)' || style.clip === 'rect(0px, 0px, 0px, 0px)') continue;
      if (parseFloat(style.fontSize) < 11) {
        problems.push(`${label}: "${words(el)}" is ${style.fontSize}, too small to read`);
      }
      const tile = boxOf(el, frame)?.getBoundingClientRect();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width < 2 || rect.height < 2) continue;
        const { visible, cut } = clip(el, rect);
        if (cut && style.textOverflow !== 'ellipsis') problems.push(`${label}: "${words(el)}" is cut off`);
        if (tile && (rect.left < tile.left + 1 || rect.right > tile.right - 1)) {
          problems.push(`${label}: "${words(el)}" runs over the edge of its box`);
        }
        if (area(visible) < 4) continue;
        // The glyphs fill the middle of a text's box; large numbers have a box much
        // higher than what they show.
        const inner = (visible.bottom - visible.top) * 0.2;
        const core = { ...visible, top: visible.top + inner, bottom: visible.bottom - inner };
        texts.push({ el, rect: core, fixed: Boolean(el.closest('.lobby-actions')) });
      }
    }
    for (const el of root.querySelectorAll('*')) {
      if (!shown(el, frame)) continue;
      const style = getComputedStyle(el);
      if (style.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1 && el.textContent.trim()) {
        problems.push(`${label}: "${words(el)}" is cut short`);
      }
    }
    for (let i = 0; i < texts.length; i += 1) {
      for (let j = i + 1; j < texts.length; j += 1) {
        const a = texts[i];
        const b = texts[j];
        if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el) || a.fixed !== b.fixed) continue;
        const both = within(a.rect, b.rect);
        if (both.right - both.left > 3 && both.bottom - both.top > 3) {
          problems.push(`${label}: "${words(a.el)}" lies on "${words(b.el)}"`);
        }
      }
    }
    if (touch) {
      for (const el of root.querySelectorAll('button, input, select, textarea, a[href], [role="button"], [role="tab"], [tabindex="0"]')) {
        if (!shown(el, frame) || el.closest('svg') || el.type === 'hidden') continue;
        const rect = el.getBoundingClientRect();
        // Controls only a keyboard reaches until they have the focus.
        if (rect.width <= 2 || rect.height <= 2 || getComputedStyle(el).clipPath === 'inset(50%)') continue;
        if (rect.height < 40 || rect.width < 40) {
          problems.push(`${label}: "${words(el) || el.getAttribute('aria-label') || el.tagName.toLowerCase()}" is ${Math.round(rect.width)}x${Math.round(rect.height)} for a finger`);
        }
      }
    }
    const board = root.querySelector('.scoreboard.full:not(.choosing)');
    if (board && box.bottom > innerHeight - inset + 1) {
      problems.push(`${label} runs ${Math.round(box.bottom - innerHeight + inset)} px below the screen`);
    }
  }
  return { cards: cards.length, problems: [...new Set(problems)] };
}
"""
# Screenshots of every screen for a look by eye, when BROWSER_SCREENSHOTS is set.
SCREENSHOTS = os.environ.get("BROWSER_SCREENSHOTS", "")


def screens(browser: Browser) -> None:
    """Every view of both dashboards and the scoreboard's screens on every size, in
    German with its long words: nothing broken, whatever the screen and its side."""
    found: list[str] = []
    # A choice of screens for a local run, comma-separated, such as "iPhone".
    chosen = {name.strip() for name in os.environ.get("BROWSER_SCREENS", "").split(",")}
    for screen, size, insets, touch in SCREENS:
        if chosen - {""} and screen not in chosen:
            continue
        problems = screen_views(browser, screen, size, insets, touch)
        print(f"  {screen}: {len(problems)} problems", flush=True)
        found += problems
    check(not found, "Layout problems:\n" + "\n".join(found))


def screen_views(
    browser: Browser,
    screen: str,
    size: dict[str, int],
    insets: tuple[int, int],
    touch: bool,
) -> list[str]:
    context = browser.new_context(
        locale="de-DE",
        viewport=size,
        device_scale_factor=2,
        is_mobile=touch and size["width"] < 1000,
        has_touch=touch,
    )
    page = context.new_page()
    page.add_init_script(CAPTURE_ERRORS)
    page.add_init_script(phone_style(*insets))
    found: list[str] = []

    def look(name: str) -> None:
        page.wait_for_function(CARDS_DRAWN, timeout=30000)
        # Positions, profiles and trends arrive over the websocket after the first draw.
        page.wait_for_timeout(800)
        state = page.evaluate(LAYOUT_PROBLEMS, touch)
        found.extend(f"{screen} · {name}: {problem}" for problem in state["problems"])
        if SCREENSHOTS and ARTIFACTS:
            folder = Path(ARTIFACTS) / "screens" / screen.replace(" ", "-")
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / f"{name}.png"), full_page=True)

    page.goto(f"{HA}/autodarts-auto/live")
    page.wait_for_function(CARDS_DRAWN, timeout=30000)
    views = [f"autodarts-auto/{view}" for view in AUTO_VIEWS]
    views += [f"autodarts-demo/{view}" for view in page.evaluate(DEMO_VIEWS)]
    for view in views:
        page.goto(f"{HA}/{view}")
        look(view.replace("/", "-"))

    # The scoreboard's own screens: the new game screen, four players with long names
    # and the keypad, its board to tap, and Cricket for four.
    page.goto(f"{HA}/autodarts-auto/scoreboard")
    page.wait_for_function(CARDS_DRAWN, timeout=30000)
    root = f"({SCOREBOARD_CARDS})()[0].shadowRoot"
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.wait_for_function(f"() => {root}.querySelector('.lobby-cta')", timeout=15000)
    page.evaluate(f"() => {root}.querySelector('.lobby-cta').click()")
    page.wait_for_function(f"() => {root}.querySelector('.lobby')", timeout=15000)
    look("scoreboard-new-game")
    page.evaluate(f"() => {root}.querySelector(\"[data-lobby='close']\").click()")
    # The keypad is a choice of the card; the demo's keypad view has it.
    page.goto(f"{HA}/autodarts-demo/keypad")
    page.wait_for_function(CARDS_DRAWN, timeout=30000)
    page.evaluate(CALL_SERVICE, ["switch", "turn_on", "practice_manual_entry"])
    page.evaluate(CALL_ACTION, ["start_game", {"game": "501", "players": LONG_NAMES}])
    page.wait_for_function(f"() => {root}.querySelector('.pad')", timeout=15000)
    control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
    look("scoreboard-keypad-four-players")
    page.evaluate(f"() => {root}.querySelector(\"[data-pad='board']\").click()")
    page.wait_for_function(f"() => {root}.querySelector('.pad-board')", timeout=15000)
    look("scoreboard-board-to-tap")
    found.extend(
        f"{screen} · scoreboard-board-to-tap: {problem}"
        for problem in page.evaluate(PAD_PROBLEMS)
    )
    page.evaluate(CALL_SERVICE, ["switch", "turn_off", "practice_manual_entry"])
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    # A dart the board read wrong and the board to correct it: zoomed in on where the
    # board saw it on a small screen, whole on a large one.
    page.evaluate(CALL_ACTION, ["start_game", {"game": "301", "players": ["Alex"]}])
    control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
    page.wait_for_function(
        f"() => ({SCOREBOARD_STATE})().darts.join() === 'T20,S20,–'", timeout=15000
    )
    page.evaluate(f"() => {root}.querySelector(\"[data-dart='2']\").click()")
    page.wait_for_function(f"() => {root}.querySelector('.pad-board')", timeout=15000)
    look("scoreboard-correction-board")
    found.extend(
        f"{screen} · scoreboard-correction-board: {problem}"
        for problem in page.evaluate(PAD_PROBLEMS)
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    page.evaluate(
        CALL_ACTION, ["start_game", {"game": "cricket", "players": LONG_NAMES}]
    )
    page.wait_for_function(f"() => {root}.querySelector('.cricket')", timeout=15000)
    control({"event": "Throw detected", "throws": [T20, SINGLE_20]})
    look("scoreboard-cricket-four-players")
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": "off"}]
    )
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    errors = page_errors(page, [])
    found.extend(f"{screen}: console problem {error}" for error in errors)
    context.close()
    return found


def caller(browser: Browser) -> None:
    """The caller stays silent until a tap switches it on."""
    page, problems = open_view(
        browser, "scoreboard", SCOREBOARD_CARDS, ".caller-toggle"
    )
    toggle = f"({SCOREBOARD_CARDS})()[0].shadowRoot.querySelector('.caller-toggle')"
    state = page.evaluate(f"() => {toggle}.getAttribute('aria-pressed')")
    check(state == "false", f"Caller before the tap: {state}")
    page.evaluate(f"() => {toggle}.click()")
    page.wait_for_function(
        f"() => {toggle}.getAttribute('aria-pressed') === 'true'", timeout=5000
    )
    # The label stays "Caller"; the pressed state tells that it is on.
    text = page.evaluate(f"() => {toggle}.textContent")
    check(text == "🔊Caller", f"Caller after the tap: {text}")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def strategy(browser: Browser) -> None:
    """The generated dashboard shows each card in its view."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 900})
    page.add_init_script(CAPTURE_ERRORS)
    for view, cards, ready in (
        ("live", CARDS, ".board svg"),
        ("scoreboard", SCOREBOARD_CARDS, ".main"),
        ("training", TRAINING_CARDS, ".heat-layer"),
        ("players", PLAYERS_CARDS, ".players-card"),
        ("players", LEADERBOARD_CARDS, ".leaderboard"),
        ("board", STATUS_CARDS, ".camera"),
    ):
        page.goto(f"{HA}/autodarts-auto/{view}")
        page.wait_for_function(
            f"() => ({cards})().some((card) => card.shadowRoot?.querySelector('{ready}'))",
            timeout=30000,
        )
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


def players_export(browser: Browser) -> None:
    """The export button of the players card downloads every table as a ZIP file."""
    page, problems = open_view(browser, "players", PLAYERS_CARDS, ".export")
    with page.expect_download(timeout=30000) as download:
        page.evaluate(
            f"() => ({PLAYERS_CARDS})()[0].shadowRoot.querySelector('.export').click()"
        )
    name = download.value.suggested_filename
    check(
        name.startswith("autodarts-all-") and name.endswith(".zip"),
        f"Unexpected export download: {name}",
    )
    with zipfile.ZipFile(download.value.path()) as archive:
        tables = sorted(archive.namelist())
    check(
        tables == ["matches.csv", "profiles.csv", "sessions.csv"],
        f"Unexpected export tables: {tables}",
    )
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def editor(
    browser: Browser,
    view: str = "board",
    cards: str = CARDS,
    ready: str = ".board svg",
    rows: int = 6,
) -> None:
    """Home Assistant builds the card's form from getConfigForm."""
    page, problems = open_view(browser, view, cards, ready)
    page.goto(f"{HA}/autodarts-demo/{view}?edit=1")
    page.wait_for_function(
        f"() => ({cards})().some((card) => card.shadowRoot?.querySelector('{ready}'))",
        timeout=30000,
    )
    page.evaluate(
        f"() => ({cards})()[0].dispatchEvent(new CustomEvent('ll-edit-card',"
        " {bubbles: true, composed: true, detail: {path: [0, 0, 0]}}))"
    )
    page.locator("hui-form-editor ha-form").first.wait_for(timeout=15000)
    fields = page.evaluate(f"() => ({FORM_EDITORS})()[0].schema.length")
    check(fields == rows, f"{view} form has {fields} rows")
    # The labels are the card's own, not generic names.
    label = page.evaluate(
        f"() => ({FORM_EDITORS})()[0].computeLabel({{name: 'device_id'}})"
    )
    check(label == "Board", f"{view} form labels the board {label!r}")
    page.keyboard.press("Escape")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def strategy_editor(browser: Browser) -> None:
    """Editing the generated dashboard opens the strategy's own editor."""
    page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 900})
    page.add_init_script(CAPTURE_ERRORS)
    page.goto(f"{HA}/autodarts-auto/live")
    page.wait_for_function(
        f"() => ({CARDS})().some((card) => card.shadowRoot?.querySelector('.board svg'))",
        timeout=30000,
    )
    page.evaluate(f"() => ({find('hui-root')})()[0]._enableEditMode()")
    form = page.locator("autodarts-strategy-editor > ha-form")
    form.wait_for(timeout=15000)
    fields = form.evaluate("(element) => element.schema.map((field) => field.name)")
    check(
        fields == ["device_id", "title", "scoreboard"],
        f"Strategy editor fields {fields}",
    )
    page.keyboard.press("Escape")
    errors = page_errors(page, [])
    check(not errors, f"Console problems: {errors}")
    page.close()


def light_theme(browser: Browser) -> None:
    page, problems = open_board(browser, "light")
    check(page.evaluate(RENDERED) == 1, "Card not rendered in the light theme")
    errors = page_errors(page, problems)
    check(not errors, f"Console problems: {errors}")
    page.close()


def read(path: str) -> str:
    return (INTEGRATION / path).read_text(encoding="utf-8")


def card_texts(language: str) -> dict[str, str]:
    """TEXT.<language> of the card module."""
    source = read("frontend/autodarts-card.js")
    start = source.index(f"\n  {language}: {{\n", source.index("const TEXT = {"))
    body = source[start : source.index("\n  },\n", start)]
    return {
        key: json.loads(value)
        for key, value in re.findall(r'^    (\w+):\s+(".*"),$', body, re.M)
    }


# What the page shows and what Home Assistant serves in the language of the browser.
LANGUAGE_STATE = f"""
async (language) => {{
  const hass = document.querySelector('home-assistant').hass;
  const root = ({CARDS})()[0].shadowRoot;
  const served = await hass.callWS({{
    type: 'frontend/get_translations',
    language,
    category: 'entity',
    integration: ['autodarts'],
  }});
  return {{
    language: hass.locale.language,
    label: root.querySelector('.visit-label').textContent,
    reset: root.querySelector('[data-action="reset"]').textContent,
    status: served.resources['component.autodarts.entity.sensor.local_status.name'],
  }};
}}
"""


def languages(browser: Browser) -> None:
    """A browser in Dutch, French or Spanish gets the cards and the entity texts in it."""
    for language in ("nl", "fr", "es"):
        page, problems = open_board(browser, locale=f"{language}-{language.upper()}")
        texts = card_texts(language)
        translation = json.loads(read(f"translations/{language}.json"))
        expected = {
            "language": language,
            "label": texts["visit"],
            "reset": texts["reset"],
            "status": translation["entity"]["sensor"]["local_status"]["name"],
        }
        state = page.evaluate(LANGUAGE_STATE, language)
        check(state == expected, f"{language}: {state} != {expected}")
        errors = page_errors(page, problems)
        check(not errors, f"{language}: console problems: {errors}")
        page.close()


def keep_screenshots(browser: Browser, step: str) -> None:
    """Save every page still open after a failed step for the CI artifact."""
    if not ARTIFACTS or not os.path.isdir(ARTIFACTS):
        return
    slug = "".join(char if char.isalnum() else "-" for char in step)
    pages = [page for context in browser.contexts for page in context.pages]
    for number, page in enumerate(pages, start=1):
        path = os.path.join(ARTIFACTS, f"{slug}-{number}.png")
        try:
            page.screenshot(path=path, full_page=True)
        except Exception as error:  # A screenshot must never hide the real failure.
            print(f"No screenshot of {step}: {error}", flush=True)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        steps = [
            ("fresh loads", lambda: fresh_loads(browser)),
            # The training card reads the demo session before any control changes it.
            ("training card", lambda: training(browser)),
            ("live card", lambda: visit(browser)),
            ("practice game", lambda: practice(browser)),
            ("progress and leaderboard", lambda: progress(browser)),
            ("status card", lambda: status(browser)),
            ("scoreboard", lambda: scoreboard(browser)),
            ("more games", lambda: more_games(browser)),
            ("scoreboard caller", lambda: caller(browser)),
            ("new game screen", lambda: lobby(browser)),
            ("correcting, the keypad and the bot", lambda: play_comfort(browser)),
            ("tournament", lambda: tournament(browser)),
            ("tablet screen", lambda: tablet_screen(browser)),
            ("touch screens", lambda: touch_screens(browser)),
            ("every screen size", lambda: screens(browser)),
            ("automatic dashboard", lambda: strategy(browser)),
            ("players export", lambda: players_export(browser)),
            ("live card editor", lambda: editor(browser, rows=7)),
            (
                "training card editor",
                lambda: editor(browser, "training", TRAINING_CARDS, ".heat-layer", 7),
            ),
            (
                "status card editor",
                lambda: editor(browser, "status", STATUS_CARDS, ".toggle", 4),
            ),
            (
                "doubles editor",
                lambda: editor(browser, "doubles", DOUBLES_CARDS, ".doubles-card", 4),
            ),
            (
                "players editor",
                lambda: editor(browser, "players", PLAYERS_CARDS, ".players-card", 6),
            ),
            (
                "leaderboard editor",
                lambda: editor(
                    browser, "leaderboard", LEADERBOARD_CARDS, ".leaderboard", 5
                ),
            ),
            (
                "scoreboard editor",
                lambda: editor(browser, "scoreboard", SCOREBOARD_CARDS, ".main", 9),
            ),
            ("dashboard strategy editor", lambda: strategy_editor(browser)),
            ("light theme", lambda: light_theme(browser)),
            ("languages", lambda: languages(browser)),
        ]
        unknown = {
            wanted
            for wanted in ONLY
            if not any(name.startswith(wanted) for name, _ in steps)
        }
        check(not unknown, f"BROWSER_STEPS names no step: {sorted(unknown)}")
        for name, step in steps:
            if ONLY and not any(name.startswith(wanted) for wanted in ONLY):
                continue
            # A failure then names the step, not only a timeout deep in Playwright.
            print(f"Browser step: {name}", flush=True)
            try:
                step()
            except Exception:
                keep_screenshots(browser, name)
                raise
        browser.close()
    print(
        "Browser check passed: card registration on every load, visit, highlights, "
        "controls with confirmation, last visits, practice game, match and "
        "training games, "
        "training heatmap with dart positions, badges, trends, the leaderboard, "
        "history and "
        "sessions, board status, the scoreboard with teams, Tactics, Golf and a "
        "match summary, its caller, new game screen, a corrected dart, the keypad "
        "and a match against the bot, a tournament, the screens on an 800 x 480 "
        "tablet and idle mode with reduced motion, touch screens driven by taps, every "
        "view on eight screen sizes both ways round, the generated "
        "dashboard, the players export, all seven card forms, the strategy editor, "
        "light theme and the cards and entity texts in Dutch, French and Spanish."
    )


if __name__ == "__main__":
    main()
