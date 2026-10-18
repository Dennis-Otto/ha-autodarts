---
description: "Why the texts of the cards are one small module per language, served with the cards from a folder that has the version in its address."
---

# Give each language of the cards a module of its own, in a folder of the version

- Status: accepted
- Date: 2026-10-18

## Context

The texts of the cards were the dictionary `TEXT` in `autodarts-card.js`: 578 texts in each of five languages, 141,716 bytes, a quarter of a module of 12,800 lines. The translation bot sent volunteers to the block `fr: {` of that file, and three parsers of their own read it: the bot evaluated its object literal, `tests/test_consistency.py` and the browser test matched its lines with regular expressions.

The integration sends its files with the cache headers of Home Assistant's own, for a month, and the version in the query of their address (`?v=1.15.0-0123abcd`) made a release load new ones. A module that imports another by a relative address loses that query, so texts in files of their own would have been kept from an older release beside a newer card module.

## Options

1. **Keep `TEXT` in the card module.** Nothing to change, but translators keep looking for their block in the largest file of the repository, and every check of the texts keeps parsing JavaScript of its own.
2. **A JSON file per language, with an import attribute** (`import de from "./text/de.json" with { type: "json" }`). Plain JSON for translators, but Safari understands import attributes only since 17.2, and wall tablets at the board often run older versions.
3. **A JavaScript module per language** in `frontend/text/`, `export default` followed by JSON, with comments on lines of their own, imported statically by the card module; the whole folder served under an address with the version, such as `/autodarts/1.16.0-0123abcd/text/de.js`.
4. **Load only the language of the user**, with `import()`, and draw the cards again when it has arrived. Fewer bytes, but every card would first show English, or wait for its texts, and the editors of Home Assistant ask for texts before any card has `hass`.

## Decision

Option 3. Each language is `custom_components/autodarts/frontend/text/<language>.js`, a module that every browser of the cards understands and that every tool reads alike: drop the lines of comments and read the rest after `export default` as JSON. The consistency tests, the browser test and the translation bot do exactly that, and the tests name the line of a slip, such as a comma after the last text. The bot reads the history of a text across the move: a commit has the texts of the file of its language, or, before the move, those of `TEXT` in the card module, so a translation that was outdated before stays outdated.

The integration digests every file of the folder at its start and serves each one at `/autodarts/<version>-<digest>/<path>`, compressed, with the cache headers of Home Assistant's own files; it hands both modules to every page at those addresses. Relative imports keep the folder, so the card module gets the texts of its own version, and the strategy finds the card module that Home Assistant loads already. A change of any file, also of a text of one language, gives every file a new folder. The folder of a version that has gone, which a page from before an update asks for, and the addresses without a version, which resources in YAML name, serve today's files with `Cache-Control: no-cache`. This replaces the query of [0017](0017-modules-in-the-dashboard-resources-for-cast.md): the dashboard resources for Home Assistant Cast keep both modules in the folder of the version, and the integration still finds its own, with a query, a folder or neither, and brings them up to date in their place.

## Consequences

- A translator edits one small file of their language, which the issue of the translation bot links with the line of each text.
- The card module is 489 KB instead of 641 KB. A first load gets it and five files of texts, together about 175 KB compressed instead of 165 KB, because each file is compressed on its own; the browser keeps them for a month as before.
- A browser asks for the texts once the card module has arrived: one round trip more on the first load, while the strategy, the small module that Home Assistant waits for, comes as early as before.
- A new language needs its file in `text/` and its import in the card module, which the consistency tests ask for.
- Loading only the language of the user (option 4) stays possible later: English would stay imported as the fallback.
