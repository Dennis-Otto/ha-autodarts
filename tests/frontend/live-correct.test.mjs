// Correcting a dart on the live card: a tap on a dart of the visit opens the same pad as
// on the scoreboard, with its keys, its board, the loupe and the zoom.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, READY, loadCards, makeHass, mount, text, update, window } from "./dom.mjs";

await loadCards();

const ENTRY = "01JENTRY";
const dart = (number, multiplier, extra = {}) => ({ number, multiplier, segment: "x", ...extra });
const visit = (...throws) => ({
  "sensor.local_visit_score": {
    state: String(throws.reduce((sum, item) => sum + item.number * item.multiplier, 0)),
    attributes: { throws, recent_visits: [] },
  },
});
const THROWS = [dart(20, 3, { dart: 1, x: 0.02, y: 0.62 }), dart(20, 1, { dart: 2, x: 0.02, y: 0.8 })];
const setup = (states = {}, config = {}, options = {}) => {
  const hass = makeHass({
    states: { ...READY, ...visit(...THROWS), ...states },
    device: { primary_config_entry: ENTRY },
    ...options,
  });
  return { hass, card: mount("autodarts-card", hass, config) };
};
const actions = (hass) =>
  hass.calls.filter(([domain]) => domain === "autodarts").map(([, service, data]) => [service, data]);
const slots = (card) =>
  $$(card, ".slot").map((slot) => [slot.tagName.toLowerCase(), slot.className, Boolean(slot.querySelector(".cue.edit"))]);
// A board laid out as a square of 460 pixels at (100, 50): a pixel is a millimetre.
const laidOut = (element) => {
  element.getBoundingClientRect = () => ({ left: 100, top: 50, width: 460, height: 460 });
  return element;
};
const touch = (element, type, pointerId, clientX, clientY) =>
  element.dispatchEvent(
    new window.PointerEvent(type, { bubbles: true, cancelable: true, pointerId, pointerType: "touch", clientX, clientY })
  );

test("the darts of the visit on the live card correct with a tap, and show a pencil for it", () => {
  const { hass, card } = setup();
  // Two darts of the visit are buttons with a pencil; the third slot is still empty.
  assert.deepEqual(slots(card), [
    ["button", "slot triple tappable", true],
    ["button", "slot single latest tappable", true],
    ["div", "slot empty", false],
  ]);
  const second = $(card, '.slot[data-dart="2"]');
  assert.equal(second.getAttribute("aria-label"), "S20 20 – Correct dart 2");
  assert.equal($(card, ".pad-area").hidden, true);
  // A tap opens the pad for that dart, with its multiplier chosen.
  second.click();
  assert.equal($(card, ".pad-area").hidden, false);
  assert.equal(text(card, ".pad .section-label"), "Correct dart 2");
  assert.equal($(card, '.slot[data-dart="2"]').className, "slot single latest picked tappable");
  assert.equal($(card, '[data-pad="multiplier"][aria-pressed="true"]').dataset.value, "1");
  // T and 20 put the dart in the treble, and the pad closes.
  $(card, '[data-pad="multiplier"][data-value="3"]').click();
  $(card, '[data-pad="bed"][data-value="T20"]').click();
  assert.deepEqual(actions(hass), [["correct_dart", { config_entry_id: ENTRY, dart: 2, segment: "T20" }]]);
  assert.equal($(card, ".pad-area").hidden, true);
  // A second tap on the dart, or Cancel, closes the pad without a correction.
  $(card, '.slot[data-dart="1"]').click();
  $(card, '.slot[data-dart="1"]').click();
  assert.equal($(card, ".pad-area").hidden, true);
  $(card, '.slot[data-dart="1"]').click();
  $(card, '[data-pad="cancel"]').click();
  assert.equal($(card, ".pad-area").hidden, true);
  assert.equal(actions(hass).length, 1);
});

