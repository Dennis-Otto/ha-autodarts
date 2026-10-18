---
description: "Why the games of a board run in an engine without Home Assistant, which the coordinators bring the darts and whose events they announce."
---

# Run the games in an engine without Home Assistant, apart from the connection to the board

- Status: accepted
- Date: 2026-10-18

## Context

One class, `AutodartsLocalCoordinator`, held everything about a board in 2303 lines and 129 methods: the realtime events and reads of the Board Manager, its generations, stuck takeouts and repair issues, and next to them the training, the practice games, the tournament, the bot, the darts entered by hand, the undo of a visit and the stored data. A rule of the games could only be tested through a board set up in Home Assistant, which takes seconds per test, and the entities reached into the parts of the games on the coordinator. The defects of an undo, a pass and the statistics that [#231](https://github.com/Dennis-Otto/ha-autodarts/pull/231) fixed came from changes in one part that affected another.

## Options

1. Keep the one class and test the games through Home Assistant: no change, but every rule of the games stays slow to test and entangled with the connection.
2. Split the games into several helpers on the coordinator: smaller methods, but the games still need Home Assistant's timers, store and events to run, and so a `hass` to be tested.
3. An engine of the games without Home Assistant, `BoardGames` in `games.py`, whose steps take the time as a parameter and return the board events they bring; a coordinator of the games, `AutodartsGamesCoordinator`, that brings it the darts and the actions, announces its events, stores it with `BoardStore` and keeps its timers; and the connection to the Board Manager in `AutodartsLocalCoordinator`, which extends the coordinator of the games.

## Decision

Option 3. The engine holds every rule of the games and can be tested in milliseconds; the Home Assistant side of the games is small and the same for every kind of board, which a dartboard without Autodarts, and later a tournament on several boards, can use without a Board Manager. The behaviour stays the same: the existing tests run unchanged against the new classes, with every line and branch covered.

## Consequences

Entities read the games through `coordinator.games` and change them only through the actions of the coordinator, which save and announce the change. A new rule of the games goes into `BoardGames` or a class it holds, with a test in `tests/test_games.py` without a `hass` fixture; that test also fails when `games.py` imports anything of Home Assistant. An action the games refuse raises `ActionRefused`, which the coordinator turns into the message for the user. [Development](../development.md#the-board-and-its-games) describes the classes with a diagram.
