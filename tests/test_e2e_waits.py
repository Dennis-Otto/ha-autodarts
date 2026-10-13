"""How the browser tests wait, checked without a browser.

Playwright's sync API handles the events of the browser, such as a request that a
route holds back, only while the script is inside one of its calls. ``time.sleep``
stops all of them: in a route handler, every request the handler delays waits for the
ones before it, one after another, and a page that waits for its ``load`` event runs
into its timeout. The scripts wait with ``page.wait_for_timeout``, which keeps
handling them.
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
