# Deliver through HACS, with signed release packages

- Status: accepted
- Date: 2026-09-26

## Context

Custom integrations of Home Assistant reach their users through HACS. HACS can install the files of a branch or a release package of a GitHub release.

## Options

1. Let HACS install from the repository as it is.
2. Publish a zip release (`zip_release` in `hacs.json`) built from the tagged commit, with signed provenance, and submit the integration to the default catalog of HACS.

## Decision

Option 2. Every release carries `autodarts.zip`, built by the release workflow with signed SLSA provenance, an SBOM and the licenses of its components; users can verify it with `gh attestation verify`. The integration is submitted to the default catalog (hacs/default#11306).

## Consequences

A user gets exactly what the release workflow built, and can check it. The release process follows the repository blueprint ([0007](0007-the-repository-blueprint.md)); betas reach testers as prereleases ([0008](0008-betas-for-testers.md)).
