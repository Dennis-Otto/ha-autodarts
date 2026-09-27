// The summary of a finished match on the scoreboard and the live card.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, READY, loadCards, makeHass, mount, text, update } from "./dom.mjs";

await loadCards();

// Alex beat Sam 2 : 1 in 301, first to two legs, as the practice sensor shows it.
const player = (number, name, extra) => ({
  player: number,
  name,
  sets: 0,
  checkouts: 1,
  darts_at_double: 2,
  checkout_rate: 50,
  highest_checkout: 40,
  scores_100: 0,
  scores_140: 1,
  scores_180: 0,
  best_leg: 12,
  ...extra,
});
const SUMMARY = {
  game: 301,
  ended: "2026-09-27T20:00:00+00:00",
  winner: 1,
  legs_to_win: 2,
  sets_to_win: 1,
  double_out: true,
  players: [
    player(1, "Alex", { legs: 2, sets: 1, darts: 30, average: 60.2, first_9_average: 71.3, scores_180: 1 }),
    player(2, "Sam", { legs: 1, darts: 27, average: 55.67, first_9_average: 58 }),
  ],
};
const finished = (attributes = {}) => ({
  "sensor.practice_remaining": {
    state: "0",
    attributes: {
      game: 301,
      player: 1,
      name: "Alex",
      winner: 1,
      legs_to_win: 2,
      sets_to_win: 1,
      scores: [
        { player: 1, name: "Alex", remaining: 0, legs: 2, sets: 1, match_legs: 2, average: 60.2 },
        { player: 2, name: "Sam", remaining: 61, legs: 1, sets: 0, match_legs: 1, average: 55.67 },
      ],
      summary: SUMMARY,
      ...attributes,
    },
  },
});
// The first dart of the next match.
const nextMatch = () =>
  finished({
    winner: null,
    scores: [
      { player: 1, name: "Alex", remaining: 241, legs: 0, sets: 0, match_legs: 0, average: 180 },
      { player: 2, name: "Sam", remaining: 301, legs: 0, sets: 0, match_legs: 0, average: null },
    ],
  });
const rows = (card) =>
  $$(card, ".summary tbody tr").map((row) => [...row.children].map((cell) => cell.textContent));

test("a won match shows its summary on the scoreboard until the next game", () => {
  const hass = makeHass({ states: { ...READY, ...finished() } });
  const card = mount("autodarts-scoreboard-card", hass);
  assert.equal(text(card, ".banner"), "Alex wins the match 2 : 1!");
  assert.equal($(card, ".main .players"), null);
  assert.deepEqual(
    $$(card, ".summary thead th").map((cell) => [cell.className, cell.textContent]),
    [
      ["caption", "Match summary"],
      ["winner", "Alex"],
      ["", "Sam"],
    ]
  );
  assert.deepEqual(rows(card), [
    ["Legs", "2", "1"],
    ["3-dart avg.", "60.2", "55.7"],
    ["First 9", "71.3", "58.0"],
    ["Checkout rate", "50.0% (1/2)", "50.0% (1/2)"],
    ["Highest checkout", "40", "40"],
    ["180s", "1", "0"],
    ["140+", "1", "1"],
    ["100+", "0", "0"],
    ["Best leg", "12 darts", "12 darts"],
    ["Darts at a double", "2", "2"],
    ["Darts", "30", "27"],
  ]);
  assert.equal($(card, ".summary tbody tr").className, "result");
  // The first dart of the next match ends the summary.
  card.hass = update(hass, nextMatch());
  assert.equal($(card, ".summary"), null);
  assert.equal($(card, ".banner").hidden, true);
  assert.equal($$(card, ".main .player").length, 2);
});

test("the summary can stay for some seconds only, or not show at all", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"], now: 1_000_000 });
  const hass = makeHass({ states: { ...READY, ...finished() } });
  const card = mount("autodarts-scoreboard-card", hass, { summary_seconds: 30 });
  assert.notEqual($(card, ".summary"), null);
  // Other updates keep the time the card first showed the summary.
  t.mock.timers.tick(20_000);
  card.hass = update(hass, { "sensor.num_throws": "1" });
  assert.notEqual($(card, ".summary"), null);
  t.mock.timers.tick(10_000);
  assert.equal($(card, ".summary"), null);
  // The result stays in the banner and on the players.
  assert.equal(text(card, ".banner"), "Alex wins the match 2 : 1!");
  assert.equal($(card, ".main .player.winner .name").textContent, "Alex");

  // A card that was away while the time ran out shows the players when it returns.
  const away = mount("autodarts-scoreboard-card", hass, { summary_seconds: 5 });
  assert.notEqual($(away, ".summary"), null);
  away.remove();
  t.mock.timers.tick(6_000);
  assert.notEqual($(away, ".summary"), null);
  document.body.append(away);
  assert.equal($(away, ".summary"), null);

  const off = mount("autodarts-scoreboard-card", hass, { show_summary: false });
  assert.equal($(off, ".summary"), null);
  assert.equal(text(off, ".banner"), "Alex wins the match 2 : 1!");
});

