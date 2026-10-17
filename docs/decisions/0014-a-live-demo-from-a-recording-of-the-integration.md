# Replay a recording of the integration for the live demo of the website

- Status: accepted
- Date: 2026-10-14

## Context

Trying the cards took Git, Docker and the demo instance of `tests/e2e/demo.sh`, so most visitors of the website and the README saw them only in pictures and animations. The cards are one module without dependencies, which needs nothing from Home Assistant but the `hass` object, its `ha-card` element and a few commands. A demo in the browser has to show the cards as they are in the current version, follow every change of the integration and the cards without work by hand, run on a static website with no server and no secret, and stay deterministic, so that a test can check it.

## Options

1. **A public Home Assistant instance with the demo.** The real thing, but it needs a server, its updates and its security, which a free project can't promise, and every visitor would share and change the same games.
2. **States written by hand for the page.** Small and quick, but they drift from the integration with every new attribute, and nobody notices until a card breaks in the demo.
3. **A recording from the Docker demo of the images.** The real integration in a real Home Assistant, but it needs Docker and minutes for every recording, and the screenshot groups would have to pass it between their runners.
4. **A recording from the Home Assistant of the tests.** The integration plays the games in pytest, at a simulated board, on a clock that moves only with the games: in seconds, without Docker, the same in every run, and in every run of the tests.

## Decision

Option 4. `scripts/record_demo.py` lets the integration play a 501 against the bot, a Cricket game and a tournament in the Home Assistant of the tests and keeps the states that changed after every move in `docs/demo/timeline.json`. The page in `docs/demo/` replays it with the cards of the integration, which the website copies next to it, and a small stand-in for Home Assistant gives the cards the states with their moments moved to the time of the replay. Actions change nothing there; a note says that this is a recording.

The screenshot bot records the games anew with the images, so the demo follows the integration in the same pull request as the pictures. `tests/test_demo_timeline.py` plays the games in every run of the tests, and the job *live demo* of the end-to-end tests plays the page in a real browser in every language, on a desktop and a phone.

## Consequences

- Anyone can try the cards from a link, on a phone too, without installing anything; creators and the README can link to it.
- The demo shows what the integration does, not what a page claims it does. A change of the integration that breaks the games fails the tests; a change of the cards that breaks the page fails the required check `e2e`.
- The recording is about half a megabyte of JSON, a line per step, which GitHub Pages sends compressed (about 30 KB). A new game in the demo is a few lines in `tests/demo_timeline.py`.
- The cards in the demo can't open Home Assistant's dialogs, forms or history; they show what a dashboard shows while a game is played.
