# Changelog

All notable changes of the Autodarts integration. The complete notes of every version, with each pull request, are on the [releases page](https://github.com/Dennis-Otto/ha-autodarts/releases); what comes next is in the [roadmap](docs/roadmap.md). Versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

## [1.12.1](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.12.0...v1.12.1) (2026-10-10)

### Fixed

- **Nothing jumps after a tap:** on a phone, choosing a game far down the new game screen scrolled the page back up, so the next one had to be scrolled to again. In Safari, as in the Home Assistant app on an iPhone, the page jumped to its top; in every browser the rules of the game chosen before left above the tapped game and moved it away from the finger. A tapped button now stays where it is, on every card: the same jump hit *All badges* of the players card and the calibration of a camera on the status card in Safari. The heatmap's choice of whose darts and *All badges* keep the focus of a keyboard too.

## [1.12.0](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.11.0...v1.12.0) (2026-10-09)

### New

- **Darts by voice:** the new blueprint *Enter darts by voice* enters the darts of a game when you tell Assist, as at a dart machine: the score of a visit, such as "Alex hat 140" or "140 points", a checkout, such as "Checkout mit zwei Darts", a single dart, such as "Triple 20" or "Fehlwurf", "Next player" and "Undo", in English and German. Assist answers in the words of the scoreboard's caller: "140 for Alex, 361 left. Sam, you require 501." A sentence that names a player who is not at the board is refused, so a misheard visit never counts for the wrong player ([blueprint](docs/automations.md#enter-darts-by-voice)).
- **Answers of the actions at the board:** `autodarts.enter_visit`, `autodarts.throw_dart`, `autodarts.next_player` and `autodarts.undo_visit` answer with `response_variable` in words instead of failing, as `autodarts.start_game` does: what a visit scored and left and who throws next, the bed of a dart, the leg or the match, a visit taken back, or why they refused. `autodarts.enter_visit` takes `checkout: true` for a visit that checks out what the player has left, and both it and `autodarts.throw_dart` take `player`, which refuses the entry while another player is at the board ([actions](docs/entities.md#enter-a-visits-score-autodartsenter_visit)).

### Documentation

- The page about security lists `autodarts.enter_visit` among the actions a login can call.

## [1.11.0](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.10.0...v1.11.0) (2026-10-09)

### New

- **Play without Autodarts:** any dartboard can be set up as a board of its own, under *Dartboard without Autodarts: enter every dart yourself*. Its darts are entered on the keypad, which the live card and the scoreboard show without an option to switch on, and every game, the training sessions and all statistics work as with Autodarts. It has the entities of the games, without detection, cameras or a board PC, and the automatic dashboard leaves out its *Board* view ([guide](docs/without-autodarts.md)).
- **Autodarts later:** *Reconfigure* of a dartboard without Autodarts connects the Autodarts board it got, found on the network or by its address. The dartboard keeps its games, statistics, entity IDs and dashboards, and gets the detection, the cameras and the controls ([how](docs/without-autodarts.md#autodarts-later)).
- **The score of a visit:** in X01, *Score* at the top of the keypad takes a visit as its score, such as 140, instead of its darts, as on a dart machine. A checkout asks for its darts and the darts at a double, a visit that left a double in reach for the darts at it, so the checkout rate stays right; the visit counts for the averages, the 180s and the records, but for no bed. On a narrow pad, such as on a 360 pixel phone, the views of the keypad show icons, so they keep the line of S, D and T. The new action `autodarts.enter_visit` does the same ([how](docs/without-autodarts.md#enter-your-darts), [action](docs/entities.md#enter-a-visits-score-autodartsenter_visit)).
- **The keypad on the live card:** the option `keypad` of the live card shows the scoreboard's keypad below the darts while *Practice manual entry* is on, with *Next player* and *Undo last visit* ([cards](docs/cards.md#live-card)).

### Changed

- **Undo with the keypad:** on the scoreboard, the tile *Last* beside the darts takes the last visit back with the keypad too, as without it, so the keypad keeps the same keys after every visit; on a phone, its keys used to run over their edges in German. The curved arrow of *Last* keeps to its corner, clear of the words and the score, and on a short screen, such as a phone on its side, the score of the visit is as high as the beds of the darts beside it.

## [1.10.0](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.9.2...v1.10.0) (2026-10-08)

### New

- **Party games for up to eight:** Shanghai, Halve-It, Killer, Golf, Baseball and Count-Up take a whole party of up to eight players, on the new game screen, in `autodarts.start_game` and in *Practice players*, with four more name fields; the scoreboard shows them in two rows of four. X01, the Cricket and the training games stay at four ([games](docs/games.md#party-games)).
- **Big moments on the scoreboard:** confetti and a golden glow for a 180, confetti for a game shot and the match, and a glow for a ton and for nine marks in Cricket, on top of the scoreboard without moving anything. `celebrations: false` switches them off ([how](docs/scoreboard.md#during-the-game)).
- **How to play:** the new game screen explains the chosen game in a sentence or two, in every language of the cards, for guests who have never played Halve-It or Killer, with a link to all its rules on the documentation website ([how](docs/scoreboard.md#choose-the-next-game)).
- **Aim hints in Cricket:** as on a dart machine, the chalkboard frames the cells of the player at the board: green where a dart scores, because they have closed the number and somebody still needs it, amber where somebody else has closed it and scores on them. A dart that counted nothing is struck through on the live card and the scoreboard, and a tap or a mouse tells why ([how](docs/games.md#cricket-games)).
- **Wild Mouse:** a fourth Cricket game, also known as Minnesota Cricket. Besides 20 to 15 and the bull, every player closes three doubles, three triples and three in a bed. A dart counts for its number while it is open, otherwise for doubles or triples; the chalkboard has a row for each, the board outlines the next target, and teams, the bot and tournaments play it too. *Three in a bed* on the new game screen, or *Practice Wild Mouse three in a bed*, leaves the bed out ([rules](docs/games.md#wild-mouse)).
- **Free a stuck takeout:** Board Manager 2.0.2 sometimes starts a takeout again on the empty board right after one and keeps it, so darts thrown then are not counted and `takeout_finished` never comes. After ten seconds without darts and without a hand at the board, the integration now resets the board, at most three times in a row, and the takeout ends. The new switch *Free a stuck takeout*, on by default, turns it off; the automatic dashboard shows it with the board settings ([how it works](docs/entities.md#a-takeout-the-board-never-finishes)). Found by @JoeyAwwad (#172).

### Fixed

- **The scoreboard's header on a phone:** during a game, the *New game* button, the caller and the status kept to one row wider than the card, which cut off the end of the status, such as *Ready – throw!*, on a small phone in every language and on an iPhone in German and French. Where they do not fit beside each other, they now wrap below the title, and the status still keeps its width, so nothing moves while it changes.

### Documentation

- Animations of Wild Mouse, of the aim hints in Cricket and of a 180 on the scoreboard, pictures of the Wild Mouse chalkboard and of Killer for a party of eight, and diagrams of where a dart counts in Wild Mouse and of how a stuck takeout is freed ([games](docs/games.md#wild-mouse)).
- What changes on the way from Autodarts 1.x to 2.x, as a player reported it: the cameras to choose again in their old order, the first contact with the Autodarts server, the port and the stuck takeout ([troubleshooting](docs/troubleshooting.md#from-autodarts-1x-to-2x)).

## [1.9.2](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.9.1...v1.9.2) (2026-10-08)

### New

- **Betas for testers:** every change for users becomes a beta of the next release within minutes, which HACS offers to those who turn on the switch *Pre-release* of the integration ([how](docs/installation.md#betas-for-testers)).

### Changed

- **Help on the documentation website:** the help links of the cards in the card picker and of the automatic dashboard, and the documentation link of the integration, open the [documentation website](https://dennis-otto.github.io/ha-autodarts/) instead of GitHub, in German when Home Assistant speaks German.

### Documentation

- The website switches between English and German on every page, with German menus, search and dates, and starts with a page of its own for each language. The German pages moved next to the English ones, such as `docs/games.de.md` next to `docs/games.md`; the old addresses of the German overview and card guide lead there.

## [1.9.1](https://github.com/Dennis-Otto/ha-autodarts/compare/v1.9.0...v1.9.1) (2026-10-07)

### Fixed

- **Readable badges:** the words under a badge of the players card, such as when it was earned, had too little contrast on the gold of the badge in the dark theme. They now take the muted text of every other card and reach the contrast that WCAG 2.1 AA asks for.
- **The keyboard reaches the scores:** when the pad leaves a full-height scoreboard on a phone too little room, its scores scroll. A keyboard can now reach and scroll them as well, and a screen reader names them *Scoreboard*.

### Documentation

- The accessibility check of the cards, which axe-core runs in the browser test on a laptop and a phone in both themes.

## 1.9.0

### New

- **Start a game by voice:** a new blueprint lets Assist start a practice game, for example "Starte 501 für Alex und Sam", "Start the game Cricket for Alex" or "Spiele 501 gegen den Bot", in German or English. Assist answers with the game and the players, or with what was wrong. Every sentence has a number from 101 to 1001 or the word "Spiel" or "game", so Assist's own commands, such as a timer, stay its own (#123).
- **`autodarts.start_game` understands a voice:** a game by its name in any language of the integration, such as "Around the Clock" or "Doppeltraining", or by the beginning of a name that fits one game alone; a player's name in the spelling of the player's profile; and with `response_variable`, an answer in words to say instead of a failure (#123).
- **Hints on a tap:** what a mouse shows as a tooltip, a tap with a finger or a pen now shows in a small bubble over the card, without moving anything: the darts of a last visit, a visit in the training chart, a trend arrow, a double, the columns of a tournament's table, a camera's dot and the hint of a setup (#122).

### Changed

- **Game settings in a view of their own:** the live view of the automatic dashboard shows the live card alone. The rows of the practice game, its players, start scores and the tournament moved to the new view *Game settings* (#121).

### Documentation

- The voice blueprint with its sentences, the names and the answer of the start action, the new view and the hint building block, in English and German, with the screenshots and animations recorded anew. The example of an automation of your own no longer catches "start a timer for 5 minutes".

## 1.8.1

### Fixed

- **Nothing moves while a game goes on:** the scoreboard's tiles grew and shrank with what they showed: the average after the first dart, a route or a setup that took another line on a narrow tile, the points under a thrown dart, and *Undo last visit* as a row of its own after every takeout, which also shrank the numbers of a full-height scoreboard. Every tile, the visit and the Cricket chalkboard now keep their height from the start of a game to its last dart, on every screen from a 360 pixel phone to a 27 inch monitor, and the new browser step *steady heights* keeps it so (#119).
- **The status** keeps the width of its longest words during a game, so *Remove your darts* no longer pushes the scoreboard's buttons onto another line on a phone.
- **Training games:** the checkout rate and the best show a dash until they are known, and a narrow screen lays the facts out in columns; the live card's training head has a line for the game and one for what it says.

### Changed

- **Undo the last visit:** the tile beside the darts shows the last visit while the board is empty, between games too, with a curved arrow where a tap can take it back; a second tap on the red *Undo?* does it. The button below the visit is gone.
- **Killer notes** are shorter in German, Spanish, French and Dutch, so they fit one line.

### Documentation

- The README's animation is recorded anew with tiles that hold still, and the development guide has the rule that nothing moves during a game.

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
