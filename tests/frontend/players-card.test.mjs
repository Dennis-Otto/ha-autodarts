// The players card in a browser DOM: profiles, head-to-head records, recent matches and escaping.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, loadCards, makeHass, mount, text, update } from "./dom.mjs";

await loadCards();

const ALEX = {
  name: "Alex",
  legs_played: 20,
  legs_won: 12,
  matches_played: 5,
  matches_won: 3,
  average: 61.25,
  first_9_average: 70.1,
  checkout_rate: 31.3,
  mpr: 2.4,
  highest_visit: 140,
  highest_checkout: 121,
  best_mpr: 3.1,
  fewest_darts: { 501: 18, 301: 12 },
};
const LEA = { name: "Lea", legs_played: 8, legs_won: 3, matches_played: 2, matches_won: 1 };
const profiles = (...players) => ({
  "sensor.player_profiles": { state: String(players.length), attributes: { players } },
});
const lastMatch = (attributes) => ({
  "sensor.last_match": {
    state: "2026-09-26T20:00:00+00:00",
    attributes: { game: "killer", winner: null, matches: [], head_to_head: [], ...attributes },
  },
});
const MATCHES = [
  {
    ended: "2026-09-26T20:00:00+00:00",
    game: "killer",
    winner: 2,
    players: [
      { name: "Alex", legs: 0, sets: 0 },
      { name: null, legs: 1, sets: 0 },
    ],
  },
  { ended: "later", game: 501, winner: 1, players: [{ name: "Lea", legs: 2, sets: 1 }] },
  { ended: "2026-09-25T19:00:00+00:00", game: "cricket", winner: null, players: [{ name: "Alex" }] },
  { ended: "2026-09-24T19:00:00+00:00", game: null, winner: null, players: [] },
];
const setup = (states, config = {}, options = {}) => {
  const hass = makeHass({ states, ...options });
  return { hass, card: mount("autodarts-players-card", hass, config) };
};
const rows = (profile) =>
  [...profile.querySelectorAll("dt")].map((term) => [term.textContent, term.nextElementSibling.textContent]);

test("the players card shows every profile with its statistics and bests", () => {
  const { card } = setup({ ...profiles(ALEX, LEA), ...lastMatch({}) });
  assert.equal(text(card, ".title"), "Players");
  assert.equal(text(card, ".count"), "2");
  assert.equal($(card, ".empty").hidden, true);
  const [alex, lea] = $$(card, ".profile");
  assert.equal(alex.querySelector(".profile-name").textContent, "Alex");
  assert.equal(alex.querySelector(".muted").textContent, "Legs 12/20 · Matches 3/5");
  assert.deepEqual(rows(alex), [
    ["3-dart avg.", "61.3"],
    ["First 9", "70.1"],
    ["Checkout", "31.3%"],
    ["MPR", "2.40"],
    ["Best MPR", "3.10"],
    ["Highest visit", "140"],
    ["Highest checkout", "121"],
    ["Best 301", "12 darts"],
    ["Best 501", "18 darts"],
  ]);
  assert.deepEqual(rows(lea), [
    ["3-dart avg.", "–"],
    ["First 9", "–"],
    ["Checkout", "–"],
    ["Highest visit", "–"],
    ["Highest checkout", "–"],
  ]);
  assert.equal(card.getCardSize(), 6);
});

test("head-to-head records show the wins and the balance between two players", () => {
  const { hass, card } = setup({
    ...profiles(ALEX, LEA),
    ...lastMatch({ head_to_head: [{ players: ["Alex", "Lea"], wins: [3, 1] }] }),
  });
  assert.equal($(card, ".h2h-section").hidden, false);
  const versus = $(card, ".versus");
  assert.deepEqual(
    [...versus.querySelectorAll("span")].map((part) => part.textContent),
    ["Alex", "3 : 1", "Lea"]
  );
  assert.equal(versus.querySelector(".balance i").style.width, "75%");
  card.hass = update(hass, lastMatch({ head_to_head: [{ players: ["Alex", "Lea"], wins: [0, 0] }] }));
  assert.equal($(card, ".balance i").style.width, "50%");
  card.hass = update(hass, lastMatch({}));
  assert.equal($(card, ".h2h-section").hidden, true);
});

