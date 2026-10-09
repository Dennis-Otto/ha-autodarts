// The score of a visit on the keypad: the fewest darts of a checkout, what a score says,
// the questions after it, and the score view of the scoreboard and the live card.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, READY, loadCards, makeHass, mount, text, update, withLanguage } from "./dom.mjs";

const { checkoutDarts, scoreAnswer, scoreEntry, scoreHint, gameView } = await loadCards();

const T = (key) => ({ checkout: "Checkout", bust: "Bust", setup_leave: "leaves {leave}" })[key] ?? key;
const ENTRY = "01JSCORE";
const practice = (remaining, attributes = {}) => ({
  "sensor.practice_remaining": {
    state: String(remaining),
    attributes: {
      game: 501,
      player: 1,
      name: "Alex",
      visit_from: remaining,
      scores: [{ player: 1, name: "Alex", remaining, legs: 0, sets: 0, average: null }],
      ...attributes,
    },
  },
});
const visit = (...throws) => ({
  "sensor.local_visit_score": {
    state: String(throws.reduce((sum, dart) => sum + dart.number * dart.multiplier, 0)),
    attributes: { throws },
  },
});
const board = (states = {}, options = {}) =>
  makeHass({
    states: { "sensor.local_status": "manual", ...practice(501), ...visit(), ...states },
    device: { primary_config_entry: ENTRY },
    ...options,
  });
const actions = (hass) =>
  hass.calls.filter(([domain]) => domain === "autodarts").map(([, service, data]) => [service, data]);
const tap = (card, selector) => $(card, selector).click();
const type = (card, digits) => {
  for (const digit of digits) tap(card, `.pad-score [data-pad="digit"][data-value="${digit}"]`);
};

// -- helpers ---------------------------------------------------------------------------

test("the fewest darts of a checkout follow the doubles", () => {
  assert.equal(checkoutDarts(40, true), 1);
  assert.equal(checkoutDarts(50, true), 1);
  assert.equal(checkoutDarts(41, true), 2);
  assert.equal(checkoutDarts(100, true), 2);
  assert.equal(checkoutDarts(170, true), 3);
  for (const bogey of [159, 162, 163, 165, 166, 168, 169, 171, 1]) assert.equal(checkoutDarts(bogey, true), null, bogey);
  // Without double out, any bed ends the leg.
  assert.equal(checkoutDarts(57, false), 1);
  assert.equal(checkoutDarts(180, false), 3);
  assert.equal(checkoutDarts(179, false), null);
});

test("the score view is there in an X01 leg being played", () => {
  const view = (states) => gameView((name) => ({ practice: states["sensor.practice_remaining"] })[name]);
  assert.deepEqual(scoreEntry(view(practice(321, { remaining: 300, visit_from: 361 }))), { from: 361, doubleOut: true });
  // Without the visit's start, its remaining score.
  assert.deepEqual(scoreEntry(view({ "sensor.practice_remaining": { state: "40", attributes: { game: 501, double_out: false } } })), {
    from: 40,
    doubleOut: false,
  });
  assert.equal(scoreEntry(view(practice(0, { winner: 1 }))), null);
  assert.equal(scoreEntry({ mode: "cricket" }), null);
  assert.equal(scoreEntry({ mode: "idle" }), null);
});

test("a score says what it leaves, a checkout or a bust", () => {
  const entry = { from: 40, doubleOut: true };
  assert.equal(scoreHint(entry, 40, T), "Checkout");
  assert.equal(scoreHint(entry, 20, T), "leaves 20");
  assert.equal(scoreHint(entry, 39, T), "Bust");
  assert.equal(scoreHint(entry, 60, T), "Bust");
  // No dart finishes 159, so scoring it busts.
  assert.equal(scoreHint({ from: 159, doubleOut: true }, 159, T), "Bust");
  assert.equal(scoreHint({ from: 40, doubleOut: false }, 39, T), "leaves 1");
});

test("a score asks for the darts of a checkout and the darts at a double where they can differ", () => {
  const entry = { from: 100, doubleOut: true };
  assert.deepEqual(scoreAnswer(entry, 100), { ask: "darts", choices: [2, 3] });
  assert.deepEqual(scoreAnswer(entry, 100, { darts: 2 }), { ask: "doubles", choices: [1, 2] });
  assert.deepEqual(scoreAnswer(entry, 100, { darts: 3, doubles: 2 }), {
    data: { score: 100, darts: 3, darts_at_double: 2 },
  });
  // A checkout of three darts asks only for the darts at a double, one of one dart for nothing.
  assert.deepEqual(scoreAnswer({ from: 170, doubleOut: true }, 170), { ask: "doubles", choices: [1, 2, 3] });
  assert.deepEqual(scoreAnswer({ from: 40, doubleOut: true }, 40, { darts: 1 }), {
    data: { score: 40, darts: 1, darts_at_double: 1 },
  });
  // Without double out, a checkout asks for its darts only.
  assert.deepEqual(scoreAnswer({ from: 60, doubleOut: false }, 60, { darts: 1 }), { data: { score: 60, darts: 1 } });
  assert.deepEqual(scoreAnswer({ from: 180, doubleOut: false }, 180), { data: { score: 180, darts: 3 } });
  // A visit that left a double in reach asks for the darts at it, others for nothing.
  assert.deepEqual(scoreAnswer({ from: 60, doubleOut: true }, 20), { ask: "doubles", choices: [0, 1, 2, 3] });
  assert.deepEqual(scoreAnswer({ from: 60, doubleOut: true }, 20, { doubles: 2 }), {
    data: { score: 20, darts_at_double: 2 },
  });
  assert.deepEqual(scoreAnswer({ from: 501, doubleOut: true }, 140), { data: { score: 140 } });
  assert.deepEqual(scoreAnswer({ from: 40, doubleOut: false }, 20), { data: { score: 20 } });
  // A score that is no checkout, such as 159 from 159, goes in as it is.
  assert.deepEqual(scoreAnswer({ from: 159, doubleOut: true }, 159), { data: { score: 159 } });
});

