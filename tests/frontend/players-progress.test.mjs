// The players card's badges, trends and groupings, and the leaderboard card, in a browser DOM.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, loadCards, makeHass, mount, settle, text, update, window, withLanguage } from "./dom.mjs";

await loadCards();

const WEEKS = Array.from({ length: 12 }, (_, index) => `2026-${String(7 + Math.floor(index / 4)).padStart(2, "0")}-0${1 + (index % 4)}`);
const column = (values) => [...Array(12 - values.length).fill(0), ...values];
const TREND = {
  weeks: WEEKS,
  darts: column([90, 0, 120]),
  x01_darts: column([90, 0, 120]),
  x01_points: column([1350, 0, 2400]),
  first9_points: column([150, 0, 180]),
  first9_darts: column([9, 0, 9]),
  at_double: column([10, 0, 8]),
  checkouts: column([2, 0, 3]),
  double_attempts: column([10, 0, 8]),
  double_hits: column([2, 0, 3]),
  maximums: column([1, 0, 2]),
  highest_checkout: [...Array(10).fill(null), 81, 100],
  best_501: [...Array(10).fill(null), 24, 21],
  best_mpr: Array(12).fill(null),
};
const PROFILES = {
  "sensor.player_profiles": {
    state: "2",
    attributes: {
      players: [
        {
          name: "Alex",
          legs_played: 4,
          legs_won: 3,
          average: 62.5,
          highest_checkout: 100,
          fewest_darts: { 501: 21 },
          maximums: 3,
          best_streak: 4,
          darts_thrown: 210,
          trend: TREND,
          spread: [{ target: "T20", darts: 60, offset_x: -6, offset_y: 0.4, r50: 38, r80: 61, change: -4 }],
        },
        { name: "Sam", legs_played: 4, legs_won: 1, average: 48.1, maximums: 0, darts_thrown: 90, trend: { weeks: WEEKS } },
      ],
    },
  },
};
const ACHIEVEMENTS = {
  "sensor.achievements": {
    state: "3",
    attributes: {
      latest: { name: "Alex", achievement: "maximum", tier: 1, date: "2026-09-23T20:00:00+00:00" },
      catalogue: [
        { id: "maximum", tiers: [1, 10, 100], lower: false },
        { id: "hat_trick", tiers: [1], lower: false },
      ],
      players: [
        {
          name: "Alex",
          badges: { maximum: { tier: 1, dates: ["2026-09-23T20:00:00+00:00"] }, hat_trick: { tier: 1, dates: ["2026-09-22T20:00:00+00:00"] } },
          progress: { maximum: 3, hat_trick: 1 },
        },
        { name: "Sam", badges: {}, progress: { maximum: 0, hat_trick: 0 } },
      ],
    },
  },
};
const states = { ...PROFILES, ...ACHIEVEMENTS, "sensor.last_match": { state: "unknown", attributes: {} } };
const players = (config = {}, extra = {}, language = "en") =>
  mount("autodarts-players-card", withLanguage(makeHass({ states: { ...states, ...extra } }), language), config);
const click = (card, selector) => $(card, selector).dispatchEvent(new window.Event("click", { bubbles: true }));

test("the players card shows every player's badges, earned and locked", () => {
  const card = players();
  const section = $(card, ".badges-section");
  assert.equal(section.hidden, false);
  assert.equal(text(card, ".badges-section .section-label"), "Badges");
  assert.deepEqual(
    $$(card, ".badge-owner").map((owner) => owner.textContent),
    ["Alex2 badges", "Sam0 badges"]
  );
  const [alex, sam] = $$(card, ".badge-list");
  assert.deepEqual(
    [...alex.querySelectorAll(".badge")].map((badge) => [badge.dataset.badge, badge.classList.contains("locked")]),
    [
      ["maximum", false],
      ["hat_trick", false],
    ]
  );
  assert.match(alex.querySelector(".badge").textContent, /180 · Bronze180s in X01: 103 of 10/);
  assert.equal(sam.querySelectorAll(".badge.locked").length, 2);
  assert.equal(alex.querySelector("ha-icon").getAttribute("icon"), "mdi:crown");
});

test("locked badges and players without a badge can be hidden", () => {
  const card = players({ show_locked: false });
  assert.deepEqual(
    $$(card, ".badge-owner").map((owner) => owner.querySelector("b").textContent),
    ["Alex"]
  );
  const single = players({}, {
    "sensor.achievements": {
      state: "1",
      attributes: { ...ACHIEVEMENTS["sensor.achievements"].attributes, players: [ACHIEVEMENTS["sensor.achievements"].attributes.players[0]] },
    },
  });
  assert.equal(single.shadowRoot.querySelector(".badge-owner .muted").textContent, "2 badges");
  const one = players({}, {
    "sensor.achievements": {
      state: "1",
      attributes: {
        catalogue: [{ id: "maximum", tiers: [1] }],
        players: [{ name: "Alex", badges: { maximum: { tier: 1, dates: [] } } }],
      },
    },
  });
  assert.equal(one.shadowRoot.querySelector(".badge-owner .muted").textContent, "1 badge");
  const none = players({}, { "sensor.achievements": { state: "0", attributes: {} } });
  assert.equal($(none, ".badges-section").hidden, true);
});

