"""Capture documentation screenshots and animations from the demo instance.

Runs in the Playwright container on the demo's Compose network (see screenshots.sh).
Every image shows the synthetic demo board, so no personal data can appear.
"""

from __future__ import annotations

import io
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

HA = "http://homeassistant:8123"
BOARD = "http://board-mock:3180"
LANGUAGE = os.environ.get("DEMO_LANGUAGE", "en")
OUTPUT = Path(os.environ.get("OUTPUT", "/repo/docs/images")) / LANGUAGE
LOCALE = {"en": "en-US", "de": "de-DE"}[LANGUAGE]

# Demo darts as the Board Manager reports them (see demo.py).
T20 = {
    "segment": {"name": "T20", "number": 20, "multiplier": 3, "bed": "Triple"},
    "coords": {"x": 0.035, "y": 0.608},
}
S5 = {
    "segment": {"name": "S5", "number": 5, "multiplier": 1, "bed": "SingleOuter"},
    "coords": {"x": -0.24, "y": 0.76},
}
BULL = {
    "segment": {"name": "Bull", "number": 25, "multiplier": 2, "bed": "Double"},
    "coords": {"x": 0.012, "y": -0.02},
}

# The numbers clockwise from the top, to place darts in the middle of a bed.
ORDER = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]


def at(name: str) -> dict:
    """A detected dart in the middle of the named bed, like S17 or T19."""
    number, multiplier = int(name[1:]), "SDT".index(name[0]) + 1
    radius = {1: 0.79, 2: 0.976, 3: 0.606}[multiplier]
    angle = math.radians(90 - ORDER.index(number) * 18)
    return {
        "segment": {"name": name, "number": number, "multiplier": multiplier},
        "coords": {
            "x": round(radius * math.cos(angle), 3),
            "y": round(radius * math.sin(angle), 3),
        },
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

FIND_CARDS = """
() => {
  const cards = [];
  (function collect(root) {
    root.querySelectorAll('autodarts-card').forEach((card) => cards.push(card));
    root.querySelectorAll('*').forEach((el) => el.shadowRoot && collect(el.shadowRoot));
  })(document);
  return cards;
}
"""

# Pauses the card animations at a given time, so blinking beds render deterministically.
SEEK = (
    "(time) => { for (const card of ("
    + FIND_CARDS
    + ")()) { for (const animation of card.shadowRoot.getAnimations()) {"
    " animation.pause(); animation.currentTime = time; } } }"
)
EDIT_CARD = (
    "() => { const [card] = ("
    + FIND_CARDS
    + ")(); card.dispatchEvent(new CustomEvent('ll-edit-card', {bubbles: true,"
    " composed: true, detail: {path: [0, 0, 0]}})); }"
)


def control(changes: dict) -> None:
    request = urllib.request.Request(
        f"{BOARD}/control/state",
        data=json.dumps(changes).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=10).read()


def wait_for_score(page: Page, score: str) -> None:
    page.wait_for_function(
        f"() => ({FIND_CARDS})().some((c) => c.shadowRoot.querySelector('.score')?.textContent === '{score}')",
        timeout=15000,
    )


def open_dashboard(page: Page, view: str) -> None:
    page.goto(f"{HA}/autodarts-demo/{view}")
    page.wait_for_function(
        f"() => ({FIND_CARDS})().some((c) => c.shadowRoot.querySelector('.board svg'))",
        timeout=60000,
    )
    page.wait_for_timeout(1200)


def peak(page: Page) -> None:
    # The end of a blink cycle shows the highlight at full strength.
    page.evaluate(SEEK, 800)


def card_shot(
    page: Page, name: str, index: int = 0, tag: str = "autodarts-card"
) -> None:
    card = page.locator(tag).nth(index)
    card.screenshot(path=str(OUTPUT / f"{name}.png"), animations="allow")
    print(f"saved {OUTPUT / name}.png")


def page_shot(page: Page, name: str) -> None:
    page.screenshot(path=str(OUTPUT / f"{name}.png"))
    print(f"saved {OUTPUT / name}.png")


class Recorder:
    """Frames of one element and how long each shows, for an animated WebP."""

    def __init__(self, page: Page, tag: str = "autodarts-card") -> None:
        self.page = page
        self.element = page.locator(tag).first
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []

    def shot(self, duration: int) -> None:
        image = self.element.screenshot(animations="allow")
        self.frames.append(Image.open(io.BytesIO(image)))
        self.durations.append(duration)

    def blink(self, count: int = 1, step: int = 100, hold: int | None = None) -> None:
        """The blinking beds of the live card, frame by frame; the last frame holds."""
        for index in range(count):
            self.page.evaluate(SEEK, index * step)
            self.shot(hold if hold and index == count - 1 else step)

    def save(self, name: str, width: int = 760) -> None:
        # Animated WebP keeps the colours of every frame at a fraction of a GIF's size.
        resized = [
            frame.convert("RGB").resize(
                (width, round(frame.height * width / frame.width)),
                Image.Resampling.LANCZOS,
            )
            for frame in self.frames
        ]
        target = OUTPUT / f"{name}.webp"
        resized[0].save(
            target,
            save_all=True,
            append_images=resized[1:],
            duration=self.durations,
            loop=0,
            quality=85,
            method=6,
        )
        size = target.stat().st_size // 1024
        print(f"saved {target} ({size} KiB, {len(self.frames)} frames)")


def visit_animation(page: Page) -> None:
    """Darts landing one by one, then the takeout, as an animation."""
    recorder = Recorder(page)
    capture = recorder.blink

    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    wait_for_score(page, "0")
    capture(1, hold=900)
    for darts, score in (([T20], "60"), ([T20, S5], "65"), ([T20, S5, BULL], "115")):
        control({"event": "Throw detected", "throws": darts})
        wait_for_score(page, score)
        capture(16)
    capture(1, hold=900)
    control({"status": "Takeout in progress", "event": "Takeout started"})
    page.wait_for_timeout(700)
    capture(8)
    control({"status": "Throw", "event": "Takeout finished", "throws": []})
    wait_for_score(page, "0")
    capture(1, hold=1200)
    recorder.save("card-visit")
    # Restore the demo visit for the remaining screenshots.
    for darts in ([T20], [T20, S5], [T20, S5, BULL]):
        control({"event": "Throw detected", "throws": darts})
    wait_for_score(page, "115")


# Animations of the games -----------------------------------------------------------


def game(page: Page, option: str) -> None:
    page.evaluate(
        CALL_SERVICE, ["select", "select_option", "practice_game", {"option": option}]
    )


def players(page: Page, count: int) -> None:
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": count}]
    )


