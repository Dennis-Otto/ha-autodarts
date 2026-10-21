---
description: "Why the prepared cloud link is gone: Autodarts issues no client IDs to third parties, so the integration stays with the Board Manager and the online bridge."
---

# Remove the cloud link, since Autodarts issues no client IDs to third parties

- Status: accepted
- Date: 2026-10-21

## Context

The integration talks to the board through the local API of the Board Manager ([0002](0002-local-api-of-the-board-manager.md)). For what only the Autodarts cloud knows, the game of an online match and the darts of a board without a Board Manager in the network, such as Lens, a cloud link was prepared and kept hidden behind `CLOUD_LINK_AVAILABLE` in `const.py`, waiting for a public client ID with the device grant ([0020](0020-a-public-client-for-the-cloud-link.md)).

On 2026-10-21 Autodarts answered the request: it issues no client IDs for external authentication flows or cloud interfaces, and it offers no support for any of its interfaces. The hidden code would therefore never run for a user. It was the device login, the refresh and the cloud client in `api.py`, the cloud coordinator in `coordinator.py`, the sensors of a cloud entry (*Cloud status*, *Game mode*, *Match state*, *Round*, *Visit score* and *Darts thrown*), the **Events** entity of a board that only the cloud reaches, `CloudMoments` in `online.py`, the search for a missing board at the addresses the cloud reports, the reauthentication flow, and their tests and texts in five languages.

## Options

1. Keep the code behind the flag, in case Autodarts changes course: every change of the setup, the entities or the translations would carry code that no user runs, and the documentation would go on promising a link that cannot come.
2. Remove the cloud link and keep the integration local; the history of git keeps the code.

## Decision

Option 2. The integration stays local:

- It talks to the Board Manager in the network, as before ([0002](0002-local-api-of-the-board-manager.md)).
- The board search through `https://discover.autodarts.com` stays: it needs no login and runs only when the user chooses it in the setup.
- The moments of online matches come through the online bridge, from the browser extension Tools for Autodarts.
- The binary sensor *Cloud link* of Board Manager 2, and the switch and buttons of Board Manager 1, stay: they show and control the board's own connection to Autodarts, over the local API.

Existing entries move to the minor version 2 of their config entry, which removes `token`, `client_id` and `local_only` from their data and the six sensors of a cloud entry from the entity registry. An entry without a board address, such as one that was linked to the cloud only, still stops with the error that asks for the address in **Reconfigure**.

## Consequences

- Home Assistant keeps no Autodarts login and no token, and the setup asks for no account. The rule `reauthentication-flow` of the quality scale is exempt, since there is no login to renew.
- A board without a Board Manager in the network, such as Lens, has its darts entered on the keypad, as a [dartboard without Autodarts](../without-autodarts.md). Online moments need a browser with Tools for Autodarts and the bridge.
- This record replaces [0020](0020-a-public-client-for-the-cloud-link.md). Should Autodarts issue client IDs to third parties later, the code of the cloud link is in the history of git up to version 1.18.0, and a new record decides whether it returns.
