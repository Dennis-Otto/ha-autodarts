# Changelog

All notable changes of the Autodarts integration. The complete notes of every version, with each pull request, are on the [releases page](https://github.com/Dennis-Otto/ha-autodarts/releases); what comes next is in the [roadmap](docs/roadmap.md). Versions follow [Semantic Versioning](https://semver.org/).

## 1.8.0

### New

- **Correct darts on the live card:** a tap on a dart of the visit opens the scoreboard's pad below the darts, with its keys, its board, the loupe and the zoom. A pencil at the top right marks every dart a tap corrects. The new option `corrections` switches it off.
- **Loupe and zoom on touch screens:** on a small screen, the board of a correction opens zoomed in on where the board saw the dart. A finger held on the board shows a loupe above it and sets the dart where it lets go; two fingers zoom and move the board. A round magnifier switches between the zoomed part and the whole board. The loupe and the fingers work on every touch screen, a 24 or 27 inch touch monitor too.
- **Every double hit counts:** the doubles card counts every double any dart hits, in every game and in plain training, next to the rate where darts were aimed at a double. The doubles sensor carries them as `landed`.

### Improved

- **Phones, tablets and touch monitors:** every card fits and reads well from a 360 pixel phone to a 27 inch touch monitor, upright and on its side. The full-height scoreboard stays one screen high, the board to tap fills the room the scores leave, keys grow on large screens, and every control is at least 40 pixels for a finger on any touch screen, also with a mouse plugged in.
- **Clear at a glance:** a pencil shows what a tap edits, an arrow what a tap opens; static parts such as the player tiles, the visit's total, the status and the beds of a route no longer look like buttons. The second tap that confirms is red on every card, the pad says why it waits while the bot throws, and the new game screen says why a player sits out. States change with calm animations, and not at all where the device asks for less motion.
- **The badge gallery** shows each player's badges earned and the three nearest goals; *All 18 badges* opens the rest.
- **Trends** run on through weeks without darts, and a figure without two halves to compare shows no arrow.
- **Grids** keep a tile from standing alone in a last row: four players stand two by two rather than three and one.

### Fixed

- **The scoreboard on a phone** was cut off at the bottom, and the new game screen's start bar showed what scrolled beneath it.
- **The positions heatmap** drew darts that landed beside the board; only darts on the board show (#112).
- **The doubles card** stayed empty after a game with doubles in it.
- **On a phone on its side,** the board to tap was only 160 pixels high, and a zoomed board drew over the keys.
- **A finger on the board to tap** could outlast a pad that closed under it, and later boards no longer redrew.

### Changed

- **Shorter entity names** where Home Assistant's rows cut them: *Distortion correction* instead of *Automatic distortion correction* in every language, and in German *Übungsspiel neues Match*, *Übungsspiel neues Leg* and *Turnier Dauer der Zusammenfassung*. Existing entity ids stay; a new installation names the distortion switch `switch.<board>_distortion_correction`.
- **Taps that opened details unannounced:** the training card's tiles open nothing any more, *Details* below them does; the live card's board is a picture. The status card's own calibration reads *Calibrate all*.

### Documentation

- The loupe, the zoom and touch monitors, correcting on the live card with a new animation, and the UI building blocks in the development guide.

## 1.7.1

### Fixed

- **No error in the log when Home Assistant restarts:** a board poll that started after Home Assistant had closed its connections logged *Unexpected error fetching autodarts_local data* with a traceback. It now counts as an ordinary lost connection, like the event stream, the camera stream and the cloud requests. Reported by @JoeyAwwad in #107.
- **Board settings show at once:** with Board Manager 1, a setting switched on or off, such as *Auto distortion*, could show its old value for up to 30 seconds when a poll was reading the settings at that moment.

### Documentation

- **Autodarts Desktop on Linux** is listed under the supported devices: a player reported version 2.0.2 on Ubuntu 24.04 working with every feature (#105). Autodarts Desktop on Windows is still untested; a compatibility report helps.

## 1.7.0

### New

- **Where a corrected dart really is:** the scoreboard's pad has a new *🎯 Board* view. Tap the spot where the dart is, and the bed and the position come in one step; a dashed ring shows where the board saw the dart. The keypad for darts entered by hand uses it too. `autodarts.correct_dart` and `autodarts.throw_dart` take the position as `x` and `y`, and the bed follows from it.

### Improved

- **Live dart positions:** the positions heatmap of the training card shows the darts of the current visit the moment they land, as blue pins, and loads the logged darts again as soon as you pull them, instead of a visit later.
- **Clean positions after corrections:** where the board misread a bed, it misread the spot as well. A dart corrected into another bed therefore leaves the board's position behind and stays out of the dart positions, the grouping and a bull-off by distance, unless the correction says where the dart is.

## 1.6.0

### New

- **More games:** Cut-Throat Cricket and Tactics; the party games Golf (9 or 18 holes), Baseball and Count-Up; the training games 121 checkout, Catch 40, JDC Challenge and singles training.
- **Handicap and teams:** every player can start X01 from a score of their own, and four players play X01 or a Cricket game as two teams of two.
- **Tournaments** for three to eight players at one board: a round robin with a table or a knockout with a bracket, in X01 with start scores or a Cricket game; the next match starts by itself, the results go into the player profiles, and `autodarts.start_tournament`, `autodarts.next_tournament_match` and `autodarts.stop_tournament` run them from automations.
- **Match summary:** after an X01 or Cricket match, the scoreboard and the live card show every player's averages, checkout rate, highest checkout, 180s and best leg; `match_won` carries the numbers, and the winner's banner names the result, such as 3 : 2.
- **A bot** to play X01 and the Cricket games against, from level 20 to 120: it aims like a player, its darts land with a scatter calibrated to its 3-dart average and show on the cards, and it never counts in your statistics. Seat it on the new game screen, with *Practice bot level* or with `bot_level` of `autodarts.start_game`.
- **Corrections and darts entered by hand:** a tap on a dart of the scoreboard, or `autodarts.correct_dart`, corrects a dart the board read wrong; with *Practice manual entry*, a keypad or `autodarts.throw_dart` enters darts the board missed; `autodarts.next_player` passes the turn, and `autodarts.undo_visit` takes the last visit back, with the new `visit_undone` event.
- **Setup hints:** where the darts left cannot check out, the cards, `turn_changed` and the callers suggest a setup that leaves a good double, such as T20 T20 S17 to leave 32.
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
- **Safe statistics:** a board whose stored training cannot be read right now, or was saved by a newer version, waits instead of starting empty, so its data is never overwritten. Every leg and visit counts once in the statistics, undo also rewinds the progress, the weekly report and the calendar, and in a team match only the player who checks out gets the checkout.
- **Rules:** Golf counts a double as a hole in one and a triple as two strokes; in the checkout training, the 121 checkout and Catch 40 a bust voids only its visit, the 121 checkout plays every score up to 170, and Catch 40 scores 3 points for 99 in three darts; Cut-Throat Cricket checks the win after every dart; a tournament hands the practice game its players and settings back when it ends; the bot plays Cricket at the marks per round of its level.
- **Scoreboard:** fits every screen, with the pad and the keypad beside the scores on a full-height screen in landscape; starting a game in the lobby also starts the detection; the automatic dashboard sets the scoreboard's caller, keypad, corrections, lobby games and idle panels without taking control; the training card's chart follows the history live, and an undone visit leaves it.
- **Actions and security:** deleting, linking and exporting the players' data are administrator actions, which automations still run; exports go to the media folder by default, only to folders where Home Assistant allows writing and at most 20 an hour; a board found at a new address moves only after you confirm a repair; the highlight gallery shows small thumbnails; invalid values of an action get a message in your language.
- **Quieter entities:** *Last event* and *CPU usage*, which change all the time, start disabled on boards set up from now on.
- **Blueprints:** the visit score and the light show leave the bot out unless you turn on *Also for the bot*, and the callers and the light show name it "Bot" like the scoreboard; the highlight photo hands the saved photo to your notification as `photo_url`; the light show keeps up to nine moments waiting behind an effect, reacts to the takeout only when you ask, and never pauses the detection in the middle of a visit; player names never become templates.
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
- Card colors accept valid CSS colors only.

## 1.0.0

- Local realtime connection to Board Manager 1 and 2, with automatic discovery; no Autodarts cloud account needed.
- Controls, board settings, camera health and Board Manager updates.
- Training analytics with hits per bed, a visit history and the `visit_completed` event.
- Three dashboard cards, an automatic dashboard and six blueprints.
- Documentation in English and German.

## 0.4.2 to 0.4.5

Pre-releases that led to 1.0.0.
