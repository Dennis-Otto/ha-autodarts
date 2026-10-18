---
description: "Why the release package carries the blueprints and each start keeps unchanged ones current, while edited ones stay and get a repair."
---

# Ship the blueprints with the integration and keep unchanged copies current

- Status: accepted
- Date: 2026-10-18

## Context

The blueprints read the attributes of the board events and call the actions of the integration, so each version of a blueprint belongs to a version of the integration. HACS updates only the integration, though, and a blueprint stays as it was imported: the guide asked users to update both together by hand, with **Re-import blueprint**, which fetches the blueprint from `source_url` on the main branch. Main can be ahead of the latest release, so an older installation could get a blueprint that relies on events, attributes or actions it lacks, and defaults such as `| int(0)` would hide the mistake ([#383](https://github.com/Dennis-Otto/ha-autodarts/issues/383)). Thirty commits have changed the blueprints since they were added.

Home Assistant saves a blueprint imported from `github.com/<owner>/<repository>` as `/config/blueprints/automation/<owner>/<file>`, here `Dennis-Otto/`. It writes the file anew: without comments, with the address it came from as `source_url`, and with every option of a selector that its release knows, such as `multiple: false`, which differs between releases of Home Assistant.

## Options

1. **Keep the import**, and let release-please point `source_url` to the tag of each release. A re-import would then fetch the matching version, but users would still have to know when to re-import, the import buttons would still lead to main, and nothing would tell an old installation that its blueprints moved on.
2. **Ship the blueprints in the release package and copy them into `/config/blueprints/automation/autodarts/`.** Simple, but a user who imported the blueprints has them in `Dennis-Otto/`: the blueprints page would show each blueprint twice, and the automations would keep using the old copies.
3. **Ship them and keep the files in `Dennis-Otto/` current**, where the import puts them, so imported and shipped blueprints are the same files: add a missing one, update one nobody changed, and leave one alone that someone changed.

## Decision

Option 3. The release package carries `custom_components/autodarts/blueprints/`, a copy of `blueprints/` that `python scripts/ship_blueprints.py` makes, and `blueprint_versions.json` with a fingerprint of every version of each blueprint that main has had. Each start of Home Assistant compares each blueprint of the release with its file in `/config/blueprints/automation/Dennis-Otto/`:

- A missing file is installed, unless the integration saw it before: then the user deleted it, and it stays deleted. `.storage/autodarts.blueprints` remembers the files the integration saw.
- A file that is the version of the release stays as it is, also when Home Assistant's import wrote it: the comparison validates the selectors of both with the running Home Assistant, which completes them alike.
- A file whose fingerprint is one of an earlier version is updated, and the automations made from it reload, as after a re-import. The fingerprint leaves out `source_url` and the options of each selector, so an import by any release of Home Assistant matches the version it imported.
- Any other file, changed by the user or imported from a main that is ahead of the release, stays. A fixable repair offers the version of the release; its ID carries the version, so a later release that changes the blueprint asks again after the user ignored it.

The import buttons, `source_url` and the rule of CONTRIBUTING.md that a blueprint on main works with the latest release stay: the buttons import a deleted blueprint again, and the integration keeps an imported blueprint current like a shipped one.

## Consequences

- After a HACS update and the restart, every unchanged blueprint matches the installed integration, and nobody needs to re-import.
- A change of a blueprint runs `python scripts/ship_blueprints.py`; `tests/test_shipped_blueprints.py` fails until the copy and the fingerprint are there. The fingerprints stay in the file, so that installations of any earlier version are recognised.
- The integration sets up after Home Assistant's automations (`after_dependencies`), so that it can reload the automations of an updated blueprint at once.
- An update replaces an unchanged blueprint with its comments, and a change of only the options of a selector, such as a range, counts as unchanged. Users who want their own variant save it under another name.
- The end-to-end tests mount the blueprints of the repository at `Dennis-Otto/`, where the integration finds them current and writes nothing.
