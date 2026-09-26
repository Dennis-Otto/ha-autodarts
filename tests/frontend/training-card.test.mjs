// The training card in a browser DOM: session totals, heatmap, history and session controls.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, loadCards, makeHass, moreInfo, mount, settle, text, update, withLanguage } from "./dom.mjs";

const { bedPath } = await loadCards();

const STARTED = "2026-09-26T14:30:00+00:00";
const EVENTS = "event.dartboard_board_events";
const HITS = { T20: 3, S20: 6, S5: 2, D16: 1, BULL: 1, 25: 2, S1: 4, MISS: 5 };
const SESSION = {
  "sensor.training_darts": { state: "24", attributes: { hits: HITS } },
  "sensor.training_points": "446",
  "sensor.training_average": "55.75",
  "sensor.training_visits": "8",
  "sensor.training_highest_visit": "140",
  "sensor.training_scores_100": "3",
  "sensor.training_scores_140": "1",
  "sensor.training_scores_180": "0",
  "sensor.training_triples": "3",
  "sensor.training_doubles": "1",
  "sensor.training_bulls": "1",
  "sensor.training_misses": "5",
  "sensor.training_started": STARTED,
  "event.board_events": { state: "2026-09-26T14:29:00.000+00:00", attributes: { event_type: "session_started" } },
  "button.reset_training": "unknown",
  "switch.training_session": { state: "on", last_changed: STARTED },
  "sensor.training_streak": "3",
  "sensor.darts_today": { state: "60", attributes: { goal: 120, goal_reached: false, progress: 50 } },
};
const setup = (states = {}, config = {}, options = {}) => {
  const hass = makeHass({ states: { ...SESSION, ...states }, ...options });
  return { hass, card: mount("autodarts-training-card", hass, config) };
};
const visitRow = (time, score, segments = ["S20", "S20", "S20"]) => ({
  s: time,
  a: { event_type: "visit_completed", score, darts: segments.length, segments },
  lu: Date.parse(time) / 1000,
});
// The recorder's answer to history/history_during_period; requests are kept in `asked`.
const asked = [];
const history = (rows) => async (message) => {
  asked.push(message);
  return { [EVENTS]: rows };
};

test("the training card shows the session average, darts and visits", () => {
  const { card } = setup();
  assert.equal(text(card, ".title"), "Training · Dartboard");
  assert.match(text(card, ".since"), /^since 09\/26, 2:30\sPM$/);
  assert.equal(text(card, ".average"), "55.8");
  assert.equal(text(card, ".average-label"), "3-dart average");
  assert.equal(text(card, '[data-total="darts"]'), "24");
  assert.equal(text(card, '[data-total="visits"]'), "8");
  assert.equal($(card, ".empty-hint").hidden, true);
  assert.equal(text(setup({}, { title: "Practice room" }).card, ".title"), "Practice room");
  assert.equal(setup().card.getCardSize(), 9);
});

test("older integrations without average and daily darts still show the session", () => {
  const { "sensor.training_average": _, "sensor.darts_today": __, ...states } = SESSION;
  const hass = makeHass({ states });
  const card = mount("autodarts-training-card", hass);
  assert.equal(text(card, ".average"), "55.8");
  assert.deepEqual([$(card, ".daily").hidden, $(card, ".goal").hidden], [false, true]);
  assert.equal(text(card, ".streak"), "🔥 3 days in a row");
  card.hass = update(hass, { "sensor.training_darts": "0" });
  assert.equal(text(card, ".average"), "–");
});

test("an empty session invites the first dart, or a session start", () => {
  const { hass, card } = setup({ "sensor.training_darts": "0", "sensor.training_triples": "0" });
  assert.equal($(card, ".empty-hint").hidden, false);
  assert.equal(text(card, ".empty-hint"), "No darts in this session yet. Start throwing!");
  assert.equal(text(card, '[data-tile="triple_rate"] .value'), "–");
  card.hass = update(hass, { "switch.training_session": "off" });
  assert.equal(text(card, ".empty-hint"), "Start a session to count your darts.");
});

