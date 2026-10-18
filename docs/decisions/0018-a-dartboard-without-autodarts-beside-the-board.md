---
description: "Why a dartboard without Autodarts has a coordinator of its own beside the board's, without a client, instead of a board whose transport is switched off."
---

# Play a dartboard without Autodarts beside the board, without a transport

- Status: accepted
- Date: 2026-10-18

## Context

A dartboard without Autodarts plays the same games as a board with one, with every dart entered in Home Assistant. Its coordinator, `AutodartsManualCoordinator`, extended the board's `AutodartsLocalCoordinator` and switched its transport off again: it had no client, so the property `client` raised an error, and it replaced the realtime events, the reads, the polling interval and the diagnostics with methods that do nothing. Every new path of the transport that used `self.client` could therefore crash a dartboard without Autodarts at runtime, and only a test that happened to take that path would notice. Since [0016](0016-a-game-engine-without-home-assistant.md), the games run in `AutodartsGamesCoordinator`, which needs no Board Manager.

## Options

1. Keep the subclass and guard every new path of the transport: no change now, but each guard is one more place to forget.
2. A coordinator of its own beside the board's: `AutodartsManualCoordinator` extends `AutodartsGamesCoordinator` and has no client, no realtime events and no reads, and the code that needs the Board Manager asks for `AutodartsLocalCoordinator` by its type.

## Decision

Option 2. A dartboard without Autodarts has no transport that could be switched on by mistake, and the type checker finds every place that needs the Board Manager: `runtime.local` is an `AutodartsGamesCoordinator`, the entities of the games take any coordinator of the games, and the entities of the Board Manager, `AutodartsBoardEntity`, take only an `AutodartsLocalCoordinator`.

## Consequences

The setup of each platform adds the entities of the Board Manager after `isinstance(coordinator, AutodartsLocalCoordinator)`, the diagnostics, the repair of the calibration and the setup of a board ask for the type the same way, and a dartboard without Autodarts gets none of them. The flag `manual_board` stays for what follows from having no detection, such as manual entry that can't be switched off. A test plays a game on a dartboard without Autodarts, presses every button and switches every switch, reloads and unloads it, and fails if a client of a Board Manager is made or an address is asked.
