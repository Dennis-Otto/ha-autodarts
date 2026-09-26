// The doubles card in a browser DOM: the hit rate of every double, for everybody or one player.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, loadCards, makeHass, mount, text, update } from "./dom.mjs";

const { bedPath } = await loadCards();

const DOUBLES = [
  { double: "D16", attempts: 40, hits: 20, rate: 50 },
  { double: "D20", attempts: 50, hits: 12, rate: 24 },
  { double: "BULL", attempts: 30, hits: 10 },
  { double: "D99", attempts: 5, hits: 1 },
];
const favourite = (state, attributes) => ({ "sensor.favourite_double": { state, attributes } });
const EVERYBODY = favourite("D16", { attempts: 120, hits: 42, rate: 35, doubles: DOUBLES });
const PROFILES = {
  "sensor.player_profiles": {
    state: "1",
    attributes: {
      players: [
        {
          name: "Lea",
          doubles: { attempts: 12, hits: 3, rate: 25, doubles: [{ double: "D8", attempts: 12, hits: 3 }] },
        },
      ],
    },
  },
};
const setup = (states, config = {}, options = {}) => {
  const hass = makeHass({ states, ...options });
  return { hass, card: mount("autodarts-doubles-card", hass, config) };
};
const list = (card) =>
  $$(card, ".double").map((item) => [
    item.className,
    item.querySelector(".bed").textContent,
    item.querySelector(".bar i").style.width,
    item.querySelector(".count").textContent,
    item.querySelector(".rate").textContent,
  ]);

test("the doubles card colours every double on the board by its hit rate", () => {
  const { card } = setup({ ...EVERYBODY, ...PROFILES });
  assert.equal(text(card, ".title"), "Doubles");
  assert.equal(text(card, ".meta"), "120 darts at a double · 35.0%");
  assert.equal($(card, ".empty").hidden, true);
  assert.equal($(card, ".doubles-body").hidden, false);
  assert.equal($(card, "svg").getAttribute("aria-label"), "Doubles");
  assert.deepEqual(
    $$(card, ".ring path").map((path) => [path.getAttribute("d"), path.style.fill, path.textContent]),
    [
      [bedPath("D16"), "hsl(130 70% 46%)", "D16: 20/40"],
      [bedPath("D20"), "hsl(62 70% 46%)", "D20: 12/50"],
      [bedPath("Bull"), "hsl(87 70% 46%)", "Bull: 10/30"],
    ]
  );
  assert.equal(card.getCardSize(), 6);
});

test("the list ranks the doubles by hit rate and marks the favourite", () => {
  const { hass, card } = setup(EVERYBODY);
  assert.deepEqual(list(card), [
    ["double favourite", "D16", "50%", "20/40", "50%"],
    ["double", "Bull", "33.3%", "10/30", "33%"],
    ["double", "D20", "24%", "12/50", "24%"],
  ]);
  // The same rate ranks the double with more darts first.
  const tied = [
    { double: "D1", attempts: 4, hits: 1, rate: 25 },
    { double: "D2", attempts: 8, hits: 2, rate: 25 },
  ];
  card.hass = update(hass, favourite("D2", { attempts: 12, hits: 3, rate: 25, doubles: tied }));
  assert.deepEqual(
    list(card).map((item) => item[1]),
    ["D2", "D1"]
  );
});

test("one player's doubles come from the profiles", () => {
  const { card } = setup({ ...EVERYBODY, ...PROFILES }, { player: " lea " });
  assert.equal(text(card, ".title"), "Doubles · Lea");
  assert.equal(text(card, ".meta"), "12 darts at a double · 25.0%");
  assert.deepEqual(list(card), [["double", "D8", "25%", "3/12", "25%"]]);
  const unknown = setup({ ...EVERYBODY, ...PROFILES }, { player: "Kim" }).card;
  assert.equal(text(unknown, ".title"), "Doubles · Kim");
  assert.equal($(unknown, ".empty").hidden, false);
  // A name without a profile is most likely mistyped.
  assert.equal(
    text(unknown, ".empty"),
    "No doubles of Kim yet. Check the name in the card settings, or throw at doubles in a practice game as Kim."
  );
  const german = setup(PROFILES, { player: "Kim" }, { language: "de" }).card;
  assert.match(text(german, ".empty"), /^Noch keine Doubles von Kim\./);
});

test("without darts at a double the card explains how to get a hit rate", () => {
  const { hass, card } = setup(favourite("unknown", { attempts: 0, hits: 0, rate: null, doubles: [] }));
  assert.equal($(card, ".empty").hidden, false);
  assert.equal($(card, ".doubles-body").hidden, true);
  assert.equal(
    text(card, ".empty"),
    "Throw at doubles in X01, the doubles training or Bob's 27 to see your hit rate on every double."
  );
  assert.equal(text(card, ".meta"), "");
  card.hass = update(hass, favourite("D20", { attempts: 50, hits: 12, rate: null, doubles: DOUBLES.slice(1, 2) }));
  assert.equal(text(card, ".meta"), "50 darts at a double");
  assert.equal($(card, ".empty").hidden, true);
});

test("the doubles card has a configurable title and speaks German", () => {
  assert.equal(text(setup(EVERYBODY, { title: "Finishing" }).card, ".title"), "Finishing");
  const { card } = setup(EVERYBODY, {}, { language: "de" });
  assert.equal(text(card, ".title"), "Doubles");
  assert.equal(text(card, ".meta"), "120 Darts aufs Double · 35,0 %");
  assert.equal(text(card, ".muted:not(.meta)"), "Persönliche Checkout-Wege nutzen Doubles mit mindestens 10 Darts.");
});
