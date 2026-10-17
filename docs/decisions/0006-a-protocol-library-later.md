# Keep the protocol of the Board Manager in the integration for now

- Status: accepted
- Date: 2026-09-26

## Context

Home Assistant prefers integrations whose protocol code lives in a library on PyPI. A library for the local API of the Board Manager, *aioautodarts*, would serve other projects too.

## Options

1. Split the protocol into the library aioautodarts on PyPI now.
2. Keep it in the integration and split it later.

## Decision

Option 2. The library is on the roadmap under *Later*, with the name aioautodarts in mind. The name is not reserved: PyPI holds a name only from its first upload, and a pending trusted publisher holds none. That first upload is a task for the maintainer and can wait until the protocol settles; until then, another project may take the name.

## Consequences

The integration ships no Python requirements. A core integration of Home Assistant would need the library first.