test("a player's gallery shows the badges earned and the next goals, and opens to all of them", () => {
  const ids = ["maximum", "hat_trick", "ton_plus", "ton_forty", "high_finish", "short_leg"];
  const gallery = {
    "sensor.achievements": {
      state: "1",
      attributes: {
        catalogue: ids.map((id) => ({ id, tiers: [10] })),
        players: [
          {
            name: "Alex",
            badges: { maximum: { tier: 1, dates: [] } },
            // The goals closest to being earned come first; one without progress last.
            progress: { hat_trick: 2, ton_plus: 9, ton_forty: 5, high_finish: 1 },
          },
        ],
      },
    },
  };
  const card = players({}, gallery);
  const shown = () => $$(card, ".badge").map((badge) => badge.dataset.badge);
  // Earned, then the three nearest goals, in the catalogue's order.
  assert.deepEqual(shown(), ["maximum", "hat_trick", "ton_plus", "ton_forty"]);
  const more = () => $(card, ".more-badges");
  assert.deepEqual([more().textContent, more().getAttribute("aria-expanded")], ["All 6 badges", "false"]);
  assert.equal(more().querySelectorAll(".cue.expand.inline").length, 1);
  click(card, ".more-badges");
  assert.deepEqual(shown(), ids);
  assert.deepEqual([more().textContent, more().getAttribute("aria-expanded")], ["Show fewer", "true"]);
  click(card, ".more-badges");
  assert.deepEqual(shown(), ["maximum", "hat_trick", "ton_plus", "ton_forty"]);
  // A tap beside the link changes nothing.
  click(card, ".badge-owner");
  assert.equal(shown().length, 4);
  // Without locked badges, only the earned ones show, and nothing opens.
  const earned = players({ show_locked: false }, gallery);
  assert.deepEqual($$(earned, ".badge").map((badge) => badge.dataset.badge), ["maximum"]);
  assert.equal($(earned, ".more-badges"), null);
});

test("trends show every active player's weeks with arrows", () => {
  const card = players({ trend_weeks: 4 });
  const section = $(card, ".trends-section");
  assert.equal(section.hidden, false);
  assert.equal(text(card, ".trends-meta"), "last 4 weeks");
  // Sam threw no darts in these weeks.
  assert.deepEqual(
    $$(card, ".trend-player .trend-name").map((name) => name.textContent),
    ["Alex"]
  );
  const tiles = $$(card, ".trend").map((tile) => [tile.dataset.metric, tile.querySelector(".trend-value").textContent]);
  assert.deepEqual(tiles, [
    ["average", "53.6 ↗"],
    ["first_9", "55.0 ↗"],
    ["checkout_rate", "27.8% ↗"],
    ["doubles_rate", "27.8% ↗"],
    ["darts", "210 ↗"],
  ]);
  assert.ok($(card, ".trend .spark polyline"));
  // Out-of-range weeks fall back to the limits.
  assert.equal(text(players({ trend_weeks: 40 }), ".trends-meta"), "last 12 weeks");
  assert.equal(text(players({ trend_weeks: "many" }), ".trends-meta"), "last 12 weeks");
  assert.equal(text(players({ trend_weeks: 1 }), ".trends-meta"), "last 4 weeks");
});

test("groupings show every player's beds in millimetres", () => {
  const card = players();
  assert.equal($(card, ".groups-section").hidden, false);
  assert.equal(text(card, ".groups-section .section-label"), "Grouping");
  assert.equal(text(card, ".group-player .trend-name"), "Alex");
  assert.equal(
    text(card, ".group-text"),
    "grouping 38 mm · 80 % within 61 mm · 6 mm left of center"
  );
  assert.match(text(card, ".groups-section p"), /^Half of the darts land within the grouping/);
});

test("badges, trends and groupings can be hidden, and hide without data", () => {
  const card = players({ show_badges: false, show_trends: false, show_spread: false });
  for (const name of ["badges", "trends", "groups"]) assert.equal($(card, `.${name}-section`), null);
  const empty = players({}, { "sensor.player_profiles": { state: "0", attributes: {} }, "sensor.achievements": { state: "0", attributes: {} } });
  for (const name of ["badges", "trends", "groups"]) assert.equal($(empty, `.${name}-section`).hidden, true);
});

