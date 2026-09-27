# Changelog

All notable changes of the Autodarts integration. The complete notes of every version, with each pull request, are on the [releases page](https://github.com/Dennis-Otto/ha-autodarts/releases); what comes next is in the [roadmap](docs/roadmap.md). Versions follow [Semantic Versioning](https://semver.org/).

## 1.6.0

### New

- **More games:** Cut-Throat Cricket and Tactics; the party games Golf (9 or 18 holes), Baseball and Count-Up; the training games 121 checkout, Catch 40, JDC Challenge and singles training.
- **Handicap and teams:** every player can start X01 from a score of their own, and four players play X01 or a Cricket game as two teams of two.
- **Tournaments** for three to eight players at one board: a round robin with a table or a knockout with a bracket, in X01 with start scores or a Cricket game; the next match starts by itself, the results go into the player profiles, and `autodarts.start_tournament`, `autodarts.next_tournament_match` and `autodarts.stop_tournament` run them from automations.
- **Match summary:** after an X01 or Cricket match, the scoreboard and the live card show every player's averages, checkout rate, highest checkout, 180s and best leg; `match_won` carries the numbers, and the winner's banner names the result, such as 3 : 2.
- **Achievements** in bronze, silver, gold and platinum, from the first 180 to a nine-darter, with the `achievement_unlocked` event and badges on the players card.
- **Player progress:** twelve weeks of trends per player, a heatmap of the real dart positions for the session or any player, the grouping of the darts in millimeters, and a new leaderboard card with the records of all players.
- **A game lobby on the scoreboard:** a new game screen to choose the game, the players and the format at the board, idle mode with a leaderboard, personal bests, today's darts, the last match and a clock, and the pictures of players linked to persons of Home Assistant with `autodarts.link_player` and `autodarts.unlink_player`.
- **Reports:** a weekly report with its sensor, the `weekly_report` event and a blueprint; a training calendar of the last 365 days; `autodarts.export` and an export button on the players card for CSV or JSON.
- **Highlights and light:** a highlight gallery in the media browser, fed by the highlight photo blueprint, and a new light show blueprint for WLED and room lights.
- **Online matches** *(experimental)*: an optional bridge brings busts, won legs and matches and the darts of opponents on play.autodarts.io into Home Assistant through the browser extension Tools for Autodarts.
- **Dutch, French and Spanish:** the integration, the cards and the caller speak three more languages.
- **Events in time:** `visit_thrown` announces a visit the moment its third dart lands; dart and visit events name the game and the player.
- **Bull-off by distance:** optionally, the measured distance also decides between two darts in the same bull bed. The scoreboard shows the bed and the distance of every dart and who leads.
- **Double out from the next leg:** switching double out during a leg applies from the next leg, so no leg becomes unwinnable.

### Improved

- **Official rules:** the throw alternates within a set and every set starts with the next player, as in PDC set play; a match ends 3–2 instead of losing the legs of the deciding set; checkout routes follow the professional charts; highest checkout and fewest darts count only legs with double out; Killer and Shanghai follow their rules in every detail.
- **Cards:** Home Assistant's own editor forms with color pickers, an editor for the automatic dashboard, personal bests on the training card, numbers, dates and times in the formats of your profile, a caller that calls only what counts, and better keyboard and screen reader support.
- **Connection:** visits and entities survive short connection faults; realtime reconnects with a back-off; a board that is off at the start no longer blocks the setup; repairs for a board that refuses access, answers in an unknown format or moved to a new address.
- **Entities:** clearer names without a repeated "Board", diagnostic and configuration categories where they belong, and complete diagnostics without player names.
- Brand icons and logos in the sizes of the Home Assistant brand specification.

### Documentation

- A new structure with illustrated guides for [games and rules](docs/games.md), the [scoreboard at the board](docs/scoreboard.md), [statistics and players](docs/statistics.md) and [online matches](docs/online-matches.md), a [glossary](docs/glossary.md) in English and German and an accessibility section in the card guide.
- A new README for HACS, with an animation of the live card and the scoreboard and a feature overview; many new screenshots and animations, and a demo with four weeks of long-term statistics.

### Quality

- 100 % line and branch coverage of the integration and DOM tests of every card element; an end-to-end test against Home Assistant 2026.8.0, the oldest supported release.
- CodeQL also checks the card JavaScript; releases are published only with their signed package attached.
- Community files: security policy with response times, support routes, Discussions, governance and contributor tooling.

## 1.5.0

- Shanghai, Halve-It and Killer for one to four players; X01 from 101 to 1001 with double in and a bull-off.
- Player profiles with statistics and personal bests per name, a match history, head-to-head records and a players card.
- A doubles analysis with the hit rate of every double, a doubles card and personal checkout routes.
- A caller in the scoreboard that announces the game through the browser, off by default.

## 1.4.0

- Cricket for one to four players with marks, closed numbers, points and marks per round, and a chalkboard in the live card.
- A scoreboard card and a full-screen scoreboard view for a screen at the board.
- Personal bests with an event when one is beaten, a training streak in days and a daily goal.
- `autodarts.start_game` starts X01, Cricket or a training game with players, names and format in one action.
- Detection quality: the share of corrected darts, with a repair that recalibrates the board when it rises.

## 1.3.0

- X01 matches for two to four players at one board, with legs, sets, player names and a scoreboard in the live card.
- Training games: Around the Clock, doubles training, checkout training and Bob's 27.
- Practice statistics: first-9 average, checkout rate, doubles rate and legs per day.
- Two blueprints: a practice caller and a highlight photo after a 180 or a checkout.

## 1.2.0

- X01 practice games (301, 501, 701): remaining score, busts, double out, checkout routes and the last 10 legs, with the `bust` and `leg_won` events.
- A practice panel in the live card with the checkout route and the next bed to aim at.
- Live camera streams from Board Manager 2 instead of snapshots.

## 1.1.0

- Training sessions that start with the first dart or on purpose, end after a pause and keep the last 20 sessions.
- The `session_started` and `session_ended` events, and a blueprint that ties light, detection and calibration to a session.
- The last visits in the live card, and the session state and past sessions in the training card.
- Board PC details from Board Manager 2: operating system, processor and detection software.

## 1.0.2

- The repository is now called `Dennis-Otto/ha-autodarts`; GitHub redirects the old address.

## 1.0.1

- Setup no longer offers the cloud link while Autodarts has not issued its client ID; old cloud entries keep working locally.
- Card colours accept valid CSS colours only.

## 1.0.0

- Local realtime connection to Board Manager 1 and 2, with automatic discovery; no Autodarts cloud account needed.
- Controls, board settings, camera health and Board Manager updates.
- Training analytics with hits per bed, a visit history and the `visit_completed` event.
- Three dashboard cards, an automatic dashboard and six blueprints.
- Documentation in English and German.

## 0.4.2 to 0.4.5

Pre-releases that led to 1.0.0.
