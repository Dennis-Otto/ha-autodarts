# Put each German page next to its English page, for the language switch of the website

- Status: accepted
- Date: 2026-10-08

## Context

The documentation is in English and German ([0005](0005-documentation-in-english-and-german.md)) and is also a website. The German pages were in `docs/de/` under German names, such as spiele.md for `docs/games.md`. On the website, they were a section of the English menu, and no link led from a page to the same page in the other language.

## Options

1. Keep `docs/de/` with German names and link the languages by hand.
2. Name each German page like its English page with `.de`, such as `docs/games.de.md` next to `docs/games.md`, and let the plugin mkdocs-static-i18n build a German website under `/de/` from them: German menus, search and theme texts, and a switch in the header that leads to the same page in the other language.

## Decision

Option 2. Both languages of a page sit side by side, so a change of one shows its partner, and the website switches between them on every page. A page without a German version appears in English on the German website. The website starts with its own pages, `docs/index.md` and `docs/index.de.md`; `docs/README.md` and `docs/README.de.md` stay the overviews of the folder on GitHub.

## Consequences

Every link to a German page changed, and the help links of the cards and the documentation link of the integration lead to the website. The old addresses `docs/de/README.md` and `docs/de/karten.md`, which released versions link to, point to the new pages. Links between the languages, such as `[Deutsch](games.de.md)`, work on GitHub, and the hooks of the website (`scripts/mkdocs_hooks.py`) lead them to the page of the other language there.
