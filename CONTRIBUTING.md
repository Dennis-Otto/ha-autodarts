# Contributing

Contributions are welcome through issues and pull requests.
Participation follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and project decision-making is described in [GOVERNANCE.md](GOVERNANCE.md).
Use [SUPPORT.md](SUPPORT.md) to choose the correct public support channel and [SECURITY.md](SECURITY.md) for private vulnerability reports.

All changes, including release version commits, reach the protected `main` branch through pull requests. Pull requests must pass every required check before they are merged.

## Requirements for changes

- New functionality and bug fixes must include automated tests. Use pytest for integration behavior and extend the Docker end-to-end test in `tests/e2e/` when a user-visible Home Assistant flow changes.
- Code must pass Ruff (lint and format) and strict mypy with the rules configured in `pyproject.toml`, keep the test coverage of every line and branch at 100 %, and remain compatible with the Home Assistant version used by the tests.
- Dashboard card changes need Node tests in `tests/frontend/` and, for visible changes, the browser test in `tests/e2e/browser.py`.
- User-facing text belongs in `strings.json` and every translation, card texts in every language of `TEXT`; see [Translations](#translations).
- Update the README and `docs/` when behavior, setup, or supported versions change. The documentation is English, with a German translation in `docs/de/`; update both. Regenerate screenshots with `bash tests/e2e/screenshots.sh` when a visible card or dialog changes.
- Local Board Manager communication must not log, store, or expose the board API key. Cloud tokens remain in the config entry.

## Workflow

1. Open an issue or a discussion first for anything larger than a small fix, so we can agree on the approach.
2. Fork the repository and create a branch from `main`, for example `feat/cricket-variants` or `fix/bull-off-tie`.
3. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`, `refactor:` or `perf:`, with an optional scope such as `feat(scoreboard): …`. Mark breaking changes with `!`.
4. Open a pull request with a Conventional Commit title. A workflow checks the title and labels the pull request; the label decides the section in the release notes. Pull requests are squashed into one commit on `main`.
5. The maintainer reviews every pull request for correctness, tests, documentation in both languages, security and user impact.

By contributing, you agree that your contribution is licensed under the [MIT license](LICENSE) of this project.

## Checks

Before opening a pull request, run:

```bash
python3.14 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.txt
.venv/bin/pytest --cov
.venv/bin/ruff check custom_components tests .github/scripts
.venv/bin/ruff format --check custom_components tests .github/scripts
.venv/bin/mypy
npm ci
npm test
BOARD_MANAGER=2 bash tests/e2e/run.sh
bash tests/e2e/browser.sh
```

The end-to-end and browser tests require Docker with Compose. The [development guide](docs/development.md) describes every tool, including the demo instance.

Do not include real credentials, board IDs, API keys, private network addresses, or logs containing personal data. Use reserved documentation addresses such as `192.0.2.10` and clearly synthetic values in tests and documentation.

The development container in `.devcontainer/` sets up Python 3.14, Node.js 24 and Docker in one step, and `bash scripts/check.sh` runs the unit checks of the CI test job. Optional pre-commit hooks run Ruff and basic file checks before each commit: `pip install pre-commit && pre-commit install`.

## Translations

The integration speaks English, German, Dutch, French and Spanish. Its texts live in two places:

- `custom_components/autodarts/strings.json` with the English source, copied unchanged to `translations/en.json`, and one file per language in `translations/` with the same keys in the same order;
- the `TEXT` dictionary of `custom_components/autodarts/frontend/autodarts-card.js`: `TEXT.en` and one entry per language with the same keys in the same order.

`tests/test_consistency.py` keeps every language complete. It fails when a translation file or a `TEXT` language misses a key, has one too many, loses a placeholder such as `{name}`, uses the wrong form of address, or when a translation file has no `TEXT` language or the other way round. So a pull request that adds a text adds it to every language, and one that removes a text removes it everywhere. If you do not speak a language, ask in the pull request; a maintainer or a native speaker adds the missing texts before the merge.

A new language needs its translation file, its `TEXT` entry, the language in the list of `test_the_cards_speak_every_language_of_the_integration`, its month names and date format for the highlight gallery in `media_source.py` and a line in the documentation's [language section](docs/README.md#languages). The card picks a language by Home Assistant's language code, so `es` also serves `es-419`. The blueprints stay English because Home Assistant does not translate blueprints.

Style of the languages:

- Speak to the user as Home Assistant does in that language: informally in German ("du"), Dutch ("je") and Spanish ("tú"), formally in French ("vous"). French puts a no-break space (`\u00a0`) before `:`, `;`, `?` and `!`; Spanish opens questions with `¿`. The tests check both.
- Keep the darts terms players use in that language, and the English ones where they do: leg, set, bull, 180, game shot, double out. Game names such as Around the Clock, Bob's 27 or Shanghai stay English.
- Use one term for one thing throughout. The glossaries: German "Aufnahme" for a visit, "Übungsspiel", "Doppelquote"; Dutch "beurt", "uitgooi", "dubbel", "oefenspel", "bullen"; French "volée", "manche" for a leg, "finish", "partie"; Spanish "tirada", "cierre", "doble", "partida".
- The `say_*` texts are spoken by the caller; write them as a caller would say them.
- `practice_entity` in `TEXT` says how the names of the practice entities read, for example `Practice {name}` or `{name} de la partie`, so the automatic dashboard can show them without the section they sit in. Keep it in line with the entity names of the translation file.

The documentation is English with a complete German translation in `docs/de/`. A pull request that changes a page changes both languages.