def pull_darts() -> None:
    control({"status": "Takeout in progress", "event": "Takeout started"})
    control({"status": "Throw", "event": "Takeout finished", "throws": []})


def wait_card(
    page: Page, condition: str, tag: str = "autodarts-card", timeout: int = 15000
) -> None:
    """Wait until the card's shadow root `r` meets a JavaScript condition."""
    page.wait_for_function(
        f"() => ({find(tag)})().some((c) => {{ const r = c.shadowRoot; return {condition}; }})",
        timeout=timeout,
    )


def big(value: str) -> str:
    return f"r.querySelector('.practice-remaining')?.textContent === '{value}'"


def visit(page: Page, names: list[str]) -> None:
    """Throw a whole visit without recording it."""
    darts = [at(name) for name in names]
    for count in range(1, len(darts) + 1):
        control({"event": "Throw detected", "throws": darts[:count]})
        page.wait_for_timeout(250)
    pull_darts()
    page.wait_for_timeout(600)


def checkout_animation(page: Page) -> None:
    """A 141 checkout: the route and the outlined bed follow every dart."""
    pull_darts()
    players(page, 1)
    game(page, "501")
    wait_card(page, big("501"))
    for _ in range(2):
        visit(page, ["T20", "T20", "T20"])
    wait_card(page, big("141"))
    recorder = Recorder(page)
    recorder.blink(1, hold=1400)
    thrown: list[dict] = []
    for name, remaining in (("T20", "81"), ("T19", "24"), ("D12", "0")):
        thrown.append(at(name))
        control({"event": "Throw detected", "throws": thrown})
        wait_card(page, big(remaining))
        recorder.blink(10, hold=1100)
    recorder.blink(1, hold=1400)
    pull_darts()
    wait_card(page, big("501"))
    recorder.blink(1, hold=1400)
    recorder.save("practice-checkout")


