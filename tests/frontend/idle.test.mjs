// Idle mode of the scoreboard: panels in turn when no game runs and nobody throws or taps.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, DEVICE, READY, loadCards, makeHass, mount, text, update, window } from "./dom.mjs";

const { formatClock, idlePanels } = await loadCards();

// Saturday, 26 September 2026, 19:05 UTC; the tests run in UTC.
const NOW = Date.UTC(2026, 8, 26, 19, 5);
const PICTURE = "/api/image/serve/alex/512x512";
const profile = (name, legs_played, legs_won, average, person = null) => ({
  name,
  legs_played,
  legs_won,
  average,
  person,
});
const STATES = {
  "sensor.local_visit_score": { state: "0", attributes: { throws: [] } },
  "sensor.practice_remaining": "unknown",
  "sensor.training_darts": "24",
  "sensor.training_average": "55.75",
  "sensor.training_highest_visit": "140",
  "sensor.training_scores_180": "1",
  "sensor.training_streak": { state: "3", attributes: { best_streak: 5 } },
  "sensor.darts_today": { state: "60", attributes: { goal: 120 } },
  "sensor.personal_best": {
    state: "2026-09-25T18:00:00+00:00",
    attributes: { highest_visit: 140, fewest_darts_501: 18 },
  },
  "sensor.player_profiles": {
    state: "7",
    attributes: {
      players: [
        profile("Sam", 10, 4, 48.2),
        profile("Alex", 20, 12, 61.3, "person.alex"),
        profile("Kim", 6, 3, null),
        profile("Lea", 0, 0, null),
        profile("Tom", 6, 5, null),
        profile("Ben", 2, 0, 30),
        profile("Max", 4, 1, 40),
        // The same average and legs: the name decides.
        profile("Abe", 2, 0, 30),
      ],
    },
  },
  "sensor.last_match": {
    state: "2026-09-26T18:40:00+00:00",
    attributes: {
      matches: [
        {
          ended: "2026-09-26T18:40:00+00:00",
          game: 501,
          winner: 2,
          players: [
            { name: "Alex", legs: 1, sets: 0, average: 55.5 },
            { name: "Sam", legs: 3, sets: 1, average: 60.1 },
            { legs: 0, sets: 0, average: null },
          ],
        },
      ],
    },
  },
};

const setup = (states = {}, config = {}, options = {}) => {
  const hass = makeHass({ states: { ...READY, ...STATES, ...states }, ...options });
  hass.states["person.alex"] = { entity_id: "person.alex", state: "home", attributes: { entity_picture: PICTURE } };
  return { hass, card: mount("autodarts-scoreboard-card", hass, config) };
};
const clock = (t) => t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: NOW });
const panel = (card) => $(card, ".idle-panel")?.dataset.panel ?? null;
const rows = (card) =>
  $$(card, ".ranking li").map((row) => [...row.children].map((part) => part.textContent || part.getAttribute("src")));

test("after the idle time the panels take turns, and a tap ends it", (t) => {
  clock(t);
  const { card } = setup();
  t.mock.timers.tick(179999);
  assert.equal(panel(card), null);
  assert.equal(text(card, ".main .label"), "Current visit");
  t.mock.timers.tick(1);

  assert.equal(panel(card), "leaderboard");
  assert.equal(text(card, ".title"), "Dartboard");
  assert.equal(text(card, ".meta"), "Leaderboard");
  assert.equal($(card, ".scoreboard").classList.contains("idling"), true);
  assert.equal($(card, ".visit").hidden, true);
  assert.equal(text(card, ".idle-back"), "Tap to return");
  // The best average first; players without an X01 average by legs won; five at most.
  assert.deepEqual(rows(card), [
    ["1", PICTURE, "Alex", "Ø 61.3", "Legs 12/20"],
    ["2", "Sam", "Ø 48.2", "Legs 4/10"],
    ["3", "Max", "Ø 40.0", "Legs 1/4"],
    ["4", "Abe", "Ø 30.0", "Legs 0/2"],
    ["5", "Ben", "Ø 30.0", "Legs 0/2"],
  ]);

  t.mock.timers.tick(10000);
  assert.equal(text(card, ".meta"), "Personal bests");
  assert.deepEqual(
    $$(card, ".records div").map((record) => record.textContent),
    ["Highest visit140", "Best 50118 darts", "Longest streak5 days"]
  );

  t.mock.timers.tick(10000);
  assert.equal(text(card, ".meta"), "Today");
  assert.equal(text(card, ".idle-panel .big"), "60");
  assert.equal(text(card, ".idle-panel .label"), "of 120 darts");
  assert.equal($(card, ".goal i").getAttribute("style"), "width:50%");
  assert.equal($(card, ".goal").className, "goal");
  assert.deepEqual(
    $$(card, ".idle-panel .facts span").map((fact) => fact.textContent),
    ["55.8 3-dart avg.", "140 Highest visit", "1 180s", "3 days in a row"]
  );

  t.mock.timers.tick(10000);
  assert.equal(text(card, ".meta"), "Last match");
  assert.equal(text(card, ".match-head"), "501 · 09/26, 6:40 PM");
  assert.deepEqual(
    $$(card, ".result li").map((row) => [row.className, row.textContent]),
    [
      ["", "Alex1Ø 55.5"],
      ["winner", "Sam1Ø 60.1🏆"],
      ["", "Player 30"],
    ]
  );

  // Three minutes and forty seconds after 19:05.
  t.mock.timers.tick(10000);
  assert.equal(text(card, ".meta"), "Clock");
  assert.equal(text(card, ".clock .big"), "7:08 PM");
  assert.equal(text(card, ".clock .facts"), "Saturday, September 26");

  t.mock.timers.tick(10000);
  assert.equal(panel(card), "leaderboard");
  // A tap anywhere brings the scoreboard back and starts the idle time again.
  $(card, ".idle-panel").click();
  assert.equal(panel(card), null);
  assert.equal($(card, ".visit").hidden, false);
  assert.equal(text(card, ".meta"), "Training");
  t.mock.timers.tick(179999);
  assert.equal(panel(card), null);
  t.mock.timers.tick(1);
  assert.equal(panel(card), "leaderboard");
});

