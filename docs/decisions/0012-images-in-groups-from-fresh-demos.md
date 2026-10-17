---
description: "Why the images of the documentation render in fixed groups side by side, each from a fresh demo, so that the visual check is fast and repeatable."
---

# Render the images of the documentation in fixed groups, each from a fresh demo

- Status: accepted
- Date: 2026-10-13

## Context

The visual check of a pull request and the screenshot bot rendered every image of a language in one job, 78 images and animations one after another from one demo: about 17 minutes of rendering and 20 of the job, twice per change of the cards, and 10 % of all runner minutes in two weeks. Every step played on the demo that the steps before it left, so the players card showed the matches of every animation before it, and no image could render without all the steps before it. The bot's matrix had no `fail-fast: false` either, so a language whose rendering failed cancelled the other one, and the bot then updated no image at all; 12 of its 26 runs failed in five days.

## Options

1. Keep one job per language and only replace fixed waits with waits for what a page shows: safer images, but at most a fifth faster, because most of the time goes to the frames of the animations and the moves of the frozen clock.
2. Split the steps into groups that each start from a fresh demo, and render the groups side by side, one job per group and language, then put them together in a short job per language.
3. Pass the state of the demo from one group to the next, as a copy of its configuration: the images stay exactly as they are, but the groups run one after another again.
4. Seed a demo with everything that the later steps need, so any step can start anywhere: the most freedom, but a second, large description of the demo to keep in step with the animations.

## Decision

Option 2, with the deterministic waits of option 1 for the pages that load. Three fixed groups in `GROUPS` of `tests/e2e/screenshots.py` hold sections of steps, ordered so that each group holds what its images need: the cards before the games, whose legs end the graphs of the week; the tournament of five before the players card, which shows them; the first match of the bot, whose darts follow the fixed random numbers of the demo, before the formats that play it again; the weekly report, which starts a new week, and the dartboard without Autodarts, whose second board would be the first of the cards without one, last in their group. `screenshots.sh` renders every group from a fresh demo also on one machine, so a local run renders the images of CI byte for byte. `collect.sh` puts the groups together and compares them with the committed images, and the bot takes every language that rendered.

## Consequences

Each job takes about eight minutes instead of twenty, six jobs side by side instead of two, at about a quarter more runner minutes. A group renders the same images on its own as after the others, and a change of an animation no longer changes the images of the other groups. The images whose data came from steps of another group changed once with this decision: the players card, the doubles card, the progress cards and the weekly report show the games of their own group. A section that moves to another group changes such images once again, so the groups stay as they are until one grows clearly longer than the others; each job lists the seconds of its sections for that. `tests/test_screenshot_groups.py` keeps the scripts and both workflows at the number of groups, every section in one group and the orders above.