def cricket_animation(page: Page) -> None:
    """Two players close numbers and score on the chalkboard."""
    pull_darts()
    page.evaluate(SET_NAME, [0, "Alex"])
    page.evaluate(SET_NAME, [1, "Sam"])
    players(page, 2)
    game(page, "cricket")
    cell = (
        "r.querySelectorAll('.practice .cricket tbody tr')[{row}]"
        "?.children[{column}]?.textContent === '{mark}'"
    )
    wait_card(page, "!!r.querySelector('.practice .cricket')")
    recorder = Recorder(page)
    recorder.blink(1, hold=1200)
    # Each dart with what the card shows once it counted.
    visits = [
        [
            ("T20", cell.format(row=0, column=1, mark="Ⓧ")),
            ("T20", big("60")),
            ("S19", cell.format(row=1, column=1, mark="/")),
        ],
        [
            ("T19", cell.format(row=1, column=2, mark="Ⓧ")),
            ("T19", big("57")),
            ("D18", cell.format(row=2, column=2, mark="X")),
        ],
    ]
    for darts in visits:
        thrown: list[dict] = []
        for name, shown in darts:
            thrown.append(at(name))
            control({"event": "Throw detected", "throws": thrown})
            wait_card(page, shown)
            recorder.blink(6, step=120, hold=900)
        pull_darts()
        page.wait_for_timeout(900)
        recorder.blink(1, hold=1300)
    recorder.save("cricket")
    players(page, 1)


def training_game_animation(page: Page) -> None:
    """Around the Clock: every hit moves the target and its outlined beds."""
    pull_darts()
    game(page, "around_the_clock")
    wait_card(page, big("1"))
    recorder = Recorder(page)
    recorder.blink(1, hold=1200)
    for darts in (
        (("S1", "2"), ("S17", "2"), ("D2", "3")),
        (("T3", "4"), ("S4", "5"), ("S5", "6")),
    ):
        thrown: list[dict] = []
        for name, target in darts:
            thrown.append(at(name))
            control({"event": "Throw detected", "throws": thrown})
            wait_card(
                page,
                big(target)
                + " && r.querySelectorAll('.slot:not(.empty)').length === "
                + str(len(thrown)),
            )
            recorder.blink(6, step=120, hold=800)
        pull_darts()
        page.wait_for_timeout(600)
        recorder.blink(1, hold=900)
    recorder.save("training-game")
    game(page, "off")


