---
description: "Why Home Assistant 2026.8 stays the oldest supported release: the blueprints build on its event trigger, and older releases would cost more than they reach."
---

# Keep Home Assistant 2026.8 as the oldest supported release

- Status: accepted
- Date: 2026-10-18

## Context

The integration, its blueprints and HACS require Home Assistant 2026.8.0 (`hacs.json`), and the end-to-end tests run that release beside the current one. Home Assistant's [analytics](https://analytics.home-assistant.io/) of 18 October 2026 count 704,380 installations: 71.7 % run 2026.8 or a newer release, 76.5 % at least 2026.7, 84.1 % at least 2026.4 and 88.7 % at least 2026.1. A lower minimum would reach more of them, if the gap is small ([#377](https://github.com/Dennis-Otto/homedarts-for-autodarts/issues/377)).

To measure the gap, the whole test suite ran in a Linux container against the test harness of two older releases: `pytest-homeassistant-custom-component` 0.13.308 for Home Assistant 2026.1.3 and 0.13.344 for 2026.7.0, each with the versions of Assist that its release installs. What the integration uses, by the first release that has it:

| Release | What the integration uses from it |
| --- | --- |
| 2026.3 | `UnsupportedStorageVersionError`, which stops the setup on a store of a newer layout instead of reading it, and `async_get_config_entry` of `homeassistant.helpers.service`, which explains an unknown, foreign or unloaded board in an action |
| 2026.4 | The trigger `event.received`, behind the Labs preview of the new triggers, and the filter by `unit_of_measurement` of the entity selector, with which the training report offers only the sensors of darts and points |
| 2026.6 | `RepairsFlowResult` of the repair flows |
| 2026.7 | `event.received` for everyone, without the preview |
| 2026.8 | `DeviceRegistry.async_get_device_by_identifier`, which finds the device of a board in its own entry, and times of an event entity that always increase: two events in the same millisecond are two changes of its state, so `event.received` fires for each |

Nine of the 14 blueprints, the two callers, the score display, the light show, the highlight photo, the takeout, the training session, the visit score and the weekly report, start on `event.received` of the board events, with 15 triggers in all. On 2026.1.3 these automations do not load, because the trigger does not exist yet; the training report needs the selector filter of 2026.4. The other blueprints use state, time and conversation triggers that older releases have, but the `min_version` of every blueprint is 2026.8.0. On 2026.7.0, with a stand-in for the device lookup and the `min_version` of the blueprints lowered, everything passes except seven tests of the callers and the score display, which fail when they run together and pass alone. The board sends its events in bursts, such as a bust, the takeout, the completed visit and the next turn within a few milliseconds, which on 2026.7 can merge into one change of the state.

## Options

1. **Support 2026.1** with fallbacks. The four newer interfaces of Python are small to replace, but these nine blueprints would go back to a state trigger on the event entity with conditions on its event type and on the state it comes from, which `event.received` replaced. The training report would offer every sensor, and events of the same millisecond would still merge.
2. **Support 2026.7** with a fallback for the device lookup and an end-to-end test of 2026.7.0. It reaches 4.8 % more installations, but needs the reason for the failing tests of the callers first, and a later time for an event of the same millisecond, which only the private time of Home Assistant's event entity can give.
3. **Keep 2026.8.**

## Decision

Option 3. The blueprints build on `event.received`, and what they rely on, one run for each event, holds from 2026.8 on. A fallback for older releases would make the blueprints worse on the current ones or tie the integration to a private attribute of Home Assistant, to reach installations that update anyway: the share of 2026.8 and newer rose from 42.2 % on 18 August to 61.7 % on 18 September and 71.7 % on 18 October.

## Consequences

- HACS, the blueprints, the end-to-end tests and the documentation keep naming 2026.8; `tests/test_consistency.py` and `tests/test_blueprints.py` fail when one of them names another release than `hacs.json`.
- Whoever runs an older Home Assistant updates it first; HACS names the release it needs.
- A new minimum starts in `hacs.json`, and these tests then name most other places to change. The description of the end-to-end tests in `docs/development.md` and `docs/development.de.md`, the `e2e-shards` diagrams with their pictures and the tested releases in the supported devices of `docs/README.md` and `docs/README.de.md` are changed by hand. To measure another gap, install the release's `pytest-homeassistant-custom-component` and Assist in a Linux container, without the hashes of `requirements-test.txt`, and run `pytest`; Home Assistant does not run on Windows.
