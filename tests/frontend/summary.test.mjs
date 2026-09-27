// The summary of a finished match, the result of a match and the bull-off leader.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  bullOffLeaders,
  matchResult,
  summaryTable,
  summaryView,
  targetText,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const ui = {
  t: (key) => ({ unit_darts: "{value} darts" })[key] ?? key,
  format: (value, digits) => value.toFixed(digits),
  percent: (value, digits) => `${value.toFixed(digits)}%`,
  label: (key) => (key === "BULL" ? "Bull" : key),
};

// Alex beat Sam 2 : 1 in 301, as the integration sums the match up.
const ALEX = {
  player: 1,
  name: "Alex",
  legs: 2,
  sets: 1,
  darts: 21,
  average: 106.0,
  first_9_average: 114.0,
  checkouts: 2,
  darts_at_double: 3,
  checkout_rate: 66.7,
  highest_checkout: 121,
  scores_100: 1,
  scores_140: 1,
  scores_180: 2,
  best_leg: 6,
};
const SAM = {
  player: 2,
  name: null,
  legs: 1,
  sets: 0,
  darts: 18,
  average: 60.17,
  first_9_average: 60.17,
  checkouts: 1,
  darts_at_double: 1,
  checkout_rate: 100.0,
  highest_checkout: 124,
  scores_100: 1,
  scores_140: 1,
  scores_180: 0,
  best_leg: 6,
};
const SUMMARY = {
  game: 301,
  ended: "2026-09-27T20:00:00+00:00",
  winner: 1,
  legs_to_win: 2,
  sets_to_win: 1,
  double_out: true,
  players: [ALEX, SAM],
};
const sensor = (summary, attributes = {}) => ({
  state: "0",
  attributes: { game: 301, winner: 1, summary, ...attributes },
});
const cells = (html) =>
  [...html.matchAll(/<tr( class="result")?><th>([^<]*)<\/th>(.*?)<\/tr>/g)].map(([, result, name, row]) => [
    result ? "result" : "",
    name,
    ...[...row.matchAll(/<td class="(\w*)">([^<]*)<\/td>/g)].map(([, kind, value]) => `${kind}:${value}`),
  ]);

test("the summary of a won X01 match lists every number of every player", () => {
  const summary = summaryView(sensor(SUMMARY));
  assert.deepEqual([summary.kind, summary.winner, summary.ended, summary.doubleOut], ["x01", 1, SUMMARY.ended, true]);
  const html = summaryTable(summary, ui);
  assert.match(html, /<thead><tr><th class="caption">summary<\/th><th class="winner">Alex <span class="visually-hidden">winner<\/span><\/th><th class="">score_player 2<\/th><\/tr><\/thead>/);
  // Teams that are no list leave the winner alone.
  assert.equal(summaryTable(summary, ui, null), html);
  // A player linked to a person shows the picture.
  const pictured = summaryTable(summary, { ...ui, avatar: (name) => (name === "Alex" ? "/alex.png" : null) });
  assert.match(pictured, /<th class="winner"><img class="avatar" src="\/alex.png" alt="" draggable="false">Alex <span class="visually-hidden">winner<\/span><\/th><th class="">score_player 2<\/th>/);
  assert.deepEqual(cells(html), [
    ["result", "score_legs", "winner:2", ":1"],
    ["", "average", "winner:106.0", ":60.2"],
    ["", "first_9", "winner:114.0", ":60.2"],
    ["", "summary_checkout", "winner:66.7% (2/3)", ":100.0% (1/1)"],
    ["", "highest_checkout", "winner:121", ":124"],
    ["", "max", "winner:2", ":0"],
    ["", "scores_140", "winner:1", ":1"],
    ["", "scores_100", "winner:1", ":1"],
    ["", "summary_best_leg", "winner:6 darts", ":6 darts"],
    ["", "summary_at_double", "winner:3", ":1"],
    ["", "darts", "winner:21", ":18"],
  ]);
});

test("sets, single out, Cricket and party games have rows of their own", () => {
  const sets = summaryView(
    sensor({ ...SUMMARY, sets_to_win: 2, double_out: false, players: [{ ...ALEX, sets: 2, legs: 5 }, SAM] })
  );
  const rows = cells(summaryTable(sets, ui)).map((row) => row.slice(0, 3));
  assert.deepEqual(rows.slice(0, 2), [
    ["result", "score_sets", "winner:2"],
    ["", "score_legs", "winner:5"],
  ]);
  // Without double out, nobody throws at a double to finish.
  assert.ok(!rows.some(([, name]) => ["summary_checkout", "summary_at_double"].includes(name)));

  const cricket = {
    ...SUMMARY,
    game: "cricket",
    players: [
      { player: 1, name: "Alex", legs: 1, sets: 1, darts: 8, mpr: 7.88, marks: 21, best_leg: 8 },
      { player: 2, name: "Sam", legs: 0, sets: 0, darts: 4, mpr: 0.75, marks: 1, best_leg: null },
    ],
  };
  const chalk = summaryView(sensor(cricket, { game: "cricket" }));
  assert.equal(chalk.kind, "cricket");
  assert.deepEqual(cells(summaryTable(chalk, ui)), [
    ["result", "score_legs", "winner:1", ":0"],
    ["", "cricket_mpr", "winner:7.88", ":0.75"],
    ["", "summary_marks", "winner:21", ":1"],
    ["", "summary_best_leg", "winner:8 darts", ":–"],
    ["", "darts", "winner:8", ":4"],
  ]);

  const party = {
    ...SUMMARY,
    game: "killer",
    winner: 2,
    players: [
      { player: 1, name: "Alex", legs: 0, sets: 0, darts: 12 },
      { player: 2, name: "Sam", legs: 1, sets: 1, darts: null },
    ],
  };
  const killer = summaryView(sensor(party, { game: "killer", winner: 2 }));
  assert.equal(killer.kind, "party");
  assert.deepEqual(cells(summaryTable(killer, ui)), [
    ["result", "score_legs", ":0", "winner:1"],
    ["", "darts", ":12", "winner:–"],
  ]);
});

