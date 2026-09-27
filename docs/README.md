# Autodarts for Home Assistant: documentation

[← Project page](../README.md) · [Deutsche Dokumentation](de/README.md)

| Guide | What you'll find |
| --- | --- |
| [Installation and setup](installation.md) | Requirements, HACS and manual installation, the three ways to add a board, the optional cloud link, reconfiguration, updating and removal |
| [Entities and events](entities.md) | Every entity, board event, state and attribute, and which Board Manager generation provides it |
| [Dashboard cards](cards.md) | The live card, the training card, the board status card, the scoreboard, the players card and the doubles card, with all options |
| [Automations](automations.md) | Eleven blueprints, board events and ready-to-use examples |
| [How it works](how-it-works.md) | Architecture, update intervals, connection behavior, Board Manager generations, address changes, training rules, privacy and security |
| [Troubleshooting](troubleshooting.md) | Setup messages, repairs, unavailable entities, diagnostics and logs |
| [Security design](security.md) | What is protected, trust boundaries, threats and countermeasures |
| [Roadmap](roadmap.md) | Released versions and what comes next |
| [Development](development.md) | Tests, Docker end-to-end test, demo instance, screenshots and CI |
| [Releases](releases.md) | How versions and release notes are produced |

## Supported devices

| | Supported | Tested with |
| --- | --- | --- |
| Board Manager 2 (headless) | 2.x | 2.0.0 |
| Board Manager 1 (classic app) | 1.x | 1.0.7 |
| Cameras | Any number supported by the Board Manager | 3 |
| Home Assistant | 2026.8 or newer | 2026.9.3 |

Any board hardware that runs the Autodarts Board Manager works, because the integration talks to the Board Manager, not to the cameras.

## Use cases

- **Training dashboard:** follow your average, 180s and hit distribution over days and weeks.
- **Atmosphere:** light shows for high visits, a dart caller on your speakers, board lighting during the takeout.
- **Energy and comfort:** start the detection when you enter the darts room, and stop it when you leave.
- **Reliability:** get notified when the board goes offline or a camera fails, before your next match.
- **Home dashboards:** show the live board on a wall tablet or in the living room.
