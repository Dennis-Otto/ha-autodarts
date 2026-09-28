<div align="center">

<img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/custom_components/autodarts/brand/icon.png" alt="Autodarts logo" width="96" height="96">

# Autodarts for Home Assistant

**Your Autodarts board, live in Home Assistant: local, realtime and ready for automations.**

[![HACS custom repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Latest release](https://img.shields.io/github/v/release/Dennis-Otto/ha-autodarts?label=release)](https://github.com/Dennis-Otto/ha-autodarts/releases)
[![Home Assistant 2026.8 or newer](https://img.shields.io/badge/Home%20Assistant-2026.8%2B-41BDF5.svg?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Tests](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/tests.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/tests.yml)
[![Coverage 100 %](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/development.md#tests)
[![Docker end-to-end test](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/e2e.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/e2e.yml)

[**Documentation**](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/README.md) · [**Deutsche Anleitung**](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/de/README.md) · [Quick start](#quick-start) · [Changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md)

<img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/hero.webp" alt="Animation: a 301 match on the live card and the scoreboard side by side. Alex throws three triple 20s, the beds light up and the scoreboard counts down to 121; Sam scores 85; Alex checks out 121 with T20, outer bull and D18 for the game shot" width="880">

</div>

## Why

- **Instant and local.** Darts appear in Home Assistant a fraction of a second after they land, straight from the Board Manager in your network. No account, no cloud, no client ID.
- **A whole darts evening.** X01 from 101 to 1001, three Cricket games, six party games and eight training games, alone, as a match of up to four or as a tournament of up to eight, with a scoreboard for the tablet at the board.
- **Your progress in numbers.** Averages, heatmaps of the real dart positions, personal bests, badges, weekly trends, player profiles, a weekly report and a year of history, all kept in your home.
- **Your home plays along.** Lights for a 180, a caller on your speakers, the board light for the takeout, a photo of your best checkout.

## Features

<table>
  <tr>
    <td width="55%" valign="top">
      <h3>Play</h3>
      <ul>
        <li>X01 from 101 to 1001 with double out, double in and the checkout route after every dart</li>
        <li>Cricket, Cut-Throat Cricket and Tactics on a chalkboard</li>
        <li>Party games: Shanghai, Halve-It, Killer, Golf, Baseball and Count-Up</li>
        <li>Matches of up to four players with legs and sets, two teams of two, handicap start scores and a bull-off, and a summary of every match</li>
        <li>Tournaments of three to eight players: a round robin with a table or a knockout with a bracket</li>
        <li>A bot from level 20 to 120 to play X01 and Cricket against</li>
        <li>A tap corrects a dart the board read wrong; a keypad enters darts by hand, and the last visit can be undone</li>
        <li>Setup hints where no checkout is possible, such as T20 T20 S17 to leave 32</li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/games.md">Games and rules →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/tournament-bracket.webp" alt="Animation: the knockout bracket of five players on the scoreboard; the winners slide into the next round until Alex wins the final" width="100%"></td>
  </tr>
  <tr>
    <td width="55%" valign="top">
      <h3>Train</h3>
      <ul>
        <li>Training sessions that start with the first dart and keep your last 20 sessions</li>
        <li>Eight training games: Around the Clock, doubles training, checkout training, Bob's 27, the 121 checkout, Catch 40, the JDC Challenge and the singles training</li>
        <li>A daily goal, a training streak and personal bests with an event when you beat one</li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/games.md#training-games">Training games →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/training-game.webp" alt="Animation: Around the Clock on the live card; every hit moves the target and outlines the beds of the next number" width="100%"></td>
  </tr>
  <tr>
    <td width="55%" valign="top">
      <h3>Analyze</h3>
      <ul>
        <li>3-dart average, first 9 average, checkout and doubles rate, and a heatmap of every bed or of the real dart positions, with the grouping in millimeters</li>
        <li>Player profiles with badges in bronze, silver, gold and platinum, weekly trends, head-to-head records, the match history and a leaderboard</li>
        <li>The hit rate of every double, a weekly report, a training calendar and exports to CSV or JSON</li>
        <li>Long-term statistics for graphs over weeks and months</li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/statistics.md">Statistics and players →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/heatmap-modes.webp" alt="Animation: the heatmap of the training card switches from beds to numbers and the real dart positions, then to one player's darts" width="100%"></td>
  </tr>
  <tr>
    <td width="55%" valign="top">
      <h3>Screen at the board</h3>
      <ul>
        <li>A scoreboard for a tablet or TV, readable from the oche</li>
        <li>A new game screen to choose the game, the players and the format at the board, or to start a tournament</li>
        <li>A caller that calls the game through the screen's browser</li>
        <li>Idle mode with a leaderboard, personal bests, today's darts and a clock</li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/scoreboard.md">Scoreboard at the board →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/lobby.webp" alt="Animation: on the tablet, New game opens the game screen, Cricket and a second player are chosen and the game starts" width="100%"></td>
  </tr>
  <tr>
    <td width="55%" valign="top">
      <h3>Automate</h3>
      <ul>
        <li>Board events for every dart, visit, takeout, bust, won leg and match, personal best and more</li>
        <li>Eleven blueprints: light show, dart and practice callers, highlight photos, reports, alerts and routines</li>
        <li>Start any game with one action, also by voice</li>
        <li>Online matches on play.autodarts.io through an optional bridge <i>(experimental)</i></li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/automations.md">Automations →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/media-gallery.png" alt="The highlight gallery in the media browser of Home Assistant: photos of a checkout of 121, a 180 and a 140" width="100%"></td>
  </tr>
  <tr>
    <td width="55%" valign="top">
      <h3>Local and private</h3>
      <ul>
        <li>Found automatically with Board Manager 2; Board Manager 1 works too</li>
        <li>Nothing leaves your network unless you use the board search, the cloud link or the online bridge; board secrets are never stored</li>
        <li>Seven dashboard cards and an automatic dashboard, in English, German, Dutch, French and Spanish (<a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/README.md#languages">languages</a>)</li>
        <li>Every rule of the Home Assistant quality scale up to Platinum, 100 % test coverage</li>
      </ul>
      <p><a href="https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/how-it-works.md">How it works →</a></p>
    </td>
    <td width="45%"><img src="https://raw.githubusercontent.com/Dennis-Otto/ha-autodarts/main/docs/images/en/architecture-light.png" alt="Architecture: the Board Manager on the board PC sends realtime events to the Autodarts integration in Home Assistant, which provides entities, board events, cards and automations; the Autodarts cloud is optional" width="100%"></td>
  </tr>
</table>

## Requirements

**Home Assistant 2026.8 or newer** with [HACS](https://hacs.xyz), and an Autodarts board in your network: **Board Manager 2**, Autodarts 2 without a screen (recommended, tested up to 2.0.2), or the classic **Board Manager 1**. Autodarts Desktop and the Winmau Autodarts devices such as Autodarts X or Lens have not been tested yet; a [compatibility report](https://github.com/Dennis-Otto/ha-autodarts/issues/new?template=board_compatibility.yml) helps, whether it works or not. No Autodarts account is needed.

## Quick start

1. **Install with HACS.**

   [![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dennis-Otto&repository=ha-autodarts&category=integration)

   Or add `https://github.com/Dennis-Otto/ha-autodarts` in HACS as a custom repository of the type **Integration**, then download **Autodarts**.
2. **Restart Home Assistant.**
3. **Add your board.** With Board Manager 2, Home Assistant usually shows it under **Settings → Devices & services → Discovered** already. Otherwise:

   [![Open your Home Assistant instance and start setting up Autodarts.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=autodarts)

   Choose **Search for boards on this network** or **Enter board address** and confirm.
4. **Add the cards.** Create a complete dashboard in one step: **Settings → Dashboards → Add dashboard → Autodarts**. Or edit a dashboard, choose **Add card** and search for *Autodarts*.

New to Home Assistant? [From zero to the scoreboard](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/getting-started.md) takes you from nothing to the scoreboard next to your board. The [installation guide](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/installation.md) covers manual installation, reconfiguration, updates and removal.

## Blueprints

Import a blueprint with one click, choose your board and you're done:

| Blueprint | Import |
| --- | --- |
| **Light show.** Your WLED presets or room lights for a 180, a high finish, a bust, a won leg or match, a personal best, an achievement, the winner of a tournament and more, and back to your normal light afterwards. | [![Import the light show blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Flight_show.yaml) |
| **Celebrate a visit score.** Your actions for every 180, every ton, or any score you choose, the moment the third dart lands. | [![Import the visit score blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fvisit_score.yaml) |
| **Dart caller.** Every visit announced on your speakers, with a special call for 180. | [![Import the dart caller blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fdart_caller.yaml) |
| **Practice caller.** Who needs what, busts and game shots of the practice game on your speakers. | [![Import the practice caller blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fpractice_caller.yaml) |
| **Highlight photo.** A picture of the board after a 180 or a checkout, on your phone and in a gallery of the media browser. | [![Import the highlight photo blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fhighlight_photo.yaml) |
| **Takeout actions.** Light up the board while you pull your darts. | [![Import the takeout actions blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftakeout.yaml) |
| **Start and stop detection automatically**, based on presence in the darts room. | [![Import the automatic detection blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fauto_detection.yaml) |
| **Training session routine.** Light, detection and calibration follow your training sessions. | [![Import the training session routine blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_session.yaml) |
| **Weekly report.** Your training week with the trend of your 3-dart average, as a notification. | [![Import the weekly report blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fweekly_report.yaml) |
| **Training report.** Your daily summary with the 3-dart average. | [![Import the training report blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Ftraining_report.yaml) |
| **Board problem alert** when the board goes offline or a camera fails, with an optional all-clear. | [![Import the board problem alert blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FDennis-Otto%2Fha-autodarts%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fautodarts%2Fboard_alert.yaml) |

## Documentation

| Guide | Contents |
| --- | --- |
| [From zero to the scoreboard](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/getting-started.md) | For Autodarts players without Home Assistant: from nothing to the first game on the scoreboard |
| [Installation](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/installation.md) | Requirements, HACS and manual installation, the three ways to add a board, updates and removal |
| [Games and rules](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/games.md) | How to start a game, matches, teams, handicaps, the bull-off, the match summary, tournaments and the rules of every game |
| [Scoreboard at the board](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/scoreboard.md) | A tablet or TV at the board, the new game screen, tournaments, the caller and idle mode |
| [Statistics and players](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/statistics.md) | Sessions, personal bests, heatmaps and dart positions, doubles, player profiles, achievements, trends, the leaderboard, reports, calendar and export |
| [Dashboard cards](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/cards.md) | All seven cards, the automatic dashboard, every option and accessibility |
| [Automations](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/automations.md) | Eleven blueprints, board events and ready-to-use examples |
| [Online matches](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/online-matches.md) | Moments of online matches on play.autodarts.io in Home Assistant *(experimental)* |
| [Entities and events](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/entities.md) | Every entity, event, attribute and action |
| [How it works](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/how-it-works.md) | Data flow, update intervals, connection behavior, stored data and privacy |
| [Troubleshooting](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/troubleshooting.md) | Messages, repairs, diagnostics and logs |
| [Security design](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/security.md) | What is protected, trust boundaries, threats and countermeasures |
| [Glossary](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/glossary.md) | The words of darts and of this integration, in English and German |
| [Changelog](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CHANGELOG.md) and [releases](https://github.com/Dennis-Otto/ha-autodarts/releases) | What every version brought; the [roadmap](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/roadmap.md) shows what comes next |
| [Deutsche Dokumentation](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/de/README.md) | Die komplette Anleitung auf Deutsch |

## Known limitations

- **Cloud match data is on hold.** It needs an OAuth client ID that Autodarts issues for this integration, and none is bundled yet. Everything local works without it.
- **Online matches through a browser extension.** Busts and game shots of online matches arrive only while the Autodarts page is open with Tools for Autodarts, a third-party extension. [Limitations](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/online-matches.md#limitations).
- **Training sessions count darts, not games.** A session counts every dart the board detects; players, legs and checkouts belong to the practice game, which keeps its own statistics.
- **Board Manager updates are installed on the board PC.** The update entity reports new Board Manager 2 versions.
- **Live camera view with Board Manager 2 only.** With Board Manager 1, the camera entities show snapshots.

## Support and contributing

- **Questions and ideas:** [GitHub Discussions](https://github.com/Dennis-Otto/ha-autodarts/discussions). **Bugs:** [issues](https://github.com/Dennis-Otto/ha-autodarts/issues/new/choose), with the diagnostics of your board. [SUPPORT.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/SUPPORT.md) explains where to ask what.
- **Security:** report vulnerabilities privately as described in [SECURITY.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/SECURITY.md).
- **Show it:** for videos and articles, the [creator kit](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/creator-kit.md) has facts, videos and pictures, free to use.
- **Contributing:** contributions are welcome; [CONTRIBUTING.md](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CONTRIBUTING.md) explains the checks. Participation follows the [code of conduct](https://github.com/Dennis-Otto/ha-autodarts/blob/main/CODE_OF_CONDUCT.md) and the project's [governance](https://github.com/Dennis-Otto/ha-autodarts/blob/main/GOVERNANCE.md).

## Quality and security

[![CodeQL](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/codeql.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/codeql.yml)
[![Secret scan](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/secret-scan.yml)
[![SBOM](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/sbom.yml/badge.svg)](https://github.com/Dennis-Otto/ha-autodarts/actions/workflows/sbom.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Dennis-Otto/ha-autodarts/badge)](https://scorecard.dev/viewer/?uri=github.com/Dennis-Otto/ha-autodarts)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/14935/badge)](https://www.bestpractices.dev/projects/14935)

- Meets every rule of the [Home Assistant integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/) up to Platinum ([self-assessment](https://github.com/Dennis-Otto/ha-autodarts/blob/main/custom_components/autodarts/quality_scale.yaml)), including strict typing.
- 100 % line and branch coverage of the integration, fuzzed cards, a Docker end-to-end test against both Board Manager generations and the oldest supported Home Assistant, and a real browser test of every card. [Development](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/development.md).
- Signed release packages with SLSA provenance. [Releases](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/releases.md#signed-release-packages).

## Credits and license

This integration started as a fork of [Trkal/HACSAutodarts](https://github.com/Trkal/HACSAutodarts), a cloud-based prototype from April 2026. Since September 2026 it has been rewritten and is maintained independently by [@Dennis-Otto](https://github.com/Dennis-Otto): local realtime control for both Board Manager generations, games, training analytics, dashboard cards, blueprints, tests and documentation. Both use the `autodarts` domain; the [installation guide](https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs/installation.md#update-from-the-original-integration) explains how to switch. Thanks to Trkal for the original work and to the Autodarts team for their open local API.

Licensed under the [MIT license](https://github.com/Dennis-Otto/ha-autodarts/blob/main/LICENSE). Autodarts and Winmau names and brand artwork belong to their respective owners. The bundled brand assets identify the supported product and are not covered by the MIT license. This is an unofficial community integration and is not affiliated with Autodarts.