test("a summary shows only for the match the sensor still shows as won", () => {
  assert.equal(summaryView(undefined), null);
  assert.equal(summaryView({ state: "unavailable", attributes: { winner: 1, game: 301, summary: SUMMARY } }), null);
  assert.equal(summaryView(sensor(null)), null);
  assert.equal(summaryView(sensor("summary")), null);
  // The next match has no winner yet; another game or winner is another match.
  assert.equal(summaryView(sensor(SUMMARY, { winner: null })), null);
  assert.equal(summaryView(sensor(SUMMARY, { winner: 2 })), null);
  assert.equal(summaryView(sensor(SUMMARY, { game: 501 })), null);
  // A match needs two players.
  assert.equal(summaryView(sensor({ ...SUMMARY, players: [ALEX, null, { player: "x" }] })), null);
  assert.equal(summaryView(sensor({ ...SUMMARY, players: "none" })), null);
  const sparse = summaryView(
    sensor({ game: 301, winner: 1, players: [{ player: 1, average: null }, { player: 2, legs: "3" }] })
  );
  assert.deepEqual(
    [sparse.ended, sparse.legsToWin, sparse.setsToWin, sparse.doubleOut, sparse.players[1].legs, sparse.players[1].atDouble],
    ["", 1, 1, true, 0, 0]
  );
  assert.deepEqual(cells(summaryTable(sparse, ui))[3], ["", "summary_checkout", "winner:–", ":–"]);
});

test("the result of a match puts the winner first, in legs or in sets", () => {
  const scores = [
    { player: 1, legs: 1, sets: 0 },
    { player: 2, legs: 3, sets: 1 },
    { player: 3, legs: 2, sets: 0 },
  ];
  assert.equal(matchResult({ winner: 2, legsToWin: 3, setsToWin: 1, scores }), "3 : 1 : 2");
  assert.equal(matchResult({ winner: 2, legsToWin: 3, setsToWin: 2, scores }), "1 : 0 : 0");
  // A single leg, no winner yet or playing alone tell no result.
  assert.equal(matchResult({ winner: 2, legsToWin: 1, setsToWin: 1, scores }), "");
  assert.equal(matchResult({ winner: null, legsToWin: 3, setsToWin: 1, scores }), "");
  assert.equal(matchResult({ winner: 1, legsToWin: 3, setsToWin: 1, scores: scores.slice(0, 1) }), "");
});

test("the bull-off leader: the better bull bed, then the closer dart", () => {
  const off = (throws, byDistance = false) => ({ byDistance, throws });
  const dart = (player, hit, distance = null) => ({ player, hit, distance });
  assert.deepEqual(bullOffLeaders(off([dart(1, null), dart(2, null)])), []);
  assert.deepEqual(bullOffLeaders(off([dart(1, "BULL"), dart(2, "25", 1.5)])), [1]);
  // Two darts in the same bull bed tie, unless the players let the distance decide.
  assert.deepEqual(bullOffLeaders(off([dart(1, "25", 9), dart(2, "25", 12)])), [1, 2]);
  assert.deepEqual(bullOffLeaders(off([dart(1, "25", 9), dart(2, "25", 12)], true)), [1]);
  // Outside the bull the closer dart leads; without a position there is no telling.
  assert.deepEqual(bullOffLeaders(off([dart(1, "S20", 40), dart(2, "S5", 31.2)])), [2]);
  assert.deepEqual(bullOffLeaders(off([dart(1, "S20", 40), dart(2, "MISS")])), [1, 2]);
});

test("targets read as players call them", () => {
  const t = (key) => ({ any_double: "Any double", any_treble: "Any treble", bull_target: "Bull (25/50)" })[key];
  const labels = { ...ui, t };
  assert.deepEqual(
    ["D", "T", "25", "BULL", "D16", "7"].map((target) => targetText(labels, target)),
    ["Any double", "Any treble", "Bull (25/50)", "Bull", "D16", "7"]
  );
});