test("the players card's progress speaks German", () => {
  const card = players({ trend_weeks: 8 }, {}, "de");
  assert.equal(text(card, ".badges-section .section-label"), "Abzeichen");
  assert.equal(text(card, ".trends-meta"), "letzte 8 Wochen");
  assert.equal(text(card, ".group-text"), "Streuung 38 mm · 80 % innerhalb 61 mm · 6 mm links der Mitte");
  assert.match(text(card, ".badge"), /180 · Bronze180er in X01: 103 von 10/);
});

const leaderboard = (config = {}, extra = {}, language = "en") => {
  const hass = withLanguage(makeHass({ states: { ...PROFILES, ...ACHIEVEMENTS, ...extra } }), language);
  return { hass, card: mount("autodarts-leaderboard-card", hass, config) };
};

test("the leaderboard card ranks the records of all players", () => {
  const { card } = leaderboard();
  assert.equal(text(card, ".title"), "Leaderboard");
  assert.equal(card.getCardSize(), 5);
  assert.equal($(card, ".empty").hidden, true);
  assert.deepEqual(
    $$(card, ".periods button").map((button) => [button.textContent, button.getAttribute("aria-pressed")]),
    [
      ["All time", "true"],
      ["Last 4 weeks", "false"],
      ["This week", "false"],
    ]
  );
  const records = $$(card, ".record").map((record) => [
    record.dataset.record,
    record.querySelector(".record-name").textContent,
    record.querySelector(".record-leader").textContent,
    [...record.querySelectorAll(".record-places li")].map((item) => item.textContent),
  ]);
  assert.deepEqual(records, [
    ["average", "Best average", "Alex62.5", ["2.Sam48.1"]],
    ["checkout", "Highest checkout", "Alex100", []],
    ["maximums", "Most 180s", "Alex3", []],
    ["best_501", "Fewest darts, 501", "Alex21 darts", []],
    ["streak", "Longest streak", "Alex4 days", []],
    ["achievements", "Most badges", "Alex2", []],
    ["darts", "Most darts", "Alex210", ["2.Sam90"]],
  ]);
});

test("the period switches between all time, four weeks and this week", () => {
  const { hass, card } = leaderboard({ period: "week", limit: 1 });
  assert.equal($(card, '[data-period="week"]').getAttribute("aria-pressed"), "true");
  assert.deepEqual(
    $$(card, ".record").map((record) => [record.dataset.record, record.querySelector(".record-leader").textContent]),
    [
      ["average", "Alex60.0"],
      ["checkout", "Alex100"],
      ["maximums", "Alex2"],
      ["best_501", "Alex21 darts"],
      ["achievements", "Alex2"],
      ["darts", "Alex120"],
    ]
  );
  assert.equal($$(card, ".record-places").length, 0);
  click(card, '[data-period="month"]');
  assert.equal($(card, '[data-period="month"]').getAttribute("aria-pressed"), "true");
  assert.equal(text(card, '[data-record="maximums"] .record-leader'), "Alex3");
  // Clicks beside the buttons and new states keep the chosen period.
  click(card, ".periods");
  card.hass = update(hass, { "sensor.achievements": { ...ACHIEVEMENTS["sensor.achievements"], state: "4" } });
  assert.equal($(card, '[data-period="month"]').getAttribute("aria-pressed"), "true");
  // A new configuration starts from its own period.
  card.setConfig({ type: "custom:autodarts-leaderboard-card", period: "all" });
  card.hass = hass;
  assert.equal($(card, '[data-period="all"]').getAttribute("aria-pressed"), "true");
});

test("the leaderboard waits for the first records, and its options apply", () => {
  const { card } = leaderboard({ show_period: false, title: "Hall of fame", period: "decade", limit: 9 }, {
    "sensor.player_profiles": { state: "0", attributes: { players: [] } },
  });
  assert.equal(text(card, ".title"), "Hall of fame");
  assert.equal($(card, ".periods"), null);
  assert.equal($(card, ".empty").hidden, false);
  assert.equal(text(card, ".empty"), "No records yet. Name the players of a practice game, and their legs make the leaderboard.");
  const wide = leaderboard({ limit: 9 }).card;
  assert.deepEqual(
    $$(wide, '[data-record="darts"] li').map((item) => item.textContent),
    ["2.Sam90"]
  );
  const fallback = leaderboard({ limit: "all" }).card;
  assert.equal($$(fallback, '[data-record="average"] li').length, 1);
});

test("the leaderboard speaks German", async () => {
  const { card } = leaderboard({}, {}, "de");
  await settle();
  assert.equal(text(card, ".title"), "Bestenliste");
  assert.deepEqual(
    $$(card, ".periods button").map((button) => button.textContent),
    ["Gesamt", "Letzte 4 Wochen", "Diese Woche"]
  );
  assert.equal(text(card, '[data-record="best_501"] .record-name'), "Wenigste Darts, 501");
  assert.equal(text(card, '[data-record="best_501"] .value'), "21 Darts");
  assert.equal(text(card, '[data-record="average"] .record-leader .value'), "62,5");
});
