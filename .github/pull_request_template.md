## Summary

<!-- What changes for users, and why? Name the issues this fixes with "Fixes #123": they stay open until the next release and then close with a link to it. -->

## Checklist

- [ ] The title is a Conventional Commit, such as `feat(scope): …` or `fix: …`.
- [ ] Tests cover the change, and `scripts/check.sh` passes; the Docker end-to-end or browser test covers a visible flow.
- [ ] User-facing texts are in `strings.json`, every translation (`de`, `nl`, `fr`, `es`) and every `TEXT` language of the card.
- [ ] The documentation in `docs/` and `docs/de/` is updated, and `CHANGELOG.md` says under Unreleased what changes for users.
- [ ] Screenshots are regenerated with `bash tests/e2e/screenshots.sh` if a card or dialog looks different.
- [ ] Every commit is signed off (`git commit -s`).
- [ ] No tokens, keys, real board IDs or private addresses are included.

## Test plan

<!-- How did you verify the change? -->
