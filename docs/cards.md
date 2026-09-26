# Dashboard cards

[← Documentation](README.md) · [Deutsch](de/karten.md)

The integration includes six cards. Home Assistant loads them automatically, so no dashboard resource and no separate HACS download are needed. Each card:

- has a visual editor and follows your theme (light or dark) and language (English or German);
- adapts to its width, from a phone to a wall tablet;
- finds your board by itself. With several boards, choose one in the editor.

To add one, edit a dashboard, select **Add card** and search for **Autodarts**.

## Live card

`custom:autodarts-card` shows the current visit, dart by dart, on a board drawn with the geometry of the Autodarts Board Manager.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="images/en/card-light.png">
  <img src="images/en/card.png" alt="Live card with visit score, dart slots, the board with blinking beds, statistics, connection chips and controls" width="760">
</picture>

- **Visit:** score, the three dart slots and a progress indicator. The latest dart is outlined.
- **Last visits:** the scores of your last five visits, coloured like the training card's chart. Hover one for its darts.
- **Practice game:** while a [practice game](entities.md#practice-game) runs, the remaining score, the checkout route and busts appear above the dart slots, and the board outlines the bed to aim at next. In a match, a scoreboard lists every player with the remaining score, legs, sets and average, and highlights the player at the board. In the [party games](entities.md#party-games), the panel shows the round, the target and every player's points or, in Killer, their number and lives. During a bull-off it lists the distance of every dart. In [Cricket](entities.md#cricket), a chalkboard shows the marks of every player on 20 to 15 and the bull, the points and the marks per round, dims the numbers everybody has closed and outlines the next open number on the board. In a [training game](entities.md#training-games), the panel shows the target, the progress, darts and hit rate (Bob's 27: points and round; checkout training: the route and the checkout rate), and the board outlines the beds of the target.
- **Board:**
  - Hit beds blink in the highlight colour.
  - Numbered markers show where each dart landed.
  - The board glows in the detection status colour: green when ready, yellow during a takeout, orange when stopped, purple while calibrating, red when offline or when a camera has a problem.
- **Training statistics:** darts, 3-dart average, triples, bulls and 180s of the session.
- **Connections:** Board Manager, realtime and cameras. Tap a chip for details.
- **Controls:** start or stop detection, reset detection and calibrate. Resetting and calibrating need a second tap to confirm.

Tap the board, or press Enter on it, to open the visit details.

<img src="images/en/card-visit.webp" alt="Animation: three darts land, their beds blink and the score adds up; the takeout empties the board" width="620">

<img src="images/en/practice-checkout.webp" alt="Animation: a 141 checkout in a 501 leg. After each dart the remaining score, the route and the outlined bed change: T20 T19 D12, then game shot and a new leg" width="620">

<img src="images/en/card-match.png" alt="Live card during a 501 match of Alex and Sam: Alex at the board with 81 left and the route T19 D12, Sam with 361 left" width="760">

<img src="images/en/cricket.webp" alt="Animation: Cricket between Alex and Sam. Alex closes the 20, scores 60 and hits a 19; after the takeout Sam closes the 19, scores 57 and hits a double 18" width="620">

<img src="images/en/training-game.webp" alt="Animation: Around the Clock. Each hit moves the target from 1 to 6 and outlines every bed of the next number on the board" width="620">

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `title` | text | board name | Card title |
| `layout` | `auto`, `horizontal`, `vertical`, `board` | `auto` | Board on the right, board below, or board only. `auto` switches to vertical on narrow cards |
| `board_style` | `classic`, `autodarts` | `classic` | Classic board with wires, or the flat Autodarts look |
| `highlight` | `visit`, `last`, `none` | `visit` | Highlight all darts of the visit, only the last one, or none |
| `blink` | boolean | `true` | Blink the hit beds |
| `show_markers` | boolean | `true` | Show dart positions |
| `show_numbers` | boolean | `true` | Show the numbers around the board |
| `show_stats` | boolean | `true` | Show the training statistics |
| `show_recent` | boolean | `true` | Show the last visits |
| `show_practice` | boolean | `true` | Show the practice game and the bed to aim at |
| `show_connection` | boolean | `true` | Show the connection chips |
| `show_controls` | boolean | `true` | Show the controls |
| `accent_color` | CSS colour | theme primary colour | Labels and main button |
| `highlight_color` | CSS colour | `#ffd60a` | Hit beds and the latest dart |

<table>
  <tr>
    <td><img src="images/en/card-autodarts-style.png" alt="Vertical layout with the Autodarts board style" width="360"></td>
    <td><img src="images/en/card-board-only.png" alt="Board-only layout" width="360"></td>
  </tr>
  <tr>
    <td align="center"><code>layout: vertical</code>, <code>board_style: autodarts</code></td>
    <td align="center"><code>layout: board</code></td>
  </tr>
</table>

```yaml
type: custom:autodarts-card
layout: vertical
board_style: autodarts
highlight: last
highlight_color: "#00e5ff"
```

## Training card

`custom:autodarts-training-card` turns the local [training session](entities.md#training-session) into a dashboard you'll want to look at after every session.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="images/en/training-card-light.png">
  <img src="images/en/training-card.png" alt="Training card with 3-dart average, heatmap, statistics tiles, most hit beds and recent visits" width="760">
</picture>

- **3-dart average**, the number of darts and visits, and when the session started.
- **Streak and daily goal:** the [training streak](entities.md#personal-bests-streak-and-daily-goal) in days and today's darts, with a bar towards the daily goal that turns green when you reach it.
- **Heatmap:**
  - Every bed is coloured by how often you hit it, from blue (rarely) to red (most often).
  - Hover a bed for its count and share.
  - In `numbers` mode, the heatmap sums each number's singles, doubles and triples instead.
- **Statistics:** highest visit, 100+, 140+ and 180 visits, triple rate, doubles, bulls and misses. 180s light up in gold.
- **Most hit beds:** the top five, with count and share of all darts.
- **Recent visits:** a bar chart of your last visits with the session average as a dashed line.
  - Bars are coloured grey below 60, accent colour from 60, green for 100+, orange for 140+ and gold for 180.
  - The visits come from the recorder, so the chart survives page reloads.
- **Past sessions:** end time, duration, darts, 3-dart average and best visit of your last five finished sessions.
- **Session controls:**
  - *Start session* and *End session* switch the [training session](entities.md#training-session) on and off. Ending needs a second tap to confirm.
  - *New session* ends the running session and starts the next one, also after a second tap.
  - The line next to the buttons tells whether a session is running or when the last one ended.

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `title` | text | *Training · board name* | Card title |
| `mode` | `beds`, `numbers` | `beds` | Heatmap per bed or per number |
| `board_style` | `muted`, `classic`, `autodarts` | `muted` | The muted board lets the heatmap stand out |
| `history_size` | 5–60 | `20` | Visits in the chart; labels are shown up to 30 |
| `show_heatmap` | boolean | `true` | Show the heatmap |
| `show_stats` | boolean | `true` | Show the statistics tiles |
| `show_top` | boolean | `true` | Show the most hit beds |
| `show_history` | boolean | `true` | Show the recent visits |
| `show_sessions` | boolean | `true` | Show the past sessions |
| `show_reset` | boolean | `true` | Show the session controls |
| `accent_color` | CSS colour | theme primary colour | Labels and 60+ visits |

```yaml
type: custom:autodarts-training-card
mode: numbers
history_size: 40
show_reset: false
```

<img src="images/en/training-card-mobile.png" alt="Training card on a phone" width="320">

## Board status card

`custom:autodarts-status-card` shows the health of the board and gathers the maintenance actions in one place.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="images/en/status-card-light.png">
  <img src="images/en/status-card.png" alt="Board status card with detection switch, Board Manager version and update, connections, CPU load, cameras and maintenance buttons" width="760">
</picture>

- **Detection:** a switch with the current status, tinted in the status colour.
- **Board Manager:** the installed version and, with Board Manager 2, a badge for an available update. Tap the badge for its details.
- **Connections:** Board Manager, realtime and the cloud connection of the board.
- **Board PC** (Board Manager 2): CPU and memory load, plus the detection frame rate if you enabled it.
- **Cameras:** a tile for every camera with its status and frame rate (if the frame-rate sensor is enabled) and its own calibration. A camera with a problem turns red.
- **Maintenance:** calibrate, reset detection and restart Board Manager. Each needs a second tap to confirm.

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `title` | text | board name | Card title |
| `show_connection` | boolean | `true` | Show the connections |
| `show_system` | boolean | `true` | Show the board PC load |
| `show_cameras` | boolean | `true` | Show the cameras |
| `show_controls` | boolean | `true` | Show the maintenance buttons |
| `accent_color` | CSS colour | theme primary colour | Labels and the detection switch |

```yaml
type: custom:autodarts-status-card
show_system: false
```

## Scoreboard card

`custom:autodarts-scoreboard-card` is made for a tablet or TV next to the board: large enough to read from the oche, and it always shows what is being played.

<img src="images/en/scoreboard.webp" alt="Animation: the scoreboard during a 501 match. The turn passes between Alex and Sam after every visit, and Alex checks out 141 with T20 T19 D12 to win the match" width="760">

- **X01:** a tile for every player with the remaining score, legs, sets and average. The player at the board is outlined and gets the checkout route, a bust or the game shot.
- **Cricket:** a large chalkboard with the marks of every player, the points and the marks per round; the next open number is shown below.
- **Party games:** the round and the target, every player's points, or in Killer their number and lives in red hearts.
- **Bull-off:** the distance of every player's dart from the centre.
- **Training games:** the target in large type, with the progress, darts and hit rate (Bob's 27: points and round; checkout training: the score, the route and the checkout rate).
- **Between games:** the score of the current visit together with darts, 3-dart average, highest visit and 180s of the training session, the training streak and today's darts towards the daily goal.
- **Winner:** a banner names the winner of the match until the next dart.
- **Visit:** the three darts of the current visit and its score along the bottom.
- **Caller:** with `caller: true`, the screen at the board calls the game itself, in the language of Home Assistant: the score of every visit, "you require 81" when a checkout is possible, "No score" after a bust, the game shot of a leg and the match, and a fanfare for a 180. It uses the speech output of the browser, so nothing needs to be set up in Home Assistant. Browsers play sound only after a tap: tap *Caller* on the scoreboard once to switch it on, and again to mute it.

<img src="images/en/killer.webp" alt="Animation: Killer for Alex, Sam and Kim on the scoreboard. Everybody throws for a number, Alex becomes a killer and takes Sam's lives, Kim becomes a killer too, and Alex takes the last life to win" width="760">

<img src="images/en/scoreboard-cricket.png" alt="Scoreboard in Cricket between Alex and Sam: the chalkboard with marks, points and marks per round, and T19 as the next target" width="760">

The [automatic dashboard](#automatic-dashboard) has a *Scoreboard* view that shows the card across the whole screen. Open it on the tablet, and use the browser's full-screen mode or the Home Assistant app in kiosk mode.

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `full_height` | boolean | `false` | Fill the height of the screen, for a view in panel mode |
| `show_visit` | boolean | `true` | Show the darts of the current visit |
| `show_status` | boolean | `true` | Show the board status |
| `caller` | boolean | `false` | Switch the caller on: the screen announces visits, what a player requires, busts and game shots |
| `call_scores` | boolean | `true` | Call the score of every visit |
| `call_checkouts` | boolean | `true` | Call what the next player requires when a checkout is possible |
| `call_results` | boolean | `true` | Call busts and game shots |
| `call_sounds` | boolean | `true` | Play a fanfare for a 180 |
| `accent_color` | CSS colour | theme primary colour | The player at the board, routes and the visit score |

```yaml
type: custom:autodarts-scoreboard-card
full_height: true
```

## Doubles card

`custom:autodarts-doubles-card` shows the [doubles analysis](entities.md#doubles-analysis): the double ring of the board coloured from red (rarely hit) to green (about every second dart), and every double thrown at, the best first, with hits, darts and hit rate. The favourite double is filled. With `player`, it shows the doubles of one named player instead of everybody's.

<img src="images/en/doubles-card.png" alt="Doubles card: the double ring coloured by hit rate from red to green, and a list of the doubles with hits, darts and hit rate, the best first" width="760">

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `title` | text | *Doubles* | Card title |
| `player` | text | everybody | A player name, for that player's doubles |
| `accent_color` | CSS colour | theme primary colour | Labels |

## Players card

`custom:autodarts-players-card` shows the [player profiles](entities.md#player-profiles): a tile for every named player with legs and matches won, 3-dart average, first 9, checkout rate, marks per round, highest visit and checkout and the fewest darts per start score. Below, the head-to-head records with a balance bar and the recent matches with their winner.

<img src="images/en/players-card.png" alt="Players card with the profiles of Alex, Sam and Kim, their averages and personal bests, the head-to-head record of Alex and Sam, and the recent matches" width="760">

### Options

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `device_id` | device | first board | The board to show |
| `title` | text | *Players* | Card title |
| `show_head_to_head` | boolean | `true` | Show the head-to-head records |
| `show_matches` | boolean | `true` | Show the recent matches |
| `accent_color` | CSS colour | theme primary colour | Labels and the balance bars |

## Automatic dashboard

Instead of arranging the cards yourself, let the integration build a whole dashboard:

1. Go to **Settings → Dashboards → Add dashboard**.
2. Choose **Autodarts**.

For every board, the dashboard gets up to five views, which update themselves when you add a board or enable entities:

| View | Contents |
| --- | --- |
| **Live** | The live card across the full width, the practice game controls and the player names |
| **Scoreboard** | The [scoreboard card](#scoreboard-card) across the whole screen, for a tablet or TV at the board |
| **Training** | The training card, the [doubles card](#doubles-card), the daily goal with darts today, the streak and the last personal best, darts per day for the last 30 days (from long-term statistics, which Home Assistant compiles hourly), the 3-dart average of the last 7 days, practice legs per day, and the first 9 average and checkout rate of the practice game |
| **Players** | The [players card](#players-card), once the first named player has a profile |
| **Board** | The board status card, the board settings and the Board Manager update |

<img src="images/en/dashboard-strategy.png" alt="The training view of the automatic dashboard" width="760">

In YAML, the whole dashboard is one line; `device_id` and `title` are optional:

```yaml
strategy:
  type: custom:autodarts
  device_id: 0123456789abcdef   # only this board
  title: Darts
```

To customise it, open the dashboard's menu (⋮) → **Edit dashboard** → **Take control**. Home Assistant then turns the generated views into a normal dashboard that you can edit.

## Card editor

All options can be set in the visual editor, which offers only Autodarts boards in its device picker.

<img src="images/en/card-editor.png" alt="The visual editor of the live card" width="760">

## Tips

- **Wall tablet:** the live card with `layout: vertical` fills a portrait screen. The board scales with the card. For a landscape screen at the board, use the [scoreboard](#scoreboard-card).
- **Combine:** put the live card and the training card next to each other in a sections view with two columns.
- **Several boards:** add one card per board and choose the board in each card's editor.
- **Cached old version:** after an update, the card URL changes automatically. If a browser still shows an old card, reload the page. In the companion app, use *Settings → Companion app → Debugging → Reset frontend cache*.
