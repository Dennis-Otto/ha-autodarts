// The heatmap modes of the training card: beds, numbers and dart positions, of the session or a player.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, DEVICE, loadCards, makeHass, mount, settle, text, update, window, withLanguage } from "./dom.mjs";

await loadCards();

const SESSION = {
  "sensor.training_darts": { state: "6", attributes: { hits: { T20: 4, S20: 2 } } },
  "sensor.training_points": "280",
  "sensor.training_visits": "2",
  "switch.training_session": "on",
};
const PROFILES = {
  "sensor.player_profiles": {
    state: "2",
    attributes: {
      players: [
        { name: "Sam", darts_thrown: 0, hits: {} },
        { name: "Lea", hits: {} },
        { name: "Bo", darts_thrown: 3, hits: { S1: 3 } },
        { name: "Alex", darts_thrown: 9, hits: { T19: 6, D16: 3 } },
      ],
    },
  },
};
const GROUP = { target: "T20", darts: 40, offset_x: -6, offset_y: 2, r50: 38, r80: 61, change: -4 };

// A board that answers with the positions it logged; requests are kept in `asked`.
function board(asked, answers = {}) {
  return async (message) => {
    asked.push(message);
    const answer = answers[message.player ?? ""];
    if (answer instanceof Error) throw answer;
    return answer ?? { player: message.player ?? null, known: true, positions: [[0, 0.6], [0.02, 0.61]], spread: [GROUP] };
  };
}

const setup = (config = {}, callWS, states = {}) => {
  const hass = makeHass({ states: { ...SESSION, ...PROFILES, ...states }, ...(callWS ? { callWS } : {}) });
  return { hass, card: mount("autodarts-training-card", hass, config) };
};
const pressed = (card, group) =>
  $$(card, `.${group} button`).map((button) => [button.textContent, button.getAttribute("aria-pressed")]);
const click = (card, selector) => $(card, selector).dispatchEvent(new window.Event("click", { bubbles: true }));

test("the heatmap switches between beds, numbers and positions", async () => {
  const asked = [];
  const { card } = setup({}, board(asked));
  assert.deepEqual(pressed(card, "modes"), [
    ["Beds", "true"],
    ["Numbers", "false"],
    ["Positions", "false"],
  ]);
  assert.ok($(card, '.heat-layer path[d]'));
  assert.equal($(card, ".heat .groups").hidden, true);
  click(card, '[data-mode="numbers"]');
  assert.equal(pressed(card, "modes")[1][1], "true");
  // Numbers mode colours all four beds of the 20.
  assert.equal($$(card, ".heat-bed title").filter((title) => title.textContent.startsWith("20:")).length, 4);
  assert.equal(asked.length, 0);

  click(card, '[data-mode="positions"]');
  assert.deepEqual(asked, [{ type: "autodarts/positions", device_id: DEVICE }]);
  await settle();
  assert.equal($(card, "svg[role=img]").getAttribute("aria-label"), "Dartboard with the positions of the darts");
  assert.equal($$(card, ".heat-layer .position").length, 2);
  assert.ok($$(card, ".heat-layer .density rect").length > 10);
  assert.deepEqual([text(card, ".legend-min"), text(card, ".legend-max")], ["few", "many"]);
  assert.equal($(card, ".heat .groups").hidden, false);
  assert.equal(text(card, ".group-text"), "grouping 38 mm · 80 % within 61 mm · 6 mm left of center, 2 mm high");
  assert.equal(text(card, ".group-change"), "4 mm tighter");

  click(card, '[data-mode="beds"]');
  assert.deepEqual([text(card, ".legend-min"), $(card, ".heat .groups").hidden], ["1", true]);
  assert.equal($(card, "svg[role=img]").getAttribute("aria-label"), "Dartboard colored by how often each bed was hit");
});

test("positions load again only when a visit was booked", async () => {
  const asked = [];
  const { hass, card } = setup({ mode: "positions" }, board(asked));
  await settle();
  assert.equal(asked.length, 1);
  card.hass = update(hass, { "sensor.training_points": "300" });
  await settle();
  assert.equal(asked.length, 1);
  card.hass = update(hass, { "sensor.training_visits": "3" });
  await settle();
  assert.equal(asked.length, 2);
});

test("the heatmap shows a player's own darts", async () => {
  const asked = [];
  const { card } = setup({}, board(asked));
  // Players who threw no dart are not offered.
  assert.deepEqual(pressed(card, "sources"), [
    ["Session", "true"],
    ["Alex", "false"],
    ["Bo", "false"],
  ]);
  click(card, '[data-source="Alex"]');
  assert.deepEqual(pressed(card, "sources")[1], ["Alex", "true"]);
  const titles = $$(card, ".heat-bed title").map((title) => title.textContent);
  assert.ok(titles.some((title) => title.startsWith("T19: 6 hits")));
  assert.ok(!titles.some((title) => title.startsWith("T20")));
  assert.deepEqual(
    $$(card, ".top-row").map((row) => row.textContent),
    ["T196× · 67%", "D163× · 33%"]
  );
  click(card, '[data-mode="positions"]');
  assert.deepEqual(asked, [{ type: "autodarts/positions", device_id: DEVICE, player: "Alex" }]);
  click(card, '[data-source=""]');
  assert.deepEqual(asked.at(-1), { type: "autodarts/positions", device_id: DEVICE });
  await settle();
  assert.equal($$(card, ".heat-layer .position").length, 2);
});

