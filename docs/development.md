# Development

[← Documentation](README.md)

## Project layout

| Path | Contents |
| --- | --- |
| `custom_components/autodarts/` | The integration |
| `custom_components/autodarts/frontend/autodarts-card.js` | The six dashboard cards, served by the integration |
| `blueprints/automation/autodarts/` | Automation blueprints |
| `tests/` | Unit and integration tests with `pytest-homeassistant-custom-component` |
| `tests/frontend/` | Node tests of the card logic and of every card element in a browser DOM, including property-based tests with fast-check |
| `tests/e2e/` | Docker end-to-end test, demo instance, browser test and screenshot tool |
| `docs/` | Documentation, with German translations in `docs/de/` |

## Tests

Python 3.14 and Node.js 24:

```sh
python3.14 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.txt
.venv/bin/pytest --cov          # fails below 100 % line and branch coverage
.venv/bin/ruff check custom_components tests .github/scripts
.venv/bin/ruff format --check custom_components tests .github/scripts
.venv/bin/mypy                  # strict typing of the integration
npm ci
npm test                        # fuzzing with fast-check; fails below 100 % lines, 99 % branches and functions
```

Without a local Python, run the same in Docker:

```sh
docker run --rm -v "$PWD:/src:ro" python:3.14 sh -c \
  "cp -r /src /work && cd /work && pip install -q -r requirements-test.txt && pytest --cov"
```

The test suite covers:

- config flows, discovery, migration and reauthentication;
- realtime and poll reconciliation, both Board Manager generations and failure recovery;
- the training rules and every platform;
- repairs, diagnostics and the dashboard card registration;
- every blueprint, run by Home Assistant's automation engine, also on the real board events of a practice match, with checks that every event type and attribute a blueprint reads exists and that every import link opens the right file;
- every dashboard card, card editor and the dashboard strategy, rendered in a [happy-dom](https://github.com/capricorn86/happy-dom) browser DOM against a simulated Home Assistant: every game, every option, both languages, controls with their confirmation, the caller and escaping of player names.

The card logic is also fuzzed with [fast-check](https://fast-check.dev/): thousands of random and hostile inputs per run check that escaping, bed geometry, the heatmap and the history parser never break.

## Docker end-to-end test

The [end-to-end test](../tests/e2e/README.md) starts a real Home Assistant container with this integration and a simulated Board Manager. It runs onboarding, setup, all controls, realtime darts, persistence, diagnostics and removal:

```sh
BOARD_MANAGER=1 bash tests/e2e/run.sh
BOARD_MANAGER=2 bash tests/e2e/run.sh   # includes discovery by mDNS
```

## Demo instance and browser test

`tests/e2e/demo.sh` starts Home Assistant with a simulated board, a finished training session and a dashboard with all cards at <http://127.0.0.1:18124/autodarts-demo/board>. Login is not needed from the local network.

`tests/e2e/browser.sh` checks the cards in Chromium against the demo:

- the cards are registered on every load;
- the live visit, highlights and controls with confirmation;
- the practice game, match and training games;
- the training heatmap, history and sessions, and the status card;
- the scoreboard and its caller, the players and doubles cards;
- the generated dashboard, all six editors and the light theme.

When a step fails, the browser test saves a screenshot of every open page, and
the scripts save the Home Assistant log, in `tests/e2e/artifacts/` or in the
folder named by `E2E_ARTIFACTS`. CI keeps them as a workflow artifact for 14 days.

## Screenshots

`tests/e2e/screenshots.sh` regenerates every image in `docs/images/en` and `docs/images/de` from the demo, including the animated WebP images. Every image shows the simulated board, so no personal data can appear. The tool never opens the network search, which would list real boards.

## Diagrams

The architecture diagram is written in Mermaid in `docs/diagrams/` and rendered as PNG images for light and dark themes, because the GitHub app and HACS do not render Mermaid. After changing a diagram, run:

```sh
bash scripts/render_diagrams.sh
```

## Continuous integration

Every pull request, and every push to `main`, runs:

- pytest with a coverage gate, Ruff, strict mypy and the Node tests, with the coverage report in the job summary;
- the Docker end-to-end test against both Board Manager generations, the browser test,
  and the end-to-end test against Home Assistant 2026.8.0, the oldest supported release;
- HACS validation and hassfest;
- actionlint, CodeQL for Python, the card JavaScript and the workflows, and dependency review;
- Gitleaks and an SPDX SBOM.

A new commit to a pull request cancels the older, still running checks of that
pull request; runs on `main` are never cancelled. Every Monday the end-to-end tests
also run against the current Home Assistant beta, as an early warning before the
next release. OpenSSF Scorecard evaluates the repository weekly and on every push to `main`.

Pull request titles follow Conventional Commits. The **Pull request labels**
workflow checks the title and sets the label that sorts the change into the
release notes (see the [release guide](releases.md#keep-generated-notes-useful)).

Dependencies are pinned:

- Actions by commit hash, and container images by digest.
- Python tools with hashes, in `requirements-test.txt` (compiled from `requirements-test.in` with `pip-compile --generate-hashes`) and `tests/e2e/requirements-browser.txt`.
- Node tools by `package-lock.json`.

Dependabot keeps the Python and Node tools, the Actions and the Compose images
current, and waits seven days before it proposes a new version; security updates
come at once. The Playwright, Alpine and Mermaid images in the scripts under
`tests/e2e/` and `scripts/` are updated by hand. Two checks deliberately run moving
images: HACS validation and hassfest always apply the rules that HACS and Home
Assistant use for new submissions today, and the weekly beta run uses the beta tag.

## Releases

See the [release guide](releases.md).

## Conventions

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/), for example `feat:`, `fix:` and `docs:`.
- User-facing text goes into `strings.json` and both translations; `strings.json` equals `translations/en.json`.
- New behaviour needs tests, and new user-facing features need documentation in English and German.
