"""How the browser tests wait, checked without a browser.

Playwright's sync API handles the events of the browser, such as a request that a
route holds back, only while the script is inside one of its calls. ``time.sleep``
stops all of them: in a route handler, every request the handler delays waits for the
ones before it, one after another, and a page that waits for its ``load`` event runs
into its timeout. A script that has to let time pass waits with
``page.wait_for_timeout``, which keeps handling them.

The browser test lets no time pass for nothing: it waits for what it checks, such as
the cards drawn, a quiet websocket and the states a move at the board sets
(``tests/e2e/pages.py``). A fixed wait is too short on a slow runner or too long
everywhere else; the few that the test needs are listed here with their reasons. Nor
does it wait out the timers of the cards, such as the summary of a match or the time
before idle mode: the page of such a step runs Playwright's clock, and ``run_until()``
runs it forward until what the timer leads to shows.
"""

import ast
import importlib.util
import sys
import types
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

E2E = Path(__file__).parent / "e2e"
# Every script that drives a browser with Playwright's sync API.
PLAYWRIGHT_SCRIPTS = sorted(
    path.name
    for path in E2E.glob("*.py")
    if "playwright.sync_api" in path.read_text(encoding="utf-8")
)
# The scripts of the browser test, which waits for what it checks.
BROWSER_TEST = ("browser.py", "pages.py")
# The fixed waits the browser test needs, by their function and time, with how often
# each one is called and why.
FIXED_WAITS = {
    # A finger rests on the loupe before it lets go, as one does that reads it; one
    # that leaves still moving flings instead of entering the dart.
    ("fingers", "120"): 1,
    # Safari's requests of the cards are held back for longer than Home Assistant
    # waits for the element of its dashboard strategy, as on a slow network.
    ("safari", "CARD_MODULE_DELAY * 1000"): 1,
}


def sleeps(source: str) -> list[int]:
    """The lines that call ``time.sleep``, by its module or imported on its own."""
    tree = ast.parse(source)
    names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "time"
        for alias in node.names
        if alias.name == "sleep"
    }
    modules = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "time"
    }
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id in names)
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "sleep"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in modules
            )
        )
    )


def test_every_way_to_call_time_sleep_is_found():
    source = "\n".join(
        [
            "import time",
            "import time as clock",
            "from time import sleep, monotonic",
            "from time import sleep as nap",
            "time.sleep(1)",
            "clock.sleep(1)",
            "sleep(1)",
            "nap(1)",
            "page.wait_for_timeout(1000)",
            "asyncio.sleep(1)",
            "monotonic()",
        ]
    )
    assert sleeps(source) == [5, 6, 7, 8]


def test_the_browser_scripts_are_found():
    assert {"browser.py", "screenshots.py"} <= set(PLAYWRIGHT_SCRIPTS)


@pytest.mark.parametrize("script", PLAYWRIGHT_SCRIPTS)
def test_no_browser_script_stops_playwright_with_time_sleep(script):
    lines = sleeps((E2E / script).read_text(encoding="utf-8"))
    assert lines == [], (
        f"{script} calls time.sleep in line(s) {lines}: wait with "
        "page.wait_for_timeout, which keeps handling the events of the browser"
    )


def fixed_waits(source: str) -> list[tuple[str, str, int]]:
    """Every ``wait_for_timeout`` call: its function, its time as written and its line."""
    found = []

    def visit(node: ast.AST, function: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                visit(child, child.name)
                continue
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "wait_for_timeout"
            ):
                time = ", ".join(ast.unparse(argument) for argument in child.args)
                found.append((function, time, child.lineno))
            visit(child, function)

    visit(ast.parse(source), "")
    return found