test("darts, keys and a running game keep the scoreboard awake", (t) => {
  clock(t);
  const { hass, card } = setup();
  t.mock.timers.tick(100000);
  const dart = { state: "60", attributes: { throws: [{ number: 20, multiplier: 3 }] } };
  let next = update(hass, { "sensor.local_visit_score": dart });
  card.hass = next;
  t.mock.timers.tick(179999);
  assert.equal(panel(card), null);
  t.mock.timers.tick(1);
  assert.equal(panel(card), "leaderboard");
  // A dart ends idle mode.
  next = update(next, { "sensor.local_visit_score": { state: "0", attributes: { throws: [] } } });
  card.hass = next;
  assert.equal(panel(card), null);
  t.mock.timers.tick(180000);
  assert.equal(panel(card), "leaderboard");
  // So does a key.
  $(card, ".scoreboard").dispatchEvent(new window.KeyboardEvent("keydown", { key: "a", bubbles: true }));
  assert.equal(panel(card), null);

  // A running game never idles; a decided match is no game any more.
  const match = (winner) => ({
    "sensor.practice_remaining": {
      state: "40",
      attributes: { game: 501, player: 1, winner, scores: [{ player: 1, remaining: 40 }, { player: 2, remaining: 60 }] },
    },
  });
  next = update(next, match(null));
  card.hass = next;
  t.mock.timers.tick(600000);
  assert.equal(panel(card), null);
  next = update(next, match(2));
  card.hass = next;
  t.mock.timers.tick(180000);
  assert.equal(panel(card), "leaderboard");
  // Nor does the new game screen, once it opened by itself after the match.
  assert.equal($(card, ".lobby"), null);
});

test("only the chosen panels that have something to show take turns", (t) => {
  clock(t);
  const { card } = setup({}, { idle_panels: ["today", "clock", "today", "weather"], idle_interval: 20 });
  t.mock.timers.tick(180000);
  assert.equal(panel(card), "today");
  t.mock.timers.tick(10000);
  assert.equal(panel(card), "today");
  t.mock.timers.tick(10000);
  assert.equal(panel(card), "clock");
  t.mock.timers.tick(20000);
  assert.equal(panel(card), "today");

  // Without profiles, records, a match or today's darts, only the clock is left.
  const bare = setup(
    {
      "sensor.player_profiles": { state: "0", attributes: { players: [] } },
      "sensor.last_match": { state: "unknown", attributes: {} },
      "sensor.personal_best": { state: "unknown", attributes: {} },
      "sensor.training_streak": "0",
      "sensor.darts_today": "unavailable",
    },
    { idle_after: 0, idle_interval: 0 }
  ).card;
  // The idle time is at least five seconds and the interval three.
  t.mock.timers.tick(4999);
  assert.equal(panel(bare), null);
  t.mock.timers.tick(1);
  assert.equal(panel(bare), "clock");
  t.mock.timers.tick(3000);
  assert.equal(panel(bare), "clock");
  // Alone, the clock stays and moves on every minute.
  const time = setup({}, { idle_panels: ["clock"], idle_after: 55 }).card;
  t.mock.timers.tick(55000);
  assert.equal(text(time, ".clock .big"), "7:09 PM");
  t.mock.timers.tick(60000);
  assert.equal(text(time, ".clock .big"), "7:10 PM");
  // With none of them chosen there is no idle mode at all.
  const none = setup({ "sensor.player_profiles": "0" }, { idle_panels: ["leaderboard"] }).card;
  t.mock.timers.tick(600000);
  assert.equal(panel(none), null);
});