test("tiles show the session records and open the darts' more-info", () => {
  const { hass, card } = setup();
  assert.deepEqual(
    $$(card, ".tile").map((tile) => [tile.dataset.tile, tile.querySelector(".value").textContent]),
    [
      ["highest", "140"],
      ["scores_100", "3"],
      ["scores_140", "1"],
      ["max", "0"],
      ["triple_rate", "12.5%"],
      ["doubles", "1"],
      ["bulls", "1"],
      ["misses", "5"],
    ]
  );
  assert.equal($(card, '[data-tile="max"]').classList.contains("hot"), false);
  card.hass = update(hass, { "sensor.training_scores_180": "1" });
  assert.equal($(card, '[data-tile="max"]').classList.contains("hot"), true);
  const opened = moreInfo(card);
  $(card, '[data-tile="bulls"]').click();
  assert.deepEqual(opened, ["sensor.dartboard_training_darts"]);
});

test("the heatmap colours every hit bed from blue to red with its share", () => {
  const { card } = setup();
  const beds = $$(card, ".heat-bed");
  assert.equal(beds.length, 10);
  const byTitle = Object.fromEntries(beds.map((bed) => [bed.querySelector("title").textContent, bed]));
  assert.deepEqual(Object.keys(byTitle).sort(), [
    "25: 2 hits · 8.3%",
    "Bull: 1 hits · 4.2%",
    "D16: 1 hits · 4.2%",
    "S1: 4 hits · 16.7%",
    "S20: 6 hits · 25.0%",
    "S5: 2 hits · 8.3%",
    "T20: 3 hits · 12.5%",
  ]);
  const hottest = beds.find((bed) => bed.getAttribute("d") === bedPath("SI20"));
  assert.deepEqual(
    [hottest.getAttribute("fill"), hottest.getAttribute("fill-opacity")],
    ["hsl(0, 90%, 55%)", "0.95"]
  );
  const coldest = beds.find((bed) => bed.getAttribute("d") === bedPath("D16"));
  assert.deepEqual(
    [coldest.getAttribute("fill"), coldest.getAttribute("fill-opacity")],
    ["hsl(220, 90%, 55%)", "0.6"]
  );
  assert.equal(text(card, ".legend-max"), "6");
});

test("in numbers mode the heatmap sums every bed of a number", () => {
  const { card } = setup({}, { mode: "numbers" });
  const titles = $$(card, ".heat-bed title").map((title) => title.textContent);
  assert.equal(titles.length, 18);
  assert.equal(titles.filter((title) => title === "20: 9 hits · 37.5%").length, 4);
  assert.equal(titles.filter((title) => title === "Bull: 3 hits · 12.5%").length, 2);
  assert.equal(text(card, ".legend-max"), "9");
});

test("without hits the heatmap stays empty", () => {
  const { card } = setup({ "sensor.training_darts": { state: "0", attributes: { hits: {} } } });
  assert.equal($$(card, ".heat-bed").length, 0);
  assert.equal(text(card, ".legend-max"), "–");
  assert.equal(text(card, ".top"), "–");
});

test("the most hit beds are ranked with their share of all darts", () => {
  const { hass, card } = setup();
  assert.deepEqual(
    $$(card, ".top-row").map((row) => [
      row.querySelector(".key").textContent,
      row.querySelector(".fill").style.width,
      row.querySelector(".count").textContent,
    ]),
    [
      ["S20", "100%", "6× · 25%"],
      ["S1", "66.67%", "4× · 17%"],
      ["T20", "50%", "3× · 13%"],
      ["25", "33.33%", "2× · 8%"],
      ["S5", "33.33%", "2× · 8%"],
    ]
  );
  card.hass = update(hass, { "sensor.training_darts": { state: "0", attributes: { hits: { BULL: 2 } } } });
  assert.deepEqual(
    $$(card, ".top-row").map((row) => [row.querySelector(".key").textContent, row.querySelector(".count").textContent]),
    [["Bull", "2×"]]
  );
});

