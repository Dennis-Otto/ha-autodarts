---
description: "Why every game of the practice game is a mode of its own that the match frame plays in, instead of branches on the game in every step of the match."
---

# Play every game of the practice game as a mode of the match frame

- Status: accepted
- Date: 2026-10-18

## Context

`PracticeGame` played X01, the Cricket games, the party games and the training games in one class of more than 2,400 lines. Every step of a match asked which game was played: following the darts, booking a visit, the next turn, the state of the cards, the records of a leg and a match, the summary, the undo and the analysis of a visit, about forty branches on `self.game`, `self.cricket`, `self.party` and `self.drill`. A new game or statistic had to find and change many of them, and some paths drifted apart: the statistics after an undo, after a pass and of big party matches each needed a fix of their own. The party games (`PartyGame`) and the training games (`Drill`) already kept their rules in classes of their own.

## Options

1. Keep the branches, and test every game in every step: no change, but each new game touches the whole class again.
2. A subclass of `PracticeGame` per game: one class per game, but a game can't change while the match frame stays, and the frame would be copied with every change of the game.
3. The match frame with a mode per game: `PracticeGame` keeps what every match has, the players, seats and teams, the bot, the bull-off, legs and sets, the tallies, undo and the store, and hands every step that depends on the game to its mode in `modes.py`: `X01Mode`, `CricketMode`, `PartyMode` with its `PartyGame`, `DrillMode` with its `Drill`, and `GameMode` itself for no game.

## Decision

Option 3. A game is one class with the steps in which it differs, the frame stays the same for every game, and only the mode factory, `PracticeGame._mode`, knows the games. The store keeps its layout: the frame writes it as before and asks the mode for the parts only a game has, so stores of earlier versions load unchanged. Killer and the other differences within the party games moved into the classes of `party.py` as well, such as the lives Killer announces instead of points.

## Consequences

A new game is a mode, a `PartyGame` or a `Drill` and a line in the mode factory, and a setting that a game is made with goes in `GAME_SETTINGS`. The modes reach into the frame for what every game shares, such as the players at the board and who won a leg, through methods with a leading underscore that only the modes and the frame use. `tests/test_modes.py` loads a stored game of every kind and checks that it writes the same store byte for byte, and the state machine of `tests/test_practice_machine.py` does the same after every restart of Home Assistant that it plays.
