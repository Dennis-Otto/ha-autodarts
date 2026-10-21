---
description: "Why the cloud link waits for a public Autodarts client with the device grant, and how the cloud's matches become the board events of the online bridge."
---

# Prepare the cloud link for a public client with the device grant

- Status: replaced by [0025](0025-no-cloud-link.md)
- Date: 2026-10-18

## Context

The integration talks to the board through the local API of the Board Manager ([0002](0002-local-api-of-the-board-manager.md)). The Autodarts cloud knows what the board doesn't: the game of an online match on play.autodarts.io, with busts, won legs and matches and the darts of every player, and the darts of boards that have no Board Manager in the network, such as Lens, which scores with the camera of a phone or tablet. Today these moments reach Home Assistant only through the online bridge, while a browser with the extension Tools for Autodarts has the match open.

Autodarts retired its Keycloak login for third parties. Its new authentication service at `https://api.autodarts.io/auth/v1` issues a `client_id` to each application on request: the guide for third parties, by lloydowen of Autodarts, asks for a message on the Autodarts Discord. A public client has no secret; the device authorization grant (RFC 8628), in which the user enters a short code at `https://auth.autodarts.io/link` on any device, is switched on per client. Access tokens last 15 minutes; every refresh issues a new refresh token, which lasts 30 days, and invalidates the old one.

The integration already has the device login (`api.py`), the refresh and the cloud coordinator, which reads the board every 60 seconds and, during a match, the match and its state every 5 seconds. Without a client ID, `CLOUD_LINK_AVAILABLE` in `const.py` keeps the cloud step out of the setup.

## Options

1. Wait without preparing anything: switching the cloud link on would then need the code, its tests and the documentation at once.
2. Let every user register a client: Autodarts issues clients to applications, not to their users, and a confidential client would put a secret into every Home Assistant.
3. The authorization code flow with PKCE: it needs a redirect URI that Autodarts registers, but each Home Assistant has an address of its own, and a redirect through a service of a third party would be one more dependency.
4. One public client of the integration with the device grant, shipped with the integration, and, behind the flag, the moments of the cloud's matches as the same board events as the bridge's.

## Decision

Option 4. The device grant needs neither a redirect URI nor a secret, works for every Home Assistant, also one without an address on the internet, and the integration implements it already.

The request to Autodarts, in a message to lloydowen on the Autodarts Discord:

> Hi! I maintain Autodarts for Home Assistant (<https://github.com/Dennis-Otto/ha-autodarts>), an open-source integration that connects Autodarts boards to Home Assistant, mostly through the local Board Manager API. For the optional cloud features (match data, online-match moments, and boards without a Board Manager on the network, such as Lens), I'd like a public client ID for the app "Autodarts for Home Assistant" with the device authorization grant enabled, without a redirect URI or client secret. Scopes: `openid profile email`, plus reading the user's boards and matches (`/bs/v0/boards`, `/gs/v0/matches/{id}` and its `state`). Tokens stay in the user's Home Assistant, are never logged, the rotating refresh token is stored before the next request, and the access token is renewed a minute before it expires. During a match the integration reads the board, the match and its state every 5 seconds, otherwise the board once a minute; I'd switch to the match websocket once you can confirm its topics for third parties. Thank you!

How the integration handles the tokens:

- Tokens live only in the config entry, never in logs, diagnostics or repair issues. The device code stays private; only the user code is shown.
- Every refresh stores the new refresh token before any further request can fail or Home Assistant can restart. An access token is renewed 60 seconds before it expires, as the guide advises, and once more when the API rejects it; a second rejection asks for a new login, while a board in the network keeps working locally.

How the moments of a match become board events (`CloudMoments` in `online.py`): each poll is compared with what was already reported, and what is new becomes the trigger that Tools for Autodarts sends for it, parsed by the bridge's own parser. The board events are therefore those of the bridge, with `source` `cloud`:

| In the state of the match | Trigger | Board event |
| --- | --- | --- |
| A new visit of a player at the board | `gameon` | `online_game_on` |
| A new visit of the bot, a player with `cpuPPR` | `bot_throw` | `online_game_on` |
| A new dart of the visit, from its segment | `t20`, `s25`, `bull`, `m17`, `miss` | `online_dart` |
| A visit with its third dart, neither busted nor won | its `points`, such as `140` | `online_visit` |
| `busted` of the visit | `busted` | `online_busted` |
| `gameWinner`, with the winning dart | `gameshot+d16` | `online_game_shot` |
| `winner`, with the winning dart | `matchshot+bull` | `online_match_shot` |
| The variant `Bull-off` | `bulloff` | `online_bull_off` |
| The board leaves the match | `idle` | `online_match_left` |

Players at another board, the opponents of an online match, are skipped, as they are by a bridge whose Tools for Autodarts knows the ID of the board. A player without a board of their own, such as the bot, plays at this one.

Once Autodarts has issued the client:

1. Set `CLOUD_CLIENT_ID` in `const.py` to the issued ID, which the cloud step of the setup then fills in, and `CLOUD_LINK_AVAILABLE` to `True`.
2. Link a test account once against the real service and save a redacted state of a match as a test fixture, to confirm the fields above: `players` with `name` and `boardId`, `player`, `set`, `leg`, `round`, `turns`, `gameWinner`, `winner` and `variant`. Confirm in particular that `turns` holds the current visit first, as darts-caller reads it and `CloudMoments` assumes; the `darts_thrown` sensor (`sensor._get_darts_thrown`) instead sums all of `turns` as the history of the match, and only one reading can be right, so fix the other one to match the capture.
3. Remove "once the cloud link ships" from the documentation, and describe the release in the changelog as a `feat`. Also update the texts that say the online moments need the bridge and Tools for Autodarts: the description of the `online_matches` input of the light show (`blueprints/automation/autodarts/light_show.yaml`), the online matches section of `docs/automations.md` and `docs/automations.de.md`, and the rows on online matches in `README.md` and `README.de.md`. Check whether Autodarts X has a Board Manager in the network; if not, name it next to Lens in the FAQ (English and German).
4. Later, with the topics of the match websocket confirmed by Autodarts, replace the polling during a match with it.

## Consequences

The cloud link is ready behind the flag, with tests that force the flag on. The bridge stays as the fallback and for `tournament_ready`, which the state of a match doesn't show. While the bridge is switched on, it alone reports the moments: it is instant, and both would report every moment twice. Polling every 5 seconds can miss a moment that lasts shorter, such as a visit taken out within seconds, and doesn't replay it; a match that ran before Home Assistant started counts from the next poll on. Without a match, the board is read only every 60 seconds (`IDLE_SCAN_INTERVAL`), so the first read of a new match can come up to a minute late, and the bull-off and the first visits may be missed. A board that Home Assistant reaches only through the cloud gets an Events entity with the online events, so that the light show and automations work for Lens as well.
