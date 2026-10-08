# Roadmap

[← Documentation](README.md) · [Deutsch](de/roadmap.md)

This roadmap shows what each version brought, what the next release brings and what comes after it. *Next* and *Later* look at least a year ahead, until October 2027, and *Not planned* says what the integration won't do. It is a direction, not a promise: priorities follow feedback from players, and dates depend on spare time. Ideas and votes are welcome as [feature requests](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose).

## Version 1.0: the local foundation

Released features, all of them working without the Autodarts cloud:

- Local realtime connection to Board Manager 1 and 2, with automatic discovery.
- Controls, board settings, camera health and Board Manager updates.
- Training analytics with hits per bed, visit history and the `visit_completed` event.
- Three dashboard cards, an automatic dashboard and six blueprints.
- Documentation in English and German.

## Version 1.1: training sessions

- Training sessions that start with the first dart or on purpose, end after a pause and keep a summary of the last 20 sessions.
- The `session_started` and `session_ended` events, and a seventh blueprint that ties light, detection and calibration to a session.
- The last visits in the live card, the session state and past sessions in the training card.
- Board PC details from Board Manager 2: operating system, processor and detection software.

## Version 1.2: practice games and live cameras

- X01 practice games (301, 501, 701) on the local board: remaining score, busts, double out, checkout routes and the last 10 legs, with the `bust` and `leg_won` events.
- A practice panel in the live card with the checkout route and the bed to aim at next, and the practice controls in the automatic dashboard.
- Live camera streams from Board Manager 2 instead of snapshots.
- Camera state right after the detection starts or stops, instead of after the next poll.

## Version 1.3: matches, training games and statistics

- X01 matches for two to four players at one board: the turn passes when the darts are pulled, with legs, sets, player names and a scoreboard in the live card.
- Training games: Around the Clock, doubles training, checkout training and Bob's 27, with the target outlined on the board.
- Practice statistics: first-9 average, checkout rate, doubles rate and legs per day.
- Two blueprints: a practice caller and a highlight photo after a 180 or a checkout.

## Version 1.4: Cricket, scoreboard and personal bests

- Cricket for one to four players with marks, closed numbers, points and marks per round, and a chalkboard in the live card.
- A scoreboard card and a full-screen scoreboard view for a screen at the board, readable from the oche.
- Personal bests with an event when one is beaten, a training streak in days and a daily goal.
- `autodarts.start_game` starts X01, Cricket or a training game with players, names and format in one action.
- Detection quality: the share of corrected darts, with a repair that recalibrates the board when it rises.

## Version 1.5: party games, player profiles, doubles and a caller

- Shanghai, Halve-It and Killer for one to four players; X01 from 101 to 1001 with double in and a bull-off.
- Player profiles with statistics and personal bests per name, a match history and head-to-head records, and a players card.
- A doubles analysis with the hit rate of every double, a doubles card and personal checkout routes.
- A caller in the scoreboard that announces the game through the browser, off by default.
- `autodarts.delete_player` removes a player profile, for example after a typo in a name.

## Version 1.6: more games, a game lobby, reports and online matches

