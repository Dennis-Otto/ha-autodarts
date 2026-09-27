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
| Extras | Cloud link switch | Cloud connection, CPU, memory, update notice, mDNS discovery |

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
  3. With three darts in hand, a first treble that still leaves a two-dart finish when it lands in its single: 129 starts on T19, because a single 20 would leave 109.
  4. The biggest first treble, usually T20.
  5. Setup darts on the treble 20 or 19 or on a single towards D20, D16, D8, D18, D12, D10 or D4. With two darts left, the treble 20 or 19 is fine for any double when its single still leaves a one-dart finish: 70 with two darts is T20 D5, with the bull behind a single 20.
  6. Then any setup towards the good doubles D20, D16, D8, D18 or D12, then everything else; fewer trebles, bigger trebles, and the finishing double in the order D20, D16, D8, D18, D12, D10, D4, D14, D6, D2 and the odd doubles.

  So 144 is T20 T20 D12, 136 T20 T20 D8, 130 T20 T20 D5, 127 T20 T17 D8, 73 T19 D8 and 64 T16 D8. The scores 159, 162, 163, 165, 166, 168, 169 and everything above 170 have no route with double out. Without double out, the biggest bed finishes: a single before a double or a treble.
- **Personal routes:** with *Practice personal checkout routes*, the doubles of the player at the board with at least 10 darts each, best hit rate first, win over the usual route whenever a route with the same number of darts reaches them without a double to set up; among routes to the same double, the principles above decide.
- **Statistics:** each finished X01 leg adds one record for everybody at the board: the points and darts of the first nine darts, the darts thrown at a double and the checkout. Bust visits score nothing, also in the first nine. The statistics sensors use the last 10 records, so their history shows how you improve. *Practice legs played* counts every finished leg of X01, Cricket and the party games.
- **Storage:** the game, the rules, the players with their scores and marks, the match format and the last 10 legs are saved together with the training session.

## Rules

### X01

- **Counting down:** the score starts at 101, 301, 501, 701, 901 or 1001, and every dart subtracts its score.
- **Double out** (on by default): the last dart of a leg must hit a double or the bullseye. Without double out, any bed finishes.
- **Double in** (off by default): a player's score starts with the first double or bullseye of the leg; darts before it score nothing. A bust takes the opening double back.
- **Bust:** a dart that goes below zero, leaves 1 with double out, or reaches 0 without a double busts the visit. The score returns to the start of the visit. The dart that busts counts as thrown; later darts of the visit do not.
- **Win:** a dart that reaches exactly 0 wins the leg. `leg_won` is announced at once, with the rules of the leg (`double_out`, `double_in`). The leg is booked when you pull the darts, so a correction before that still counts. Darts after the winning dart do not count. The next visit starts a new leg.
- **Average:** points scored per three darts of the leg. Darts of a bust visit count, their points do not.

### Matches, legs and sets

- **Turns:** with two to four players, the turn passes when the darts are pulled, also after a bust.
- **Legs and sets:** the first player to win *legs per set* legs wins the set; there is no tie-break and no need for two clear legs. The first player to win *sets to win* sets wins the match. With one set to win, a match is simply the first to that many legs. With one player, legs just count up.
- **Throwing first:** as in PDC set play, the first throw passes to the next player every leg within a set, and every new set starts with the player after the one who started the previous set. With two players, player 1 starts sets 1, 3 and 5 and player 2 sets 2 and 4. The first leg of a match starts with player 1, or with the winner of the bull-off.
- **Result:** the match result stays until the next dart, which starts a new match. The winner keeps the legs of the deciding set, so a first-to-3 match ends 3–2 on the scoreboard. `match_won`, the *Last match* history and the player profiles keep every player's legs and sets; `match_legs` counts the legs of the whole match.
- **Averages:** each player's average and marks per round cover the whole match.

### Bull-off

- With *Practice bull-off* and two or more players, a match starts with one dart per player at the bull, in seat order. Only the first dart of each visit counts.
- As the WDF and PDC rules want, the bullseye beats the outer bull, which beats every other bed. Two or more darts in the same bull bed tie: those players throw again, the last of them first.
- Outside the bull, the dart closer to the centre wins. The distance comes from the position the board reports, relative to the outer edge of the double ring (170 mm).
- With *Practice bull-off by distance*, the measured distance also decides between two darts in the same bull bed; darts equally close to 0.1 mm throw again.
- A dart without a position cannot be measured, so it never beats a measured dart: when the decision needs a distance the board did not report, those players throw again.
- The bull-off only decides who starts. With three or four players, the others follow in seat order.

### Cricket