def test_every_fixed_wait_is_found_with_its_function():
    source = "\n".join(
        [
            "page.wait_for_timeout(1)",
            "def look(page):",
            "    page.wait_for_timeout(800)",
            "    def again():",
            "        control_page.wait_for_timeout(DELAY * 1000)",
            "    page.context.pages[0].wait_for_timeout(timeout=5)",
            "    page.wait_for_function('() => true', timeout=800)",
        ]
    )
    assert fixed_waits(source) == [
        ("", "1", 1),
        ("look", "800", 3),
        ("again", "DELAY * 1000", 5),
        ("look", "", 6),
    ]


def unexpected_waits(sources: dict[str, str]) -> list[str]:
    """The fixed waits of the scripts beyond FIXED_WAITS: a new one, or an allowed one
    called more often than allowed."""
    allowed = Counter(FIXED_WAITS)
    unexpected = []
    for script, source in sources.items():
        for function, time, line in fixed_waits(source):
            if allowed[(function, time)] > 0:
                allowed[(function, time)] -= 1
            else:
                unexpected.append(
                    f"{script} line {line}: {function or 'module'}() waits "
                    f"{time or 'a fixed time'}"
                )
    return unexpected


def test_a_new_fixed_wait_is_found_also_beside_an_allowed_one():
    source = "\n".join(
        [
            "def fingers(page):",
            "    page.wait_for_timeout(120)",
            "    page.wait_for_timeout(120)",
            "def safari(page):",
            "    page.wait_for_timeout(CARD_MODULE_DELAY * 1000)",
            "def look(page):",
            "    page.wait_for_timeout(800)",
        ]
    )
    assert unexpected_waits({"a.py": source, "b.py": "page.wait_for_timeout(120)"}) == [
        "a.py line 3: fingers() waits 120",
        "a.py line 7: look() waits 800",
        "b.py line 1: module() waits 120",
    ]


def test_the_browser_test_waits_for_what_it_checks():
    unexpected = unexpected_waits(
        {script: (E2E / script).read_text("utf-8") for script in BROWSER_TEST}
    )
    assert unexpected == [], (
        f"The browser test waits a fixed time ({'; '.join(unexpected)}): wait for "
        "what the step checks instead, such as settle(), expect_state() or wait_for() "
        "of pages.py, or add the wait to FIXED_WAITS with its reason"
    )


def test_every_allowed_fixed_wait_is_still_needed():
    waits = Counter(
        (function, time)
        for script in BROWSER_TEST
        for function, time, _ in fixed_waits((E2E / script).read_text("utf-8"))
    )
    unused = {wait: count for wait, count in FIXED_WAITS.items() if waits[wait] < count}
    assert unused == {}, f"Waited less often than allowed: {unused}"


# The screenshot tool times the frames of its animations with fixed waits, but waits
# for a page that opens or changes its size with ready(), which waits for loaded() of
# pages.py: a fixed wait after a load is too short on a slow runner, and an image
# taken too early differs from the committed one. Its fixed waits only get fewer.
SCREENSHOT_TOOL = "screenshots.py"
SCREENSHOT_WAITS = 100
# The steps that open a page for a picture or change its size.
SCREENSHOT_LOADS = ("open_dashboard", "tall_card_shot")


def test_the_screenshot_tool_waits_no_more_often_for_a_fixed_time():
    waits = fixed_waits((E2E / SCREENSHOT_TOOL).read_text("utf-8"))
    assert len(waits) <= SCREENSHOT_WAITS, (
        f"{SCREENSHOT_TOOL} waits a fixed time {len(waits)} times, more than the "
        f"{SCREENSHOT_WAITS} it did: wait for a page with ready() instead"
    )


