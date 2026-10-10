# Development

[← Documentation](README.md)

## Project layout

| Path | Contents |
| --- | --- |
| `custom_components/autodarts/` | The integration |
| `custom_components/autodarts/frontend/autodarts-card.js` | The seven dashboard cards, served by the integration |
| `blueprints/automation/autodarts/` | Automation blueprints |
| `tests/` | Unit and integration tests with `pytest-homeassistant-custom-component` |
| `tests/frontend/` | Node tests of the card logic and of every card element in a browser DOM, including property-based tests with fast-check, and of the translation bot |
| `tests/e2e/` | Docker end-to-end test, demo instance, browser test and screenshot tool |
| `docs/` | Documentation and the [website](https://dennis-otto.github.io/ha-autodarts/), each German translation next to its page as `<name>.de.md` |
| `scripts/` | The checks, the [translation bot](#translation-bot) and the tools for media and diagrams |
| `.github/` | Workflows, issue forms, the labels in `labels.toml` and the settings of the [issue assistant](#issue-assistant) in `issue-assistant/` |

## UI building blocks

The cards are made of shared building blocks in `autodarts-card.js`: a change to a block reaches every card, and `tests/frontend/building-blocks.test.mjs` fails where a card leaves one out. Use them instead of styling a part anew.

Nothing may move while a game goes on. A line that comes and goes, such as a route, a note or the details of a player, keeps its room while empty (`.route-line`, `.details-line`), and a narrow tile keeps two lines where a long one could wrap. A control that shows only at times takes the place of something, not a row of its own: the undo of the last visit is the tile beside the darts. The browser step *steady heights* checks it.

| Block | Where | Rule |
| --- | --- | --- |
| Control | `BASE_CSS`, every `button` | Answers every pointer: a tint under a mouse, a slight press for a finger, a focus ring for a keyboard; a disabled one fades. The second tap that confirms (`confirm` class) is red on every card. |
| Motion | `BASE_CSS`, `--ad-fast`, `--ad-slow`, `--ad-ease` | States glide; what appears as a whole fades in from a little below (`appear` class, with `@starting-style`). Parts drawn anew with every tap, such as the pad's keys, do not fade in, or they would flicker. `prefers-reduced-motion` turns motion off. |
| Cue | `cueHtml("edit" \| "details" \| "expand" \| "undo", inline)` | What a tap edits shows a pencil at its top right, what a tap opens shows an arrow, what opens below it an arrow down that turns once open, what a tap takes back a curved arrow. Static parts show none. |
| Tile | `.tappable` | A tile a tap does something with has a frame, which a pointer lights up, and a cue; a static tile is a tinted area without a frame. |
| Status | `.pill` | A glowing dot and its words, never the shape of a button. It keeps the width of the longest words it takes during a game. |
| Hint | `CardBase._initHints`, `.hint-bubble` | A `title` is the tooltip for a mouse; a tap with a finger or a pen on the same element shows it in a bubble over the card, unless the element is a control. Give information a `title` and nothing else. |
| Tag | `.bed` | A framed label such as a bed of a route, never filled like a button; the one that comes next is tinted and bold. |
| Link | `.link` | A control that looks like text, with a cue after it, for the details of what stands above it or for more below it. |
| Segmented control | `SEGMENTED_CSS`, in `BASE_CSS` | One of a few views at a time: the heatmap's mode, whose darts, the period, the pad's keys or board. |
| Balanced grid | `balancedCss(selector, min, gap, padding)`, class `balanced n4` | Tiles in rows as even as they can be; a shorter last row stands in the middle or its last tile fills it. |
| Pad | `PadCard`, `padHtml`, `PAD_CSS` | Correcting a dart of the visit on the live card and the scoreboard: keys or board, loupe, pinch and zoom. |
| Icons | `ICON_PATHS` | Lines in the colour of their text. |

## Tests

Python 3.14 and Node.js 24:

```sh
python3.14 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements-test.txt
npm ci
. .venv/bin/activate && bash scripts/check.sh
```

`scripts/check.sh` runs what the CI runs: the text checks, the version of every file, ShellCheck, Ruff, strict mypy and pytest, failing below 100 % line and branch coverage; then `scripts/check-project.sh` checks the MIT terms of both licenses, lints the JavaScript with ESLint's recommended rules (`eslint.config.mjs`) and runs `npm test`, the tests of the cards with fuzzing by fast-check and those of the [translation bot](#translation-bot), failing below 100 % lines, branches and functions. `git config core.hooksPath .githooks` runs it before every push. The [repository blueprint](https://github.com/Dennis-Otto/repo-blueprint) keeps `scripts/check.sh` and the workflows the same in every repository; what only this integration needs belongs in `scripts/check-project.sh`, `e2e.yml` and `translations.yml`.

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
- every dashboard card, card form and the dashboard strategy with its editor, rendered in a [happy-dom](https://github.com/capricorn86/happy-dom) browser DOM against a simulated Home Assistant: every game, every option, every language, controls with their confirmation, the caller and escaping of player names;
- the documentation: every relative link, heading anchor and image of the Markdown files resolves, the repository's own absolute links in the README lead to existing files, every image has a description and exists in both languages, and the card picker links to existing sections (`tests/test_docs_links.py`).

The card logic is also fuzzed with [fast-check](https://fast-check.dev/): thousands of random and hostile inputs per run check that escaping, bed geometry, the heatmap and the history parser never break.

## Docker end-to-end test

The [end-to-end test](https://github.com/Dennis-Otto/ha-autodarts/blob/main/tests/e2e/README.md) starts a real Home Assistant container with this integration and a simulated Board Manager. It runs onboarding, setup, all controls, realtime darts, persistence, diagnostics and removal. The simulated Board Manager also injects faults on request (`POST /control/fault`): dropped or refused sockets, failing or slow reads, malformed frames, a restart and the takeout Board Manager 2.0.2 sometimes never finishes; the test checks that visits and entities come through them and that the integration frees the takeout:

```sh
BOARD_MANAGER=1 bash tests/e2e/run.sh
BOARD_MANAGER=2 bash tests/e2e/run.sh   # includes discovery by mDNS
```

## Demo instance and browser test

`tests/e2e/demo.sh` starts Home Assistant with a simulated board, a finished training session, twelve weeks of practice of three made-up players, a week of sessions and matches in the training calendar, four weeks of long-term statistics for the graphs, players linked to persons with pictures, highlight photos, an automation from the weekly report blueprint and a dashboard with all cards at <http://127.0.0.1:18124/autodarts-demo/board>. Login is not needed from the local network.

`tests/e2e/browser.sh` checks the cards in Chromium against the demo:

- the cards are registered on every load;
- the live visit, highlights and controls with confirmation;
- the practice game, match and training games;
- the training heatmap with dart positions, history and sessions, and the status card;
- the scoreboard and its caller, the players card with badges and trends, the leaderboard, the doubles card, and the download of the players export;
- the generated dashboard, the forms of all seven cards, the strategy editor and the light theme;
- the new game screen, scoreboard, keypad and tournament on an 800 × 480 tablet, without sideways scrolling and with targets of at least 44 px, and idle mode on a device that asks for reduced motion;
- touch screens driven by taps: an iPhone with the safe areas of its status bar and home indicator, a small Android phone, an iPhone on its side and a 24 inch touch monitor, with a theme of see-through cards. Every game of the new game screen is tapped, a match is started, played and ended there, and four players with long names play X01 and Cricket. On the board of the keypad two fingers zoom in and a finger aims with the loupe and enters a treble 20 where it lets go; the board to correct a dart opens zoomed in on a small screen, and a tap corrects it. The scoreboard has to stay one screen high above the home indicator, the start bar has to cover what scrolls beneath it, and the board may neither cover a key nor draw beyond its box;
- every view of both dashboards and the scoreboard's own screens, with the scoreboard during a game, the keypad's board and the board of a correction, on nine sizes, from a small phone to a 27 inch touch monitor, both ways round and in German, and on the phones the scoreboard during a game in English, Spanish, French and Dutch too: no card wider than the screen, no text cut off, lying on other text, running over the edge of its tile or smaller than 11 px, no row of buttons running over its edge, no control smaller than 40 px on a touch screen, and no full-height scoreboard below the screen;
- steady heights: X01 with routes, setups, a bust and the game shot, a match of legs and sets, Cricket, Tactics, Killer and 121 checkout, dart by dart on four sizes in German. From the start of a game to its last dart, no card and no part of the scoreboard may change its height, on the live card beside the scoreboard, the full-height scoreboard and the live card with its game;
- accessibility: every card meets WCAG 2.1 at levels A and AA, checked by [axe-core](https://github.com/dequelabs/axe-core) on a laptop and an iPhone in the dark and the light theme (see [Accessibility check](#accessibility-check));
- a browser in Dutch, French and Spanish, which gets the cards and the entity texts of Home Assistant in its language.

While working on a screen, `BROWSER_STEPS` runs only the steps whose names begin with one of the given ones, such as `BROWSER_STEPS="touch screens,every screen size,correcting"`, and fails on a name that begins no step; `BROWSER_SCREENS` only some of the sizes, such as `BROWSER_SCREENS=iPhone`. With `BROWSER_SCREENSHOTS=1` the size check keeps a full-page screenshot of every view and size in `tests/e2e/artifacts/screens/`, to look at by eye.

### Accessibility check

The browser step *accessibility* runs [axe-core](https://github.com/dequelabs/axe-core) over every card of every view of both dashboards, the idle screen, a practice match on the live card and the scoreboard's own screens: the new game screen, the keypad and its board to tap, the board of a correction and Cricket. It does so on a laptop (1280 × 800) and an iPhone (393 × 852) with touch, each in the dark and the light theme, against the rules of WCAG 2.1 at levels A and AA, such as the contrast of text, names of controls and roles, and keyboard access to what scrolls.

- A serious or critical violation fails the step, with the screen, the view, the card, the rule, the element and what is wrong. Moderate and minor ones are listed in the log.
- `tests/e2e/accessibility-baseline.toml` lists the violations that are accepted for now, each with its reason: an entry names the rule, the card and a `target` that is part of the selector axe-core gives the element. The step names an entry that no longer occurs, so that it goes. The list is empty: every card passes.
- The step keeps every violation and every view it checked in `accessibility.json`, with the other artifacts of the browser test.

axe-core comes from `package.json`, pinned in `package-lock.json`, so run `npm ci` before `browser.sh`, as the CI does; `BROWSER_STEPS=accessibility` runs the check alone. Fix a violation in the card rather than accepting it: muted words take `--ad-muted-text` of the [building blocks](#ui-building-blocks), which keeps the contrast in both themes and on the tint of a tile, every control has words or an `aria-label`, and what scrolls can be reached with the keyboard.

When a step fails, the browser test saves a screenshot of every open page, and
the scripts save the Home Assistant log, in `tests/e2e/artifacts/` or in the
folder named by `E2E_ARTIFACTS`. CI keeps them as a workflow artifact for 14 days.

## Screenshots

`tests/e2e/screenshots.sh` regenerates every image in `docs/images/en` and `docs/images/de` from the demo, including the animated WebP images, and compresses the PNG images with pngquant. `tests/e2e/screenshots.py` has one function per image or animation, so a single image can be regenerated by calling its function against a running demo. Every image shows the simulated board and synthetic players, so no personal data can appear; the secret address of the online bridge is masked. The tool never opens the network search, which would list real boards. The diagrams in `docs/images` come from `scripts/render_diagrams.sh` instead (see [Diagrams](#diagrams)).

When a capture fails, the tool saves every open page in `tests/e2e/artifacts/`. Keep your own debug screenshots there as well: Git ignores that folder and PNG files directly in `tests/e2e/`.

### The same images in every run

Two runs of the tool render the same images, byte for byte. So an image that changed always shows a card or a screen that changed, and the [screenshot bot](#screenshot-bot) and the [visual check](#visual-check) can tell:

- **A frozen clock.** The demo of the screenshots stands at Tuesday, 29 September 2026, 20:30 (`DEMO_TIME` in `screenshots.sh`), whenever it runs. `tests/e2e/frozen/sitecustomize.py` sets this clock for Home Assistant and every script in its container, through `compose.frozen.yaml`, which `demo.sh` adds when `DEMO_TIME` is set. The clock moves only when the demo moves it: every move at the simulated board, a dart, a takeout or a new status, takes two seconds, in `demo.py` as in `screenshots.py`, written into the file `.demo_clock` in the configuration of the demo. So every time Home Assistant records comes out the same in every run, to the millisecond, while the history of the board, the length of a session and the training time of the weekly report look like a real evening; the weekly report gets the minute it waits for in the same way. The browser shows the time of the demo too: Playwright's clock stands still at it, except in the pages of the game animations, where the result of a tournament match has to show for its time; their frames show no time. The page of the statistics graphs asks for reduced motion, so that Home Assistant draws their lines at once instead of as an animation, which the standing clock would stop.
- **One source of changes.** The frozen demo doesn't poll the board: every change comes over the board socket, in the order the board sends it, never first from a poll whose moment depends on the run.
- **Fixed random numbers.** The darts of the bot, and every other random number without a seed of its own, start from the same seed.
- **Still pictures.** Before every screenshot and every frame of an animation, the tool waits for pictures that are still loading, lets transitions and fade-ins jump to their end and stops endless animations, such as the blinking beds, at the same moment. It goes on until a card has stopped changing and two looks a tenth of a second apart find nothing moving. Chromium draws every picture whole and animates on its main thread (`STEADY_CHROMIUM` in `screenshots.py`). The toolbar of a dashboard casts no shadow on what scrolls beneath it, a card taller than the screen is taken from the top of the page, and the dialog of the board's events opens once the recorder has written the history it shows.
- **Fixed addresses.** The online bridge shows `homeassistant.local` as the address of Home Assistant (`internal_url` in `demo.configuration.yaml`), not the address Docker happens to give the container.
- **Pinned compression.** pngquant 2.18.0 of Ubuntu 24.04 compresses every PNG image right after it is taken. `tests/e2e/pngquant.sh` installs it in the pinned Playwright image from Launchpad, where every published package keeps its address, and checks both packages against their SHA-256. The animations come from the pinned Pillow.

To find out what differs between two runs, `KEEP_RAW=1` keeps every image and every frame of an animation as taken, before compression, in `tests/e2e/artifacts/raw/`, one folder per language; `tests/e2e/compare.py` compares two folders of images.

Without `DEMO_TIME`, as in `demo.sh` for a preview or in `browser.sh`, the demo runs on the real clock.

### Screenshot bot

The **Screenshot bot** workflow (`.github/workflows/screenshots.yml`) keeps the images current. After a change of the cards (`custom_components/autodarts/frontend/`) or of the screenshot tool (`tests/e2e/`, except the browser test and the end-to-end test) reaches `main`, every Thursday and on demand, it renders every image of both languages anew with `tests/e2e/visual.sh`, one job per language, and compares them pixel by pixel with the committed ones. An image whose pixels stayed the same keeps its file.

When any image changed, the bot opens one pull request, *docs: update the screenshots of the cards*, or updates the one still open, and turns on auto-merge, so the images follow once every check passes. The description lists every changed image with the share of its pixels that changed; the workflow run keeps the images before and after, with their differences, for three days. The pull request comes from the release app, so its checks run, and its commits go through GitHub's API: GitHub signs them, as `main` requires, and they carry the app's `Signed-off-by:`. When `main` already has the images of a pull request still open, the bot closes it. The rendering runs without any secret; only the last job, which writes the pull request, uses the key of the release app in the environment `release`.

### Visual check

The **Visual check** workflow (`.github/workflows/visual.yml`) renders the images the same way for every pull request that changes the cards or the screenshot tool, and compares them with the committed ones. It only reports, because an intended change reaches `docs/images` through the screenshot bot after the merge:

- the summary of each job lists every image that looks different, with the share of its pixels that changed;
- the artifacts `visual-en` and `visual-de` keep every changed image before and after, and a picture of the difference: the new image in grey, with every changed pixel in red;
- the **Visual check comment** workflow (`visual-comment.yml`) writes the list into one comment on the pull request, with links to the artifacts, and updates it after every run.

An image that can't be rendered fails the check. The comment workflow starts when a check ends (`workflow_run`), so that it may comment on pull requests from forks as well, but it never checks out or runs their code: it reads only the reports of the check, takes nothing from them but image names and numbers it checks, and writes the comment itself. The check runs only when its files change, so it is no required check.

The same comparison runs locally; it leaves the new images in `docs/images` and the report in `tests/e2e/artifacts/visual/`:

```sh
LANGUAGES=en bash tests/e2e/visual.sh
git checkout -- docs/images   # back to the committed images
```

`scripts/creator_media.py` turns five of the animations into the MP4 and GIF files of the [creator kit](creator-kit.md#videos-and-animations) in `docs/media/`, for Reddit, Discord, forums and video editors, which don't all show animated WebP. Run it after the screenshots whenever one of those animations changes; it needs Pillow and ffmpeg, and a test fails when a video no longer has the length of its animation.

Keep animations short, below about 20 seconds and 1 MB, and give every image a descriptive `alt` text in both languages. The README uses absolute `raw.githubusercontent.com` addresses and plain `<img>` tags, because HACS shows it outside GitHub; the pages in `docs/` use relative paths and may use `<picture>` for light and dark variants.

## Diagrams

The architecture diagram is written in Mermaid in `docs/diagrams/` and rendered as PNG images for light and dark themes, because the GitHub app and HACS do not render Mermaid. After changing a diagram, run:

```sh
bash scripts/render_diagrams.sh
```

## Continuous integration

Every pull request, and every push to `main`, runs:

- pytest on every core with a coverage gate, Ruff, strict mypy and the Node tests, with the coverage report in the job summary;
- the Docker end-to-end test against both Board Manager generations, the browser test,
  and both again against Home Assistant 2026.8.0, the oldest supported release;
- the [visual check](#visual-check) of the documentation images, when a pull request changes the cards or the screenshot tool;
- HACS validation and hassfest;
- actionlint, CodeQL for Python, the card JavaScript and the workflows, and dependency review;
- Gitleaks and an SPDX SBOM.

A new commit to a pull request cancels the older, still running checks of that
pull request; runs on `main` are never canceled. Every Monday the end-to-end tests
also run against the current Home Assistant beta, as an early warning before the
next release. Pull requests replay the same derandomized Hypothesis examples on
every run; every night the **Property tests** workflow runs the property and
state-machine tests with a new random seed. Its summary names the seed, and
running the workflow with that seed replays a failure. OpenSSF Scorecard evaluates
the repository weekly and on every push to `main`.

Pull request titles follow Conventional Commits. The **Pull request title**
workflow checks the title and sets its label; the title decides the next version
(see the [release guide](releases.md)).

Dependencies are pinned:

- Actions by commit hash, and container images by digest, including the base image of the dev container in `.devcontainer/Dockerfile`; its Features are locked by digest in `.devcontainer/devcontainer-lock.json`.
- Python tools with hashes, in `requirements-test.txt` (compiled from `requirements-test.in` with `pip-compile --generate-hashes`) and `tests/e2e/requirements-browser.txt`.
- Node tools by `package-lock.json`.

Home Assistant pins its own dependencies exactly, so the test environment can carry a
version with a known advisory that no update here can raise. Such advisories are listed
with their reason in `osv-scanner.toml`, which OSV-Scanner and the OpenSSF Scorecard
read, and in `allow-ghsas` of the dependency review. Each reason starts with the pinned
version, and a consistency test fails as soon as the test base moves past it, so an
exception leaves with the update that fixes it. The integration itself ships no Python
dependencies.

Renovate keeps the Python and Node tools, the Actions, the new commits of the HACS
and hassfest actions, which follow a branch instead of releases, and the images
current, also the Playwright and Mermaid images that the scripts under `tests/e2e/`
and `scripts/` start, and the digest of the dev container's image. It waits seven days
after a release before it proposes a new version; security updates come at once.
Dependabot keeps the dev container's Features. The pngquant packages of
`tests/e2e/pngquant.sh` are updated by hand. Two checks deliberately run moving
images: HACS validation and hassfest always apply the rules that HACS and Home
Assistant use for new submissions today, and the weekly beta run uses the beta tag.

`main` only takes pull requests that are up to date with it, and auto-merge doesn't
update a branch by itself. So after every change of `main`, the branch bot
(`update-branches.yml`) brings each pull request that waits for auto-merge up to date,
as the release app, so that its checks run again and it merges once they pass.

## Issue assistant

The [issue assistant](https://github.com/Dennis-Otto/issue-assistant), a GitHub Action of its own, looks after the issues; the maintainer still reads every issue and has the last word.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/en/issue-lifecycle-dark.png">
  <img src="images/en/issue-lifecycle-light.png" alt="Life of an issue: the form sets the kind, the area and needs-triage; an AI engine posts a first analysis. Missing information marks it needs-info: an answer hands it to the maintainer, after 15 days a reminder follows, after 30 days it closes and an answer reopens it. A sure duplicate gets a notice and closes after 3 days unless someone comments or reacts with a thumbs down. A merged fix marks it fixed-in-next-release; the release closes it with a link, and a comment that it's still broken reopens it." width="640">
</picture>

- **New issues** get the area label from the *Area* field of the bug report and a first analysis by an AI that only reads: a summary, the likely cause with links to the code and the documentation, what to try, the information still missing, and related issues and discussions, in the reporter's language. It chooses the kind, areas and topics from `.github/labels.toml`, with its reason on each label, and may correct the kind while an issue has `needs-triage`.
- **Questions** of the assistant, or a comment of the maintainer that asks the reporter something, mark an issue `needs-info`. An answer, by a comment or an edit, ends the wait, and the assistant follows up on its own questions. After 15 days the reporter gets a reminder, after 30 days the issue closes as not planned, and an answer reopens it.
- **A sure duplicate** of an older, open issue gets a notice and closes, linked to the original, 3 days later unless someone comments or the reporter or maintainer reacts with 👎; a less sure candidate becomes a suggestion in GitHub's panel (`has:suggestions`).
- **A fix** names its issue in the pull request with `Fixes #123`. When the pull request is merged, the issue gets `fixed-in-next-release` and a comment, and stays open: users only get the fix with a release. The first published release that contains it closes the issue as completed, with a link to the release; drafts and pre-releases don't count. The label also works by hand, for a fix without a pull request. If the reporter writes within 30 days that the problem persists, the AI reads the comment and the issue reopens. *Auto-close issues with merged linked pull requests* is off in the repository settings, so that GitHub doesn't close the issue at the merge.
- **Labels** are code: the Labels workflow creates and updates them from `.github/labels.toml` when it changes on `main`.

The four workflows `issue-assistant.yml`, `issue-lifecycle.yml`, `labels.yml` and `findings.yml` are copies of the action's templates, pinned to a release; Renovate proposes new releases, and its routine updates merge on their own. The AI's secret `CLAUDE_CODE_OAUTH_TOKEN` belongs to the environment `issue-assistant`, which only `main` may use. The action's [README](https://github.com/Dennis-Otto/issue-assistant#security) describes the security design: the AI runs with read-only tools and token on the egress-firewall runner, and only checked code writes to GitHub.

What is set here:

| File | Contents |
| --- | --- |
| `.github/issue-assistant/project.md` | What the AI reads about the project before every task: where code, documentation and changelog are, and what matters in a bug report |
| `.github/issue-assistant/config.toml` | The engine (Claude), the hosts links may lead to, the *Area* field of the bug report, and the files that tell reporters which AI reads their issue (`SUPPORT.md` and `docs/troubleshooting.de.md`) |
| `.github/labels.toml` | Every label: the kinds, with `ask = false` for feature requests and tester feedback, the areas with the options of the *Area* field, and the lifecycle labels |
| `.github/findings.toml` | The findings of code scanning that the repository accepts, each with its reason: Scorecard's *Code-Review*, *Branch-Protection* and *Maintained*, which one maintainer of a young repository can't change |

The **Findings** workflow dismisses the accepted findings of code scanning (CodeQL and OpenSSF Scorecard) with their reason and fails while any other finding is open. It names an open finding only by the number and link of its alert, which only maintainers can open, so nothing about a possible vulnerability reaches a public log or issue. A finding is fixed, or accepted in `.github/findings.toml` through a pull request.

The job *issue-assistant* of the **Lint** workflow runs the action's `check`: it fails when a workflow differs from the template of its release, a label or an option of the *Area* field doesn't fit, or the notice to reporters doesn't name the engine. The repository variable `ISSUE_ASSISTANT_AI` set to `off` switches the AI off; labels and the lifecycle keep working.

*Actions → Issue assistant → Run workflow* analyzes an issue again, or runs a follow-up, the check of the maintainer's comment or the check of a comment after the release. The run starts as a dry run: its summary shows the comment and labels it would post. To try a change of `project.md` or the action's prompts locally, see the action's [README](https://github.com/Dennis-Otto/issue-assistant#try-a-prompt-locally).

## Translation bot

The **Translations** workflow (`.github/workflows/translations.yml`) runs `scripts/translations.mjs` after every push to `main` that changes a translation file, the card module or the bot, every Monday, and on *Run workflow*. For each language with texts to fix, it keeps one issue open, such as *Translation: French needs 4 updates · Français : 4 textes à mettre à jour*, written in that language and in English and labeled `translations`, `help wanted` and `good first issue`, so native speakers find it. It closes the issue with thanks once the language is up to date, and opens a new one when texts fall behind again.

- **Missing:** a text of `translations/en.json` (which equals `strings.json`) or of `TEXT.en` that the language lacks. The consistency tests already fail on one; the bot reports it in case one slips through.
- **Outdated:** the English text changed after the language's text last did. The bot reads the first-parent history of `main`, where each merged pull request is one commit, and needs no file to keep: for each text, it takes the newest commit that changed the text in that language, or checked it, and compares the English text of that commit with today's. A change of case alone doesn't count, because each language writes its own, and neither does an English change that was taken back.

A translation that stays right after an English change is checked by a line in the description of the pull request, which becomes the message of its commit on `main`; the issue tells translators the same:

```text
Translations-checked: de fr config.step.user.title status_ready
```

Languages come first, then keys, separated by spaces or commas; without keys, the line checks every text of the languages. GitHub wraps the description at 72 characters when it squashes it into the commit, so the bot reads a line of keys alone whose first key didn't fit on the line before as part of it.

Each issue lists the keys with a link to their line, the English text now and when the language last changed, and the translation, followed by the steps for someone who doesn't program: edit the file on GitHub, open a pull request titled like `fix(i18n): update the French texts`, and find their GitHub name in the changelog. The bot reads `TEXT` of each version of the card module by evaluating its object literal alone, without the rest of the module. It finds its issues by a hidden marker among the open issues of `github-actions[bot]`, and its job may only read the repository and write issues.

`node scripts/translations.mjs` prints the issues it would write, without GitHub. Its tests in `tests/frontend/translation-bot.test.mjs` build temporary git repositories, with merges and checks, and answer as GitHub would; `npm test` covers every line, branch and function of the bot as it does for the cards.

## Releases

See the [release guide](releases.md).

## Conventions

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/), for example `feat:`, `fix:` and `docs:`.
- Python follows Ruff and strict mypy (`pyproject.toml`), JavaScript the recommended rules of ESLint (`eslint.config.mjs`); `scripts/check.sh` fails on either.
- User-facing text goes into `strings.json` and every translation, card texts into every language of `TEXT`; `strings.json` equals `translations/en.json`, and the consistency tests fail until every language has the text ([translations](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CONTRIBUTING.md#translations)). When an English text changes, change its translations in the same pull request, or the [translation bot](#translation-bot) asks native speakers for them.
- New behavior needs tests, and new user-facing features need documentation in English and German.
- A part of a card is built of the [UI building blocks](#ui-building-blocks): what a tap does shows before the tap.
