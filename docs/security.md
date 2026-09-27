# Security design

[← Documentation](README.md) · [Deutsch](de/sicherheit.md)

This page explains how the integration protects your data and your board, what it trusts, and which risks remain. Report vulnerabilities privately as described in [SECURITY.md](../SECURITY.md).

## What is protected

| Asset | Where it lives | Protection |
| --- | --- | --- |
| Board API key, TLS key, camera device paths | Board Manager configuration | Dropped as soon as a configuration is read; never stored, logged, shown or included in diagnostics |
| Autodarts OAuth tokens (optional cloud link) | Home Assistant config entry | Stored only there, refreshed automatically, never logged; the password is never seen |
| Board ID, board address, client ID | Home Assistant config entry | Redacted from diagnostics; the connection history in diagnostics holds counts, kinds of errors and durations, never addresses or error messages |
| Training session, practice games, player names and their progress with dart positions, weekly report and training calendar | Home Assistant `.storage` | Local only; deleted together with the integration; player names are redacted from diagnostics |
| Exports with player names | A folder inside the configuration folder, by default `www/autodarts` | Written only on request; never outside the configuration folder; unguessable file names |
| Control of the board | Board Manager API | Actions only on request of a user or an automation, sent once |
| Address of the online bridge (optional) | Options of the Home Assistant config entry | A random secret of 64 hexadecimal characters, shown only in the options; never logged by the integration or included in diagnostics; replaceable with a new one in the options |

## Trust boundaries

```text
 Board PC                      Home Assistant                    Internet
┌────────────────────┐        ┌──────────────────────────┐       ┌──────────────────────┐
│ Board Manager      │  LAN   │ Autodarts integration    │ HTTPS │ Autodarts cloud      │
│ port 3180, no login├───────►│ validates every answer   ├──────►│ (optional, OAuth)    │
└────────────────────┘        │ dashboard cards (browser)│       │ discovery service    │
                              └──────────────────────────┘       │ (only when searched) │
                                                                 └──────────────────────┘
```