def test_the_screenshot_tool_waits_for_a_page_until_it_has_loaded():
    source = (E2E / SCREENSHOT_TOOL).read_text("utf-8")
    fixed = {function for function, _, _ in fixed_waits(source)}
    assert not fixed & set(SCREENSHOT_LOADS)
    functions = {
        node.name: node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef)
    }
    for name in SCREENSHOT_LOADS:
        calls = {
            node.func.id
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "ready" in calls, f"{name}() does not wait with ready()"


def load_pages() -> types.ModuleType:
    """pages.py without Playwright, which only the browser test installs: what show()
    decides needs none of it."""
    sync_api = types.ModuleType("playwright.sync_api")
    vars(sync_api).update(
        BrowserContext=object, Locator=object, Page=object, TimeoutError=TimeoutError
    )
    playwright = types.ModuleType("playwright")
    vars(playwright).update(sync_api=sync_api)
    spec = importlib.util.spec_from_file_location("e2e_pages", E2E / "pages.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    stubs = {"playwright": playwright, "playwright.sync_api": sync_api}
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


HA = "http://127.0.0.1:8123"


@pytest.mark.parametrize(
    ("current", "url", "within"),
    [
        # A view of the app opens the next one as its links do.
        (f"{HA}/autodarts-auto/live", f"{HA}/autodarts-demo/scoreboard", True),
        (f"{HA}/autodarts-auto/live", f"{HA}/autodarts-auto/live", True),
        # A page that shows nothing of Home Assistant yet loads it.
        ("about:blank", f"{HA}/autodarts-auto/live", False),
        ("http://127.0.0.1:8124/x", f"{HA}/autodarts-auto/live", False),
        # The app reads a query or a fragment only when it starts.
        (f"{HA}/autodarts-auto/live", f"{HA}/autodarts-demo/board?edit=1", False),
        (f"{HA}/autodarts-auto/live", f"{HA}/autodarts-demo/board#card", False),
        # And keeps what they set, such as edit mode, in the views it opens after.
        (f"{HA}/autodarts-demo/board?edit=1", f"{HA}/autodarts-demo/board", False),
        (f"{HA}/autodarts-demo/board?edit=1", f"{HA}/autodarts-auto/live", False),
        (f"{HA}/autodarts-demo/board#card", f"{HA}/autodarts-auto/live", False),
    ],
)
def test_show_opens_a_view_within_the_app_only_from_a_plain_one(current, url, within):
    assert load_pages().within_app(current, url) is within


class Clocked:
    """A page with Playwright's clock, whose target shows once its clock has run for
    the given milliseconds, or never."""

    url = f"{HA}/autodarts-demo/idle"
    viewport_size = {"width": 800, "height": 480}

    def __init__(self, shows_after: int | None) -> None:
        self.ran: list[int] = []
        self.shows_after = shows_after
        self.clock = types.SimpleNamespace(run_for=self.ran.append)
        self.target = types.SimpleNamespace(is_visible=self.shown)

    def shown(self) -> bool:
        return self.shows_after is not None and sum(self.ran) >= self.shows_after

    def evaluate(self, expression: str) -> str:
        return "en-US"


@pytest.mark.parametrize(
    ("shows_after", "steps"),
    [
        # A target that shows already lets no time pass.
        (0, 0),
        # One that shows a moment later after a second, and one at the end of a timer
        # of eight seconds after eight, a second at a time.
        (1, 1),
        (8000, 8),
        (8001, 9),
        # Right at the end of the time it is given.
        (15000, 15),
    ],
)
def test_run_until_runs_the_clock_a_second_at_a_time_until_the_target_shows(
    shows_after, steps
):
    page = Clocked(shows_after)
    load_pages().run_until(page, page.target, 15000, "The table", Card("Kim 0"))
    assert page.ran == [1000] * steps


class Card:
    """A card whose first match shows the given text, or breaks when it is gone."""

    def __init__(self, text: str | None) -> None:
        self.text = text
        self.first = self

    def inner_text(self, timeout: int) -> str:
        if self.text is None:
            raise RuntimeError("Target page, context or browser has been closed")
        return self.text


@pytest.mark.parametrize(("shows_after", "steps"), [(15001, 15), (None, 15)])
def test_run_until_fails_when_the_target_has_not_shown_in_the_time_it_is_given(
    shows_after, steps
):
    page = Clocked(shows_after)
    pages = load_pages()
    with pytest.raises(pages.Unsettled) as error:
        pages.run_until(
            page, page.target, 15000, "Idle mode", Card("Kim\n  101\nSam 0")
        )
    assert str(error.value) == (
        f"{HA}/autodarts-demo/idle at 800x480 in en-US: Idle mode did not show within"
        " 15000 ms on the clock of the page; the card showed 'Kim 101 Sam 0'"
    )
    assert page.ran == [1000] * steps


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        # What the card shows, in one line.
        ("Match summary\n Kim  3 - 1 Sam", "'Match summary Kim 3 - 1 Sam'"),
        # A long screen cut to 120 characters.
        ("x" * 200, repr("x" * 117 + "...")),
        # A card without text, and one that is gone.
        ("  \n ", "no text"),
        (None, "nothing"),
    ],
)
def test_a_wait_on_the_clock_names_what_the_card_showed_instead(text, shown):
    assert load_pages().showing(Card(text)) == shown


