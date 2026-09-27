# How it works

[← Documentation](README.md) · [Deutsch](de/funktionsweise.md)

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/en/architecture-dark.png">
  <img src="images/en/architecture-light.png" alt="Architecture: the Board Manager on the board PC sends realtime events to the Autodarts integration in Home Assistant, which reads and controls the board over HTTP, keeps the training session locally and provides entities, board events, cards and automations; the Autodarts cloud optionally adds match data." width="560">
</picture>

A board is one config entry with up to two independent connections:

- **Local** (recommended): directly to the Board Manager in your network. It needs no login and provides controls, realtime events and training.
- **Cloud** (optional): match data from Autodarts. If it fails, local control keeps working, and the other way round.

## Data updates

| Source | How | Interval |
| --- | --- | --- |
| Board state, dart positions, motion, cameras, frame rates | WebSocket `/api/events` of the Board Manager | Immediately |
| Reconciliation while realtime events arrive | HTTP read | Every 30 seconds; every 10 seconds with Board Manager 2, which announces no camera changes |
| Fallback without realtime events | HTTP read | Every 2 seconds; every 15 seconds once the board has been away for about half a minute |
| Board Manager 2 | One combined read of `/api/system` per interval | As above |
| Board PC details, Board Manager 2 | HTTP read of `/api/host`; only the system, processor and software versions are kept | At start, every hour and after a Board Manager update |
| Board Manager 1 settings and version | HTTP read | Every 30 seconds, and after every action |
| Cloud match data | Autodarts API | Every 5 seconds during a match, otherwise every minute |

## Connection behavior

- **Realtime first.** Polling slows down once the first valid notification arrives, not merely when the socket opens, so a socket that stays silent keeps the fast polling.
- **Reconnects.** If the realtime connection drops, the integration switches to fast polling at once. It reconnects after 1, 2, 4 … up to 60 seconds, each wait shortened by a random amount of up to a fifth. A connection that lasted 30 seconds starts over at 1 second, and when a read finds the board back after an outage, the integration reconnects right away.
- **Short hiccups.** Two missed reads in a row, a few seconds, keep the last values; the third makes the board entities unavailable. While realtime events arrive, a missed read is no outage at all.
- **A board that stays away**, for example while its PC is off, is asked every 15 seconds after about ten missed reads. Fast polling resumes with the first answer.
- **Board off at the start.** The integration loads anyway. Training, practice games, personal bests, their entities and the board events work without the board; the board entities follow as soon as it answers.
- **Visits across interruptions.** While the board is out of sight, the visit in progress is kept. If the board still shows its darts first afterwards, the visit continues and new darts are detected. Otherwise, the darts were pulled meanwhile: the visit is completed with `visit_completed`, and the practice game books it. Darts thrown after that during the interruption are not counted, because they cannot be told apart from corrected darts. A status change during the interruption is announced with the first state afterwards.
- **One read at a time.** Reads never overlap, so an older answer never replaces a newer one, and a slow HTTP read never overwrites a newer realtime message.
- **High-rate values.** Frame rates and detection statistics only update their data and the camera alarm; they never recompute the training or the practice game.
- **Faults stay contained.** An error in the training or a game rule is logged once and never cuts the connection to the board.
- **Unexpected answers.** An answer in an unknown format is logged once per read. If a required read (state, settings or `/api/system`) answers like that three times in a row, a repair notice asks to update the integration. A board that answers with HTTP 401 or 403 gets a notice of its own; the Board Manager needs no login.
- **After an action.** The integration reads the board immediately after every action, so a switch reflects the new state within about a second.

## Board Manager generations

| | Board Manager 1 (classic app) | Board Manager 2 (headless) |
| --- | --- | --- |
| Detection | Version starts with `1.` | Version starts with `2.` and `/api/system` exists |
| Reads | Separate reads for state, statistics, cameras, motion, settings and version | One combined `/api/system` read |
| Extras | Cloud link switch and buttons | Cloud connection, CPU, memory, operating system, processor and detection software of the board PC, update notice, live camera streams, mDNS discovery |

The generation is detected on every read. When you update the board, the integration reloads itself and adds or removes the generation-specific entities; nothing else changes. While a board still runs Board Manager 1, a repair notice recommends the update. While the generation is still unknown, for example when the board is off at the first start, no entities are removed.

A board that reports version 2 but has no `/api/system` counts as Board Manager 1 after three answers without it. The integration remembers this for that Board Manager version, so a restart does not switch back and forth; another version is checked again.

