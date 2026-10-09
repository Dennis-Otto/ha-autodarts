# Security design

[← Documentation](README.md) · [Deutsch](security.de.md)

This page explains how the integration protects your data and your board, what it trusts, and which risks remain. Report vulnerabilities privately as described in [SECURITY.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/SECURITY.md).

## What is protected

| Asset | Where it lives | Protection |
| --- | --- | --- |
| Board API key, TLS key, camera device paths | Board Manager configuration | Dropped as soon as a configuration is read; never stored, logged, shown or included in diagnostics |
| Autodarts OAuth tokens (optional cloud link) | Home Assistant config entry | Stored only there, refreshed automatically, never logged; the password is never seen |
| Board ID, board address, client ID | Home Assistant config entry | Redacted from diagnostics; the connection history in diagnostics holds counts, kinds of errors and durations, never addresses or error messages |
| Training sessions, practice games and tournaments, personal bests, player names and profiles with head-to-head records, match history, doubles statistics, progress with dart positions, achievements and linked persons, weekly report and training calendar | Home Assistant `.storage` ([stored data](how-it-works.md#stored-data)) | Local only; deleted together with the integration; player names are redacted from diagnostics |
| Exports with player names | By default `autodarts/exports` in the media folder; on request `www`, another media folder or a folder of `allowlist_external_dirs` | Written only by administrators and automations, at most 20 in an hour; only into folders where Home Assistant allows writing, never into hidden ones; unguessable file names; downloads for administrators only |
| Control of the board | Board Manager API | Actions only on request of a user or an automation, sent once |
| Address of the online bridge (optional) | Options of the Home Assistant config entry | A random secret of 64 hexadecimal characters, shown only in the options; never logged by the integration or included in diagnostics; replaceable with a new one in the options, which stops the old one at once, also while the bridge is switched off |

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
4. **Network → integration (mDNS).** Any device in the network can announce an Autodarts board. The integration contacts only the addresses the announcement was sent from, never loopback, link-local or multicast addresses, and never an address named only in the announcement's properties. An existing board never moves on its own: when its configured address no longer answers with its board ID, a repair notice offers the new address, and the entry moves only once you confirm it, after the board has been identified there again.
5. **Browser → integration (online bridge, optional).** Off by default. When switched on, Home Assistant accepts the calls of the browser extension Tools for Autodarts at a secret webhook address, by default only from the home network. The integration accepts only the known triggers, fields of limited length and at most 20 calls per second and 120 per minute. A call can only fire an `online_*` board event: it never controls the board or changes stored data. [Online matches](online-matches.md).

## Threats and countermeasures

| Threat | Countermeasure | Evidence |
| --- | --- | --- |
| Secrets from the board leak into Home Assistant | Configuration is reduced to an allow-list of fields right after reading; responses to writes are discarded | Tests check that the API key never appears in entities, diagnostics or logs, also in the Docker end-to-end test |
| Malformed or hostile board data crashes the integration or the cards | Validation of every payload; property-based tests with Hypothesis (training engine) and fast-check (cards) run thousands of random inputs | `tests/test_training_properties.py`, `tests/frontend/properties.test.js` |
| Script injection through board or device names in the cards | All inserted text is escaped; no `innerHTML` with unescaped data | fast-check property "escaped text never contains markup"; DOM test that a player named `<img onerror>` appears as text |
| A wrong board at a configured address shows or controls foreign data | The board ID is checked with every read of Board Manager 2, and with Board Manager 1 at the start and at least every 30 seconds; a mismatch makes the entities unavailable, ignores its realtime notifications and raises a repair notice | `tests/test_local_setup.py`, `tests/test_issues_and_metadata.py`, `tests/test_realtime.py` |
| A device in the network announces itself as a board | Only the announcing addresses are contacted; a board that still answers at its configured address is never moved; otherwise a repair notice asks you first, and the board ID is checked again when you confirm | `tests/test_discovery.py` |
| Crafted identifiers from the cloud reach other API routes | Board and match IDs are encoded as a single path segment; an empty or non-text ID sends nothing | `tests/test_api.py` |
| Someone who learns the address of the online bridge sends fake moments | Off by default; only calls from the home network unless allowed; a secret of 64 random hexadecimal characters; known triggers only, limited lengths, at most 20 calls per second and 120 per minute; events only; a new address in the options, which replaces the old one at once, also when the bridge is switched off | `tests/test_online.py` |
| Many viewers overload the board PC with camera streams | At most two live streams per camera are relayed; further viewers get snapshots | `tests/test_camera_stream.py` |
| Faulty board data or a bug in a game rule cuts the connection | Errors in the training and the games are contained and logged once; high-rate values never run the game logic; reads never overlap | `tests/test_connection.py` |
| An export writes where it should not, overwrites a file or fills the disk | Only administrators and automations export; the folder is resolved before writing, so neither `..` nor a symbolic link leads elsewhere, and it must be one where Home Assistant allows writing (`www`, the media folders, `allowlist_external_dirs`); hidden folders and control characters are refused; at most 20 exports in an hour; every export is a new file | `tests/test_reports_setup.py` |
| The user of a shared wall tablet deletes, relinks or exports the players' data | `autodarts.delete_player`, `autodarts.link_player`, `autodarts.unlink_player` and `autodarts.export` are administrator actions, which automations still run; only administrators download exports | `tests/test_services.py`, `tests/test_reports_setup.py` |
| A player name runs as a formula in a spreadsheet | CSV cells that start like a formula get a leading apostrophe | `tests/test_reports_setup.py` |
| An action runs twice, for example a restart or a reset | Actions are sent once and never retried automatically | `tests/test_local_api.py` |
| A compromised dependency or build | Hash-pinned dependencies, pinned Actions and images, Dependabot, dependency review, CodeQL, Gitleaks, OpenSSF Scorecard | [Development](development.md#continuous-integration) |
| A tampered release | Release packages carry Sigstore-signed SLSA provenance | [Releases](releases.md#signed-release-packages) |

## Common weaknesses

How the integration counters the weaknesses of the [CWE Top 25](https://cwe.mitre.org/top25/) that matter for it. CodeQL looks for them in the Python and the JavaScript on every pull request.

| Weakness | Countermeasure |
| --- | --- |
| Cross-site scripting (CWE-79) | Every text from the board, the entity registry or a player is escaped before it becomes HTML, and numbers are checked before they become SVG geometry |
| Path traversal (CWE-22) | Exports resolve their folder before writing, so neither `..` nor a symbolic link leads elsewhere; the highlight copies serve only plain file names of photos in the highlight folder |
| Improper input validation (CWE-20) | Every answer of the Board Manager, every realtime notification and every call of the online bridge is checked against known types, ranges and lengths |
| Exposure of sensitive information (CWE-200, CWE-532) | The board API key is dropped right after reading and never stored, logged or shown; OAuth tokens are never logged; the diagnostics redact board IDs, addresses and player names |
| Missing authorization (CWE-862) | Actions, downloads, highlight copies and the WebSocket command need a login to Home Assistant; deleting, relinking and exporting the data of players need an administrator |
| Server-side request forgery (CWE-918) | Discovery contacts only the addresses an announcement came from, never loopback, link-local or multicast addresses; IDs from the cloud are encoded as a single path segment |
| Uncontrolled resource consumption (CWE-400) | At most two live streams per camera, 20 exports in an hour, and 20 calls a second and 120 a minute for the online bridge |
| Formula injection in exports (CWE-1236) | CSV cells that start like a formula get a leading apostrophe |
| Command and code injection (CWE-78, CWE-94) | The integration runs no commands and evaluates no code, and it has no Python dependencies at runtime |

## Design principles

- **Least privilege:** GitHub workflows run with read-only tokens unless a job needs more; the integration only reads the Board Manager and writes to it only when you or an automation ask for it; the actions that delete, relink or export the players' data are for administrators.
- **Fail safe:** unknown data becomes *unknown*, an unreachable board makes entities unavailable, and a wrong board never shows its data.
- **Local first:** the cloud is optional, and local control never depends on it.
- **Small attack surface:** no Python dependencies at runtime and no open ports of its own. What the integration adds to Home Assistant's own web server:
  - the card file at `/autodarts/autodarts-card.js`, served without a login like every other frontend file; it contains code, no data;
  - the thirteen `autodarts.*` actions, which need a login like every action: `start_game`, `correct_dart`, `throw_dart`, `enter_visit`, `next_player`, `undo_visit`, `start_tournament`, `next_tournament_match` and `stop_tournament` for every user, and `delete_player`, `link_player`, `unlink_player` and `export` for administrators, automations and scripts started by them;
  - the downloads of this run's exports at `/api/autodarts/export/`, for administrators or with their signed link that expires after a minute;
  - small copies of the highlight photos at `/api/autodarts/highlights/`, for logged-in users like the photos themselves; only plain file names of photos in the highlight folder are served;
  - the WebSocket command `autodarts/positions`, with which the cards read the dart positions, for logged-in users;
  - only while the online bridge is on, one secret webhook address.

## Residual risks

- The Board Manager's local API has no login. Anyone who can reach port 3180 in your network can control the board, with or without this integration. Keep the board PC in a trusted network.
- Files in the `www` folder are served at `/local/` without a login to anyone who can reach Home Assistant and knows the file name. Exports go to the media folder, which needs a login, unless you choose `www`; delete exports in `www` you no longer need.
- The local API is not officially supported by Autodarts from Board Manager 2 on. A future Board Manager version may change it; the integration detects the generation and is tested against both.
- The integration talks plain HTTP to the board. If Board Manager 2 announces an HTTPS port, the plain HTTP port it announces is used; TLS to the board is not supported.
- The online bridge relies on the secrecy of its address. Whoever knows it and can reach Home Assistant can fire online board events and the automations that react to them, until you create a new address.
- Anyone in the network can announce a board over mDNS. Home Assistant then shows a discovered board, which is only added after you confirm it.