test("the streak and today's darts count towards the daily goal", () => {
  const { hass, card } = setup();
  assert.equal($(card, ".daily").hidden, false);
  assert.equal($(card, ".streak").hidden, false);
  assert.equal(text(card, ".streak"), "🔥 3 days in a row");
  assert.equal($(card, ".goal-bar").hidden, false);
  assert.equal($(card, ".goal-bar span").style.width, "50%");
  assert.equal($(card, ".goal").classList.contains("reached"), false);
  assert.equal(text(card, ".goal-text"), "60 / 120 darts today");

  card.hass = update(hass, {
    "sensor.training_streak": "1",
    "sensor.darts_today": { state: "150", attributes: { goal: 120, goal_reached: true } },
  });
  assert.equal(text(card, ".streak"), "🔥 1 day in a row");
  assert.equal($(card, ".goal-bar span").style.width, "100%");
  assert.equal($(card, ".goal").classList.contains("reached"), true);

  card.hass = update(hass, { "sensor.training_streak": "0", "sensor.darts_today": { state: "60", attributes: {} } });
  assert.equal($(card, ".streak").hidden, true);
  assert.equal($(card, ".goal-bar").hidden, true);
  assert.equal(text(card, ".goal-text"), "60 darts today");

  card.hass = update(hass, { "sensor.training_streak": "0", "sensor.darts_today": "unavailable" });
  assert.equal($(card, ".daily").hidden, true);
  assert.equal($(card, ".goal").hidden, true);
});

test("the history loads the visits of the session from the recorder", async (t) => {
  t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-09-26T15:00:00Z") });
  asked.length = 0;
  const rows = [
    visitRow("2026-09-26T14:29:59.000+00:00", 99),
    visitRow("2026-09-26T14:31:00.000+00:00", 60),
    { s: "2026-09-26T14:32:00.000+00:00", a: { event_type: "takeout_finished" } },
    visitRow("2026-09-26T14:33:00.000+00:00", 140, ["T20", "T20", "D10"]),
  ];
  const { card } = setup({}, {}, { callWS: history(rows) });
  assert.deepEqual(asked, [
    {
      type: "history/history_during_period",
      start_time: "2026-09-26T14:30:00.000Z",
      entity_ids: [EVENTS],
      minimal_response: false,
      no_attributes: false,
      significant_changes_only: false,
    },
  ]);
  assert.equal(text(card, ".history-chart"), "Completed visits appear here.");
  assert.equal($(card, ".history-chart").getAttribute("role"), null);
  await settle();
  const chart = $(card, ".history-chart");
  assert.equal(chart.getAttribute("role"), "img");
  assert.equal(chart.getAttribute("aria-label"), "Recent visits: 60, 140");
  const bars = $$(card, ".visit-bar");
  assert.equal(bars.length, 20);
  assert.equal($$(card, ".visit-bar.empty").length, 18);
  assert.deepEqual(
    bars.slice(0, 2).map((bar) => [bar.title, bar.textContent, bar.querySelector(".fill").getAttribute("style")]),
    [
      ["S20 · S20 · S20 = 60", "60", "--height:0.33;background:var(--ad-accent)"],
      ["T20 · T20 · D10 = 140", "140", "--height:0.78;background:#ff8c42"],
    ]
  );
  const line = $(card, ".average-line");
  assert.deepEqual([line.getAttribute("style"), line.title], ["--height:0.31", "3-dart average: 55.8"]);
});

test("an older session loads at most a week of history", async (t) => {
  t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-09-26T15:00:00Z") });
  asked.length = 0;
  setup({ "sensor.training_started": "2026-08-01T10:00:00+00:00" }, {}, { callWS: history([]) });
  setup({ "sensor.training_started": "unknown" }, {}, { callWS: history([]) });
  assert.deepEqual(
    asked.map((message) => message.start_time),
    ["2026-09-19T15:00:00.000Z", "2026-09-19T15:00:00.000Z"]
  );
});