// -- the scoreboard ---------------------------------------------------------------------

test("the scoreboard's keypad takes the score of a visit", () => {
  const hass = board();
  const card = mount("autodarts-scoreboard-card", hass);
  assert.deepEqual(
    $$(card, ".pad .segmented button").map((button) => button.textContent),
    ["Keys", "Board", "Score"]
  );
  tap(card, '.pad [data-pad="score"]');
  assert.equal(text(card, ".pad .section-label"), "Enter the visit's score");
  assert.equal($(card, '.pad [data-pad="score"]').getAttribute("aria-pressed"), "true");
  assert.equal($(card, ".pad-numbers"), null);
  assert.equal($(card, '.pad [data-value="BULL"]'), null);
  // The next player keeps its place below the digits, as below the keys.
  assert.equal(text(card, '.pad [data-pad="next"]'), "Next player");
  assert.equal(text(card, ".score-line"), "–");
  assert.equal($(card, '[data-pad="enter"]').disabled, true);
  assert.equal($(card, '[data-pad="erase"]').disabled, true);
  type(card, "1405");
  // Nothing beyond 180 goes in.
  assert.equal(text(card, ".score-line .typed"), "140");
  assert.equal(text(card, ".score-line .muted"), "leaves 361");
  tap(card, '[data-pad="erase"]');
  type(card, "0");
  tap(card, '[data-pad="enter"]');
  assert.deepEqual(actions(hass), [["enter_visit", { config_entry_id: ENTRY, score: 140 }]]);
  // The view stays for the next visit, with nothing typed.
  assert.equal(text(card, ".score-line"), "–");
  // A leading zero gives way to the next digit.
  type(card, "05");
  assert.equal(text(card, ".score-line .typed"), "5");
  // Back to the keys.
  tap(card, '.pad [data-pad="keys"]');
  assert.ok($(card, ".pad-numbers"));
});

test("a checkout asks for its darts and the darts at a double, and Cancel goes back to the score", () => {
  const hass = board(practice(100));
  const card = mount("autodarts-scoreboard-card", hass);
  tap(card, '.pad [data-pad="score"]');
  type(card, "100");
  assert.equal(text(card, ".score-line .muted"), "Checkout");
  tap(card, '[data-pad="enter"]');
  assert.equal(text(card, ".score-line.ask"), "Darts for the checkout");
  assert.deepEqual(
    $$(card, '[data-pad="answer"]').map((button) => button.textContent),
    ["2", "3"]
  );
  // Cancel keeps the score to change it.
  tap(card, ".ask-cancel");
  assert.equal(text(card, ".score-line .typed"), "100");
  assert.ok($(card, '[data-pad="enter"]'));
  tap(card, '[data-pad="enter"]');
  tap(card, '[data-pad="answer"][data-value="2"]');
  assert.equal(text(card, ".score-line.ask"), "Darts at a double");
  tap(card, '[data-pad="answer"][data-value="2"]');
  assert.deepEqual(actions(hass), [
    ["enter_visit", { config_entry_id: ENTRY, score: 100, darts: 2, darts_at_double: 2 }],
  ]);
  // A visit that leaves a double in reach asks for the darts at it.
  card.hass = update(hass, practice(60));
  type(card, "20");
  tap(card, '[data-pad="enter"]');
  assert.deepEqual(
    $$(card, '[data-pad="answer"]').map((button) => button.textContent),
    ["0", "1", "2", "3"]
  );
  tap(card, '[data-pad="answer"][data-value="0"]');
  assert.deepEqual(actions(hass).at(-1), ["enter_visit", { config_entry_id: ENTRY, score: 20, darts_at_double: 0 }]);
});

