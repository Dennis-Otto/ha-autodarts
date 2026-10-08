The Autodarts integration connects Home Assistant with Autodarts dartboards: it reads and controls the board through the Board Manager on the board PC, keeps training sessions, practice games, matches, statistics and records locally, and brings its own dashboard cards and blueprints. Its users are dart players with a Home Assistant installation.

Where things are:

- The integration is in `custom_components/autodarts/`, its dashboard cards in `custom_components/autodarts/frontend/autodarts-card.js`, the blueprints in `blueprints/automation/autodarts/`.
- The documentation is in `docs/` in English, with each German page next to its English one as `<name>.de.md`, and on the website <https://dennis-otto.github.io/ha-autodarts/> (German: `/de/`); the troubleshooting guide is `docs/troubleshooting.md` (German: `docs/troubleshooting.de.md`), the plans are in `docs/roadmap.md`.
- `CHANGELOG.md` lists the changes of every release with the numbers of their pull requests; `custom_components/autodarts/manifest.json` has the version on main.
- The tests are in `tests/`, the card tests in `tests/frontend/`.

What matters in a bug report: the version of the integration, the version of Home Assistant and its installation type, the Autodarts software on the board PC (Board Manager 2, Autodarts Desktop or Board Manager 1) and its version, which the board's device page in Home Assistant shows, the diagnostics (Settings → Devices & services → Autodarts → ⋮ → Download diagnostics) and, for errors, log lines with debug logging for `custom_components.autodarts`. Problems of the board itself, its detection or an Autodarts account belong to Autodarts support.

In German, address the reporter with "du", as the German documentation does.