test("the player of the configuration comes first, known or not", async () => {
  const asked = [];
  const answers = { Kim: { player: "Kim", known: false, positions: [], spread: [] } };
  const { card } = setup({ mode: "positions", player: " Kim " }, board(asked, answers));
  assert.deepEqual(pressed(card, "sources"), [
    ["Session", "false"],
    ["Alex", "false"],
    ["Bo", "false"],
    ["Kim", "true"],
  ]);
  await settle();
  assert.deepEqual(asked, [{ type: "autodarts/positions", device_id: DEVICE, player: "Kim" }]);
  assert.equal(text(card, ".heat .groups"), "No dart positions yet.");
  assert.equal(text(card, ".legend-max"), "–");
  assert.equal($$(card, ".top-row").length, 0);
});

test("without switches, a player or positions the heatmap still draws", async () => {
  const asked = [];
  const answers = { "": new Error("gone") };
  const { card } = setup({ mode: "positions", show_heatmap_controls: false }, board(asked, answers), {
    "sensor.player_profiles": { state: "0", attributes: {} },
  });
  assert.equal($(card, ".modes"), null);
  assert.equal($(card, ".sources"), null);
  await settle();
  // A board being removed answers with an error: no positions.
  assert.equal(asked.length, 1);
  assert.equal(text(card, ".heat .groups"), "No dart positions yet.");
  // Without the WebSocket, the heatmap waits for positions.
  const plain = setup({ mode: "positions" }).card;
  assert.equal($$(plain, ".heat-layer .position").length, 0);
  assert.equal($(plain, ".heat .groups").hidden, true);
  assert.equal($(plain, ".sources").hidden, false);
  // A player without profiles shows no hits.
  const lonely = setup({ player: "Kim" }, undefined, { "sensor.player_profiles": { state: "0", attributes: {} } }).card;
  assert.deepEqual(pressed(lonely, "sources"), [
    ["Session", "false"],
    ["Kim", "true"],
  ]);
  assert.equal($$(lonely, ".heat-bed").length, 0);
  // An unknown mode in the configuration shows the beds.
  assert.equal($(setup({ mode: "rings" }).card, '[data-mode="beds"]').getAttribute("aria-pressed"), "true");
});

test("an answer for a player the card no longer shows is dropped", async () => {
  let release;
  const asked = [];
  const slow = async (message) => {
    asked.push(message);
    if (message.player === "Alex") await new Promise((resolve) => (release = resolve));
    return { positions: [[0.5, 0.5]], spread: [] };
  };
  const { card } = setup({ mode: "positions" }, slow);
  click(card, '[data-source="Alex"]');
  click(card, '[data-source=""]');
  await settle();
  release();
  await settle();
  assert.equal(asked.length, 3);
  assert.equal($$(card, ".heat-layer .position").length, 1);
  assert.equal($(card, ".heat-layer .position").getAttribute("cx"), "85");
  // Clicks beside the buttons change nothing.
  click(card, ".modes");
  click(card, ".sources");
  assert.equal(asked.length, 3);
});

test("the heatmap switches speak German", () => {
  const hass = withLanguage(makeHass({ states: { ...SESSION, ...PROFILES } }), "de");
  const card = mount("autodarts-training-card", hass, {});
  assert.deepEqual(
    pressed(card, "modes").map(([name]) => name),
    ["Felder", "Zahlen", "Positionen"]
  );
  assert.equal(pressed(card, "sources")[0][0], "Session");
  assert.equal($(card, ".modes").getAttribute("aria-label"), "Heatmap");
  assert.equal($(card, ".sources").getAttribute("aria-label"), "Wessen Darts");
});

test("a new configuration shows its own mode and player", () => {
  const { hass, card } = setup({ mode: "numbers" });
  click(card, '[data-mode="beds"]');
  click(card, '[data-source="Alex"]');
  card.setConfig({ type: "custom:autodarts-training-card", mode: "numbers" });
  card.hass = hass;
  assert.equal($(card, '[data-mode="numbers"]').getAttribute("aria-pressed"), "true");
  assert.equal($(card, '[data-source=""]').getAttribute("aria-pressed"), "true");
});

test("positions without a known aim have no groupings to show", async () => {
  const answers = { "": { positions: [[0.1, 0.2]], spread: [] } };
  const { card } = setup({ mode: "positions" }, board([], answers));
  await settle();
  assert.equal($$(card, ".heat-layer .position").length, 1);
  assert.equal($(card, ".heat .groups").hidden, true);
});