test("idle mode can be switched off, never runs in the preview and ends with the card", (t) => {
  clock(t);
  const off = setup({}, { idle: false }).card;
  const preview = setup().card;
  preview.preview = true;
  preview.hass = update(preview._hass, { "sensor.training_darts": "25" });
  t.mock.timers.tick(600000);
  assert.equal(panel(off), null);
  assert.equal(panel(preview), null);

  const { card } = setup();
  t.mock.timers.tick(180000);
  assert.equal(panel(card), "leaderboard");
  // Leaving the page ends idle mode; back on the page, the idle time starts again.
  card.remove();
  document.body.append(card);
  assert.equal(panel(card), null);
  t.mock.timers.tick(179999);
  assert.equal(panel(card), null);
  t.mock.timers.tick(1);
  assert.equal(panel(card), "leaderboard");
  // The new game screen gives way to idle mode, too.
  $(card, ".lobby-toggle")?.click();
  t.mock.timers.tick(180000);
  assert.equal(panel(card), "leaderboard");

  // A card that never reached the page schedules nothing.
  const detached = document.createElement("autodarts-scoreboard-card");
  detached.setConfig({ type: "custom:autodarts-scoreboard-card" });
  detached.hass = makeHass({ states: { ...READY, ...STATES } });
  t.mock.timers.tick(600000);
  assert.equal(panel(detached), null);
});

test("a decided game in German, a full daily goal and a single day of streak", (t) => {
  clock(t);
  const { card } = setup(
    {
      "sensor.darts_today": { state: "150", attributes: { goal: 120 } },
      "sensor.training_streak": { state: "1", attributes: {} },
      "sensor.last_match": {
        state: "2026-09-26T18:40:00+00:00",
        attributes: {
          matches: [
            {
              ended: "2026-09-26T18:40:00+00:00",
              game: "cricket",
              winner: 1,
              players: [
                { name: "Alex", legs: 2, sets: 0, mpr: 2.4 },
                { name: "Sam", legs: 1, sets: 0, mpr: 1.85 },
              ],
            },
          ],
        },
      },
    },
    { idle_panels: ["today", "last_match", "clock"] },
    { language: "de" }
  );
  card.hass = {
    ...card._hass,
    locale: { language: "de", time_format: "24" },
    config: { time_zone: "Europe/Berlin" },
  };
  t.mock.timers.tick(180000);
  assert.equal(text(card, ".meta"), "Heute");
  assert.equal(text(card, ".idle-back"), "Tippen, um zurückzukehren");
  assert.equal(text(card, ".idle-panel .label"), "von 120 Darts");
  assert.equal($(card, ".goal").className, "goal reached");
  assert.equal($(card, ".goal i").getAttribute("style"), "width:100%");
  assert.equal($$(card, ".idle-panel .facts span").at(-1).textContent, "1 Tag in Folge");
  t.mock.timers.tick(10000);
  assert.equal(text(card, ".meta"), "Letztes Match");
  assert.equal(text(card, ".match-head"), "Cricket · 26.09., 20:40");
  assert.deepEqual(
    $$(card, ".result li").map((row) => row.textContent),
    ["Alex2MPR 2,40🏆", "Sam1MPR 1,85"]
  );
  t.mock.timers.tick(10000);
  // The server's time zone and a 24-hour clock.
  assert.equal(text(card, ".meta"), "Uhr");
  assert.equal(text(card, ".clock .big"), "21:08");
  assert.equal(text(card, ".clock .facts"), "Samstag, 26. September");
});

test("the panels read what the sensors leave out, and the clock can follow the browser", () => {
  const ui = {
    t: (key) => key,
    format: (value) => String(value),
    date: () => "",
    avatar: () => null,
    clock: () => ({ time: "12:00", day: "Monday" }),
  };
  const data = { players: [], match: null, records: [], stats: { today: null }, now: new Date(NOW) };
  assert.deepEqual(
    idlePanels(undefined, data, ui).map((item) => item.panel),
    ["clock"]
  );
  assert.deepEqual(idlePanels([], { ...data, stats: { today: 0, goal: 0 } }, ui).map((item) => item.panel), [
    "today",
    "clock",
  ]);
  // A player of Cricket or party games only has no X01 average.
  const cricket = { name: "Kim", legsPlayed: 3, legsWon: 2, average: null };
  assert.match(idlePanels(["leaderboard"], { ...data, players: [cricket] }, ui)[0].html, /<span class="score">–<\/span>/);
  const without = idlePanels(["today"], { ...data, stats: { today: 5, goal: 0, streak: 0 } }, ui)[0].html;
  assert.equal(without.includes('class="goal'), false);
  assert.match(without, /darts_today/);
  // In the browser's own time zone, a 12-hour clock where the profile asks for it.
  const hass = { locale: { language: "en", time_zone: "local", time_format: "12" }, config: { time_zone: "Asia/Tokyo" } };
  assert.deepEqual(formatClock(hass, new Date(NOW)), { time: "7:05 PM", day: "Saturday, September 26" });
  assert.equal(formatClock({ language: "en" }, new Date(NOW)).time, "7:05 PM");
});

test("idle panels fade in unless the device asks for less motion", () => {
  const { card } = setup();
  const style = $(card, "style").textContent;
  assert.match(style, /\.idle-panel \{[^}]*animation: ad-fade/);
  assert.match(style, /@media \(prefers-reduced-motion: reduce\) \{ \.idle-panel \{ animation: none; \} \}/);
  assert.equal(DEVICE.length > 0, true);
});