## Address changes

- **Board Manager 2** announces itself in the network (mDNS). When it announces a new address, Home Assistant follows it and reloads the integration. Only the addresses the announcement was sent from are used, and a board that still answers at its configured address is never moved.
- **Entries linked to the Autodarts cloud** use the address the cloud reports when the configured one does not answer at the start. If the board has been away for five minutes at runtime and answers with its board ID at an address the cloud reports, a repair notice offers to switch to it. The cloud addresses are checked at most every 30 minutes.
- **Otherwise**, open the integration and choose **Reconfigure**, then search for the board or enter its address. The integration never contacts the Autodarts discovery service on its own.

## Training session

Training sessions are computed in Home Assistant from what the board detects. They follow these rules:

- **Sessions decide what counts.** Only darts thrown while a session runs count. Darts already on the board when a session starts belong to no session; darts still on the board when it ends stay with the ended session.
- **Events do not depend on sessions.** Dart, correction, takeout and visit events are announced with or without a running session.
- **Pauses end sessions.** With a pause set, a session ends that many minutes after its last dart, and its end time is the time of that dart. An end that became due while Home Assistant was stopped is applied at the next start.
- **Darts count once.** Repeated messages, camera jitter of the position and reconnects never count a dart twice.
- **Corrections revise.** If the board corrects a dart in the current visit, the totals follow the correction, for example when a 180 turns into a 140.
- **Takeouts end a visit.** Removing darts ends the visit; the removed darts keep their score. The same happens when new darts appear without an empty board in between (a missed takeout), and when the detection stops.
- **The third dart completes the visit early.** When the third announced dart of a visit lands, `visit_thrown` announces the visit at once, while the darts are still in the board. It comes once per visit, also after corrections; `visit_completed` follows when the visit ends, with the final score and `thrown: true`.
- **Startup darts are ignored.** Darts that are already on the board when Home Assistant starts are not counted.
- **Interruptions keep the visit.** After the connection was interrupted, the visit goes on if the board still shows its darts; otherwise it is completed, see [connection behavior](#connection-behavior).
- **Withdrawn detections.** If the board withdraws a detection outside a takeout, the dart is removed from the totals again.
- **Visit buckets.** 100+ counts visits with 100–139 points, 140+ with 140–179, and 180 with exactly three triple 20s. Merged visits with more than three darts (after a missed takeout) are not bucketed.
- **Storage.** The session, its settings, the last 20 sessions and the last 10 visits are saved in Home Assistant's `.storage` folder at most every five seconds, at once when a session starts or ends, and on shutdown. They are deleted together with the integration.

Sessions do not know players or games. A running session counts every detected dart, whether you play X01, Cricket or just practise.

## Practice game

The practice game follows the darts of the current visit, including corrections, like the training session does. When you pull the darts, the visit is booked. The [rules](#rules) below say how every game counts.

- **Visits:** a visit has three darts. A fourth dart before the takeout does not count. Darts the board does not detect, such as bounce-outs or darts on the floor, are not counted; a visit with fewer darts counts only the darts detected.
- **Checkout route:** the integration tries every combination for the darts left in the visit and picks the route the professional checkout charts pick, by these principles in this order:
  1. The fewest darts, so 50 is the bullseye even with three darts in hand.
  2. No double to set up, and a double before the bullseye to finish.
  3. With three darts in hand, a first triple that still leaves a two-dart finish when it lands in its single: 129 starts on T19, because a single 20 would leave 109.
  4. The biggest first triple, usually T20.
  5. Setup darts on the triple 20 or 19 or on a single towards D20, D16, D8, D18, D12, D10 or D4. With two darts left, the triple 20 or 19 is fine for any double when its single still leaves a one-dart finish: 70 with two darts is T20 D5, with the bull behind a single 20.
  6. Then any setup towards the good doubles D20, D16, D8, D18 or D12, then everything else; fewer triples, bigger triples, and the finishing double in the order D20, D16, D8, D18, D12, D10, D4, D14, D6, D2 and the odd doubles.

  So 144 is T20 T20 D12, 136 T20 T20 D8, 130 T20 T20 D5, 127 T20 T17 D8, 73 T19 D8 and 64 T16 D8. The scores 159, 162, 163, 165, 166, 168, 169 and everything above 170 have no route with double out. Without double out, the biggest bed finishes: a single before a double or a triple.
- **Personal routes:** with *Practice personal checkout routes*, the doubles of the player at the board with at least 10 darts each, best hit rate first, win over the usual route whenever a route with the same number of darts reaches them without a double to set up; among routes to the same double, the principles above decide.
- **Statistics:** each finished X01 leg adds one record for everybody at the board: the points and darts of the first nine darts, the darts thrown at a double and the checkout. Bust visits score nothing, also in the first nine. The statistics sensors use the last 10 records, so their history shows how you improve. *Practice legs played* counts every finished leg of X01, the Cricket games and the party games.
- **Storage:** the game, the rules, the teams and start scores, the players with their scores and marks, the match format, the last 10 legs and the [match summary](#match-summary) with the numbers it counts are saved together with the training session, and so is every player's [progress](#player-progress).

## Rules

The rules of every game, from X01 and the bull-off to the party and training games, are in the [games guide](games.md). The route principles above and the records below are how the integration applies them.

## Match summary

When a match of several players ends, the practice game sums it up for every player. `match_won` announces the numbers the moment the deciding dart lands, as they will be once the visit is booked; the `summary` attribute keeps them until the next match ends.

- **Legs, sets and darts:** the legs won in the whole match, the sets, and every dart thrown in the match.
- **3-dart average:** points per three darts of the whole match; darts of a bust visit count, their points do not.
- **First-9 average:** points per three darts of the first nine darts of every leg; a bust visit scores nothing here either.
- **Checkout rate:** legs checked out on a double per dart thrown at a double, with both counts. A dart counts at a double as for the [statistics](#records-and-statistics). Without double out, there is no checkout rate.
- **Highest checkout:** the highest score a player finished a leg with, also in a leg without double out.
- **100+, 140+ and 180:** visits of 100 to 139, 140 to 179 and 180 points that counted; a bust scores nothing.
- **Best leg:** the fewest darts of a leg the player won.
- **Cricket:** marks per round and the marks that counted, as in the [Cricket rules](games.md#cricket), and the best leg.
- **Party games:** legs, sets and darts.
- **Teams:** both partners win the legs, and their best leg counts the darts of both; a checkout counts for the player who threw it.

## Records and statistics

- **Highest visit:** the *Training highest visit* sensor and the `highest_visit` personal best take the points of the darts on the board in a visit of up to three darts, whatever the game: a bust visit or a Cricket visit counts with its board points, like the 100+, 140+ and 180 buckets. The `highest_visit` of a [player profile](entities.md#player-profiles) is the highest X01 score of that player instead: a bust scores nothing, and neither do darts before the opening double with double in.
- **Highest checkout and fewest darts:** the personal bests `highest_checkout` and `fewest_darts_*` and the same values of the player profiles only come from won X01 legs with double out, with or without double in. A leg without double out finishes more easily and sets no record; double in only makes a leg harder.
- **Start scores and teams:** the fewest darts count for the score a leg really started from: a leg from a start score of 301 counts for `fewest_darts_301`, a leg from 401 for no record, because 401 is no X01 game. A team leg sets no fewest darts and no best marks per round.
- **Cricket games:** the marks per round of the profiles and `best_cricket_mpr` come from Cricket; Cut-Throat and Tactics count their legs and matches.
- **Training games:** `checkout_121` keeps the highest score checked out in the 121 checkout; `catch_40`, `jdc_challenge` and `singles` keep the highest score of a finished game.
- **Darts at a double:** with double out, a dart counts as thrown at a double when one double could finish the score: 2 to 40 when even, or 50. So every dart at 50 counts as an attempt at the bullseye, also when a player sets up with a single 10 instead.

## Weekly report

The weekly report counts what the board detects, like the darts of the day, and follows these rules:

- **Every dart counts.** Darts count in a session or not, in a game or not. The 3-dart average covers every completed visit of the week, also merged visits after a missed takeout; the highest visit and the 180s count visits of up to three darts.
- **Training time** is the time from one dart to the next. A pause of more than five minutes between two darts does not count, so a break between two sessions is not training.
- **Sessions** count when they end: a session that runs over the end of the week counts for the next one.
- **Checkout rate** follows the X01 practice legs booked in the week: legs checked out per dart thrown at a double, like *Practice checkout rate*.
- **The week** runs from the report day and time to the same day and time a week later, in Home Assistant's time zone. A week with a change to or from daylight saving time is an hour longer or shorter; a report time the clock skips counts in the time before the change.
- **A new report day or time** ends the running week at its next occurrence, so that week can be shorter or longer.
- **Missed reports.** A report that fell due while Home Assistant was stopped follows at the next start; weeks in between had no darts and are skipped.
- **Storage.** The running week and the last report are saved in their own store in Home Assistant's `.storage` folder, at most every ten seconds, at once when a week ends and on shutdown. They are deleted together with the integration.

## Training calendar and exports

- **Journal.** The training calendar keeps every finished session and every match of several players for 365 days, at most 3,000 of each, in its own store in `.storage`. It is saved when a session or match ends and deleted together with the integration. At the first start it takes over the sessions and matches the integration already stored.
- **First dart.** A match starts with the first dart detected while a match of several players is selected. Switching the game off, to a training game or to another game forgets that dart.
- **Exports** are written by the action `autodarts.export` only, into a folder inside the configuration folder. The folder is resolved before writing, so neither `..`, an absolute path nor a symbolic link can lead outside, and hidden folders such as `.storage` are refused. Every export gets a new name with a random part and never replaces a file. In CSV, a text that starts like a spreadsheet formula (`=`, `+`, `-`, `@`) gets a leading apostrophe, so a player name cannot run as a formula.
- **Downloads.** Besides `/local/`, logged-in users can download the exports written since Home Assistant started from `/api/autodarts/export/<name>`; the players card uses this address with a signed link that expires after a minute.

## Highlight gallery

The media source *Autodarts* shows the photos that the [highlight photo blueprint](automations.md#highlight-gallery) saves:

- **Folder:** `autodarts/highlights` in the media folder of Home Assistant. That is the media folder `local`: `/media` on Home Assistant OS and in a container, otherwise the `media` folder in the configuration folder. If you set `media_dirs` without `local`, the first of them.
- **Names:** `YYYY-MM-DD_HH-MM-SS_<player>_<score>.jpg`; the time and the player are optional, and a checkout reads `checkout-121`. Other pictures (`.jpg`, `.jpeg`, `.png`, `.webp`) show by their file name and the time they were saved.
- **Order:** the months newest first, each with its newest photo as the cover; the photos of a month newest first.
- **Titles:** in the language of Home Assistant's server, for example *September 2026* and *180 · Alex · Sep 26* in English, *26.09.* in German, *26-09* in Dutch and *26/09* in French and Spanish.
- **Safety:** only plain file names of that folder open, and only pictures; hidden files, subfolders and links out of the folder are ignored. Home Assistant's own media view serves the photos, to logged-in users or with a signed address.

## Player progress

Every named player of a practice or training game has progress of their own next to the [player profile](entities.md#player-profiles). It counts the darts of every visit the game books for the player at the board, when the darts are pulled; training games count for player 1. A player without a name counts for nobody.

- **Weeks.** Sums of every week, from Monday, for the last 12 weeks: darts, X01 darts and points, the first nine darts of each leg and their points, darts at a double and checkouts, darts at doubles and hits in all games, Cricket darts and marks, legs played and won and 180s, with the week's highest checkout, fewest darts of a 501 leg and best Cricket MPR. The legs and the numbers of a leg count in the week the leg ends. Averages and rates come from the sums, so several weeks add up exactly. Older weeks are dropped.
- **Hits per bed** of every dart the player threw, like the heatmap of the session.
- **Day streak:** days in a row with at least one dart in a practice or training game. It stays until a whole day passes without darts.
- **Counts for the achievements:** darts thrown, X01 visits of 100 or more, 140 or more and 180, hat tricks, nine-mark Cricket visits, Shanghai wins, the best checkout training finish, the fewest darts of Around the Clock and the best completed Bob's 27. Everything else comes from the player profile.

A visit scores for the achievements as the game counts it: a bust scores nothing, and neither do darts before the opening double with double in. Achievements are checked after every booked visit; the [achievement reference](entities.md#achievements) lists what each measures.

### Dart positions

The Board Manager reports where each dart landed, relative to the outer edge of the double ring. Home Assistant keeps the positions of the last 1000 darts of every named player and of the darts of the current training session, at most 5000; a new session starts empty, and darts without a position, such as bounce-outs, are left out. Each position is kept with the bed the dart was aimed at, where the game knows it:

- **X01:** the double when one dart can finish the score, that is 2 to 40 when even or the bullseye at 50. Otherwise the first bed of the checkout route when a route exists with the darts left, or the treble 20 when no checkout is possible, as in a scoring visit. Darts at a single or the outer bull, darts up to the opening double with double in, and darts after a bust or the finish have no aim.
- **Doubles training and Bob's 27:** the double of the round. **Checkout training:** the route, as in X01. **Bull-off:** the bullseye.
- **Around the Clock, Cricket and the party games:** no aim, because any bed of a number counts there.

Positions are stored to a tenth of a millimeter with the training. They say where darts land and nothing else, and they never leave Home Assistant; diagnostics only count them. The cards read them on demand with the WebSocket command `autodarts/positions` (`device_id`, optional `player`), because thousands of positions are too many for entity attributes.

### Grouping

For every bed aimed at with at least 10 logged darts, the grouping describes where those darts landed around the center of the bed:

1. Every position becomes an offset in millimeters from the center of the bed, x to the right and y up, as the player sees the board. The center of a treble lies 102 mm from the middle of the board, the center of a double 165 mm, and the bullseye in the middle.
2. The **offset** is the mean of these offsets: where the darts land on average. *6 mm left of center, 3 mm high* describes that mean point.
3. The **grouping** is the radius around the mean point that holds half of the darts, the smallest distance with at least 50 % of them within it; the second radius holds 80 %. *Grouping 38 mm* means that every second dart lands within 38 mm of the mean point.
4. The **trend** compares the grouping of the newer half of the logged darts with the older half, once there are 20: *4 mm tighter* means the newer darts land 4 mm closer together.

The offset shows the accuracy of a player, the grouping the precision. Both rely on the positions the board reports, and a player's grouping covers their last 1000 darts. The profile lists the six beds with the most darts, the cards the first three.

## Camera health

A camera counts as failed when it delivers no frames for **15 seconds** while the detection runs. Stopped detection, calibration and camera standby are not failures. The combined *Camera problem* sensor is on when any camera has failed. With realtime events, the alarm appears as soon as the frame rates show it.

The camera entities relay the live stream of Board Manager 2 to at most two viewers per camera; further viewers get snapshots, which spares the board PC that also runs the detection.

## Privacy

- **Local mode** talks only to the Board Manager in your network. The integration sends nothing to the internet.
- **Search for boards** asks `discover.autodarts.com`, the public Autodarts discovery service, once when you use it. The service sees your public IP address and returns the boards registered from it.
- **The optional cloud link** uses the Autodarts device login. Home Assistant stores OAuth tokens, never your password.
- **The optional online bridge** only receives: the browser extension Tools for Autodarts calls Home Assistant with the moments of an online match, by default only from your home network. It sends nothing anywhere. [Online matches](online-matches.md).
- **Board secrets** are dropped as soon as they are read and are never stored, logged or shown: the board API key, TLS keys, camera device paths and similar configuration.
- **Diagnostics** redact the board ID, host, client ID, tokens and player names. The connection history in them holds counts, kinds of errors and durations, but no addresses or error messages.
- **Exports** contain player names. The action writes them only on request; files in `www` are served at `/local/` without a login, see [exports](#training-calendar-and-exports).
- **Highlight photos** stay in your media folder; the gallery reads nothing else.
- **Persons:** a player linked to a person keeps only the entity ID of the person; the card reads the picture and whether the person is home from Home Assistant.
- **The caller of the scoreboard** speaks with the voice of the browser on the screen at the board. Which voice that is depends on the browser and the operating system: the voices of the operating system work offline, while some browsers offer online voices that send the text of the calls to their provider. Choose an offline voice in the settings of the device if that matters to you.

### Stored data

Everything the integration keeps lives in Home Assistant's `.storage` folder, never in the cloud, and is deleted together with the integration:

| Store | Contents |
| --- | --- |
| `autodarts.<entry>.training` | The training session with its settings, the last 20 sessions and the last 10 visits; the practice game with its rules, teams, start scores, player names and the last 10 legs; the personal bests, the training streak and the darts of the day; the player profiles with their statistics, personal bests, doubles and linked persons, the last 20 matches and the head-to-head records; the doubles analysis |
| `autodarts.<entry>.report` | The running week and the last weekly report |
| `autodarts.<entry>.journal` | The sessions and matches of the training calendar, 365 days, at most 3,000 of each |

Highlight photos and exports are files you create on purpose. They stay in the media folder and the export folder when the integration is deleted.

## Security

- The Board Manager's local API does not ask for a login, so anyone who can reach port 3180 in your network can use it, with or without Home Assistant. Keep the board PC in a trusted network.
- Actions are only sent when you or an automation trigger them. They are never repeated automatically.
