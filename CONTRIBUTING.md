# Contributing

Contributions are welcome through issues and pull requests.
Participation follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and project decision-making is described in [GOVERNANCE.md](GOVERNANCE.md).
Use [SUPPORT.md](SUPPORT.md) to choose the correct public support channel and [SECURITY.md](SECURITY.md) for private vulnerability reports.

<<<<<<< before updating
All changes, including the releases, reach the protected `main` branch through pull requests. Pull requests must pass every required check before they are merged.
=======
All changes reach the protected `main` branch through pull requests that pass every required check.
Coding agents find these rules in short in [AGENTS.md](AGENTS.md), with the files that belong to the blueprint and are changed there.
>>>>>>> after updating

## Requirements for changes

- New functionality and bug fixes must include automated tests. Use pytest for integration behavior and extend the Docker end-to-end test in `tests/e2e/` when a user-visible Home Assistant flow changes.
- Code must pass Ruff (lint and format) and strict mypy with the rules configured in `pyproject.toml`, keep the test coverage of every line and branch at 100 %, and remain compatible with the Home Assistant version used by the tests.
- The JavaScript of the cards and of their tests must pass ESLint with the rules of `eslint.config.mjs`. Dashboard card changes need Node tests in `tests/frontend/` and, for visible changes, the browser test in `tests/e2e/browser.py`.
- Blueprint changes need tests in `tests/test_blueprints.py`, which run the blueprints through Home Assistant's automation engine. The import buttons and the `source_url` of every blueprint point to `main`, so whoever imports or re-imports a blueprint between two releases gets the one on `main`, while HACS installs the latest release of the integration. A blueprint on `main` therefore keeps working with the latest release: a change that needs events, attributes or actions of an unreleased version is merged together with its release, or the blueprint's description names the version it needs. New inputs get defaults that keep existing automations working as before.
- Tests keep working under the weekly [mutation tests](docs/development.md#mutation-tests), which run them several times in one process and in processes forked from it, against changed code in a copy of the repository: a test leaves its parameters unchanged, and one that reads the code as text or asks Git is marked `@pytest.mark.mutation_unsafe`.
- User-facing text belongs in `strings.json` and every translation, card texts in every language of `TEXT`; see [Translations](#translations).
- Update the README and `docs/` when behavior, setup, or supported versions change. The documentation is English, with a German translation next to each page (`docs/games.de.md` next to `docs/games.md`); update both. Regenerate screenshots with `bash tests/e2e/screenshots.sh` when a visible card or dialog changes.
- Local Board Manager communication must not log, store, or expose the board API key. Cloud tokens remain in the config entry.
- Every commit carries a [Developer Certificate of Origin](https://developercertificate.org/) sign-off, `Signed-off-by: Your Name <you@example.com>`, which `git commit -s` adds.
- Name the issue that a pull request fixes with `Fixes #123` in its description. The issue stays open until a release ships the fix and then closes with a link to the release.

## Tests

New functionality comes with tests in the automated test suite, in the same pull request, and so does every change of behavior. A bug fix comes with a test that fails without the fix, so that the bug can't return unnoticed. `scripts/check.sh` fails when a line or a branch of the code runs in no test. A pull request without the tests it needs is not merged.

## Coding standards

- **Python** follows [PEP 8](https://peps.python.org/pep-0008/) in the format of [Ruff](https://docs.astral.sh/ruff/), which matches Black, with the rules of Ruff that `pyproject.toml` selects. The code has type hints, which mypy checks in its strict mode.
- **The integration** keeps the rules that hassfest checks for Home Assistant and the HACS action for HACS, such as those of its manifest, translations and services.
- **Shell scripts** pass [ShellCheck](https://www.shellcheck.net/), **workflows** pass actionlint and zizmor's audit of their security, and **Markdown** follows the rules of markdownlint in `.markdownlint.jsonc`.
- **Every text file** has LF line endings, no trailing whitespace and a line break at its end; `.editorconfig` sets up most editors for it.

`scripts/check.sh` and the Lint workflow check these standards on every pull request, which merges only when they pass. An exception to a rule is rare and is marked at its place in the code, with its reason in a comment.

## Workflow

<<<<<<< before updating
1. Open an issue or a discussion first for anything larger than a small fix, so we can agree on the approach.
2. Fork the repository and create a branch from `main`, for example `feat/cricket-variants` or `fix/bull-off-tie`.
3. Describe what changes for users under `## Unreleased` in `CHANGELOG.md`, in the words of a user and with the number of the pull request, as the sections of the earlier versions do. A tester who helped is thanked there by their GitHub name. The check *changelog* asks for it in every `feat`, `fix` or `perf` pull request.
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`, `refactor:` or `perf:`, with an optional scope such as `feat(scoreboard): …`. Mark breaking changes with `!`.
5. A change that makes or changes a decision that shapes the project, such as a supported platform or the way of releasing, records it in [`docs/decisions/`](docs/decisions/README.md).
6. Open a pull request with a Conventional Commit title. A workflow checks the title and labels the pull request. Pull requests are squashed into one commit on `main`, and the title decides the next version: `fix` a patch, `feat` a minor, `!` a major version.
7. The maintainer reviews every pull request for correctness, tests, documentation in both languages, security and user impact.
=======
1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Create a branch from `main`.
3. Describe what changes for users, in the words of a user, in a new file in `changelog.d/` named after your branch without its type, such as `changelog.d/dark-mode.md` for the branch `feat/dark-mode`, below the heading of its kind of change, such as `### Features` or `### Bug fixes`. The check *changelog* asks for it in every `feat`, `fix` or `perf` pull request, and checks it as the release takes it in. A file of its own conflicts with no other pull request; a line under `## Unreleased` in `CHANGELOG.md` works as well, but conflicts with each pull request that adds one at the same place.
4. A change that makes or changes a decision that shapes the project, such as a supported platform or the way of releasing, records it in [`docs/decisions/`](docs/decisions/README.md).
5. Open a pull request whose title is a [Conventional Commit](https://www.conventionalcommits.org/), such as `feat(settings): add a dark mode` or `fix: keep the token secret`. Mark a breaking change with `!`. Pull requests are squashed into one commit named after the title, and the title decides the next version: `fix` a patch, `feat` a minor, `!` a major version.
>>>>>>> after updating

### The changelog

A fragment holds the entries of one pull request, each below the heading of its kind of change:

```markdown
### Features

- **Dark mode:** the settings follow the theme of the system.
```

The headings are those of the blueprint, `Breaking changes`, `Features`, `Changes`, `Bug fixes` and `Performance`, those of [Keep a Changelog](https://keepachangelog.com/), `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` and `Security`, and every other one that `CHANGELOG.md` has already. The release bot moves the entries of every fragment and of Unreleased into the section of the next release, each kind of change below one heading, and deletes the fragments in the same commit of the release pull request. `python3 .github/blueprint.py fragments` checks them as the release takes them in.

## Checks

Before opening a pull request, run the checks of the CI, then the end-to-end and the browser test:

```bash
python3.14 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.txt
npm ci
. .venv/bin/activate && bash scripts/check.sh
BOARD_MANAGER=2 bash tests/e2e/run.sh
bash tests/e2e/browser.sh
```

`scripts/check.sh` runs the text checks, Ruff, strict mypy, pytest with every line and branch covered, and in `scripts/check-project.sh` the tests of the cards with Node. To run it before every push on its own, turn on the hook of the repository once: `git config core.hooksPath .githooks`. The end-to-end and browser tests require Docker with Compose. The [development guide](docs/development.md) describes every tool, including the demo instance.

Git runs the hook only when its file is executable. Windows has no such mode and adds the file as a plain one, which `scripts/check.sh` reports; `git update-index --chmod=+x .githooks/pre-push` and a commit make it executable.

Do not include real credentials, board IDs, API keys, private network addresses, or logs containing personal data. Use reserved documentation addresses such as `192.0.2.10` and clearly synthetic values in tests and documentation.

The development container in `.devcontainer/` sets up Python 3.14, Node.js 24 and Docker in one step, for VS Code and GitHub Codespaces, and `bash scripts/check.sh` runs in it. Optional pre-commit hooks run Ruff and basic file checks before each commit: `pip install pre-commit && pre-commit install`.

## Translations

The integration speaks English, German, Dutch, French and Spanish. Its texts live in two places:

- `custom_components/autodarts/strings.json` with the English source, copied unchanged to `translations/en.json`, and one file per language in `translations/` with the same keys in the same order;
- the `TEXT` dictionary of `custom_components/autodarts/frontend/autodarts-card.js`: `TEXT.en` and one entry per language with the same keys in the same order.

`tests/test_consistency.py` keeps every language complete. It fails when a translation file or a `TEXT` language misses a key, has one too many, loses a placeholder such as `{name}`, uses the wrong form of address, or when a translation file has no `TEXT` language or the other way round. So a pull request that adds a text adds it to every language, and one that removes a text removes it everywhere. If you do not speak a language, ask in the pull request; a maintainer or a native speaker adds the missing texts before the merge.

When an English text changes, change its translations in the same pull request. If you can't, the [translation bot](docs/development.md#translation-bot) opens an issue for each language with outdated or missing texts and asks native speakers for them. A translation that stays right after an English change is marked with a line such as `Translations-checked: de fr status_ready` in the description of the pull request: the languages first, then the keys, or no keys for every text of the languages.

A new language needs its translation file, its `TEXT` entry, the language in the list of `test_the_cards_speak_every_language_of_the_integration`, its month names and date format for the highlight gallery in `media_source.py` and a line in the documentation's [language section](docs/README.md#languages). The card picks a language by Home Assistant's language code, so `es` also serves `es-419`. The blueprints stay English because Home Assistant does not translate blueprints.

Style of the languages:

- Speak to the user as Home Assistant does in that language: informally in German ("du"), Dutch ("je") and Spanish ("tú"), formally in French ("vous"). French puts a no-break space (`\u00a0`) before `:`, `;`, `?` and `!`; Spanish opens questions with `¿`. The tests check both.
- Keep the darts terms players use in that language, and the English ones where they do: leg, set, bull, 180, game shot, double out. Game names such as Around the Clock, Bob's 27 or Shanghai stay English.
- Use one term for one thing throughout. The glossaries: German "Aufnahme" for a visit, "Übungsspiel", "Doppelquote"; Dutch "beurt", "uitgooi", "dubbel", "oefenspel", "bullen"; French "volée", "manche" for a leg, "finish", "partie"; Spanish "tirada", "cierre", "doble", "partida".
- The `say_*` texts are spoken by the caller; write them as a caller would say them.
- `practice_entity` and `tournament_entity` in `TEXT` say how the names of the practice and tournament entities read, for example `Practice {name}` or `{name} de la partie`, so the automatic dashboard can show them without the section they sit in. Keep them in line with the entity names of the translation file.

The documentation is English with a complete German translation. Each German page sits next to its English page, with the English name and `.de`, such as `docs/games.de.md` next to `docs/games.md`, and links to German pages by those names. A pull request that changes a page changes both languages. Keep the terms of the [glossary](docs/glossary.md) ([German](docs/glossary.de.md)), for example "Übungsspiel", "Aufnahme" for a visit and "Doppelquote". `tests/test_docs_links.py` checks that every link, heading anchor and image resolves.

## When a check fails

A check that fails explains itself. The PR coach writes what the check found, why that matters and how to fix it, with the commands to run, into the summary of the check and as its annotation; the pull request also shows the annotations of a tool at the lines that it names. After the checks, the coach keeps one comment on the pull request up to date with a section for each check that failed, also on a pull request from a fork, and a title that is no Conventional Commit gets one that passes. The comment follows every push and says so once every check passes. On your machine, `scripts/check.sh` explains the step that stopped it in the same words.

The explanations are in `.github/checks.toml`, which the blueprint keeps current, and in `.github/checks.project.toml` for the checks of this project alone, whose explanations win. A check that you add to the required checks of `.github/repository.project.toml`, or that `scripts/check-project.sh` runs, comes with its explanation in `.github/checks.project.toml`, in the same pull request: what it found, why that matters and how to fix it, with the commands and a link to read more. `python3 .github/blueprint.py coach verify` lists every required check and every step of `scripts/check.sh` without one. The comment follows the workflows of the checks that the blueprint sets up; for a workflow of this project alone, such as one of visual tests, name it in the answer `test_workflows` of `.copier-answers.yml`, which the next update of the blueprint brings into `.github/workflows/after-checks.yml`.

## Website

MkDocs builds the website from `mkdocs.yml` and the pages in `docs/`, the English one at <https://dennis-otto.github.io/ha-autodarts/> and the German one from the `.de` pages under `/de/`, with a switch between the two on every page. It starts with `docs/index.md` and `docs/index.de.md`; `docs/README.md` and `docs/README.de.md` are the overviews on GitHub. The check *docs* builds it strictly in every pull request, so that a broken link fails, and every change of `main` publishes it on GitHub Pages. To see it while you write, at <http://127.0.0.1:8000>:

```sh
python3 -m venv .venv-docs
.venv-docs/bin/pip install --require-hashes -r .github/docs-requirements.txt
.venv-docs/bin/mkdocs serve
```

On Windows, use `py -3` in place of `python3` and `.venv-docs/Scripts/` in place of `.venv-docs/bin/`; the dev container sets these tools up on its own. With them, `bash scripts/check.sh` builds the website strictly as well, as the check *docs* does, and without them it leaves that to the CI. The preview cards for social media come from the CI alone, because they need the Cairo library, which Windows doesn't have; where it is installed, `CI=true` before the command draws them too.

## Pages in one column

The READMEs, this guide and the pages of `docs/` have one column, so that they read well in the GitHub app and on a phone, which keep columns side by side and squeeze them until the text is a few words wide and the pictures tiny:

- A table holds tabular data, never a layout: no `<table>` that sets a picture beside text, and no `<td width="…">`.
- A picture or a GIF comes at full width below the text that it illustrates.
- A long list, such as every option or every entity, goes into `<details>` with a `<summary>` that names it, so that the page stays short.

`scripts/check.sh` fails on a `<table>` with a picture and on a cell with a width in a README, a CONTRIBUTING file or a page of `docs/`, with its file and line. `python3 .github/blueprint.py pages --fix` puts the cells of such a table one below the other, the text before its picture, and leaves out the widths; a table inside a table it leaves to you.

## Diagrams

The GitHub app, the stores of the projects and other renderers of Markdown show a `mermaid` block as code, so a diagram is a picture of its source. The source is Mermaid in `docs/diagrams/<name>.mmd`, and `bash scripts/diagrams.sh` draws it, with Docker, as `docs/images/diagrams/<name>.svg` on a white card and `<name>.dark.svg` for a dark theme. The Markdown shows them with paths from its own folder, and the website draws the source itself:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/diagrams/<name>.dark.svg">
  <img src="docs/images/diagrams/<name>.svg" alt="The title of the diagram: its description">
</picture>
```

- A diagram runs from top to bottom (`flowchart TB`), so that it keeps its size in a narrow column and on a phone, and has `accTitle` and `accDescr` for screen readers, which the `alt` of its picture repeats.
- Labels are text in the pictures: `<br>` breaks a line, and a label in `` "`…`" `` takes `**bold**` and `*italic*`.
- Colors are tints that read in the light and the dark theme, the same in every repository made from the blueprint: blue (`#526cfe`) the blueprint and its bots, orange (`#f59e0b`) you and what is yours, green (`#16a34a`) what comes out, as in `classDef bot fill:#526cfe2e,stroke:#526cfe,stroke-width:2px`.
- A diagram of a German page is `<name>.de.mmd`. A diagram in a README that has a German twin, `README.de.md`, comes in both languages.
- `bash scripts/diagrams.sh --extract` turns every `mermaid` block of the Markdown into a source and its picture. `scripts/check.sh` fails on a `mermaid` block once a page shows a picture of a diagram, and on a source or a picture without the other.
- The check *diagrams* draws the pictures anew when a pull request changes a diagram or adds a `mermaid` block. On a branch of this repository, the diagram bot commits the sources and pictures that it made, with a comment that names the pages it changed, so you need no Docker for a diagram: change its source and push. When the bot can't commit, it says so in a comment on the pull request. For a fork, the summary of the check lists the files and the command, and the run keeps them as its artifact.
- On `main`, the Diagrams workflow draws every diagram after each change of a diagram or a new `mermaid` block, and every week, and keeps one pull request from the branch `bot/diagrams` with what is left, which merges itself once every check passes; without the release app, the run warns and names the command instead. A failed run opens an issue, which the weekly run closes once the bot passes again.

## Releases

<<<<<<< before updating
The release bot keeps a pull request titled `chore: release x.y.z` with the next version, up to date with `main` and decided anew with every merge. Its section of the changelog is the text of Unreleased; without one, it lists the pull requests. Merging it creates the release with the package for HACS, its SBOM and its signed provenance; the [release guide](docs/releases.md) describes every step. A release of dependency updates merges and publishes itself.

A line `Release-As: 2.0.0-beta.1` in the description of a pull request sets the version of the next release, for a beta for example, which HACS offers only with its beta switch on. A prerelease keeps the text of Unreleased for the release that follows it.
=======
The release bot keeps a pull request titled `chore: release x.y.z` with the next version, up to date with `main` and decided anew with every merge. Its section of the changelog is the text of the fragments in `changelog.d/` and of Unreleased, and it deletes the fragments; without such text, it lists the pull requests. Merging it creates the release with its package, SBOM and signed provenance, and delivers it to HACS. A release of dependency updates merges and publishes itself.

A line `Release-As: 2.0.0-beta.1` in the description of a pull request sets the version of the next release, for a prerelease for example. A prerelease leaves the fragments and the text of Unreleased to the release that follows it.
>>>>>>> after updating

By contributing, you agree that your contribution is licensed under the [MIT license](LICENSE) of this project.