def scoreboard_animation(page: Page) -> None:
    """A 501 match on the scoreboard: turns pass, and Alex checks out 141."""
    pull_darts()
    page.evaluate(SET_NAME, [0, "Alex"])
    page.evaluate(SET_NAME, [1, "Sam"])
    players(page, 2)
    # One leg decides the match, so the checkout brings the winner banner.
    for key in ("practice_legs", "practice_sets"):
        page.evaluate(CALL_SERVICE, ["number", "set_value", key, {"value": 1}])
    game(page, "501")
    board = page.context.new_page()
    board.set_viewport_size({"width": 1280, "height": 800})
    board.goto(f"{HA}/autodarts-auto/scoreboard")
    tag = "autodarts-scoreboard-card"
    # The first load of the dashboard takes a while.
    wait_card(board, "r.querySelectorAll('.player').length === 2", tag, 60000)
    board.wait_for_timeout(1500)
    recorder = Recorder(board, tag)
    recorder.shot(1400)
    active = "r.querySelector('.player.active .name')?.textContent === '{name}'"
    visits = [
        ("Alex", ["T20", "T20", "T20"], "Sam"),
        ("Sam", ["T20", "S5", "T20"], "Alex"),
        ("Alex", ["T20", "T20", "T20"], "Sam"),
        ("Sam", ["S20", "T20", "S20"], "Alex"),
    ]
    for _, names, following in visits:
        darts = [at(name) for name in names]
        for count in range(1, 4):
            control({"event": "Throw detected", "throws": darts[:count]})
            board.wait_for_timeout(350)
        wait_card(
            board, "r.querySelectorAll('.visit .dart:not(.empty)').length === 3", tag
        )
        recorder.shot(900)
        pull_darts()
        wait_card(board, active.format(name=following), tag)
        board.wait_for_timeout(300)
        recorder.shot(1000)
    thrown: list[dict] = []
    for name in ("T20", "T19", "D12"):
        thrown.append(at(name))
        control({"event": "Throw detected", "throws": thrown})
        wait_card(
            board,
            f"r.querySelectorAll('.visit .dart:not(.empty)').length === {len(thrown)}",
            tag,
        )
        board.wait_for_timeout(300)
        recorder.shot(1100)
    # The game shot shows at once; pulling the darts books the leg and the match.
    recorder.shot(900)
    pull_darts()
    wait_card(board, "!r.querySelector('.banner').hidden", tag)
    board.wait_for_timeout(300)
    recorder.shot(2600)
    recorder.save("scoreboard")
    board.close()
    players(page, 1)
    game(page, "off")


def killer_animation(page: Page) -> None:
    """Killer for three on the scoreboard: numbers, killers, lives, the last one left."""
    pull_darts()
    for index, name in enumerate(("Alex", "Sam", "Kim")):
        page.evaluate(SET_NAME, [index, name])
    players(page, 3)
    for key in ("practice_legs", "practice_sets"):
        page.evaluate(CALL_SERVICE, ["number", "set_value", key, {"value": 1}])
    game(page, "killer")
    board = page.context.new_page()
    board.set_viewport_size({"width": 1280, "height": 800})
    board.goto(f"{HA}/autodarts-auto/scoreboard")
    tag = "autodarts-scoreboard-card"
    wait_card(board, "r.querySelectorAll('.player').length === 3", tag, 60000)
    board.wait_for_timeout(1500)
    recorder = Recorder(board, tag)
    recorder.shot(1400)
    detail = "r.querySelectorAll('.player .details')[{0}]?.textContent.includes('{1}')"
    lives = "r.querySelectorAll('.player .big')[{0}]?.textContent === '{1}'"
    # Each visit with what the scoreboard shows after the darts are pulled.
    visits = [
        (["S7"], detail.format(0, "7")),
        (["S12"], detail.format(1, "12")),
        (["S3"], detail.format(2, "3")),
        (["D7", "D12", "D12"], lives.format(1, "♥")),
        (["S1"], detail.format(2, "3")),
        (["D3"], detail.format(2, "Killer")),
        (["D12", "D3", "D3"], lives.format(2, "♥")),
        (["S5"], lives.format(2, "♥")),
    ]
    for names, shown in visits:
        thrown: list[dict] = []
        for name in names:
            thrown.append(at(name))
            control({"event": "Throw detected", "throws": thrown})
            board.wait_for_timeout(500)
            if len(names) > 1:
                recorder.shot(700)
        pull_darts()
        wait_card(board, shown, tag)
        board.wait_for_timeout(400)
        recorder.shot(1000)
    control({"event": "Throw detected", "throws": [at("D3")]})
    wait_card(board, lives.format(2, "✕"), tag)
    board.wait_for_timeout(300)
    recorder.shot(1000)
    pull_darts()
    wait_card(board, "!r.querySelector('.banner').hidden", tag)
    board.wait_for_timeout(300)
    recorder.shot(2600)
    recorder.save("killer")
    board.close()
    players(page, 1)
    game(page, "off")