test("on the live card the dart goes where a tap or a finger on the pad's board puts it", () => {
  const { hass, card } = setup();
  $(card, '.slot[data-dart="2"]').click();
  $(card, '[data-pad="board"]').click();
  const board = laidOut($(card, ".pad-board"));
  // The dashed ring shows where the board saw the dart; a tap in the middle is the bull.
  assert.equal($$(card, ".pad-board .spot.seen").length, 1);
  board.dispatchEvent(new window.MouseEvent("click", { bubbles: true, clientX: 330, clientY: 280 }));
  assert.deepEqual(actions(hass), [["correct_dart", { config_entry_id: ENTRY, dart: 2, x: 0, y: 0 }]]);
  // A finger shows the loupe in the card and sets the dart where it lets go.
  $(card, '.slot[data-dart="1"]').click();
  const again = laidOut($(card, ".pad-board"));
  $(card, ".layout").getBoundingClientRect = () => ({ left: 0, top: 0, width: 900, height: 700 });
  touch(again, "pointerdown", 1, 330, 280 - 102);
  assert.equal($(card, ".loupe").hidden, false);
  // New states leave the pad as it is while the finger is on it.
  card.hass = update(hass, { "sensor.local_darts": "12" });
  assert.equal($(card, ".pad-board"), again);
  touch(again, "pointerup", 1, 330, 280 - 102);
  assert.equal($(card, ".loupe").hidden, true);
  assert.deepEqual(actions(hass)[1], ["correct_dart", { config_entry_id: ENTRY, dart: 1, x: 0, y: 0.6 }]);
  // The click that follows the finger sets nothing more.
  $(card, '.slot[data-dart="1"]').click();
  laidOut($(card, ".pad-board")).dispatchEvent(new window.MouseEvent("click", { bubbles: true, clientX: 330, clientY: 280 }));
  assert.equal(actions(hass).length, 2);
  // Darts pulled while a finger is on the board close the pad, as there is nothing left
  // to correct; the finger that lets go then sets nothing.
  const last = laidOut($(card, ".pad-board"));
  touch(last, "pointerdown", 1, 330, 280);
  card.hass = update(hass, visit());
  assert.equal($(card, ".pad-area").hidden, true);
  touch(last, "pointerup", 1, 330, 280);
  assert.equal(actions(hass).length, 2);
  // The next dart's board is drawn afresh, the finger forgotten.
  card.hass = update(hass, visit(...THROWS));
  $(card, '.slot[data-dart="2"]').click();
  assert.notEqual($(card, ".pad-board"), last);
  assert.equal($(card, ".loupe").hidden, true);
});

test("the live card corrects nothing of the bot, without its option or in the editor, and keeps correcting offline", () => {
  // The bot's darts are no buttons, and while the bot is at the board the pad waits.
  const bot = setup(visit(dart(20, 3, { dart: 1 }), dart(19, 1, { dart: 2, bot: true }))).card;
  assert.deepEqual(slots(bot).slice(0, 2), [
    ["button", "slot triple tappable", true],
    ["div", "slot single latest", false],
  ]);
  const up = {
    "sensor.practice_remaining": {
      state: "301",
      attributes: {
        game: 301,
        player: 2,
        scores: [
          { player: 1, name: "Alex", remaining: 169 },
          { player: 2, name: null, remaining: 301, bot: true },
        ],
      },
    },
  };
  const waiting = setup(up).card;
  $(waiting, '.slot[data-dart="1"]').click();
  assert.equal($(waiting, '[data-pad="bed"][data-value="T20"]').disabled, true);
  // Without the option, the darts are plain tiles.
  assert.deepEqual(slots(setup({}, { corrections: false }).card).map(([tag]) => tag), ["div", "div", "div"]);
  // In the card editor's preview, nothing corrects.
  const { card: preview } = setup();
  preview.preview = true;
  preview.hass = update(makeHass({ states: { ...READY, ...visit(...THROWS) } }), {});
  assert.deepEqual(slots(preview).map(([tag]) => tag), ["div", "div", "div"]);
  // An offline board keeps the darts correctable: Home Assistant corrects them.
  const { hass, card } = setup();
  $(card, '.slot[data-dart="2"]').click();
  card.hass = update(hass, { "binary_sensor.local_connected": "off" });
  assert.equal($(card, ".pad-area").hidden, false);
  assert.deepEqual(slots(card).map(([tag]) => tag), ["button", "button", "div"]);
});