test("completed visits of the open dashboard are added once each", async () => {
  const rows = [visitRow("2026-09-26T14:31:00.000+00:00", 60)];
  const { hass, card } = setup({}, {}, { callWS: history(rows) });
  await settle();
  // Visits without segments show their score alone.
  const visit = { state: "2026-09-26T14:35:00.000+00:00", attributes: { event_type: "visit_completed", score: 26 } };
  const next = update(hass, { "event.board_events": visit });
  card.hass = next;
  card.hass = update(next, { "sensor.training_visits": "9" });
  assert.equal($(card, ".history-chart").getAttribute("aria-label"), "Recent visits: 60, 26");
  assert.deepEqual(
    $$(card, ".visit-bar:not(.empty)").map((bar) => bar.title),
    ["S20 · S20 · S20 = 60", "26"]
  );
});

test("a new session starts an empty history and ignores late results of the old one", async () => {
  const pending = [];
  const callWS = (message) => new Promise((resolve) => pending.push({ message, resolve }));
  const { hass, card } = setup({}, {}, { callWS });
  card.hass = update(hass, {
    "sensor.training_started": "2026-09-26T16:00:00+00:00",
    "sensor.training_visits": "0",
  });
  assert.equal(pending.length, 2);
  pending[0].resolve({ [EVENTS]: [visitRow("2026-09-26T16:01:00.000+00:00", 180)] });
  await settle();
  assert.equal(text(card, ".history-chart"), "Completed visits appear here.");
  pending[1].resolve({ [EVENTS]: [visitRow("2026-09-26T16:02:00.000+00:00", 45)] });
  await settle();
  assert.equal($(card, ".history-chart").getAttribute("aria-label"), "Recent visits: 45");
});

test("without a recorder the history still waits for visits", async () => {
  const failing = setup({}, {}, { callWS: () => Promise.reject(new Error("recorder disabled")) }).card;
  await settle();
  assert.equal(text(failing, ".history-chart"), "Completed visits appear here.");
  const offline = setup().card;
  await settle();
  assert.equal(text(offline, ".history-chart"), "Completed visits appear here.");
  const { "event.board_events": _, ...states } = SESSION;
  let asked = false;
  const noEvents = mount("autodarts-training-card", makeHass({ states, callWS: async () => (asked = true) }));
  await settle();
  assert.equal(asked, false);
  assert.equal(text(noEvents, ".history-chart"), "Completed visits appear here.");
});

test("the history size keeps between five and sixty visits, with labels up to thirty", async () => {
  const rows = [60, 45, 100, 26, 140, 81, 180].map((score, index) =>
    visitRow(`2026-09-26T14:4${index}:00.000+00:00`, score)
  );
  const small = setup({}, { history_size: 2 }, { callWS: history(rows) }).card;
  await settle();
  assert.equal($$(small, ".visit-bar").length, 5);
  assert.equal($(small, ".history-chart").getAttribute("aria-label"), "Recent visits: 100, 26, 140, 81, 180");
  const large = setup({}, { history_size: 100 }, { callWS: history(rows) }).card;
  await settle();
  assert.equal($$(large, ".visit-bar").length, 60);
  assert.equal($$(large, ".visit-bar .label").length, 0);
  const invalid = setup(
    { "sensor.training_average": "unknown" },
    { history_size: "many" },
    { callWS: history(rows) }
  ).card;
  await settle();
  assert.equal($$(invalid, ".visit-bar").length, 20);
  assert.equal($$(invalid, ".visit-bar .label").length, 7);
  assert.equal($(invalid, ".average-line"), null);
});