def doubles_card(page: Page) -> None:
    """The doubles card after a doubles training with a few misses per double."""
    open_dashboard(page, "board")
    pull_darts()
    game(page, "doubles")
    for number in range(1, 13):
        misses = (number * 3) % 7
        darts = [at(f"S{number}")] * misses + [at(f"D{number}")]
        for start in range(0, len(darts), 3):
            visit = darts[start : start + 3]
            for count in range(1, len(visit) + 1):
                control({"event": "Throw detected", "throws": visit[:count]})
                page.wait_for_timeout(200)
            pull_darts()
            page.wait_for_timeout(300)
    game(page, "off")
    page.goto(f"{HA}/autodarts-auto/training")
    page.wait_for_function(
        f"() => ({find('autodarts-doubles-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.double').length >= 10)",
        timeout=60000,
    )
    page.wait_for_timeout(1200)
    card_shot(page, "doubles-card", tag="autodarts-doubles-card")


def players_card(page: Page) -> None:
    """The players card after the matches of the animations."""
    page.goto(f"{HA}/autodarts-auto/players")
    page.wait_for_function(
        f"() => ({find('autodarts-players-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.profile').length >= 2)",
        timeout=60000,
    )
    page.wait_for_timeout(1200)
    card_shot(page, "players-card", tag="autodarts-players-card")


def scoreboard_page(page: Page) -> Page:
    """The scoreboard view of the generated dashboard, as on a tablet at the board."""
    board = page.context.new_page()
    board.set_viewport_size({"width": 1280, "height": 800})
    board.goto(f"{HA}/autodarts-auto/scoreboard")
    board.wait_for_function(
        f"() => ({find('autodarts-scoreboard-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.player').length === 2)",
        timeout=60000,
    )
    board.wait_for_timeout(1500)
    return board


def practice_card(page: Page) -> None:
    """A 501 match in the live card, and the scoreboard in Cricket."""

    def service(option: str) -> None:
        page.evaluate(
            CALL_SERVICE,
            ["select", "select_option", "practice_game", {"option": option}],
        )

    def takeout() -> None:
        control({"status": "Takeout in progress", "event": "Takeout started"})
        control({"status": "Throw", "event": "Takeout finished", "throws": []})
        wait_for_score(page, "0")

    # A 501 match of two players, three legs to win.
    takeout()
    service("501")
    page.evaluate(SET_NAME, [0, "Alex"])
    page.evaluate(SET_NAME, [1, "Sam"])
    for key, value in (("practice_players", 2), ("practice_legs", 3)):
        page.evaluate(CALL_SERVICE, ["number", "set_value", key, {"value": value}])
    for visit in ([T20] * 3, [T20, S5, S5], [T20] * 3, [T20, S5, S5]):
        for count in range(1, len(visit) + 1):
            control({"event": "Throw detected", "throws": visit[:count]})
            page.wait_for_timeout(300)
        takeout()
    control({"event": "Throw detected", "throws": [T20]})
    page.wait_for_function(
        f"() => ({FIND_CARDS})().some((c) => "
        "c.shadowRoot.querySelector('.practice-remaining')?.textContent === '81')",
        timeout=15000,
    )
    page.wait_for_timeout(800)
    peak(page)
    card_shot(page, "card-match")
    scoreboard = scoreboard_page(page)

    # Cricket between the same two players, Alex aiming at the 19.
    takeout()
    service("cricket")
    for names in (
        ("T20", "T20", "S19"),
        ("T19", "T19", "S18"),
        ("T18", "S17", "D17"),
        ("T20", "D16", "S18"),
    ):
        visit = [at(name) for name in names]
        for count in range(1, 4):
            control({"event": "Throw detected", "throws": visit[:count]})
            page.wait_for_timeout(300)
        takeout()
    control({"event": "Throw detected", "throws": [at("T16")]})
    page.wait_for_function(
        f"() => ({FIND_CARDS})().some((c) => c.shadowRoot"
        ".querySelectorAll('.practice .cricket tbody tr')[4]?.children[1]?.textContent === 'Ⓧ')",
        timeout=15000,
    )
    scoreboard.wait_for_function(
        f"() => ({find('autodarts-scoreboard-card')})().some((c) => c.shadowRoot"
        ".querySelectorAll('.cricket tbody tr')[4]?.children[1]?.textContent === 'Ⓧ')",
        timeout=15000,
    )
    scoreboard.wait_for_timeout(800)
    page_shot(scoreboard, "scoreboard-cricket")
    scoreboard.close()
    page.evaluate(
        CALL_SERVICE, ["number", "set_value", "practice_players", {"value": 1}]
    )
    service("off")


