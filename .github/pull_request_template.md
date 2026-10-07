## Summary

<!-- What changes for users, and why? Name the issues this fixes with "Fixes #123": they stay open until the next release and then close with a link to it. -->

## Type

- [ ] Bug fix (`bug`)
- [ ] New feature (`enhancement`)
- [ ] Breaking change: users must adapt automations or settings (`breaking-change`)
- [ ] Documentation (`documentation`)
- [ ] Maintenance, CI or dependencies (`maintenance`)

## Checklist

- [ ] Tests cover the change (`pytest --cov`, `npm test`, and the Docker end-to-end or browser test for visible flows).
- [ ] User-facing texts are in `strings.json`, every translation (`de`, `nl`, `fr`, `es`) and every `TEXT` language of the card.
- [ ] The documentation in `docs/` and `docs/de/` is updated.
- [ ] Screenshots are regenerated with `bash tests/e2e/screenshots.sh` if a card or dialog looks different.
- [ ] No tokens, keys, real board IDs or private addresses are included.

## Test plan

<!-- How did you verify the change? -->