test("past sessions list when they ended, how long they took and how they went", () => {
  const sessions = [
    { ended: "2026-09-25T20:00:00+00:00", duration_minutes: 42, darts: 150, average: 48.2, highest_visit: 100 },
    { ended: "2026-09-24T19:00:00+00:00", duration_minutes: 0.5, darts: 9, average: 30, highest_visit: 45 },
    { ended: "2026-09-23T18:00:00+00:00", duration_minutes: null, darts: 3, average: null, highest_visit: null },
    { ended: "not a date", darts: 3 },
  ];
  const { hass, card } = setup({ "sensor.training_last_session": { state: "48.2", attributes: { sessions } } });
  assert.equal($(card, ".sessions").hidden, false);
  const rows = $$(card, ".session-table tbody tr").map((row) =>
    [...row.children].map((cell) => cell.textContent.replace(/\s/g, " "))
  );
  assert.deepEqual(rows, [
    ["09/25, 8:00 PM", "42 min", "150", "48.2", "100"],
    ["09/24, 7:00 PM", "<1 min", "9", "30.0", "45"],
    ["09/23, 6:00 PM", "–", "3", "–", "–"],
  ]);
  card.hass = update(hass, { "sensor.training_last_session": { state: "unknown", attributes: { sessions: [] } } });
  assert.equal($(card, ".sessions").hidden, true);
});

test("the session state tells whether a session runs or when it ended", () => {
  const { hass, card } = setup();
  assert.equal(text(card, ".session-state"), "Session running");
  card.hass = update(hass, { "switch.training_session": { state: "off", last_changed: "2026-09-26T15:10:00+00:00" } });
  assert.match(text(card, ".session-state"), /^Session ended 09\/26, 3:10\sPM$/);
  card.hass = update(hass, { "switch.training_session": "off" });
  assert.equal(text(card, ".session-state"), "No session running");
  const { "switch.training_session": _, ...states } = SESSION;
  const lean = mount("autodarts-training-card", makeHass({ states }));
  assert.equal(text(lean, ".session-state"), "");
  assert.equal($(lean, '[data-action="session"]').hidden, true);
});

test("a new session and the end of a session need a second tap; a start does not", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const { hass, card } = setup();
  const reset = $(card, '[data-action="new_session"]');
  const toggle = $(card, '[data-action="session"]');
  assert.deepEqual(
    [toggle.hidden, toggle.textContent, toggle.classList.contains("primary")],
    [false, "End session", false]
  );

  reset.click();
  assert.deepEqual([reset.textContent, reset.classList.contains("confirm")], ["Confirm?", true]);
  t.mock.timers.tick(4000);
  assert.deepEqual([reset.textContent, reset.classList.contains("confirm")], ["New session", false]);
  reset.click();
  reset.click();
  assert.deepEqual(hass.calls, [["button", "press", { entity_id: "button.dartboard_reset_training" }]]);

  toggle.click();
  assert.deepEqual([toggle.textContent, toggle.classList.contains("confirm")], ["Confirm?", true]);
  toggle.click();
  assert.deepEqual(hass.calls.at(-1), ["switch", "turn_off", { entity_id: "switch.dartboard_training_session" }]);

  card.hass = update(hass, { "switch.training_session": "off" });
  assert.deepEqual([toggle.textContent, toggle.classList.contains("primary")], ["Start session", true]);
  toggle.click();
  assert.deepEqual(hass.calls.at(-1), ["switch", "turn_on", { entity_id: "switch.dartboard_training_session" }]);
  assert.equal(hass.calls.length, 3);
});

test("session controls ignore taps in the preview and without their entities", () => {
  const { hass, card } = setup();
  card.preview = true;
  for (const action of ["new_session", "new_session", "session", "session"]) {
    $(card, `[data-action="${action}"]`).click();
  }
  assert.deepEqual(hass.calls, []);
  assert.equal(text(card, '[data-action="new_session"]'), "New session");

  const { "switch.training_session": _, "button.reset_training": __, ...states } = SESSION;
  const bare = makeHass({ states });
  const lean = mount("autodarts-training-card", bare);
  assert.equal($(lean, '[data-action="new_session"]').disabled, true);
  $(lean, '[data-action="session"]').click();
  assert.deepEqual(bare.calls, []);
});

