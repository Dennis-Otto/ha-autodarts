// The doubles card: hit rates per double for everybody or one player.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dashboardStrategy,
  doubleColor,
  doublesHtml,
  doublesView,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const doubles = {
  state: "D16",
  attributes: {
    attempts: 42,
    hits: 13,
    rate: 31,
    doubles: [
      { double: "D16", attempts: 20, hits: 9, rate: 45 },
      { double: "D20", attempts: 20, hits: 3, rate: 15 },
      { double: "BULL", attempts: 2, hits: 1 },
      { double: "S20", attempts: 5, hits: 5 },
      { double: "D8", attempts: 0, hits: 0 },
    ],
  },
};
const profiles = {
  state: "1",
  attributes: {
    players: [{ name: "Alex", doubles: { attempts: 10, hits: 4, rate: 40, favourite: null, doubles: [{ double: "D8", attempts: 10, hits: 4, rate: 40 }] } }],
  },
};

test("without sensors nobody has doubles yet", () => {
  const empty = { attempts: 0, hits: 0, rate: null, favourite: null, doubles: [] };
  assert.deepEqual(doublesView(undefined, undefined), { player: null, known: true, ...empty });
  assert.deepEqual(doublesView(undefined, { state: "0", attributes: {} }, "Lea"), { player: "Lea", known: false, ...empty });
});

test("everybody's doubles or one player's", () => {
  const all = doublesView(doubles, profiles);
  assert.deepEqual([all.player, all.favourite, all.attempts, all.rate], [null, "D16", 42, 31]);
  assert.deepEqual(
    all.doubles.map((item) => [item.double, item.rate]),
    [
      ["D16", 45],
      ["D20", 15],
      ["BULL", 50],
    ]
  );
  const alex = doublesView(doubles, profiles, " alex ");
  assert.deepEqual([alex.player, alex.known, alex.attempts, alex.doubles[0].double], ["Alex", true, 10, "D8"]);
  const nobody = doublesView(doubles, profiles, "Kim");
  assert.deepEqual([nobody.player, nobody.known, nobody.doubles], ["Kim", false, []]);
  assert.equal(doublesView({ state: "unknown", attributes: {} }).favourite, null);
});

test("colours run from red to green and the list starts with the best double", () => {
  assert.equal(doubleColor(0), "hsl(0 70% 46%)");
  assert.equal(doubleColor(50), "hsl(130 70% 46%)");
  assert.equal(doubleColor(90), "hsl(130 70% 46%)");
  const html = doublesHtml(doublesView(doubles, profiles), {
    format: (value, digits) => value.toFixed(digits),
    percent: (value, digits) => `${value.toFixed(digits)} %`,
    label: (key) => (key === "BULL" ? "Bull" : key),
  });
  assert.match(html.list, /^<div class="double"><span class="bed"[^>]*>Bull<\/span>/);
  assert.match(html.list, /<div class="double favourite"><span class="bed"[^>]*>D16<\/span>.*<span class="count">9\/20<\/span><span class="rate">45 %<\/span>/);
  assert.equal((html.ring.match(/<path /g) || []).length, 3);
  assert.match(html.ring, /<title>D20: 3\/20<\/title>/);
});

test("the training view shows the doubles card once the sensor exists", () => {
  const entity = (entity_id, translation_key) => ({ entity_id, translation_key, device_id: "dev1", platform: "autodarts" });
  const config = dashboardStrategy({
    locale: { language: "en" },
    entities: Object.fromEntries(
      [entity("sensor.b_darts", "training_darts"), entity("sensor.b_double", "favourite_double")].map((item) => [
        item.entity_id,
        item,
      ])
    ),
    devices: { dev1: { id: "dev1" } },
    states: {},
  });
  const training = config.views.find((view) => view.path === "training");
  assert.equal(training.sections[1].cards[0].type, "custom:autodarts-doubles-card");
});