def clocked(source: str) -> dict[tuple[str, str], str]:
    """Each function with each page whose clock it runs with ``run_until()``, and when
    it installs that clock: "before it loads", "after it loads" or "never"."""
    found = {}
    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, ast.FunctionDef):
            continue
        # The lines of the calls of the function, also in the functions within it, by
        # what they call, such as "page.goto".
        lines: dict[str, list[int]] = {}
        clocks = []
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                lines.setdefault(ast.unparse(node.func), []).append(node.lineno)
                if ast.unparse(node.func) == "run_until":
                    clocks.append(ast.unparse(node.args[0]))
        for page in clocks:
            installs = lines.get(f"{page}.clock.install")
            loads = lines.get(f"{page}.goto")
            if not installs:
                found[function.name, page] = "never"
            elif loads and min(loads) < min(installs):
                found[function.name, page] = "after it loads"
            else:
                found[function.name, page] = "before it loads"
    return found


def test_when_a_function_installs_the_clock_it_runs_is_found():
    source = "\n".join(
        [
            "def early(browser):",
            "    page = browser.new_page()",
            "    page.clock.install()",
            "    def again():",
            "        page.goto(URL)",
            "    page.goto(URL)",
            "    run_until(page, page.locator('.a'), 1000, 'A')",
            "def late(browser):",
            "    page = browser.new_page()",
            "    page.goto(URL)",
            "    page.clock.install()",
            "    run_until(page, page.locator('.a'), 1000, 'A')",
            "def never(browser, other):",
            "    other.clock.install()",
            "    other.goto(URL)",
            "    run_until(pages[0], pages[0].locator('.a'), 1000, 'A')",
            "def unloaded(page):",
            "    page.clock.install()",
            "    run_until(page, page.locator('.a'), 1000, 'A')",
            "def waits(page):",
            "    page.goto(URL)",
            "    page.locator('.a').wait_for(timeout=10000)",
        ]
    )
    assert clocked(source) == {
        ("early", "page"): "before it loads",
        ("late", "page"): "after it loads",
        ("never", "pages[0]"): "never",
        ("unloaded", "page"): "before it loads",
    }


# The steps that run the clock of their page through the timers of the cards instead
# of waiting them out: the summary of a match in both, and the time before idle mode
# on the tablet.
CLOCKED_STEPS = {"tournament", "tablet_screen"}


def test_the_browser_test_runs_the_clock_through_the_timers_of_the_cards():
    found = clocked((E2E / "browser.py").read_text("utf-8"))
    assert {function for function, _ in found} == CLOCKED_STEPS
    late = {step: when for step, when in found.items() if when != "before it loads"}
    assert late == {}, (
        f"A step runs the clock of a page that it installs late or never: {late}; call "
        "page.clock.install() before the page loads, or the timers of the cards run "
        "on the real clock"
    )