Released as 1.6.0 on 27 September 2026; the [changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md#160) has the details.

| Topic | What it brings | Status |
| --- | --- | --- |
| **More games** | Cut-Throat Cricket, Tactics, Golf, Baseball and Count-Up; the training games 121 checkout, Catch 40, JDC Challenge and singles training | Done |
| **Handicap starts and teams** | Different X01 start scores per player in the same match, for example 501 against 301, and two teams of two in X01 and the Cricket games | Done |
| **Official rules** | PDC set order, match results as 3–2, checkout routes like the professional charts, the bull-off of the WDF and PDC rules | Done |
| **A scoreboard to start games** | A new game screen at the board, idle mode with a leaderboard, and the pictures of players linked to persons of Home Assistant | Done |
| **Reports** | A weekly report with a blueprint, a training calendar of a year and exports to CSV or JSON | Done |
| **Highlights and light** | A highlight gallery in the media browser and a light show blueprint | Done |
| **Online matches** *(experimental)* | Busts, won legs and matches of online matches through the browser extension Tools for Autodarts | Done |
| **Tournament mode** | Round robin or knockout for three to eight named players at one board: the table or bracket on the scoreboard, the next match starts by itself, and the results go into the player profiles | Done |
| **Match summary** | Every player's averages, checkout rate, highest checkout, 180s and best leg after a match, on the scoreboard, the live card and in `match_won` | Done |
| **Achievements** | Milestones per player in tiers, such as the first 180, a ton-plus checkout, a nine-darter or a ten-day streak, each with an event and shown as badges | Done |
| **Trends and heatmaps per player** | Average, checkout rate and doubles rate per week as a trend, every player's own heatmap and a leaderboard of the records of all players | Done |
| **Heatmap of the dart positions** | A heatmap that draws where every dart landed, from the positions the board reports, with the grouping in millimeters; the card switches between beds, numbers and positions | Done |
| **A bot and corrections** | A bot from level 20 to 120 in X01 and the Cricket games, corrections with a tap, darts entered by hand on a keypad, undo of the last visit, and setup hints where no checkout is possible | Done |
| **Dutch, French and Spanish** | The integration, the cards and the caller in three more languages, with tests that keep every language complete | Done |
| **Documentation** | Illustrated guides for games, the scoreboard and statistics, a glossary and an accessibility section | Done |

## Version 1.7: dart positions you can trust

Released as 1.7.0 on 28 September 2026; the [changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md#170) has the details.

- The positions heatmap of the training card follows every dart live.
- Corrected darts leave the board's misread position behind, or take the spot you tap on the scoreboard's board, which gives the bed at the same time.

## Version 1.8: every card on every screen

Released as 1.8.0 on 28 September 2026 and 1.8.1 on 29 September 2026; the [changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md#180) has the details.

- Every card fits from a 360 pixel phone to a 27 inch touch monitor, upright and on its side, with controls of at least 40 pixels for a finger.
- Corrections on the live card too, with a loupe and a zoom on every touch screen.
- A pencil shows what a tap edits, an arrow what a tap opens; states change with calm animations.
- The doubles card counts every double hit, in every game.
- Nothing on the cards changes its height while a game goes on.

## Version 1.9: games by voice

Released as 1.9.0 on 29 September 2026; the [changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md#190) has the details.

- A blueprint that starts a game when you tell Assist, for example "Start 501 for Alex and Sam" or "Starte das Spiel Cricket für Alex", in English and German, with an answer in words.
- What a mouse shows as a tooltip, a tap shows too.
- The game settings of the automatic dashboard in a view of their own.

## Next

Ideas for the versions after 1.9. Votes and reactions on the [feature requests](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose) decide the order.

| Topic | What it brings | Dependency |
| --- | --- | --- |
| **Questions to Assist** | "What is my average today?", "How many 180s this week?" as sentences of their own, and the voice start in every language of the integration | Sentences that feel natural at the board, from players who speak the language |
| **Autodarts Desktop** | Verify boards run by Autodarts Desktop and document what works; a player reported 2.0.2 on Linux working ([#105](https://github.com/Dennis-Otto/ha-autodarts/issues/105)) | Test reports from players who use it on Windows |
| **Cloud link** | Cloud match data and cloud match events: leg and match won, bust, player change, remaining score | An OAuth client ID from Autodarts, which has been requested |
| **HACS default repository** | Installation without adding a custom repository | Submitted in September 2026 ([hacs/default#11306](https://github.com/hacs/default/pull/11306)); the HACS review queue takes several months |
| **Further languages** | The integration and the cards in more languages | Contributions from native speakers ([how to add a language](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CONTRIBUTING.md#translations)) |

## Later

| Topic | Dependency |
| --- | --- |
| **Protocol library on PyPI** (`aioautodarts`) | A separate library for the Board Manager protocol, a prerequisite for a possible Home Assistant core integration; postponed until the protocol settles |

## Not planned

- **A cloud account for local play.** Everything that works with the Board Manager in your network keeps working without an Autodarts account; cloud features stay optional.
- **Telemetry.** The integration sends nothing about your games or your home anywhere, and in local mode nothing leaves your network.
- **Breaking changes without a way forward.** Existing config entries, entity IDs and automations keep working, or a release migrates them and its notes say what changes.

## How priorities are set

1. Anything that breaks for users, including changes in Board Manager versions, comes first.
2. Features that work locally come before cloud features.
3. Requests with the most reactions on GitHub come next.