test("a keyboard types the score", () => {
  const hass = board();
  const card = mount("autodarts-scoreboard-card", hass);
  const key = (name, target = $(card, ".pad-area")) =>
    target.dispatchEvent(new window.KeyboardEvent("keydown", { key: name, bubbles: true }));
  // The keys view takes no digits.
  key("6");
  tap(card, '.pad [data-pad="score"]');
  for (const name of ["6", "0", "x", "Backspace", "0"]) key(name);
  assert.equal(text(card, ".score-line .typed"), "60");
  // Enter on a key of the pad presses that key, not the score.
  key("Enter", $(card, '[data-pad="digit"][data-value="1"]'));
  assert.deepEqual(actions(hass), []);
  key("Enter");
  assert.deepEqual(actions(hass), [["enter_visit", { config_entry_id: ENTRY, score: 60 }]]);
  card.hass = update(hass, practice(32));
  key("0");
  key("Enter");
  assert.ok($(card, '[data-pad="answer"]'));
  key("Escape");
  assert.equal($(card, '[data-pad="answer"]'), null);
  assert.equal(text(card, ".score-line .typed"), "0");
});

test("the score view leaves with an X01 leg, waits for the bot and speaks German", () => {
  const hass = board();
  const card = mount("autodarts-scoreboard-card", hass);
  tap(card, '.pad [data-pad="score"]');
  type(card, "1");
  // In Cricket, the keys come back, and no score goes in.
  card.hass = update(hass, {
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: { game: "cricket", player: 1, scores: [{ player: 1, name: "Alex", marks: [0, 0, 0, 0, 0, 0, 0], points: 0 }] },
    },
  });
  assert.ok($(card, ".pad-numbers"));
  assert.equal($(card, '.pad [data-pad="score"]'), null);
  card._padAction("enter");
  assert.deepEqual(actions(hass), []);
  // While the bot throws, the digits wait too.
  card.hass = update(hass, practice(501, { player: 2, bot: { player: 2, level: 60 }, scores: [{ player: 2, remaining: 501, bot: true }] }));
  assert.ok($(card, ".pad-score"));
  assert.ok($$(card, ".pad-score button").every((button) => button.disabled));
  const german = mount("autodarts-scoreboard-card", withLanguage(board(), "de"));
  tap(german, '.pad [data-pad="score"]');
  assert.equal(text(german, ".pad .section-label"), "Punkte der Aufnahme");
  assert.equal(text(german, '[data-pad="enter"]'), "OK");
  assert.equal($(german, '[data-pad="erase"]').getAttribute("aria-label"), "Letzte Ziffer löschen");
});

// -- the live card ----------------------------------------------------------------------

test("the live card's keypad takes the score of a visit too", () => {
  const hass = board(practice(40));
  const card = mount("autodarts-card", hass);
  tap(card, '.pad [data-pad="score"]');
  type(card, "40");
  tap(card, '[data-pad="enter"]');
  tap(card, '[data-pad="answer"][data-value="1"]');
  assert.deepEqual(actions(hass), [["enter_visit", { config_entry_id: ENTRY, score: 40, darts: 1, darts_at_double: 1 }]]);
  // A board without a config entry sends the action without one.
  const alone = mount("autodarts-card", makeHass({ states: { "sensor.local_status": "manual", ...practice(501), ...visit() } }));
  tap(alone, '.pad [data-pad="score"]');
  type(alone, "26");
  tap(alone, '[data-pad="enter"]');
  assert.deepEqual(alone._hass.calls.at(-1), ["autodarts", "enter_visit", { score: 26 }]);
  // With Autodarts and the keypad off, there is no score view.
  assert.equal($(mount("autodarts-card", makeHass({ states: { ...READY, ...practice(501), ...visit() } })), ".pad-score"), null);
});

test("the darts of a visit entered as its score show their points, light no bed and leave the last visit its score", () => {
  const total = (points, extra = {}) => ({ number: points / 3, multiplier: 3, segment: "x", total: true, manual: true, ...extra });
  const darts = visit(total(60, { dart: 1 }), total(60, { dart: 2 }), { number: 20, multiplier: 1, segment: "S20", dart: 3, manual: true, total: true });
  const hass = board({
    ...darts,
    "sensor.local_visit_score": {
      ...darts["sensor.local_visit_score"],
      attributes: {
        ...darts["sensor.local_visit_score"].attributes,
        recent_visits: [
          { score: 140, segments: [], total: true },
          { score: 60, segments: ["T20", "MISS", "MISS"] },
        ],
      },
    },
  });
  const card = mount("autodarts-card", hass);
  assert.deepEqual(
    $$(card, ".slot .segment").map((segment) => segment.textContent),
    ["60", "60", "20"]
  );
  assert.ok($$(card, ".slot").every((slot) => slot.classList.contains("total")));
  assert.equal($(card, ".hits").innerHTML, "");
  assert.deepEqual(
    $$(card, ".recent-visit").map((item) => item.title),
    ["140", "T20 · MISS · MISS = 60"]
  );
  const scoreboard = mount("autodarts-scoreboard-card", hass);
  assert.deepEqual(
    $$(scoreboard, ".visit .dart .segment").map((segment) => segment.textContent),
    ["60", "60", "20"]
  );
});
