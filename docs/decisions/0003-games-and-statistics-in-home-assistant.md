# Keep games, training and statistics in Home Assistant itself

- Status: accepted
- Date: 2026-09-26

## Context

Without the cloud ([0002](0002-local-api-of-the-board-manager.md)), the matches, scores and statistics of Autodarts aren't available to the integration. Players still want to play X01, Cricket and training games at the board and see their progress in Home Assistant.

## Options

1. Show the darts only and leave games to the app of Autodarts.
2. Count games, training sessions and statistics in the integration, from the darts that the Board Manager reports, and store them in Home Assistant.

## Decision

Option 2. The integration runs its own practice games, matches, tournaments, the bot and the training drills, and keeps profiles, records and statistics in the storage of Home Assistant, from the local darts alone.

## Consequences

Games and statistics work offline and belong to the user. The integration has to get the rules of every game right itself, which its tests check in depth. A later link to the cloud adds to this; it doesn't replace it.
