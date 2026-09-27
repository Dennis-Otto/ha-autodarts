# Entities and events

[← Documentation](README.md) · [Deutsch](de/entitaeten.md)

Every board is one device with the entities below. Its name is the one the board has in Autodarts when the board search or the cloud found it, otherwise *Autodarts Board*. The entity names follow your Home Assistant language and do not repeat the device name. Entity IDs are derived from both when an entity is created, for example `sensor.autodarts_board_training_3_dart_average`, and stay as they are when a later version renames an entity.

**Legend:**

| Column or mark | Meaning |
| --- | --- |
| **BM** | The Board Manager generation that provides the entity: 1, 2 or both |
| *Disabled* | Created disabled; enable it in the entity settings if you need it |
| *Diagnostic*, *Configuration* | The entity category; these entities are grouped separately on the device page |

<img src="images/en/device.png" alt="Device page of an Autodarts board in Home Assistant" width="760">

## Live visit

| Entity | Type | Description |
| --- | --- | --- |
| Detection status | Sensor (enum) | `offline`, `starting`, `stopping`, `stopped`, `throw` (ready), `takeout`, `takeout_in_progress`, `calibrating`, `error`. Unknown statuses of future Board Manager versions read as *unknown*. |
| Last dart | Sensor | Segment of the last dart, for example `T20`, `D16`, `S5`, `25`, `Bull`. |
| Last dart score | Sensor, points | Score of the last dart. |
| Darts in visit | Sensor, darts | Darts currently detected on the board (0–3). |
| Detected visit score | Sensor, points | Sum of the detected darts. The `throws` attribute lists each dart with `segment`, `number`, `multiplier`, `score`, `bed` and the normalised position `x`/`y`. The `recent_visits` attribute lists the last ten completed visits, newest first, with `time`, `score`, `darts` and `segments`. The recorder stores neither attribute. |
| Last event | Sensor | The Board Manager's latest event text, such as `Throw detected` or `Takeout started`. |

The visit score is the plain sum of the darts, without game rules such as busts.

## Board events

