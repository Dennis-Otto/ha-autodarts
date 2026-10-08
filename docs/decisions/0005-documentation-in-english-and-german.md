# Write the documentation in English, with a complete German translation

- Status: accepted
- Date: 2026-09-26

## Context

Many Autodarts players are in German-speaking countries, and the maintainer is German; the Home Assistant community writes in English.

## Options

1. English only.
2. English first, with a complete German translation that changes in the same pull request.

## Decision

Option 2. The documentation is in `docs/`, its German translation in `docs/de/`, and every pull request that changes one changes the other. The integration and its cards speak English, German, Spanish, French and Dutch.

## Consequences

Every change of the documentation is written twice. A bot opens an issue per language when texts of the integration go stale.
