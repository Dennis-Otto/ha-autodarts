# Follow the repository blueprint

- Status: accepted
- Date: 2026-10-07

## Context

The maintainer keeps several repositories, and their checks, release bot, security workflows and settings drifted apart.

## Options

1. Keep the workflows of this repository its own.
2. Take the [repository blueprint](https://github.com/Dennis-Otto/repo-blueprint), a Copier template whose updates a bot brings.

## Decision

Option 2, since blueprint 0.3.1. The blueprint owns the workflows, `scripts/check.sh` and the community files; the end-to-end tests, the cards and their checks (`scripts/check-project.sh`) and the documentation stay the project's.

## Consequences

The release process, the curated changelog, Renovate, the settings as code and the security checks are the same as in the other repositories, and an improvement of one reaches all. A change of a file of the blueprint belongs in the blueprint.
