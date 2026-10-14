# Notes of this project for coding agents

Autodarts: Autodarts for Home Assistant: local realtime board control, X01, Cricket, party and training games, tournaments and a bot, player statistics with heatmaps, seven dashboard cards and thirteen blueprints, games started by voice. No cloud account needed.

This file belongs to the project: the blueprint wrote it once, and its updates leave it alone. It adds to `AGENTS.md` what a coding agent needs to know about this project alone, such as its architecture, the commands of its own checks and what to watch for in its tests.

## Where things are

- The integration is in `custom_components/autodarts/`, its manifest and version in `custom_components/autodarts/manifest.json`, the HACS metadata in `hacs.json`.
- `README.md` documents installation, configuration and use, `docs/` holds the pages of the website, and `CHANGELOG.md` lists the changes of every release.
- The tests are in `tests/`; `scripts/check.sh` runs every check.
