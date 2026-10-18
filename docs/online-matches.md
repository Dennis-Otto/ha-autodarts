---
description: "Play online on play.autodarts.io and let Home Assistant celebrate: busts, won legs and the darts of your opponents arrive as board events. Experimental."
---

# Online matches (experimental)

[← Documentation](README.md) · [Deutsch](online-matches.de.md)

Play online on play.autodarts.io and let Home Assistant celebrate with you: busts, won legs and matches, and the darts of your opponents arrive as board events, for the light show, a caller or a notification when your tournament match is ready.

**On this page:** [How it works](#how-it-works) · [Set up the bridge](#set-up-the-bridge) · [Triggers and events](#triggers-and-events) · [The cloud link](#the-cloud-link) · [Security](#security) · [Limitations](#limitations)

## How it works

The integration sees the darts on your board in an online match on play.autodarts.io, too: `dart_detected`, `visit_thrown` and the takeout arrive as usual. It cannot see the game itself: a bust, a won leg or match and the darts of your opponents happen in the browser. Autodarts shares them through its cloud, which a third-party integration reaches only with a client ID from Autodarts: the [cloud link](#the-cloud-link) is ready for it.

The optional **online bridge** brings these moments into Home Assistant with the browser extension [Tools for Autodarts](https://github.com/creazy231/tools-for-autodarts). Its WLED feature calls an address of your choice for each moment of the game. The bridge offers a secret Home Assistant address for it and turns every call into a [board event](entities.md#board-events) whose type starts with `online_` and whose `source` is `online`. It is off by default.

Once Autodarts has issued the client ID of the integration, the **cloud link** brings the same moments without a browser: the integration reads the state of the match from the Autodarts cloud and reports what is new as the same board events, with the `source` `cloud`. The bridge then remains for those who don't link their Autodarts account.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/en/online-moments-dark.png">
  <img src="images/en/online-moments-light.png" alt="Two ways for the moments of an online match: a match on play.autodarts.io reaches Home Assistant in one of two ways. With the cloud link, once Autodarts issues its client, the integration reads the state of the match from the Autodarts cloud every 5 seconds and turns what is new into the triggers of Tools for Autodarts. With the online bridge, Tools for Autodarts in the browser calls a secret webhook of Home Assistant. Both become the same board events, such as online_busted and online_game_shot, for the light show, the callers and your automations. While the bridge is switched on, it alone reports the moments." width="560">
</picture>

## Set up the bridge

1. Go to **Settings → Devices & services → Autodarts**, open **Configure** (the cog) of your board, turn on **Receive online matches from Tools for Autodarts** and submit. Only entries with a local board have these options.
2. The next step shows the secret address and ready-made lines for Tools for Autodarts. Copy the lines and submit. From now on, Home Assistant accepts calls at the address. Open the options again whenever you need the address.
3. In the browser at the board, open the settings of Tools for Autodarts, turn on **WLED**, choose **Import CSV**, paste the lines and save. Each line is an effect of the type **URL** for one trigger; delete the ones you don't need.
4. Check that the moments arrive: open the address with `?event=gameon` added in a browser of your home network, or play a match. The **Online bridge last event** sensor on the device page, under *Diagnostic*, shows when the last moment arrived and its trigger.

<img src="images/en/online-bridge.png" alt="The options of the Autodarts board in Home Assistant: the secret address for Tools for Autodarts, here masked, and the lines to import into its WLED settings, one for every trigger" width="760">

To add an effect by hand, give it one trigger, the type **URL** and the address followed by `?event=` and the same trigger, for example `…/api/webhook/<secret>?event=busted`. The name of a player can follow as `&player=Lea`. An effect of the type **JSON API** works too, with a body such as `{"event": "busted", "player": "Lea"}`.

## Triggers and events

| Trigger in Tools for Autodarts | Board event | Details |
| --- | --- | --- |
| `gameon`, `bot_throw` | `online_game_on` | Tools for Autodarts sends `gameon` at the start of every turn and after every moment without an effect of its own: a good moment to return to your normal light. |
| `busted` | `online_busted` | A bust. |
| `gameshot`, `gameshot+d10`, `gameshot_<name>` | `online_game_shot` | A won leg, with the `segment` of the winning dart or the `name` of the player when the trigger names them. The name keeps its case, `gameshot_Lea` gives `Lea`, and a player of your [profiles](entities.md#player-profiles) arrives as the profile spells the name: `gameshot_lea` gives `Lea` too. |
| `matchshot`, `matchshot+bull`, `matchshot_<name>` | `online_match_shot` | A won match, with the same details. |
| `0` to `180` | `online_visit` | The `score` of a visit. |
| `range_100_140` or `100-140` | `online_visit` | A visit in the range, with `score_min` and `score_max`. |
| Three darts such as `t20_t20_t20` | `online_visit` | `score`, `darts` and `segments` (for example `["T20", "T20", "T20"]`). |
| `t20`, `d16`, `s5`, `s25`, `bull`, `m17`, `miss`, `outside` | `online_dart` | A dart, with `segment` (`T20`, `D16`, `S5`, `25`, `BULL` or `MISS`) and `score`. |
| `bulloff` | `online_bull_off` | The bull-off begins. |
| `tournament_ready` | `online_tournament_ready` | A tournament match of yours waits for you to mark yourself ready. |
| `idle` | `online_match_left` | You left the match. |
| `other` | none | A moment on another board; the bridge ignores it. |

Every online event has `trigger` (as sent, in lowercase), `source` (`online`) and `name` when the address has `&player=`. Like every player name, `name` is at most 20 characters long and never contains `{`, `}`, `%` or `#`, which notifications and file names would read as a template: `&player={{ 6*7 }}` gives `6*7`. A plain number is always the score of a visit, so `25` is a visit of 25 points and `s25` a dart in the outer bull. The board triggers of Tools for Autodarts, such as `board_started`, `throw` or `takeout`, are not accepted: the board events report them directly from your board, faster and without a browser.

- **Your own darts** come from the board anyway: `dart_detected`, `visit_thrown` and the takeout are faster than the extension and work without it. Use the online events for what only the match knows: busts, won legs and matches, and the darts of your opponents.
- **Only your board:** Tools for Autodarts reports the moments of every player in the match, your opponents' as well. To react to your own board only, enter your board ID under **Board IDs** in its WLED settings and keep the `other` line: moments on other boards then send `other` instead.
- **Light show:** turn on *Also react to online matches* in the [light show](automations.md#light-show) to play busts, won legs and won matches of online matches.

A notification when a tournament match is ready:

```yaml
alias: Darts - tournament match ready
triggers:
  - trigger: event.received
    target:
      entity_id: event.autodarts_board_events
    options:
      event_type:
        - online_tournament_ready
actions:
  - action: notify.mobile_app_phone
    data:
      message: Your tournament match is ready. Mark yourself ready on Autodarts.
mode: single
```

## The cloud link

The cloud link is not available yet: it waits for the client ID that Autodarts issues to the integration, which has been requested ([roadmap](roadmap.md#next), [decision 0020](decisions/0020-a-public-client-for-the-cloud-link.md)). Everything else is ready, and once it ships, the setup links your Autodarts account with a short code that you enter on any device. During a match, the integration reads the state of the match every 5 seconds and reports what is new since the last read as the triggers above, so the light show, the callers and your automations work without the browser extension:

| In the match | Trigger | Board event |
| --- | --- | --- |
| A new visit of a player at your board | `gameon` | `online_game_on` |
| Every dart of the visit | `t20`, `s25`, `bull`, `m17`, `miss` … | `online_dart` |
| The third dart of a visit that neither busts nor wins | its score, such as `140` | `online_visit` |
| A bust | `busted` | `online_busted` |
| A won leg, with the winning dart | `gameshot+d16` | `online_game_shot` |
| A won match, with the winning dart | `matchshot+bull` | `online_match_shot` |
| The bull-off begins | `bulloff` | `online_bull_off` |
| Your board leaves the match | `idle` | `online_match_left` |

- **The same events.** Each event has the details of its trigger, `name` with the player as your [profiles](entities.md#player-profiles) spell the name, and `source` `cloud`. An automation that reacts to `online_busted` works with the bridge and with the cloud link alike.
- **Only your board.** Moments of players at another board, your opponents in an online match, are skipped, as with the bridge when Tools for Autodarts knows your board ID. The bot and players without a board of their own throw at yours.
- **The bridge first.** While the bridge is switched on, it alone reports the moments: it is instant, and both together would report every moment twice. Switch it off to let the cloud link take over.
- **Without a Board Manager in your network.** A board that Home Assistant reaches only through the cloud, such as Lens, gets the **Events** entity with these events, for the light show and your automations.
- **Every 5 seconds.** A moment that lasts shorter than a read, such as a visit taken out within seconds, can be missed and is never replayed. A match that ran before Home Assistant started counts from the next read on. `tournament_ready` comes only from the bridge, because the state of a match doesn't show it.

## Security

- The address contains a secret of 64 random hexadecimal characters. Whoever knows it can send moments of a game to your Home Assistant, nothing else: the bridge accepts only the triggers above, fields of limited length and at most 20 calls per second and 120 per minute. The integration never logs the address, and diagnostics don't contain it. Home Assistant itself names it in a few of its own warnings, for example about a call from outside your network, so check logs before you share them.
- By default, only devices in your home network can call the address; Home Assistant ignores calls from the internet. Turn on **Accept calls from outside your home network** only for an https address through Home Assistant Cloud or your own domain.
- If the address got out, turn on **Create a new secret address** in the options and import the new lines into Tools for Autodarts. The old address stops working at once, also when you switch the bridge off in the same step.
- Switched off, the bridge does not exist: Home Assistant answers its address like any unknown one. The integration keeps the address for the next time you switch the bridge on.

## Limitations

- **A browser extension of a third party.** Moments arrive only while the Autodarts page is open in a browser with Tools for Autodarts and its WLED feature on. When the extension changes its triggers, the bridge may need an update. The events are never replayed.
- **One effect per trigger.** Tools for Autodarts plays one effect per trigger and picks one at random when several effects share a trigger. A trigger that drives a WLED device in the extension and Home Assistant at the same time reaches each of them only now and then. Let Home Assistant drive your lights, for example with the light show, or use separate triggers.
- **Effects only once.** With *trigger Effects only once* on, the extension skips an effect that is already playing, so the same moment twice in a row arrives once.
- **Mixed content.** play.autodarts.io is an https page, and browsers may block its calls to a plain http address; the extension warns about that when you enter one. What works:
  - An https address of Home Assistant with a trusted certificate, such as your Home Assistant Cloud address or your own domain. Turn on *Accept calls from outside your home network* unless the browser reaches that address inside your home network.
  - A plain http address in your home network, such as `http://homeassistant.local:8123`, if the browser lets the calls through: allow *Insecure content* for play.autodarts.io in the site settings of Chrome or Edge, and allow access to devices on your local network when the browser asks.
  - Whichever you choose, the *Online bridge last event* sensor shows whether the moments arrive.
- **Board events only.** Online moments don't count in the training session, the practice game or the personal bests.
