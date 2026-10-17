---
description: "Why the entities of fast readings update by topic, without the internals of the DataUpdateCoordinator of Home Assistant, to keep up with every dart."
---

# Update the entities of fast readings by topic, without the internals of Home Assistant's coordinator

- Status: accepted
- Date: 2026-10-13

## Context

A board has more than a hundred entities, and all of them followed one `DataUpdateCoordinator` of Home Assistant. The motion of the detection, a hand at the board or a takeout, changes several times per visit, and each change updated every entity: about 4 ms on a desktop and several times as long on a Raspberry Pi, between two darts, for at most four sensors that show the motion. Frame rates and the load of the board PC change with nearly every read. To update only their entities after a read, the coordinator overrode the private `_async_refresh` with the signature of Home Assistant 2026.9, iterated its private `_listeners` and read its private `_shutdown_requested`. Home Assistant may change any of them in a release; a changed signature would have made every read fail and every board unavailable, and the nightly test against the next Home Assistant would have been the first to notice.

## Options

1. Keep the overrides and test them against every beta of Home Assistant: fast, but each release can break every board, and the motion still updates every entity.
2. One coordinator per kind of value: public API only, but the motion, the cameras and the frame rates come in the same messages and reads as the state, so the reads would be split or repeated.
3. Keep the fast readings, the motion, whether the cameras run, frame rates and the load, in `readings` beside the coordinator's data, and give each kind a topic in a small `BoardTopics` hub that the entities showing it listen to. The data then stays equal when only readings change, so Home Assistant's `always_update=False` skips the update of every entity by itself.

## Decision

Option 3. It needs only what Home Assistant documents for coordinators, `_async_setup` and `_async_update_data`, and its own flag for an unload in progress. A message or a read that changes readings alone tells the listeners of their topics; anything else, also a camera alarm, updates every entity as before. Frame rates of realtime messages arrive several times a second, so their sensors show them with the next read.

## Consequences

A hand at the board writes the motion sensors alone, in under a tenth of a millisecond in a busy home. An entity that shows a reading names its topic, `_topic`, and reads it from `coordinator.readings`; the diagnostics list the readings under `local_readings`. `tests/test_topics.py` fails when the integration reads, writes or overrides a private member of `DataUpdateCoordinator`, and `tests/test_attribute_budget.py` checks that motion in a busy home updates only the motion sensors.
