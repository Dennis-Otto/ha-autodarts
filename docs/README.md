# Autodarts for Home Assistant: documentation

[← Project page](../README.md) · [Deutsche Dokumentation](de/README.md)

Everything about the Autodarts integration: how to set it up, play and train with it, put a scoreboard next to the board, follow your statistics and let your home join in.

<img src="images/en/hero.webp" alt="Animation: a 301 match on the live card and the scoreboard side by side. Alex throws three triple 20s, Sam scores 85, and Alex checks out 121 for the game shot" width="760">

## Get started

| Guide | What you'll find |
| --- | --- |
| [Installation and setup](installation.md) | Requirements, HACS and manual installation, the three ways to add a board, the optional cloud link, reconfiguration, updating and removal |

## Guides

| Guide | What you'll find |
| --- | --- |
| [Games and rules](games.md) | Every game at a glance, four ways to start one, matches, the match summary, teams, handicaps, the bull-off, tournaments and the rules of X01, the Cricket games, the party games and the training games |
| [Scoreboard at the board](scoreboard.md) | A tablet or TV next to the board: setup, landscape and portrait, the new game screen, tournaments, the caller and idle mode |
| [Statistics and players](statistics.md) | Training sessions, personal bests, the heatmap and dart positions, progress over time, doubles, player profiles, achievements, trends and grouping, the leaderboard, the weekly report, the training calendar and exports |
| [Automations](automations.md) | Eleven blueprints, their settings, board events and ready-to-use examples |
| [Online matches](online-matches.md) | Busts, won legs and matches of online matches as board events, with the browser extension Tools for Autodarts *(experimental)* |

## Reference

| Page | What you'll find |
| --- | --- |
| [Dashboard cards](cards.md) | The live card, the training card, the board status card, the scoreboard, the doubles card, the players card, the leaderboard card and the automatic dashboard, with every option and accessibility |
| [Entities and events](entities.md) | Every entity, board event, state, attribute and action, and which Board Manager generation provides it |
| [How it works](how-it-works.md) | Architecture, update intervals, connection behavior, Board Manager generations, address changes, training and records, stored data and privacy |
| [Troubleshooting](troubleshooting.md) | Setup messages, repairs, unavailable entities, failing actions, diagnostics and logs |
| [Security design](security.md) | What is protected, trust boundaries, threats and countermeasures |
| [Glossary](glossary.md) | The words of darts and of this integration, with their German terms |

## Project

| Page | What you'll find |
| --- | --- |
| [Changelog](../CHANGELOG.md) | What every version brought |
| [Roadmap](roadmap.md) | Released versions and what comes next |
| [Development](development.md) | Tests, Docker end-to-end test, demo instance, screenshots and CI |
| [Releases](releases.md) | How versions and release notes are produced |

## Use cases

<table>
  <tr>
    <td width="50%" valign="top"><img src="images/en/training-card.png" alt="Training card with 3-dart average, heatmap, statistics and recent visits" width="100%"><br><b>Train with a purpose.</b> Follow your average, your 180s and where your darts land after every session, and let a daily goal and a training streak keep you going. <a href="statistics.md">Statistics</a></td>
    <td width="50%" valign="top"><img src="images/en/lobby.webp" alt="Animation: a game is chosen on the new game screen of the tablet at the board and starts on the scoreboard" width="100%"><br><b>A darts night with friends.</b> Choose the game on the tablet at the board or start a tournament, let the scoreboard keep the score and call the game, and watch the table or the leaderboard between games. <a href="scoreboard.md">Scoreboard</a></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="images/en/blueprint-light-show.png" alt="A new automation from the light show blueprint with a section for every moment of the game" width="100%"><br><b>Atmosphere.</b> Light shows for a 180 or a won match, a dart caller on your speakers and the board light for the takeout. <a href="automations.md">Automations</a></td>
    <td width="50%" valign="top"><img src="images/en/media-gallery.png" alt="The highlight gallery in the media browser with photos of a checkout and two high visits" width="100%"><br><b>Keep the highlights.</b> A photo of the board after every 180 or checkout, on your phone and in a gallery by month. <a href="automations.md#highlight-gallery">Highlight gallery</a></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="images/en/dashboard-trends.png" alt="Graphs of darts per day, the 3-dart average and practice legs over four weeks" width="100%"><br><b>Progress over months.</b> Long-term graphs, a weekly report on your phone and a training calendar with a year of sessions and matches. <a href="statistics.md#progress-over-time">Progress over time</a></td>
    <td width="50%" valign="top"><img src="images/en/status-card.png" alt="Board status card with detection, connections, board PC load and cameras" width="100%"><br><b>A board that looks after itself.</b> Start the detection when you enter the darts room, stop it when you leave, and get a notification when the board goes offline or a camera fails. <a href="automations.md#blueprints">Blueprints</a></td>
  </tr>
</table>

## Supported devices

| | Supported | Tested with |
| --- | --- | --- |
| Board Manager 2 (headless) | 2.x | 2.0.0 |
| Board Manager 1 (classic app) | 1.x | 1.0.7 |
| Autodarts Desktop | Not tested yet | – |
| Cameras | Any number supported by the Board Manager | 3 |
| Home Assistant | 2026.8 or newer | 2026.8.0 and 2026.9.3 |

Any board hardware that runs the Autodarts Board Manager works, because the integration talks to the Board Manager, not to the cameras.
