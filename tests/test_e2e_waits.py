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
everywhere else; the few that the test needs are listed here with their reasons.
"""

import ast
from pathlib import Path

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
# The fixed waits the browser test needs, by their function and time, with reasons.
FIXED_WAITS = {
    # A finger rests on the loupe before it lets go, as one does that reads it; one
    # that leaves still moving flings instead of entering the dart.
    ("fingers", "120"),
    # Safari's requests of the cards are held back for longer than Home Assistant
    # waits for the element of its dashboard strategy, as on a slow network.
    ("safari", "CARD_MODULE_DELAY * 1000"),
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


@pytest.mark.parametrize("script", BROWSER_TEST)
def test_the_browser_test_waits_for_what_it_checks(script):
    unknown = [
        f"line {line}: {function or 'module'}() waits {time or 'a fixed time'}"
        for function, time, line in fixed_waits((E2E / script).read_text("utf-8"))
        if (function, time) not in FIXED_WAITS
    ]
    assert unknown == [], (
        f"{script} waits a fixed time ({'; '.join(unknown)}): wait for what the step "
        "checks instead, such as settle(), expect_state() or wait_for() of pages.py, "
        "or add the wait to FIXED_WAITS with its reason"
    )


def test_every_allowed_fixed_wait_is_still_needed():
    waits = {
        (function, time)
        for script in BROWSER_TEST
        for function, time, _ in fixed_waits((E2E / script).read_text("utf-8"))
    }
    assert FIXED_WAITS <= waits, f"No longer waited: {sorted(FIXED_WAITS - waits)}"
