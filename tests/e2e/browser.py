"""Verify the dashboard cards in a real browser against the demo instance.

Runs in the Playwright container on the demo's Compose network (see browser.sh).
"""

from __future__ import annotations

import json
import os
import urllib.request
import zipfile

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

HA = "http://homeassistant:8123"
BOARD = "http://board-mock:3180"
LOADS = 5
# Board Manager generation of the demo board, passed on by browser.sh.
GENERATION = int(os.environ.get("BOARD_MANAGER", "1"))
# Writable folder for screenshots of a failed step, mounted by browser.sh.
ARTIFACTS = os.environ.get("BROWSER_ARTIFACTS", "")


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
    browser: Browser, view: str, cards: str, ready: str, scheme: str = "dark"
) -> tuple[Page, list[str]]:
    page = browser.new_page(
        locale="en-US", viewport={"width": 1280, "height": 820}, color_scheme=scheme
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


def open_board(browser: Browser, scheme: str = "dark") -> tuple[Page, list[str]]:
    return open_view(browser, "board", CARDS, ".board svg", scheme)


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
    check(fields == ["device_id", "title"], f"Strategy editor fields {fields}")
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
            ("status card", lambda: status(browser)),
            ("scoreboard", lambda: scoreboard(browser)),
            ("scoreboard caller", lambda: caller(browser)),
            ("automatic dashboard", lambda: strategy(browser)),
            ("players export", lambda: players_export(browser)),
            ("live card editor", lambda: editor(browser)),
            (
                "training card editor",
                lambda: editor(browser, "training", TRAINING_CARDS, ".heat-layer", 6),
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
                lambda: editor(browser, "players", PLAYERS_CARDS, ".players-card", 5),
            ),
            (
                "scoreboard editor",
                lambda: editor(browser, "scoreboard", SCOREBOARD_CARDS, ".main", 5),
            ),
            ("dashboard strategy editor", lambda: strategy_editor(browser)),
            ("light theme", lambda: light_theme(browser)),
        ]
        for name, step in steps:
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
        "training heatmap, "
        "history and "
        "sessions, board status, the scoreboard and its caller, "
        "the generated dashboard, the players export, all six card forms, the strategy editor and light theme."
    )


if __name__ == "__main__":
    main()