test("recent matches show when they ended, the game and the winner in bold", () => {
  const { card } = setup({ ...profiles(ALEX), ...lastMatch({ matches: MATCHES }) });
  assert.equal($(card, ".matches-section").hidden, false);
  const matches = $$(card, ".match");
  assert.deepEqual(
    matches.map((match) => [...match.children].map((part) => part.textContent.replace(/\s/g, " "))),
    [
      ["09/26, 8:00 PM", "Killer", "Alex 0 · Player 2 1"],
      ["", "501", "Lea 1"],
      ["09/25, 7:00 PM", "Cricket", "Alex 0"],
      ["09/24, 7:00 PM", "", ""],
    ]
  );
  assert.deepEqual(
    matches.map((match) => match.querySelector("b")?.textContent),
    ["Player 2 1", "Lea 1", undefined, undefined]
  );
});

test("without profiles the card explains how players get one", () => {
  const { hass, card } = setup({ ...profiles(), ...lastMatch({}) });
  assert.equal($(card, ".empty").hidden, false);
  assert.equal(
    text(card, ".empty"),
    "No player profiles yet. Give the players of a practice game a name, and every leg counts for them."
  );
  assert.equal(text(card, ".count"), "");
  assert.equal(text(card, ".profiles"), "");
  assert.equal($(card, ".matches-section").hidden, true);
  card.hass = update(hass, profiles(LEA));
  assert.equal($(card, ".empty").hidden, true);
  assert.equal(text(card, ".count"), "1");
});

test("head-to-head records and matches can be hidden and the title changed", () => {
  const states = {
    ...profiles(ALEX, LEA),
    ...lastMatch({ matches: MATCHES, head_to_head: [{ players: ["Alex", "Lea"], wins: [3, 1] }] }),
  };
  const { card } = setup(states, { show_head_to_head: false, show_matches: false, title: "League" });
  assert.equal($(card, ".h2h-section"), null);
  assert.equal($(card, ".matches-section"), null);
  assert.equal(text(card, ".title"), "League");
  assert.equal($$(card, ".profile").length, 2);
});

test("player names are shown as text, never as markup", () => {
  const evil = '<img src=x onerror="alert(1)">';
  const { card } = setup({
    ...profiles({ ...ALEX, name: evil }),
    ...lastMatch({
      head_to_head: [{ players: [evil, "Lea"], wins: [1, 0] }],
      matches: [{ ended: "2026-09-26T20:00:00+00:00", game: evil, winner: 1, players: [{ name: evil, legs: 1 }] }],
    }),
  });
  assert.equal($$(card, "img").length, 0);
  assert.equal(text(card, ".profile-name"), evil);
  assert.equal(text(card, ".versus .who"), evil);
  assert.equal(text(card, ".match .game"), evil);
  assert.equal(text(card, ".match b"), `${evil} 1`);
  assert.ok(!$(card, ".profiles").innerHTML.includes("<img"));
});

test("the players card speaks German, also without a locale", () => {
  const hass = makeHass({ states: { ...profiles(ALEX), ...lastMatch({ matches: MATCHES.slice(0, 1) }) } });
  const card = mount("autodarts-players-card", { ...hass, locale: undefined, language: "de" });
  assert.equal(text(card, ".title"), "Spieler");
  assert.equal($(card, ".profile .muted").textContent, "Legs 12/20 · Matches 3/5");
  assert.deepEqual(rows($(card, ".profile")).slice(0, 3), [
    ["3-Dart-Average", "61,3"],
    ["First 9", "70,1"],
    ["Checkout", "31,3 %"],
  ]);
  assert.deepEqual(rows($(card, ".profile")).slice(3, 5), [
    ["MPR", "2,40"],
    ["Beste MPR", "3,10"],
  ]);
  assert.deepEqual(rows($(card, ".profile")).slice(-2), [
    ["Bestes 301-Leg", "12 Darts"],
    ["Bestes 501-Leg", "18 Darts"],
  ]);
  assert.equal(text(card, ".match .muted"), "26.09., 20:00");
});