test("heatmap, statistics, top list, history, sessions and controls can be hidden", () => {
  const heatOnly = setup({}, { show_stats: false, show_top: false }).card;
  assert.equal($(heatOnly, ".body").getAttribute("class"), "body single");
  assert.equal($(heatOnly, ".side"), null);
  const sideOnly = setup({}, { show_heatmap: false }).card;
  assert.equal($(sideOnly, ".body").getAttribute("class"), "body single");
  assert.equal($(sideOnly, ".heat"), null);
  assert.equal($$(sideOnly, ".tile").length, 8);
  const topOnly = setup({}, { show_heatmap: false, show_stats: false }).card;
  assert.equal($(topOnly, ".tiles"), null);
  assert.equal($$(topOnly, ".top-row").length, 5);
  const statsOnly = setup({}, { show_heatmap: false, show_top: false }).card;
  assert.equal($(statsOnly, ".top"), null);
  const minimal = setup(
    { "sensor.training_last_session": { state: "40", attributes: { sessions: [] } } },
    {
      show_heatmap: false,
      show_stats: false,
      show_top: false,
      show_history: false,
      show_sessions: false,
      show_reset: false,
    }
  ).card;
  for (const selector of [".body", ".history", ".sessions", ".footer-row"]) assert.equal($(minimal, selector), null);
  assert.equal(text(minimal, ".average"), "55.8");
  assert.equal($(setup().card, ".body").getAttribute("class"), "body");
});

test("the training card speaks German", () => {
  const { card } = setup({}, {}, { language: "de" });
  assert.equal(text(card, ".title"), "Training · Dartboard");
  assert.equal(text(card, ".since"), "seit 26.09., 14:30");
  assert.equal(text(card, ".average"), "55,8");
  assert.equal(text(card, ".average-label"), "3-Dart-Average");
  assert.equal(text(card, '[data-tile="triple_rate"] .value'), "12,5 %");
  assert.equal(text(card, ".streak"), "🔥 3 Tage in Folge");
  assert.equal(text(card, ".goal-text"), "60 / 120 Darts heute");
  assert.equal(text(card, ".session-state"), "Session läuft");
  assert.equal(text(card, '[data-action="session"]'), "Session beenden");
  assert.equal($(card, ".heat-bed title").textContent.includes("Treffer"), true);
  card.hass = withLanguage(makeHass({ states: SESSION }), "en");
  assert.equal(text(card, ".average"), "55.8");
  // Without a locale, Home Assistant's language decides.
  const ended = { ...SESSION, "switch.training_session": { state: "off", last_changed: "2026-09-26T15:10:00+00:00" } };
  const legacy = mount("autodarts-training-card", {
    ...makeHass({ states: ended }),
    locale: undefined,
    language: "de",
  });
  assert.equal(text(legacy, ".session-state"), "Session beendet 26.09., 15:10");
});

const BESTS = {
  "sensor.personal_best": {
    state: "2026-09-20T18:00:00+00:00",
    attributes: {
      record: "highest_checkout",
      value: 121,
      previous: 100,
      name: "Alex",
      highest_visit: 140,
      highest_checkout: 121,
      fewest_darts_501: 18,
      fewest_darts_301: 12,
      fewest_darts_x: 3,
      best_cricket_mpr: 3.125,
      best_session_average: 58.44,
      around_the_clock: 38,
      doubles: 0,
      bobs_27: 412,
    },
  },
  "sensor.training_streak": { state: "3", attributes: { best_streak: 12 } },
};
const bests = (card) => $$(card, ".bests dl > div").map((row) => [row.firstChild.textContent, row.lastChild.textContent]);

