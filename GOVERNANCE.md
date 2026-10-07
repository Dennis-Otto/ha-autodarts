# Governance

This repository is an independent, community-oriented fork of [Trkal/HACSAutodarts](https://github.com/Trkal/HACSAutodarts), maintained by Dennis Otto. It is not affiliated with Autodarts.

## Maintainers and access

| Person | Role | Access |
| --- | --- | --- |
| [@Dennis-Otto](https://github.com/Dennis-Otto) | Maintainer | Repository administration, releases and the release automation's GitHub App, security advisories, the OpenSSF Best Practices entry and the HACS listing |

## Decisions

Feature, compatibility and maintenance decisions are discussed in public GitHub issues, discussions and pull requests whenever they do not contain security-sensitive information. Decisions prioritize local control without cloud dependencies, secure handling of tokens and board credentials, compatibility with current Home Assistant releases, backward compatibility of existing config entries and entity IDs, and maintainability. The [roadmap](docs/roadmap.md) records what comes next.

The maintainer has final responsibility for releases, repository access, security responses and project direction. Significant behavior changes include rationale, tests, documentation in English and German, and categorized release notes.

## Reviews

Every change reaches `main` through a pull request that passes all required checks: tests with a coverage gate, linting and typing, the Docker end-to-end tests, HACS and hassfest validation, CodeQL, dependency review and the secret scan. Contributions from others are reviewed by the maintainer for correctness, tests, documentation, security and user impact before they are merged.

## Contributions and maintainership

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md). An automated [issue assistant](docs/development.md#issue-assistant) posts a first analysis of new issues, labels them, closes likely duplicates after a notice and issues that wait for their reporter for 30 days; it never decides on behalf of the maintainer, who reads every issue. Sustained contributors may be invited to help triage issues or review changes. Maintainer access is granted only after a history of constructive, security-conscious contributions and may be removed when it is no longer needed.

## Continuity

If the current maintainer can no longer maintain the project, the preferred outcome is a transparent handover to a trusted active contributor, announced in the repository. Until that handover is complete, the repository should be archived rather than presented as actively maintained, so that users are not left with an unmaintained integration that still looks active.

## Security

Potential vulnerabilities follow [SECURITY.md](SECURITY.md) and are handled privately until a coordinated fix and disclosure are ready.
