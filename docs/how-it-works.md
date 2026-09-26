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
| Reconciliation while realtime events arrive | HTTP read | Every 30 seconds |
| Fallback without realtime events | HTTP read | Every 2 seconds |
| Board Manager 2 | One combined read of `/api/system` per interval | As above |
| Board PC details, Board Manager 2 | HTTP read of `/api/host`; only the system, processor and software versions are kept | At start, every hour and after a Board Manager update |
| Board Manager 1 settings and version | HTTP read | Every 30 seconds, and after every action |
| Cloud match data | Autodarts API | Every 5 seconds during a match, otherwise every minute |

Further details:

- **Reconnects.** If the realtime connection drops, the integration switches to fast polling at once. It then reconnects with a back-off of 1 to 60 seconds.
- **No stale overwrites.** A slow HTTP read never overwrites a newer realtime message.
- **Short hiccups.** A single missed read while realtime events still arrive is not treated as an outage.
- **After an action.** The integration reads the board immediately after every action, so a switch reflects the new state within about a second.

## Board Manager generations

| | Board Manager 1 (classic app) | Board Manager 2 (headless) |
| --- | --- | --- |
| Detection | Version starts with `1.` | Version starts with `2.` and `/api/system` exists |
| Reads | Separate reads for state, statistics, cameras, motion, settings and version | One combined `/api/system` read |
| Extras | Board cloud link switch | Cloud connection, CPU, memory, update notice, mDNS discovery |

The generation is detected on every read. When you update the board, the integration reloads itself and adds or removes the generation-specific entities; nothing else changes. While a board still runs Board Manager 1, a repair notice recommends the update.

## Training session

Training sessions are computed in Home Assistant from what the board detects. They follow these rules:

- **Sessions decide what counts.** Only darts thrown while a session runs count. Darts already on the board when a session starts belong to no session; darts still on the board when it ends stay with the ended session.
- **Events do not depend on sessions.** Dart, correction, takeout and visit events are announced with or without a running session.
- **Pauses end sessions.** With a pause set, a session ends that many minutes after its last dart, and its end time is the time of that dart. An end that became due while Home Assistant was stopped is applied at the next start.
- **Darts count once.** Repeated messages, camera jitter of the position and reconnects never count a dart twice.
- **Corrections revise.** If the board corrects a dart in the current visit, the totals follow the correction, for example when a 180 turns into a 140.
- **Takeouts end a visit.** Removing darts ends the visit; the removed darts keep their score. The same happens when new darts appear without an empty board in between (a missed takeout), and when the detection stops.
- **The third dart completes the visit early.** When the third announced dart of a visit lands, `visit_thrown` announces the visit at once, while the darts are still in the board. It comes once per visit, also after corrections; `visit_completed` follows when the visit ends, with the final score and `thrown: true`.
- **Startup darts are ignored.** Darts that are already on the board when Home Assistant or the connection starts are not counted.
- **Withdrawn detections.** If the board withdraws a detection outside a takeout, the dart is removed from the totals again.
- **Visit buckets.** 100+ counts visits with 100–139 points, 140+ with 140–179, and 180 with exactly three triple 20s. Merged visits with more than three darts (after a missed takeout) are not bucketed.
- **Storage.** The session, its settings, the last 20 sessions and the last 10 visits are saved in Home Assistant's `.storage` folder at most every five seconds, at once when a session starts or ends, and on shutdown. They are deleted together with the integration.

Sessions do not know players or games. A running session counts every detected dart, whether you play X01, Cricket or just practise.

## Practice game

The practice game follows the darts of the current visit, including corrections, like the training session does. When you pull the darts, the visit is booked.

- **Counting down:** the score starts at 301, 501 or 701 and every dart subtracts its score.
- **Bust:** a dart that goes below zero, leaves 1 with double out, or reaches 0 without a double busts the visit. The score returns to the start of the visit. The dart that busts counts as thrown; later darts of the visit do not.
- **Win:** a dart that reaches exactly 0, with double out on a double or the bullseye, wins the leg. `leg_won` is announced at once. The leg is booked when you pull the darts, so a correction before that still counts. The next visit starts a new leg.
- **Average:** points scored per three darts of the leg. Darts of a bust visit count, their points do not.
- **Personal routes:** with *Practice personal checkout routes*, the doubles with the best hit rate of the player at the board (at least 10 darts each) move to the front of that order; the other rules stay.
- **Checkout route:** the integration tries every combination for the darts left in the visit. It prefers fewer darts, setup darts that are not doubles, a double over the bullseye to finish, fewer trebles, then the finishing double in the order D20, D16, D8, D18, D12, D10, D4, D14, D6, D2 and the odd doubles, and finally the bigger dart first. The scores 159, 162, 163, 165, 166, 168, 169 and everything above 170 have no route with double out.
- **Statistics:** each finished leg adds one record for everybody at the board: the points and darts of the first nine darts, the darts thrown at a double and the checkout. Bust visits score nothing, also in the first nine. The statistics sensors use the last 10 records, so their history shows how you improve.
- **Matches:** with several players, the turn passes when the darts are pulled, also after a bust. The player who starts the leg changes every leg. Winning *legs per set* legs wins a set and resets everybody's legs; winning *sets to win* sets wins the match. Each player's average covers the whole match.
- **Cricket:** a dart adds its marks to its number until three close it; further marks score the number's value while another player has it open. The win is checked after every dart, so a closing dart wins at once when the points are enough, and later darts of the visit do not count. Marks per round count the marks that closed a number or scored, per three darts.
- **Party games:** Shanghai and Killer are decided by the dart that makes the Shanghai or takes the last life, and announce the win at once; the end of the last round in Shanghai and Halve-It is decided when the darts are pulled. Halve-It halves a visit without a hit on the target also when fewer than three darts were thrown.
- **Bull-off:** only the first dart of each player's visit counts. Its distance comes from the position the board reports, relative to the outer edge of the double ring (170 mm).
- **Storage:** the game, the players with their scores and marks, the match format and the last 10 legs are saved together with the training session.

## Camera health

A camera counts as failed when it delivers no frames for **15 seconds** while the detection runs. Stopped detection, calibration and camera standby are not failures. The combined *Camera problem* sensor is on when any camera has failed.

## Privacy

- **Local mode** talks only to the Board Manager in your network. Nothing is sent to the internet.
- **Search for boards** asks `discover.autodarts.com`, the public Autodarts discovery service, once when you use it. The service sees your public IP address and returns the boards registered from it.
- **The optional cloud link** uses the Autodarts device login. Home Assistant stores OAuth tokens, never your password.
- **Board secrets** are dropped as soon as they are read and are never stored, logged or shown: the board API key, TLS keys, camera device paths and similar configuration.
- **Diagnostics** redact the board ID, host, client ID and tokens.

## Security

- The Board Manager's local API does not ask for a login, so anyone who can reach port 3180 in your network can use it, with or without Home Assistant. Keep the board PC in a trusted network.
- Actions are only sent when you or an automation trigger them. They are never repeated automatically.
