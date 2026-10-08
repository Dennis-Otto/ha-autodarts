# Releases and update notes

[← Documentation](README.md)

HACS installs the GitHub releases of the integration and shows their notes in the Home Assistant update dialog. Releases follow the [repository blueprint](https://github.com/Dennis-Otto/repo-blueprint): nobody chooses a version or writes the notes of a release by hand.

## The release pull request

Every pull request that changes something for users describes it under `## Unreleased` in `CHANGELOG.md`, in the words of a user, with the number of the pull request and the GitHub name of a tester who helped. The release bot (**Release** workflow) keeps a pull request titled `chore: release x.y.z` up to date with `main`:

- **The version** follows from the titles of the pull requests merged since the last release: `fix` makes a patch, `feat` a minor and `!` or `BREAKING CHANGE` a major version. Every merge decides it anew. Pull requests of the types `docs`, `test`, `ci`, `chore`, `refactor`, `build` and `style` make no release on their own.
- **The notes:** the text of *Unreleased* becomes the section of the release in `CHANGELOG.md`. The release notes show that text, followed by every pull request of the release.
- **The files of the version:** `custom_components/autodarts/manifest.json`, `version.txt` and `.release-please-manifest.json`.

The release pull request needs the same required checks as every other one, the Docker end-to-end tests with Board Manager 1 and 2 and the oldest supported Home Assistant included, and it is always up to date with `main`, so its checks are those of the commit that becomes the release. Merging it publishes the release; until then, nothing reaches users. A release of dependency updates alone merges itself; every other release waits for the maintainer.

## Betas

Every pull request of the types `feat`, `fix` and `perf` that reaches `main` also becomes a beta of the next release (the repository variable `BETA_CHANNEL` in `.github/repository.project.toml`): the version of the release pull request with `-beta.N`, such as `1.10.0-beta.2`, with the text of *Unreleased* as its notes. It is built, signed and verified like a release, and published as a prerelease that HACS offers only to those who turn on the beta switch ([Betas for testers](installation.md#betas-for-testers)); it announces nothing in the discussions. Updates of dependencies make no beta.

A line `Release-As: 2.0.0-beta.1` in the description of a pull request sets the version of the next release. A version with a suffix such as `-beta.1` becomes a prerelease, which HACS offers only to those who turn on its beta switch for the integration. A beta keeps the text of *Unreleased* for the release that follows it, so the final release names everything again.

## Publication

Merging the release pull request creates the release as a draft, with its tag `vx.y.z`, and then:

1. The archive `autodarts.zip` is built from the folder `custom_components/autodarts` of the tagged commit with `git archive`, which HACS installs (`zip_release` and `filename` in `hacs.json`).
2. Every asset gets its signed SLSA build provenance, and the release an SPDX SBOM.
3. The complete release is published; GitHub keeps it immutable from then on.
4. The **Release verification** checks the release as its users can: the provenance of every asset, the SBOM, the immutability and the signed commit. It checks the latest release every week as well.

## Signed release packages

| Asset | Contents |
| --- | --- |
| `autodarts.zip` | The folder `custom_components/autodarts` of the released commit, built reproducibly with `git archive` |
| `ha-autodarts.spdx.json` | The software bill of materials of the release |
| `provenance.sigstore.json` | A Sigstore bundle with the signed SLSA build provenance of every asset |
| `provenance.intoto.jsonl` | The same signed provenance as in-toto JSON lines, for SLSA tools |

The provenance proves that GitHub Actions built the archive from this repository and commit, so a HACS installation gets exactly the signed file; the download count of `autodarts.zip` shows how often each release was installed. To verify a download:

```sh
gh attestation verify autodarts.zip --repo Dennis-Otto/ha-autodarts
```

Offline, with the downloaded bundle:

```sh
gh attestation verify autodarts.zip --repo Dennis-Otto/ha-autodarts \
  --bundle provenance.sigstore.json
```

Releases up to 1.9.0 carry their bundle as `autodarts.zip.sigstore.json`. Releases 1.0.0 and 1.0.1 were signed before the repository was renamed from `HACSAutodarts` to `ha-autodarts`; verify them with `--repo Dennis-Otto/HACSAutodarts`. Releases before 1.0.0 have no archive.

## Secrets and recovery

The release app opens and updates the release pull request, so that its checks run. Its private key is the secret `RELEASE_AUTOMATION_PRIVATE_KEY` of the environment `release`, which only `main` may use; its client ID is the repository variable `RELEASE_AUTOMATION_CLIENT_ID`, and the variable `PUBLISH_TO` is `hacs`. Every token is short-lived and limited to what its job needs.

If a job of the Release workflow fails, re-run its failed jobs: the draft is completed and published, and nothing is released twice. A published release is never replaced. To leave out a change that is merged already, revert it in a pull request before the release pull request is merged.