1. **Board Manager → integration.** The local API has no login. The integration treats every answer as untrusted input: types, ranges and structures are checked before any value reaches an entity, and unexpected data reads as *unknown* instead of raising errors. Version numbers must look like version numbers, texts longer than 255 characters read as unknown, and realtime notifications are reduced to the same known values as reads. An answer in an unknown format is logged once; if a required read keeps answering like that, a repair notice appears. HTTP 401 or 403 is reported as refused access; the integration never sends credentials to the board.
2. **Integration → dashboard.** The cards render board data in the browser. Every text from the board or the entity registry is escaped, and numbers are validated before they become SVG geometry.
3. **Integration → internet.** Nothing leaves the local network in local mode. *Search for boards* contacts the public Autodarts discovery service once, on request; the integration never contacts it on its own. The optional cloud link uses the OAuth device login over HTTPS through Home Assistant's shared session, and board and match IDs from the cloud are encoded as a single path segment.
4. **Network → integration (mDNS).** Any device in the network can announce an Autodarts board. The integration contacts only the addresses the announcement was sent from, never loopback, link-local or multicast addresses, and never an address named only in the announcement's properties. An existing board moves to a new address only when its configured address no longer answers with its board ID.
5. **Browser → integration (online bridge, optional).** Off by default. When switched on, Home Assistant accepts the calls of the browser extension Tools for Autodarts at a secret webhook address, by default only from the home network. The integration accepts only the known triggers, fields of limited length and at most 20 calls per second. A call can only fire an `online_*` board event: it never controls the board or changes stored data. [Online matches](automations.md#online-matches-experimental).

## Threats and countermeasures

| Threat | Countermeasure | Evidence |
| --- | --- | --- |
| Secrets from the board leak into Home Assistant | Configuration is reduced to an allow-list of fields right after reading; responses to writes are discarded | Tests check that the API key never appears in entities, diagnostics or logs, also in the Docker end-to-end test |
| Malformed or hostile board data crashes the integration or the cards | Validation of every payload; property-based tests with Hypothesis (training engine) and fast-check (cards) run thousands of random inputs | `tests/test_training_properties.py`, `tests/frontend/properties.test.js` |
| Script injection through board or device names in the cards | All inserted text is escaped; no `innerHTML` with unescaped data | fast-check property "escaped text never contains markup"; DOM test that a player named `<img onerror>` appears as text |
| A wrong board at a configured address shows or controls foreign data | The board ID is checked with every read of Board Manager 2, and with Board Manager 1 at the start and at least every 30 seconds; a mismatch makes the entities unavailable, ignores its realtime notifications and raises a repair notice | `tests/test_quality.py`, `tests/test_realtime.py` |
| A device in the network announces itself as a board | Only the announcing addresses are contacted; a board that still answers at its configured address is never moved; the board ID must match | `tests/test_discovery.py` |
| Crafted identifiers from the cloud reach other API routes | Board and match IDs are encoded as a single path segment; an empty or non-text ID sends nothing | `tests/test_api.py` |
| Someone who learns the address of the online bridge sends fake moments | Off by default; only calls from the home network unless allowed; a secret of 64 random hexadecimal characters; known triggers only, limited lengths, at most 20 calls per second; events only; a new address in the options | `tests/test_online.py` |
| Many viewers overload the board PC with camera streams | At most two live streams per camera are relayed; further viewers get snapshots | `tests/test_camera_stream.py` |
| Faulty board data or a bug in a game rule cuts the connection | Errors in the training and the games are contained and logged once; high-rate values never run the game logic; reads never overlap | `tests/test_connection.py` |
| An export writes outside the configuration folder or overwrites a file | The folder is resolved before writing, so `..`, absolute paths and symbolic links cannot lead outside, and hidden folders are refused; every export is a new file | `tests/test_reports_setup.py` |
| A player name runs as a formula in a spreadsheet | CSV cells that start like a formula get a leading apostrophe | `tests/test_reports_setup.py` |
| An action runs twice, for example a restart or a reset | Actions are sent once and never retried automatically | `tests/test_local_api.py` |
| A compromised dependency or build | Hash-pinned dependencies, pinned Actions and images, Dependabot, dependency review, CodeQL, Gitleaks, OpenSSF Scorecard | [Development](development.md#continuous-integration) |
| A tampered release | Release packages carry Sigstore-signed SLSA provenance | [Releases](releases.md#signed-release-packages) |

## Design principles

- **Least privilege:** GitHub workflows run with read-only tokens unless a job needs more; the integration only reads the Board Manager and writes to it only when you or an automation ask for it.
- **Fail safe:** unknown data becomes *unknown*, an unreachable board makes entities unavailable, and a wrong board never shows its data.
- **Local first:** the cloud is optional, and local control never depends on it.
- **Small attack surface:** no Python dependencies at runtime, no open ports of its own, no services beyond the entities and, only while the online bridge is on, one secret webhook address of Home Assistant's own web server.

## Residual risks

- The Board Manager's local API has no login. Anyone who can reach port 3180 in your network can control the board, with or without this integration. Keep the board PC in a trusted network.
- Files in the `www` folder, such as exports, are served at `/local/` without a login to anyone who can reach Home Assistant and knows the file name. Delete exports you no longer need, or export to a folder outside `www`.
- The local API is not officially supported by Autodarts from Board Manager 2 on. A future Board Manager version may change it; the integration detects the generation and is tested against both.
- The integration talks plain HTTP to the board. If Board Manager 2 announces an HTTPS port, the plain HTTP port it announces is used; TLS to the board is not supported.
- The online bridge relies on the secrecy of its address. Whoever knows it and can reach Home Assistant can fire online board events and the automations that react to them, until you create a new address.
- Anyone in the network can announce a board over mDNS. Home Assistant then shows a discovered board, which is only added after you confirm it.