test("the live card shows the result and the summary of a won match", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"], now: 1_000_000 });
  const hass = makeHass({ states: { ...READY, ...finished() } });
  const card = mount("autodarts-card", hass, { summary_seconds: 10 });
  assert.equal(text(card, ".practice-remaining"), "2 : 1");
  assert.equal(text(card, ".practice-route .note.won"), "Alex wins the match 2 : 1!");
  assert.equal($(card, ".practice .scoreboard").hidden, false);
  assert.deepEqual(rows(card)[0], ["Legs", "2", "1"]);
  t.mock.timers.tick(10_000);
  assert.equal($(card, ".summary"), null);
  assert.equal(text(card, ".practice-remaining"), "0");
  assert.equal($$(card, ".player-score").length, 2);

  // A match of one leg has no result to tell: the big number stays.
  const single = mount("autodarts-card", update(hass, finished({ legs_to_win: 1 })));
  assert.equal(text(single, ".practice-remaining"), "0");
  assert.equal(text(single, ".practice-route .note.won"), "Alex wins the match!");
  assert.notEqual($(single, ".summary"), null);

  // Without the practice game, the live card has no summary either.
  const plain = mount("autodarts-card", hass, { show_practice: false });
  assert.equal($(plain, ".summary"), null);
});

test("the summary comes before the new game screen and needs the room of the visit", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: 1_000_000 });
  const board = (states) => ({
    ...READY,
    "select.practice_game": { state: "301", attributes: { options: ["off", "301", "cricket"] } },
    ...states,
  });
  const hass = makeHass({ states: board(nextMatch()) });
  const card = mount("autodarts-scoreboard-card", hass, { summary_seconds: 20 });
  card.hass = update(hass, finished());
  assert.equal($(card, ".visit").hidden, true);
  // A game that ends opens the screen after eight seconds; its summary goes first.
  t.mock.timers.tick(8000);
  assert.notEqual($(card, ".summary"), null);
  assert.equal($(card, ".lobby"), null);
  t.mock.timers.tick(12000);
  assert.equal($(card, ".summary"), null);
  assert.equal($(card, ".visit").hidden, false);
  t.mock.timers.tick(7999);
  assert.equal($(card, ".lobby"), null);
  t.mock.timers.tick(1);
  assert.equal(text(card, ".title"), "New game");

  // Until the next game, the summary stays; a tap opens the screen.
  const other = makeHass({ states: board(nextMatch()) });
  const stay = mount("autodarts-scoreboard-card", other);
  stay.hass = update(other, finished());
  t.mock.timers.tick(60000);
  assert.notEqual($(stay, ".summary"), null);
  assert.equal($(stay, ".lobby"), null);
});

test("party games keep their scores on screen", () => {
  const killer = {
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: {
        game: "killer",
        player: 2,
        winner: 2,
        scores: [
          { player: 1, name: "Alex", number: 7, lives: 0, killer: true, legs: 0, sets: 0 },
          { player: 2, name: "Sam", number: 12, lives: 2, killer: true, legs: 1, sets: 1 },
        ],
        summary: {
          game: "killer",
          winner: 2,
          players: [
            { player: 1, name: "Alex", legs: 0, sets: 0, darts: 12 },
            { player: 2, name: "Sam", legs: 1, sets: 1, darts: 15 },
          ],
        },
      },
    },
  };
  const card = mount("autodarts-scoreboard-card", makeHass({ states: { ...READY, ...killer } }));
  assert.equal($(card, ".summary"), null);
  assert.equal($(card, ".main .player.winner .name").textContent, "Sam");
  assert.equal(text(card, ".banner"), "Sam wins the match!");
});

test("the summary speaks German", () => {
  const hass = makeHass({ language: "de", states: { ...READY, ...finished() } });
  const card = mount("autodarts-scoreboard-card", hass);
  assert.equal(text(card, ".banner"), "Alex gewinnt das Match 2 : 1!");
  assert.equal(text(card, ".summary thead .caption"), "Match-Zusammenfassung");
  assert.deepEqual(
    rows(card).map((row) => row[0]),
    [
      "Legs",
      "3-Dart-Average",
      "First 9",
      "Checkout-Quote",
      "Höchster Checkout",
      "180er",
      "140+",
      "100+",
      "Bestes Leg",
      "Darts aufs Double",
      "Darts",
    ]
  );
  assert.deepEqual(rows(card)[3], ["Checkout-Quote", "50,0 % (1/2)", "50,0 % (1/2)"]);
  assert.deepEqual(rows(card)[8], ["Bestes Leg", "12 Darts", "12 Darts"]);
});