The **Events** entity (for example `event.autodarts_board_events`, or `event.autodarts_board_board_events` for a board set up with an earlier version) fires native Home Assistant events. Its `event_type` attribute tells what happened, and further attributes carry the details. Every event also has `source`: `websocket` for realtime events, `poll` when it was noticed during a reconciliation read, `training` for session events, or `online` for the moments of [online matches](automations.md#online-matches-experimental), which the optional online bridge receives from the browser extension Tools for Autodarts. The entity stays available while the board is away, so events of Home Assistant itself, such as `session_ended` or `personal_best`, always arrive.

| `event_type` | When | Attributes |
| --- | --- | --- |
| `dart_detected` | A new dart lands | `dart_index` (1–3), `segment` (for example `T20`, `S5`, `Bull`, `25` or `M` for a miss), `score`, `game` |
| `dart_corrected` | The board corrects a detected dart | `dart_index`, `segment`, `score`, `game` |
| `takeout_started` | You start pulling the darts | none |
| `takeout_finished` | The board is clear again | none |
| `visit_thrown` | The third dart of a visit lands, while the darts are still in the board; once per visit | `score`, `darts` (3), `segments` (for example `["T20", "T20", "S20"]`), `game` |
| `visit_completed` | A visit ends: on takeout, when new darts follow a missed takeout, or when detection stops | `score`, `darts`, `segments`, `game`, `thrown` (`true` when `visit_thrown` already announced the visit) |
| `status_changed` | The detection status changes | `status` |
| `session_started` | A training session starts: with the *Training session* switch, the *New training session* button, or the first dart when *Start sessions automatically* is on | `started` and `reason` (`manual`, `new_session` or `first_dart`) |
| `session_ended` | A training session ends: with the switch, the button, or after the pause set in *Session idle timeout* | `reason` (`manual`, `new_session` or `idle`), `started`, `ended`, `duration_minutes`, `darts`, `points`, `average`, `visits`, `highest_visit` and the other training totals |
| `bust` | A dart of the [practice game](#practice-game) goes below zero, leaves 1 with double out, or reaches 0 without a double | `game`, `player`, `name`, `players`, `remaining` (the score at the start of the visit, which stays) |
| `leg_won` | A dart finishes the practice leg | `game`, `player`, `name`, `players`, `darts` and `average` of the leg, `checkout` (the score checked out), `double_out` and `double_in` (the rules of the leg), `legs` of the winner in the set including this leg and `sets` afterwards, `match` (`true` when the leg decides the match); in [Cricket](#cricket) `points` and `mpr` instead of `average`, `checkout` and the rules |
| `match_won` | A dart decides a practice match of several players | `game`, `player`, `name`, `players`, `legs` (of the winner in the deciding set) and `sets`, `scores` with `player`, `name`, `legs` and `sets` of everybody, for example 3 : 2, and the `average` of the match; `mpr` in Cricket |
| `turn_changed` | In a practice game, the darts were pulled and the next visit is up: the next player in a match, the same player when playing alone | `game`, `player`, `name`, `players`, `remaining`, `checkout` (the route for three darts, or none); in Cricket `points`, in [party games](#party-games) `points` and `target` of the next player; during a bull-off `bull_off` |
| `drill_finished` | A [training game](#training-games) ends: Around the Clock or doubles training reach the end, or Bob's 27 ends | `drill`, `darts`, `hits`, `hit_rate` (percent); Bob's 27 adds `score` and `completed` |
| `checkout_attempt` | An attempt of the checkout training ends | `drill`, `target`, `success`, `darts`, `attempts`, `successes`, `rate` (percent) |
| `bull_off_won` | The [bull-off](#practice-game) decides who starts the match | `game`, `player`, `name`, `players`, `hit` (the bed of the winning dart: `BULL`, `25` or for example `S20`), `distance` (millimetres from the centre, or none without a position from the board) |
| `personal_best` | A value beats your [personal best](#personal-bests-streak-and-daily-goal) | `record`, `value`, `previous`, `name` (the player, if known) |
| `daily_goal_reached` | Today's darts reach the [daily goal](#personal-bests-streak-and-daily-goal), once per day | `goal`, `darts`, `streak` |
| `online_game_on` | [Online match](automations.md#online-matches-experimental): a turn starts, or a moment without an effect of its own | `trigger`, `name` |
| `online_visit` | Online match: a visit | `trigger`, `score`; for three darts also `darts` and `segments`; for a range `score_min` and `score_max` instead of `score` |
| `online_dart` | Online match: a dart | `trigger`, `segment` (`T20`, `D16`, `S5`, `25`, `BULL` or `MISS`), `score` |
| `online_busted` | Online match: a bust | `trigger`, `name` |
| `online_game_shot` | Online match: a won leg | `trigger`, `segment` of the winning dart and `name`, if the trigger names them |
| `online_match_shot` | Online match: a won match | `trigger`, `segment`, `name` as with `online_game_shot` |
| `online_bull_off` | Online match: the bull-off begins | `trigger` |
| `online_tournament_ready` | A tournament match of yours is ready | `trigger` |
| `online_match_left` | You left the online match | `trigger` |

`game` is the [practice game](#practice-game) being played while the dart lands, such as `501`, `cricket` or `shanghai`, and empty without one and in [training games](#training-games). A visit of three darts is announced twice: with `visit_thrown` the moment its third dart lands, for 180 celebrations and callers, and with `visit_completed` when it ends, with the final score after corrections. To react to every visit exactly once and as early as possible, use `visit_thrown` and `visit_completed` whose `thrown` is `false`; the [blueprints](automations.md#blueprints) do that.

Events are never replayed after a restart or reconnection. See [automations](automations.md) for examples.

## Training session

The integration counts your darts in training sessions, in Home Assistant and independent of Autodarts games. Sessions survive restarts.

- **Start and end:** the *Training session* switch starts a session from zero and ends it. *New training session* ends the running session and starts the next one.
- **Automatically:** with *Start sessions automatically* on, the first dart starts a session when none runs. *Session idle timeout* ends a session that many minutes after its last dart; `0` keeps it running.
- **Without a session,** darts and visits are still announced as [board events](#board-events), for example for a 180 celebration during an online game, but they are not counted.
- **History:** a finished session keeps its totals until the next one starts. *Last session average* keeps the 3-dart average of every finished session with darts, so its history shows your progress.

The defaults, automatic start on and no pause limit, count every dart as version 1.0 did.

| Entity | Type | Description |
| --- | --- | --- |
| Training darts | Sensor, total | Darts in the session. The `hits` attribute counts the hits per bed, for example `{"T20": 12, "S20": 30, "BULL": 2, "MISS": 3}`; the heatmap uses it. The recorder does not store `hits`. |
| Training points | Sensor, total | Sum of all dart scores. |
| Training 3-dart average | Sensor | Points per three darts, the usual darts average. *Unknown* before the first dart. |
| Training visits | Sensor, total | Visits with at least one counted dart. |
| Training highest visit | Sensor | Highest visit score of the session. |
| Training 100+ visits | Sensor, total | Visits with 100–139 points. |
| Training 140+ visits | Sensor, total | Visits with 140–179 points. |
| Training 180s | Sensor, total | Visits with three triple 20s. |
| Training triples | Sensor, total | Darts in a triple bed. |
| Training doubles | Sensor, total | Darts in a double bed (bull excluded). |
| Training bull hits | Sensor, total | Darts in the bull or outer bull. |
| Training misses | Sensor, total | Darts outside the scoring area. |
| Training session start | Sensor, timestamp | When the session started. |
| Training session | Switch | On while a session runs. Turning it on starts a session from zero; turning it off ends it. |
| New training session | Button | Ends the running session and starts the next one. The board itself is not touched. |
| Start sessions automatically | Switch, *Configuration* | The first dart starts a session when none runs. On by default. |
| Session idle timeout | Number, *Configuration* | Minutes without darts, 0–240, after which a session ends by itself. `0`, the default, keeps it running. |
| Last session average | Sensor, points | 3-dart average of the last finished session. Attributes: `started`, `ended`, `duration_minutes`, the totals, and `sessions` with the last 20 sessions, which the recorder does not store. |

Totals use the state class *total increasing*, so Home Assistant's statistics and energy-style graphs handle resets correctly. [How the counting works](how-it-works.md#training-session).

## Personal bests, streak and daily goal

Home Assistant keeps your best values, the days you trained and your darts per day. Every detected dart counts for the day, in a session or not. The first value of each record sets it quietly; beating it fires `personal_best`, and equal values do not count.

| Record | Best value | From |
| --- | --- | --- |
| `highest_visit` | highest | a visit of up to three darts |
| `highest_checkout` | highest | a won X01 leg with double out |
| `fewest_darts_101` to `fewest_darts_1001` | fewest | a won X01 leg with double out from 101, 301, 501, 701, 901 or 1001 |
| `best_cricket_mpr` | highest | the marks per round of a won Cricket leg |
| `around_the_clock`, `doubles` | fewest | darts of a finished training game |
| `bobs_27` | highest | the score of a completed Bob's 27 |
| `best_session_average` | highest | a finished training session of at least 30 darts |

| Entity | Type | Description |
| --- | --- | --- |
| Last personal best | Sensor, timestamp | When the last personal best fell; *unknown* before the first. Attributes: `record`, `value`, `previous` and `name` of that best, and the best value of every record under its key, for example `highest_checkout`. |
| Darts today | Sensor, darts, total | Darts detected today; starts from 0 at midnight. Attributes: `goal`, `goal_reached`, `progress` (percent of the goal). |
| Training streak | Sensor, duration in days | Days in a row with at least one dart. It stays until a whole day passes without darts. Attributes: `best_streak`, `trained_today`, `last_day`. |
| Daily goal | Number, darts, *Configuration* | Darts to throw every day, 0–2000; `0`, the default, sets no goal. When today's darts reach it, `daily_goal_reached` fires once. |

## Practice game

Play X01, [Cricket](#cricket) or a [party game](#party-games) on the local board without an Autodarts game. Home Assistant counts down, recognises busts and shows the checkout route. The game needs no cloud and survives restarts.

<img src="images/en/practice-checkout.webp" alt="Animation: a 141 checkout in a 501 leg. After each dart the remaining score, the route and the outlined bed change: T20 T19 D12, then game shot and a new leg" width="620">

- **Start:** choose 101, 301, 501, 701, 901 or 1001 in *Practice game*. Darts already on the board do not count. *New practice leg* starts the leg again from the full score.
- **Double in:** with *Practice double in*, a player's score starts with the first double or bullseye of the leg; darts before it score nothing, and a bust takes the opening back. The card asks for a double and outlines the double ring.
- **Bull-off:** with *Practice bull-off* and two or more players, a match starts with one dart per player at the bull. As in the official rules, the bullseye beats the outer bull, which beats every other bed; two darts in the same bull bed throw again, in reverse order. Outside the bull, and inside it with *Practice bull-off by distance*, the dart closest to the centre wins, measured from the dart positions the board reports; a dart without a position never beats a measured one. [The bull-off rules](how-it-works.md#bull-off).
- **Visits:** a visit ends when you pull the darts. After a bust, the score of the visit start stays. Darts after a bust or after the winning dart do not count.
- **Checkout:** the route for the darts left in the visit, for example `T20 T20 BULL` for 170. [How the route is chosen](how-it-works.md#practice-game).
- **Matches:** set *Practice players* to 2, 3 or 4. After a visit, the next player throws; a bust passes the turn too. The first player to win *Practice legs per set* legs wins the set, and the first to win *Practice sets to win* sets wins the match. The first throw passes every leg within a set, and every set starts with the next player. The result, with the legs of the deciding set, stays on the card until the next dart, which starts a new match. With one player, legs and sets are not counted. [The match rules](how-it-works.md#matches-legs-and-sets).
- **Sessions:** the practice game and [training sessions](#training-session) are independent. A dart counts in both.
- **More games:** *Practice game* also offers three [party games](#party-games) and four [training games](#training-games).

| Entity | Type | Description |
| --- | --- | --- |
| Practice game | Select | `off`, `101`, `301`, `501`, `701`, `901`, `1001`, `cricket`, a party game (`shanghai`, `halve_it`, `killer`) or a training game: `around_the_clock`, `doubles`, `checkout`, `bobs_27`. Choosing starts a new match or game. |
| Practice remaining score | Sensor | Remaining score of the player at the board; *unknown* without a game. Attributes: `game`, `double_out`, `player` and `name` of the player at the board, `checkout`, `bust`, `won`, `visit` (the segments of the current visit), `darts` and `average` of the leg, `players`, `legs_to_win`, `sets_to_win`, `winner` (the player who won the match, until the next dart), `scores` with `player`, `name`, `remaining`, `legs` (in the current set, or the deciding set of a finished match), `sets`, `match_legs` (legs of the whole match) and the match `average` of every player, `bull_off` during a bull-off (the `player` at the board, `rethrow`, `by_distance` and `throws` with `player`, `name`, `hit` and `distance`), and `legs` with the last 10 legs (`game`, `player`, `name`, `darts`, `average`, `checkout`, `ended`). The recorder stores neither `visit`, `scores` nor `legs`. |
| Practice checkout | Sensor | The checkout route, for example `T20 25 D18`; *unknown* when no route exists. |
| Practice target | Sensor | The target of the [training game](#training-games), for example `7`, `D16`, `BULL` or the checkout score `81`, or the next open number in [Cricket](#cricket), for example `T19`; *unknown* without a target. Attributes: `drill`, `finished`, `visit`, `progress` and `targets`, `darts`, `hits`, `hit_rate`, the best result as `best`, and `results` with the last 10 results, which the recorder does not store. Bob's 27 adds `score`; the checkout training adds `remaining`, `checkout`, `bust`, `won`, `attempt_visit`, `attempt_visits`, `attempts`, `successes` and `rate`. |
| New practice leg | Button | Starts the leg again from the full score; legs and sets stay. |
| New practice match | Button | Starts the match again from zero legs and sets. |
| Practice first 9 average | Sensor, points | 3-dart average of the first nine darts of each leg, over the last 10 legs of everybody at the board. |
| Practice checkout rate | Sensor, % | Legs won per dart thrown at a double, over the last 10 legs. A dart counts at a double when one double could finish the score: 2 to 40 when even, or 50. Only with double out. |
| Practice doubles rate | Sensor, % | The same darts at a double together with the last 10 results of the doubles training and Bob's 27. |
| Practice legs played | Sensor, total | Legs finished in X01, Cricket and the party games; its long-term statistics show the legs per day. |
| Practice players | Number, *Configuration* | 1–4 players. A change starts a new match. |
| Practice legs per set | Number, *Configuration* | 1–11 legs win a set. A change starts a new match. |
| Practice sets to win | Number, *Configuration* | 1–7 sets win the match. A change starts a new match. |
| Practice player *N* | Text, *Configuration* | Name of player 1–4, at most 20 characters, for the scoreboard and the events. Without a name, the card shows *Player N*. |
| Practice double out | Switch, *Configuration* | Finish on a double or the bullseye. On by default. |
| Practice double in | Switch, *Configuration* | Start scoring with a double or the bullseye. Off by default; a change starts a new match. |
| Practice bull-off | Switch, *Configuration* | A bull-off decides who starts a match of several players. Off by default; a change starts a new match. |
| Practice bull-off by distance | Switch, *Configuration* | Two darts in the same bull bed are decided by the distance the board measured instead of a rethrow. Off by default, as the official rules want; applies at once. |

## Cricket

Choose `cricket` in *Practice game*, alone or as a match of up to four players with legs and sets, like X01.

<img src="images/en/cricket.webp" alt="Animation: Cricket between Alex and Sam. Alex closes the 20, scores 60 and hits a 19; after the takeout Sam closes the 19, scores 57 and hits a double 18" width="620">

- **Marks:** only 20 to 15 and the bull count. A single is one mark, a double two, a treble three; the outer bull is one mark, the bullseye two. Three marks close a number.
- **Points:** marks on a closed number score its value (25 for the bull) as long as another player still has it open.
- **Win:** close every number with at least as many points as everybody else. Alone, closing every number wins the leg.
- **Target:** *Practice target* shows the next open number from 20 down to the bull, for example `T19` or `BULL`, and the card outlines it on the board.
- **Marks per round (MPR):** marks that counted per three darts, the usual Cricket statistic. Marks on a number nobody needs any more do not count.

The card shows a chalkboard with the marks of every player (`/`, `X`, `Ⓧ`), the points and the MPR. *Practice remaining score* stays *unknown* in Cricket; its attributes carry the game: `game` is `cricket`, plus `points`, `mpr`, `target`, `numbers` (20 to 15 and 25) and `scores` with `marks`, `points`, `legs`, `sets` and `mpr` of every player. Cricket legs do not count for the X01 statistics.

## Player profiles

Every named player of a practice game gets a profile with lifetime numbers. Names are the same player regardless of upper and lower case; players without a name count for nobody. Every leg of X01, Cricket and the party games counts; X01 legs add the averages and the checkout rate, Cricket legs the marks per round.

| Entity | Type | Description |
| --- | --- | --- |
| Player profiles | Sensor, players | The number of profiles. Attribute `players` with, for every player: `name`, `legs_played`, `legs_won`, `matches_played`, `matches_won`, `average`, `first_9_average`, `checkout_rate`, `mpr`, `highest_visit`, `highest_checkout`, `best_mpr`, `fewest_darts` (start score → fewest darts for a won leg) and `last_played`. `highest_visit` is the highest X01 score of the player; `highest_checkout` and `fewest_darts` come from legs with double out only. The recorder does not store the list. |
| Last match | Sensor, timestamp | When the last match of several players ended. Attributes: `game` and `winner` of that match, `matches` with the last 20 matches (`ended`, `game`, `legs_to_win`, `sets_to_win`, `winner` and every player's `name`, `legs` and `sets` at the end, `match_legs` and `average`, `mpr` or `points`), and `head_to_head` with the wins of every pair of named players. The recorder stores neither list. |

The [players card](cards.md#players-card) shows all of it. To remove a profile, for example after a typo in a name, use [`autodarts.delete_player`](#delete-a-player-profile-autodartsdelete_player).

## Doubles analysis

Home Assistant counts every dart thrown at a double and whether it hit: in X01 when one double could finish the remaining score (2 to 40 when even, or 50 for the bullseye), in the doubles training at the current double, and in Bob's 27 at the double of the round. It keeps the numbers for everybody and, in the [player profiles](#player-profiles), for every named player.

| Entity | Type | Description |
| --- | --- | --- |
| Favorite double | Sensor | The double with the best hit rate among those with at least 10 darts, for example `D16`; *unknown* before. Attributes: `attempts`, `hits`, `rate` (percent) and `doubles` with `double`, `attempts`, `hits` and `rate` of every double thrown at. The recorder does not store the list. |
| Practice personal checkout routes | Switch, *Configuration* | Checkout routes prefer the strongest doubles of the player at the board (their profile, otherwise everybody's darts): a route with the same number of darts to a double with a better hit rate wins, without a double to set up; only doubles with at least 10 darts count. Off by default. |

The [doubles card](cards.md#doubles-card) draws the hit rate of every double on the board.

## Party games

<img src="images/en/killer.webp" alt="Animation: Killer for Alex, Sam and Kim on the scoreboard. Everybody throws for a number, Alex becomes a killer and takes Sam's lives, Kim becomes a killer too, and Alex takes the last life to win" width="760">

Three pub classics for one to four players, chosen in *Practice game*. They follow the darts like X01, book a visit when you pull the darts, and win legs and sets like any match. The live card and the [scoreboard](cards.md#scoreboard-card) show the round, the target, every player's points or lives, and outline the beds to aim at.

| Game | Rules |
| --- | --- |
| **Shanghai** (`shanghai`) | Seven rounds at the numbers 1 to 7. Every dart in a bed of the round's number scores its value; a miss next to it does not. A single, double and treble of that number in one visit (a *Shanghai*) wins the leg at once; otherwise the most points after seven rounds win. |
| **Halve-It** (`halve_it`) | Everybody starts with 40 points. The rounds aim at 15, 16, any double (the bullseye included), 17, 18, any treble, 19, 20 and the bull (`25`: the outer bull scores 25, the bullseye 50); hits add their score. A visit without a hit on the target halves the points, rounded down. The most points after nine rounds win. |
| **Killer** (`killer`) | Two to four players. Each first throws one dart for a number of their own (any bed of a number nobody has yet; after a miss, the bull or a taken number, throw again). Then only doubles count: hitting the double of your own number makes you a killer for the rest of the leg. Killers take a life with every hit on another player's double, and lose one when they hit their own. Everybody has 3 lives; a player without lives is out, and the rest of their visit does nothing. The last one with a life left wins. |

In Shanghai and Halve-It, a tie in points goes to the player with more hits; if that is equal too, the leg is played again. Shanghai and Killer are won by a single dart; later darts of the visit do not count. [All rules](how-it-works.md#rules). *Practice remaining score* stays *unknown*; its attributes carry `game`, `round`, `rounds`, `target` (`D` and `T` mean any double and any treble), `phase` (`choose` or `play` in Killer), `points` and `scores` with `points`, `legs`, `sets` and, in Killer, `number`, `lives` and `killer` of every player. *Practice target* shows the target, in Killer the own double until you are a killer. Party games do not count for the X01 statistics.

## Training games

Four classic drills, chosen in *Practice game*. Each follows the darts of the current visit and books the visit when you pull the darts. Darts already on the board when a game starts do not count. A finished game stays on the card until the next dart starts it again; *New practice leg* starts it again at once. Every game keeps its last 10 results.

<img src="images/en/training-game.webp" alt="Animation: Around the Clock. Each hit moves the target from 1 to 6 and outlines every bed of the next number on the board" width="620">

| Game | Goal |
| --- | --- |
| **Around the Clock** (`around_the_clock`) | Hit 1, 2, … 20 and then the bull, in order, with any bed of the number. The bull target is `25`: the outer bull and the bullseye both count. Fewer darts are better. |
| **Doubles training** (`doubles`) | The same with the doubles only: D1 to D20, then the bullseye (`BULL`). |
| **Checkout training** (`checkout`) | A random score from 2 to 170 that three darts can finish, checked out on a double within three visits. A bust ends the attempt; the route shows only while the attempt goes on. The checkout rate counts successful attempts. |
| **Bob's 27** (`bobs_27`) | Start with 27 points and throw one visit at each double from D1 to D20 and then at the bullseye. Every hit adds the value of the double; a visit without a hit subtracts it. The game is lost as soon as the score reaches zero or less, and completed after the bullseye. |

Training games are for one player; *Practice players* applies to X01, Cricket and the party games.

## Controls

| Entity | Type | Description |
| --- | --- | --- |
| Detection | Switch | Starts or stops the dart detection. |
| Start detection, Stop detection | Buttons | The same actions as buttons, for scripts and dashboards. |
| Reset detection | Button | Discards the darts detected on the board. |
| Start automatic calibration | Button, *Configuration* | Calibrates all cameras. |
| Calibrate camera *N* | Button, *Configuration* | Calibrates one camera. |
| Restart Board Manager | Button, *Configuration* | Restarts the Board Manager service. |
| Start camera streams, Stop camera streams | Buttons, *Configuration*, *Disabled* | Controls the camera streams of the Board Manager. |
| Cloud link | Switch, **BM 1** | Connects or disconnects the board's own connection to Autodarts. |
| Connect cloud link, Disconnect cloud link | Buttons, **BM 1**, *Disabled* | The same as buttons. |

Every action is sent **once**. If the board rejects it or does not answer, Home Assistant shows an error message instead of retrying, so an action is never executed twice.

## Board settings

| Entity | Type | Description |
| --- | --- | --- |
| Calibrate on start | Switch, *Configuration* | Calibrates when the detection starts. |
| Automatic recalibration | Switch, *Configuration* | Lets the Board Manager recalibrate by itself. |
| Automatic distortion correction | Switch, *Configuration* | Corrects lens distortion during calibration. |
| Camera standby | Select, *Configuration* | Puts the cameras on standby after 5, 10, 15, 30 or 60 idle minutes. |

A change is written to the Board Manager configuration; only the changed setting is sent.

## Health and connections

| Entity | Type | Description |
| --- | --- | --- |
| Local connection | Binary sensor, *Diagnostic* | Home Assistant reaches the Board Manager. One or two missed reads, a few seconds, keep it on. |
| Realtime connection | Binary sensor, *Diagnostic* | The connection for realtime events is open. Until events arrive over it, the integration reads every 2 seconds. |
| Autodarts cloud connection | Binary sensor, **BM 2**, *Diagnostic* | The board's connection to Autodarts. |
| Cameras active | Binary sensor | The cameras are running. |
| Calibration in progress | Binary sensor | A calibration is running. |
| Camera problem | Binary sensor, *Diagnostic* | On when any camera delivers no frames for 15 seconds during active detection. Normal stops, calibration and standby are ignored. |
| Camera *N* problem | Binary sensor, *Diagnostic* | The same for one camera. |
| Detection frame rate | Sensor, fps, *Diagnostic*, *Disabled* | Frames per second of the detection. |
| Detection correction rate | Sensor, %, *Diagnostic* | Share of the last 100 detected darts that the board corrected afterwards. From 20 % over at least 50 darts, a [repair](troubleshooting.md#repairs) suggests to recalibrate. Attributes: `darts`, `corrected`. |
| Camera *N* frame rate | Sensor, fps, *Diagnostic*, *Disabled* | Frames per second of one camera. |
| CPU usage | Sensor, %, **BM 2**, *Diagnostic* | CPU load of the board PC. |
| Memory usage | Sensor, **BM 2**, *Diagnostic*, *Disabled* | Memory use as reported by Board Manager 2. |
| Operating system | Sensor, **BM 2**, *Diagnostic* | Distribution and version of the board PC, for example *Debian 13*. Attributes: `kernel`, `architecture`. |
| Processor | Sensor, **BM 2**, *Diagnostic* | Processor model of the board PC. Attribute: `cores`. |
| Detection software version | Sensor, **BM 2**, *Diagnostic* | Version of the Autodarts detection software. Attribute: `opencv_version`. |
| Software | Update, **BM 2** | Installed and latest Board Manager version. Install updates on the board PC. |
| Online bridge last event | Sensor, timestamp, *Diagnostic* | When the last moment of an [online match](automations.md#online-matches-experimental) arrived; *unknown* before the first. Only while the online bridge is on. Attributes: `trigger`, `event_type`. |

Per-camera entities carry a `camera` attribute with the camera number, which the [status card](cards.md#board-status-card) uses.

## Motion

| Entity | Type | Description |
| --- | --- | --- |
| Hand detected | Binary sensor, *Diagnostic* | A hand is in front of the board. |
| Image stable | Binary sensor, *Diagnostic*, *Disabled* | The camera image is steady. |
| Darts partially removed | Binary sensor, *Diagnostic* | Some darts are removed. |
| Darts fully removed | Binary sensor, *Diagnostic*, *Disabled* | All darts are removed. |

These sensors are *off* while the detection is stopped, starting, stopping or calibrating. They change with nearly every dart and takeout, and each change is recorded. The live card shows a hand at the board and a takeout from the first and third, so these two are enabled; the other two start disabled. Boards set up with an earlier version keep all four enabled; disable those you do not need in the entity settings.

## Cameras

| Entity | Type | Description |
| --- | --- | --- |
| Camera *N* | Camera, *Disabled* | One board camera, for example in a picture card or the camera dialog. With **BM 2**, the live view relays the board's camera stream through Home Assistant; when the stream is not running, and with BM 1, it shows snapshots. To show a camera, the integration never starts or stops the detection or the streams. |

## Cloud match data (optional)

These entities exist only with a [linked Autodarts account](installation.md#link-the-autodarts-cloud-optional) and are read every 5 seconds during a match, otherwise once a minute.

| Entity | Type | Description |
| --- | --- | --- |
| Cloud status | Sensor (enum), *Diagnostic* | `connected` or `disconnected` in the Autodarts cloud. |
| Game mode | Sensor | Variant of the current match, such as `X01` or `Cricket`. |
| Match state | Sensor (enum) | `no_match`, `active` or `finished`. |
| Round | Sensor | Current round. |
| Visit score | Sensor, points | Score of the current visit in the match. |
| Darts thrown | Sensor, darts | Darts thrown in the match. |

Without a local board, *Last event*, *Last dart* and *Darts in visit* come from the cloud as well.

## Actions

### Start a practice game: `autodarts.start_game`

Sets up and starts a game in one call, for automations, scripts, dashboard buttons and voice control. Values you leave out stay as they are.

| Field | Values | Description |
| --- | --- | --- |
| `game` | `101`, `301`, `501`, `701`, `901`, `1001`, `cricket`, `shanghai`, `halve_it`, `killer`, `around_the_clock`, `doubles`, `checkout`, `bobs_27` | The game; required |
| `players` | 1–4 names | Players in throwing order; the number of names sets the number of players |
| `legs` | 1–11 | Legs that win a set |
| `sets` | 1–7 | Sets that win the match |
| `double_out` | `true`, `false` | Finish X01 legs on a double or the bullseye |
| `double_in` | `true`, `false` | Start X01 legs with a double or the bullseye |
| `bull_off` | `true`, `false` | A bull-off decides who starts a match of several players |
| `bull_off_distance` | `true`, `false` | Two darts in the same bull bed are decided by the measured distance instead of a rethrow |
| `config_entry_id` | Autodarts entry | Only needed with more than one board |

```yaml
action: autodarts.start_game
data:
  game: "501"
  players: [Dennis, Lea]
  legs: 3
```

The action fails with a clear message when no board is loaded, when several boards are set up and none is chosen, when the chosen entry is unknown, belongs to another integration or is not loaded, when a name appears twice among the players, or when Killer would have fewer than two players. Values beyond the limits above are rejected before anything changes.

### Delete a player profile: `autodarts.delete_player`

Forgets a player's statistics, personal bests and head-to-head records. The name also disappears from the board's [personal bests](#personal-bests-streak-and-daily-goal), whose values stay, and from the practice player names, so the next leg does not create the profile again. The match history keeps the name.

| Field | Values | Description |
| --- | --- | --- |
| `name` | text | The player name, in any upper and lower case; required |
| `config_entry_id` | Autodarts entry | Only needed with more than one board |

The action fails with a clear message when there is no profile by that name.

## Availability

- Local entities become *unavailable* when the Board Manager does not answer and recover on their own.
- Training entities stay available, because the session is stored in Home Assistant.
- If the configured address answers as a **different board**, the entities stay unavailable and Home Assistant shows a repair notice.
- When the board is updated from Board Manager 1 to 2, the integration reloads by itself and adds or removes the generation-specific entities.