test("personal bests list every record with a value and the longest streak", () => {
  const { hass, card } = setup(BESTS);
  assert.equal($(card, ".bests").hidden, false);
  assert.equal(text(card, ".bests .section-label"), "Personal bests");
  assert.deepEqual(bests(card), [
    ["Highest visit", "140"],
    ["Highest checkout", "121"],
    ["Best 301", "12 darts"],
    ["Best 501", "18 darts"],
    ["Best Cricket MPR", "3.13"],
    ["Best session average", "58.4"],
    ["Around the Clock", "38 darts"],
    ["Bob's 27", "412 points"],
    ["Longest streak", "12 days"],
  ]);
  card.hass = update(hass, { "sensor.training_streak": { state: "1", attributes: { best_streak: 1 } } });
  assert.deepEqual(bests(card).at(-1), ["Longest streak", "1 day"]);
  // Without records the section waits for the first one.
  card.hass = update(hass, { "sensor.personal_best": "unknown", "sensor.training_streak": "0" });
  assert.equal($(card, ".bests").hidden, true);
  assert.equal($(setup(BESTS, { show_bests: false }).card, ".bests"), null);
  const german = setup(BESTS, {}, { language: "de" }).card;
  assert.equal(text(german, ".bests .section-label"), "Bestleistungen");
  assert.deepEqual(bests(german).slice(2, 5), [
    ["Bestes 301-Leg", "12 Darts"],
    ["Bestes 501-Leg", "18 Darts"],
    ["Beste MPR im Cricket", "3,13"],
  ]);
  assert.deepEqual(bests(german).at(-1), ["Längste Serie", "12 Tage"]);
});

test("the statistics tiles are a button for the keyboard too", () => {
  const { card } = setup();
  const tiles = $(card, ".tiles");
  assert.deepEqual(
    [tiles.getAttribute("role"), tiles.getAttribute("tabindex"), tiles.getAttribute("aria-label")],
    ["button", "0", "Training statistics, open the details"]
  );
  const opened = moreInfo(card);
  for (const key of ["Enter", " ", "Tab"]) {
    tiles.dispatchEvent(new window.KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
  }
  assert.deepEqual(opened, ["sensor.dartboard_training_darts", "sensor.dartboard_training_darts"]);
  // The fire emoji is decoration only.
  assert.equal($(card, ".streak [aria-hidden]").textContent, "🔥");
});

test("board events other than visits and session starts leave the card alone", () => {
  const { hass, card } = setup();
  $(card, ".title").textContent = "stale";
  const event = (type) => ({ state: new Date().toISOString(), attributes: { event_type: type } });
  let next = update(hass, { "event.board_events": event("takeout_finished") });
  card.hass = next;
  assert.equal(text(card, ".title"), "stale");
  next = update(next, { "event.board_events": { ...event("visit_completed"), attributes: { event_type: "visit_completed", score: 60, darts: 3, segments: ["S20", "S20", "S20"] } } });
  card.hass = next;
  assert.equal(text(card, ".title"), "Training · Dartboard");
});

test("numbers, times and time zones follow the user profile", () => {
  const ended = { ...SESSION, "switch.training_session": { state: "off", last_changed: "2026-09-26T15:10:00+00:00" } };
  const profile = (locale, config) => {
    const hass = makeHass({ states: ended });
    return mount("autodarts-training-card", { ...hass, locale: { ...hass.locale, ...locale }, config });
  };
  // English words with German numbers and a 24-hour clock in the server's time zone.
  const card = profile(
    { number_format: "decimal_comma", time_format: "24", time_zone: "server" },
    { time_zone: "Europe/Berlin" }
  );
  assert.equal(text(card, ".average"), "55,8");
  assert.equal(text(card, ".session-state"), "Session ended 09/26, 17:10");
  // The browser's time zone, a 12-hour clock and no grouping.
  const local = profile({ number_format: "none", time_format: "12", time_zone: "local" }, { time_zone: "Europe/Berlin" });
  assert.match(text(local, ".session-state"), /^Session ended 09\/26, 3:10\sPM$/);
  assert.equal(text(profile({ number_format: "space_comma" }), ".average"), "55,8");
  const system = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(55.75);
  assert.equal(text(profile({ number_format: "system", time_format: "system" }), ".average"), system);
  assert.equal(text(profile({ number_format: "quote_decimal" }), ".average"), "55.8");
});
