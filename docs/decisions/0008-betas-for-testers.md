# Give testers a beta after every change for users

- Status: accepted
- Date: 2026-10-08

## Context

Testers want to try a change before its release, at their own board, without installing a branch.

## Options

1. Prereleases by hand, now and then.
2. A beta of the next release after every `feat`, `fix` or `perf` that reaches `main`, which HACS offers to those who turn on its switch *Pre-release*.

## Decision

Option 2: the repository variable `BETA_CHANNEL` turns on the beta channel of the blueprint for this repository.

## Consequences

Every change for users reaches testers within minutes, built and signed like a release. The release still waits for the maintainer.