- **Marks:** only 20 to 15 and the bull count. A single is one mark, a double two, a treble three; the outer bull is one mark, the bullseye two. Three marks close a number.
- **Points:** further marks score the number's value (25 for the bull) while another player has it open.
- **Win:** close every number with at least as many points as everybody else. The win is checked after every dart, so a closing dart wins at once when the points are enough, and later darts of the visit do not count. Alone, closing every number wins.
- **Marks per round:** the marks that closed a number or scored, per three darts actually thrown.

### Shanghai

- Seven rounds at the numbers 1 to 7; the traditional pub game plays 1 to 20 or nine rounds.
- Every dart in any bed of the round's number scores its value. A miss next to the number counts nothing.
- A single, a double and a treble of the number in one visit, a *Shanghai*, win the leg at once; later darts of the visit do not count.
- After seven rounds, the most points win. A tie in points goes to the player with more hits; with equal hits, the leg is played again and the next player starts it.

### Halve-It

- Everybody starts with 40 points. The nine rounds aim at 15, 16, any double, 17, 18, any treble, 19, 20 and the bull, shown as 25.
- Hits add their score. *Any double* includes the bullseye. In the bull round, the outer bull scores 25 and the bullseye 50.
- A visit without a hit on the target halves the points, rounded down, also when fewer than three darts were thrown.
- The most points after nine rounds win; ties are decided like in Shanghai.

### Killer

- Two to four players with 3 lives each.
- First, everybody throws one dart for a number of their own: any bed of 1 to 20 that nobody has yet. A miss, the bull or a number already taken means throwing again.
- Only doubles count after that. Hitting the double of your own number makes you a killer for the rest of the leg. Before that, the doubles of the others do nothing.
- A killer takes a life with every hit on another player's double and loses one with every hit on their own, also with a second own double in the visit that made them a killer.
- A player without lives is out: the rest of the visit does nothing, and the turn skips them from then on.
- The last player with a life left wins at once; later darts of the visit do not count.

### Training games

- **Around the Clock:** 1 to 20, then the bull, in order, with any bed of the number. The bull target is shown as `25`: the outer bull and the bullseye both count.
- **Doubles training:** D1 to D20, then the bullseye (`BULL`); only the double ring and the bullseye count.
- **Checkout training:** a random score from 2 to 170 that three darts can finish, checked out on a double within three visits. A bust or a third visit without the finish ends the attempt; the route shows only while the attempt goes on.
- **Bob's 27:** start with 27 points and throw one visit at each double from D1 to D20 and then at the bullseye. Every hit adds the value of the double; a visit without a hit subtracts it. The game is lost as soon as the score reaches zero or less, and completed after the bullseye.

### Records and statistics

- **Highest visit:** the *Training highest visit* sensor and the `highest_visit` personal best take the points of the darts on the board in a visit of up to three darts, whatever the game: a bust visit or a Cricket visit counts with its board points, like the 100+, 140+ and 180 buckets. The `highest_visit` of a [player profile](entities.md#player-profiles) is the highest X01 score of that player instead: a bust scores nothing, and neither do darts before the opening double with double in.
- **Highest checkout and fewest darts:** the personal bests `highest_checkout` and `fewest_darts_*` and the same values of the player profiles only come from won X01 legs with double out, with or without double in. A leg without double out finishes more easily and sets no record; double in only makes a leg harder.
- **Darts at a double:** with double out, a dart counts as thrown at a double when one double could finish the score: 2 to 40 when even, or 50. So every dart at 50 counts as an attempt at the bullseye, also when a player sets up with a single 10 instead.

## Camera health

A camera counts as failed when it delivers no frames for **15 seconds** while the detection runs. Stopped detection, calibration and camera standby are not failures. The combined *Camera problem* sensor is on when any camera has failed. With realtime events, the alarm appears as soon as the frame rates show it.

The camera entities relay the live stream of Board Manager 2 to at most two viewers per camera; further viewers get snapshots, which spares the board PC that also runs the detection.

## Privacy

- **Local mode** talks only to the Board Manager in your network. Nothing is sent to the internet.
- **Search for boards** asks `discover.autodarts.com`, the public Autodarts discovery service, once when you use it. The service sees your public IP address and returns the boards registered from it.
- **The optional cloud link** uses the Autodarts device login. Home Assistant stores OAuth tokens, never your password.
- **Board secrets** are dropped as soon as they are read and are never stored, logged or shown: the board API key, TLS keys, camera device paths and similar configuration.
- **Diagnostics** redact the board ID, host, client ID, tokens and player names. The connection history in them holds counts, kinds of errors and durations, but no addresses or error messages.

## Security

- The Board Manager's local API does not ask for a login, so anyone who can reach port 3180 in your network can use it, with or without Home Assistant. Keep the board PC in a trusted network.
- Actions are only sent when you or an automation trigger them. They are never repeated automatically.