def find(tag: str) -> str:
    return FIND_CARDS.replace("'autodarts-card'", f"'{tag}'")


def training_card(page: Page, suffix: str) -> None:
    """The heatmap, statistics and the visit history read from the recorder."""
    size = page.viewport_size
    # A tall page keeps the whole card below the toolbar.
    tall = 2600 if size["width"] < 600 else 1700
    page.set_viewport_size({"width": size["width"], "height": tall})
    page.goto(f"{HA}/autodarts-demo/training")
    page.wait_for_function(
        f"() => ({find('autodarts-training-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.history-chart .visit-bar:not(.empty)').length >= 5)",
        timeout=60000,
    )
    page.wait_for_timeout(1200)
    card_shot(page, f"training-card{suffix}", tag="autodarts-training-card")
    page.set_viewport_size(size)


def status_card(page: Page, suffix: str) -> None:
    page.goto(f"{HA}/autodarts-demo/status")
    page.wait_for_function(
        f"() => ({find('autodarts-status-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.camera').length === 3)",
        timeout=60000,
    )
    page.wait_for_timeout(1200)
    card_shot(page, f"status-card{suffix}", tag="autodarts-status-card")


def strategy_dashboard(page: Page) -> None:
    """The training view of the dashboard that the strategy generates."""
    size = page.viewport_size
    page.set_viewport_size({"width": size["width"], "height": 1700})
    page.goto(f"{HA}/autodarts-auto/training")
    page.wait_for_function(
        f"() => ({find('autodarts-training-card')})().some((c) =>"
        " c.shadowRoot.querySelectorAll('.history-chart .visit-bar:not(.empty)').length >= 5)",
        timeout=60000,
    )
    page.wait_for_timeout(2500)
    page_shot(page, "dashboard-strategy")
    page.set_viewport_size(size)


def config_flow(page: Page) -> None:
    page.goto(f"{HA}/config/integrations/dashboard/add?domain=autodarts")
    # An integration that is already set up asks before adding another entry.
    confirm = page.get_by_role("button", name="OK", exact=True)
    try:
        confirm.wait_for(timeout=10000)
        confirm.click()
    except PlaywrightTimeoutError:
        pass
    # Never open the network search here: it would list the real boards of this
    # internet connection in a public screenshot.
    menu = page.get_by_text(
        "Enter board address" if LANGUAGE == "en" else "Board-Adresse eingeben",
        exact=True,
    )
    menu.wait_for(timeout=30000)
    page.wait_for_timeout(800)
    page_shot(page, "setup-menu")
    menu.click()
    title = "Connect local board" if LANGUAGE == "en" else "Lokales Board verbinden"
    page.get_by_text(title, exact=True).wait_for(timeout=15000)
    page.wait_for_timeout(800)
    page_shot(page, "setup-local")
    # Leave the unfinished flow; the demo instance is discarded afterwards.
    page.goto(f"{HA}/autodarts-demo/board")


