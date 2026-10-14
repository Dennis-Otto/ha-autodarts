"""The live demo of the website in a real browser (tests/e2e/live_demo.sh).

The page of docs/demo/ goes to a folder as the website has it, with the cards of
the integration next to it (scripts/mkdocs_hooks.py), and a small web server serves
it. Chromium opens it in every language, on a desktop and on a phone: the games
start on their own, every step of the recording reaches the cards, the tournament
ends with its winner, the page stays as wide as the screen, a button of a card says
that this is a recording, and nothing writes an error to the console.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

# What the website has of the repository for the demo: its page, the project's icon
# and the cards of the integration.
DEMO = Path(__file__).resolve().parents[2] / "docs" / "demo"
BRANDING = Path(__file__).resolve().parents[2] / "docs" / "branding"
CARDS = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "autodarts"
    / "frontend"
    / "autodarts-card.js"
)
ARTIFACTS = Path(os.environ.get("LIVE_DEMO_ARTIFACTS", "artifacts/live-demo"))
LANGUAGES = ["en", "de", "nl", "fr", "es"]
SCREENS = {"desktop": (1366, 900), "phone": (390, 844)}
# The winner of the tournament, the last game of the recording.
CHAMPION = "Kim"

# Every step of the recording, one after the other, each drawn by the cards
# before the next one comes.
EVERY_STEP = """
async () => {
  const replay = window.autodartsDemo;
  replay.pause();
  for (let index = 0; index < replay.steps.length; index++) {
    replay._apply(index);
    replay._emit();
    await new Promise((done) => requestAnimationFrame(() => done()));
  }
  return replay.index;
}
"""
CARD_TEXT = "(tag) => document.querySelector(tag).shadowRoot.textContent"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        """Only the failures speak."""


def website(folder: Path) -> Path:
    """The demo as the website has it: its page, the cards and the project's icon."""
    shutil.copytree(DEMO, folder / "demo")
    shutil.copytree(BRANDING, folder / "branding")
    shutil.copyfile(CARDS, folder / "demo" / CARDS.name)
    return folder


def check(page: Page, address: str, language: str, screen: str) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda message: (
            errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{address}/demo/index.html?lang={language}")
    expect(page.locator("html")).to_have_attribute("lang", language)
    # The games start on their own.
    page.wait_for_function("window.autodartsDemo?.index > 1", timeout=20_000)
    steps = page.evaluate("window.autodartsDemo.steps.length")
    assert page.evaluate(EVERY_STEP) == steps - 1
    page.wait_for_function(
        f"document.querySelector('autodarts-scoreboard-card').shadowRoot"
        f".textContent.includes('{CHAMPION}')"
    )
    for tag in (
        "autodarts-card",
        "autodarts-training-card",
        "autodarts-players-card",
    ):
        assert page.evaluate(CARD_TEXT, tag).strip(), f"{tag} shows nothing"
    # The page fits the screen; only the cards' own boards may scroll inside them.
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        f"the page is wider than the {screen}"
    )
    # A button of a card says that this is a recording.
    page.locator("autodarts-card button[data-action='toggle']").click()
    expect(page.locator("#notice")).to_be_visible()
    assert not errors, errors


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        handler = partial(Quiet, directory=str(website(Path(temporary))))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        address = f"http://127.0.0.1:{server.server_port}"
        failed = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for screen, (width, height) in SCREENS.items():
                for language in LANGUAGES:
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        is_mobile=screen == "phone",
                        has_touch=screen == "phone",
                    )
                    page = context.new_page()
                    try:
                        check(page, address, language, screen)
                        print(f"ok  {language} on a {screen}", flush=True)
                    except Exception as error:
                        failed.append(f"{language} on a {screen}: {error}")
                        page.screenshot(
                            path=str(ARTIFACTS / f"{language}-{screen}.png"),
                            full_page=True,
                        )
                        print(f"FAILED {language} on a {screen}: {error}", flush=True)
                    finally:
                        context.close()
            browser.close()
        server.shutdown()
    if failed:
        raise SystemExit("The live demo failed:\n- " + "\n- ".join(failed))
    print(
        f"The live demo played in {len(LANGUAGES)} languages on {len(SCREENS)} screens."
    )


if __name__ == "__main__":
    main()