def device_page(page: Page) -> None:
    open_dashboard(page, "board")
    device_id = page.evaluate(
        "() => Object.values(document.querySelector('home-assistant').hass.devices)"
        ".find((d) => d.identifiers.some((i) => i[0] === 'autodarts')).id"
    )
    page.goto(f"{HA}/config/devices/device/{device_id}")
    page.get_by_text("Autodarts Board").first.wait_for(timeout=30000)
    page.wait_for_timeout(2500)
    page_shot(page, "device")


def editor(page: Page) -> None:
    page.goto(f"{HA}/autodarts-demo/board?edit=1")
    page.wait_for_timeout(2500)
    page.evaluate(EDIT_CARD)
    # Home Assistant builds the form of the card from getConfigForm.
    page.locator("hui-form-editor ha-form").first.wait_for(timeout=15000)
    page.wait_for_timeout(2000)
    peak(page)
    page_shot(page, "card-editor")
    page.keyboard.press("Escape")


def strategy_editor(page: Page) -> None:
    """The editor of the generated dashboard: the board and the title."""
    page.goto(f"{HA}/autodarts-auto/live")
    page.wait_for_function(
        f"() => ({FIND_CARDS})().some((c) => c.shadowRoot.querySelector('.board svg'))",
        timeout=60000,
    )
    page.evaluate(f"() => ({find('hui-root')})()[0]._enableEditMode()")
    page.locator("autodarts-strategy-editor > ha-form").wait_for(timeout=15000)
    page.wait_for_timeout(2000)
    page_shot(page, "strategy-editor")
    page.keyboard.press("Escape")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for scheme, suffix in (("dark", ""), ("light", "-light")):
            context = browser.new_context(
                viewport={"width": 1280, "height": 820},
                device_scale_factor=2,
                locale=LOCALE,
                color_scheme=scheme,
            )
            page = context.new_page()
            open_dashboard(page, "board")
            wait_for_score(page, "115")
            peak(page)
            card_shot(page, f"card{suffix}")
            training_card(page, suffix)
            status_card(page, suffix)
            if scheme == "dark":
                open_dashboard(page, "styles")
                peak(page)
                card_shot(page, "card-autodarts-style", 0)
                card_shot(page, "card-board-only", 1)
                editor(page)
                strategy_editor(page)
                strategy_dashboard(page)
                config_flow(page)
                device_page(page)
            context.close()

        mobile = browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale=LOCALE,
            color_scheme="dark",
        )
        page = mobile.new_page()
        open_dashboard(page, "board")
        peak(page)
        card_shot(page, "card-mobile")
        training_card(page, "-mobile")
        mobile.close()

        animation = browser.new_context(
            viewport={"width": 1100, "height": 700},
            device_scale_factor=1,
            locale=LOCALE,
            color_scheme="dark",
        )
        page = animation.new_page()
        open_dashboard(page, "board")
        visit_animation(page)
        animation.close()

        # Last, because the practice leg adds visits to the demo session.
        practice = browser.new_context(
            viewport={"width": 1280, "height": 820},
            device_scale_factor=2,
            locale=LOCALE,
            color_scheme="dark",
        )
        page = practice.new_page()
        open_dashboard(page, "board")
        practice_card(page)
        practice.close()

        # The games as animations, at the size the documentation shows them.
        games = browser.new_context(
            viewport={"width": 1100, "height": 1100},
            device_scale_factor=1,
            locale=LOCALE,
            color_scheme="dark",
        )
        page = games.new_page()
        open_dashboard(page, "board")
        checkout_animation(page)
        cricket_animation(page)
        training_game_animation(page)
        scoreboard_animation(page)
        killer_animation(page)
        games.close()

        people = browser.new_context(
            viewport={"width": 1280, "height": 1000},
            device_scale_factor=2,
            locale=LOCALE,
            color_scheme="dark",
        )
        players_card(people.new_page())
        doubles_card(people.new_page())
        people.close()
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
