// The caller of the scoreboard: what it says, and when. It calls only what counts.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  callerCalls,
  callerState,
  callerText,
  dartKey,
  visitCount,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const dart = (number, multiplier) => ({ number, multiplier });
const visit = (...darts) => ({ state: "0", attributes: { throws: darts } });
const x01 = (overrides = {}) => ({
  mode: "x01",
  practice: {
    player: 1,
    name: "Alex",
    remaining: 501,
    route: [],
    bust: false,
    won: false,
    winner: null,
    opened: true,
    visit: [],
    scores: [
      { player: 1, name: "Alex" },
      { player: 2, name: "Sam" },
    ],
    ...overrides,
  },
});
const all = { call_scores: true, call_checkouts: true, call_results: true, call_sounds: true };
const calls = (before, after, options = all) => callerCalls(before, after, options).map((call) => call.kind);
// The states of one visit, from the empty board to the last dart.
const play = (steps) => {
  let previous = null;
  return steps.map(([board, view]) => (previous = callerState(board, view, previous)));
};

test("the caller waits for a first state and repeats nothing", () => {
  assert.deepEqual(
    [callerState(undefined, undefined)].map(({ darts, mode, player, route, count }) => [darts, mode, player, route, count]),
    [[0, "idle", null, [], { kind: "score", score: 0 }]]
  );
  const state = callerState(visit(), x01());
  assert.deepEqual(callerCalls(null, state, all), []);
  assert.deepEqual(callerCalls(state, state, all), []);
});

test("between games the third dart calls the visit on the board, a 180 with a fanfare", () => {
  const idle = { mode: "idle" };
  const two = callerState(visit(dart(20, 3), dart(20, 3)), idle);
  const three = callerState(visit(dart(20, 3), dart(20, 3), dart(20, 1)), idle, two);
  assert.deepEqual(callerCalls(two, three, all), [{ kind: "score", score: 140 }]);
  const maximum = callerState(visit(dart(20, 3), dart(20, 3), dart(20, 3)), idle, two);
  assert.deepEqual(calls(two, maximum), ["score", "fanfare"]);
  assert.deepEqual(calls(two, maximum, { ...all, call_sounds: false }), ["score"]);
  assert.deepEqual(calls(two, maximum, { ...all, call_scores: false }), []);
  const misses = callerState(visit(dart(0, 0), dart(5, 0), dart(20, 0)), idle, two);
  assert.deepEqual(callerCalls(two, misses, all), [{ kind: "score", score: 0 }]);
});

test("in X01 the caller calls the points the visit took off, a 180 with a fanfare", () => {
  const states = play([
    [visit(), x01({ remaining: 501 })],
    [visit(dart(20, 3), dart(20, 3)), x01({ remaining: 381, visit: ["T20", "T20"] })],
    [visit(dart(20, 3), dart(20, 3), dart(20, 3)), x01({ remaining: 321, visit: ["T20", "T20", "T20"] })],
  ]);
  assert.deepEqual(states[2].count, { kind: "score", score: 180 });
  assert.deepEqual(calls(states[1], states[2]), ["score", "fanfare"]);
});

test("before the opening double the visit scores nothing and gets no fanfare", () => {
  const states = play([
    [visit(), x01({ remaining: 501, opened: false })],
    [visit(dart(20, 3), dart(20, 3)), x01({ remaining: 501, opened: false, visit: ["T20", "T20"] })],
    [
      visit(dart(20, 3), dart(20, 3), dart(20, 3)),
      x01({ remaining: 501, opened: false, visit: ["T20", "T20", "T20"] }),
    ],
  ]);
  assert.deepEqual(callerCalls(states[1], states[2], all), [{ kind: "score", score: 0 }]);
  // Darts before the opening double score nothing; the double and what follows do.
  const opening = play([
    [visit(), x01({ remaining: 501, opened: false })],
    [visit(dart(20, 3), dart(10, 2)), x01({ remaining: 481, visit: ["T20", "D10"] })],
    [visit(dart(20, 3), dart(10, 2), dart(20, 3)), x01({ remaining: 421, visit: ["T20", "D10", "T20"] })],
  ]);
  assert.deepEqual(callerCalls(opening[1], opening[2], all), [{ kind: "score", score: 80 }]);
});

test("a bust is called as no score only, also with more darts on the board", () => {
  const states = play([
    [visit(), x01({ remaining: 40, route: ["D20"] })],
    [visit(dart(20, 3)), x01({ remaining: 40, bust: true, visit: ["T20"] })],
    [visit(dart(20, 3), dart(5, 1), dart(1, 1)), x01({ remaining: 40, bust: true, visit: ["T20", "S5", "S1"] })],
  ]);
  assert.deepEqual(calls(states[0], states[1]), ["bust"]);
  assert.deepEqual(calls(states[1], states[2]), []);
  // A bust with the third dart: no sum of the darts before the bust.
  const late = play([
    [visit(), x01({ remaining: 60, route: ["S20", "D20"] })],
    [visit(dart(20, 1), dart(20, 1)), x01({ remaining: 20, visit: ["S20", "S20"] })],
    [
      visit(dart(20, 1), dart(20, 1), dart(19, 3)),
      x01({ remaining: 60, bust: true, visit: ["S20", "S20", "T19"] }),
    ],
  ]);
  assert.deepEqual(calls(late[1], late[2]), ["bust"]);
});

test("a game shot is called without the score, and darts after it are not called", () => {
  const states = play([
    [visit(), x01({ remaining: 40, route: ["D20"] })],
    [visit(dart(20, 2)), x01({ remaining: 0, won: true, visit: ["D20"] })],
    [visit(dart(20, 2), dart(1, 1), dart(1, 1)), x01({ remaining: 0, won: true, visit: ["D20"] })],
  ]);
  assert.deepEqual(calls(states[0], states[1]), ["leg"]);
  assert.deepEqual(calls(states[1], states[2]), []);
  const won = callerState(visit(dart(20, 2)), x01({ won: true, winner: 1, visit: ["D20"] }), states[0]);
  assert.deepEqual(callerCalls(states[0], won, all), [{ kind: "match", name: "Alex" }]);
  assert.deepEqual(calls(states[0], states[1], { ...all, call_results: false }), []);
});

test("a visit joined halfway is not called, since its start is unknown", () => {
  const joined = callerState(visit(dart(20, 1), dart(20, 1)), x01({ remaining: 461, visit: ["S20", "S20"] }));
  const three = callerState(
    visit(dart(20, 1), dart(20, 1), dart(20, 1)),
    x01({ remaining: 441, visit: ["S20", "S20", "S20"] }),
    joined
  );
  assert.deepEqual(callerCalls(joined, three, all), []);
  // The next player at the board starts a new count.
  assert.equal(callerState(visit(), x01({ player: 2, remaining: 301 }), three).start, 301);
});

test("Cricket calls the marks of the visit, party games their points, Killer and training games nothing", () => {
  const numbers = [20, 19, 18, 17, 16, 15, 25];
  const cricket = (keys, won = false) => ({
    mode: "cricket",
    cricket: { player: 1, won, winner: null, numbers, visit: keys, scores: [] },
  });
  assert.deepEqual(visitCount(cricket([]), ["T20", "D19", "S5"], null), { kind: "marks", marks: 5 });
  assert.deepEqual(visitCount(cricket([]), ["BULL", "25", "MISS"], null), { kind: "marks", marks: 3 });
  const noBull = { mode: "cricket", cricket: { won: false, numbers: [20, 19, 18, 17, 16, 15, 14] } };
  assert.deepEqual(visitCount(noBull, ["BULL", "S14"], null), { kind: "marks", marks: 1 });
  assert.equal(visitCount(cricket([], true), ["T20"], null), null);
  const two = callerState(visit(), cricket(["T20", "T19"]));
  const nine = callerState(visit(), cricket(["T20", "T19", "T18"]), two);
  assert.deepEqual(callerCalls(two, nine, all), [{ kind: "marks", marks: 9 }]);

  const party = (kind, target, won = false) => ({
    mode: "party",
    party: { kind, target, player: 1, won, winner: null, visit: [], scores: [] },
  });
  assert.deepEqual(visitCount(party("shanghai", "3"), ["S3", "T3", "S17"], null), { kind: "score", score: 12 });
  assert.deepEqual(visitCount(party("halve_it", "D"), ["D20", "BULL", "T20"], null), { kind: "score", score: 90 });
  assert.deepEqual(visitCount(party("halve_it", null), ["D20"], null), { kind: "score", score: 0 });
  assert.deepEqual(visitCount(party("halve_it", "BULL"), ["25", "BULL", "S20"], null), { kind: "score", score: 75 });
  assert.equal(visitCount(party("shanghai", "3", true), ["S3", "D3", "T3"], null), null);
  assert.equal(visitCount(party("killer", null), ["D7", "D7", "D7"], null), null);
  assert.equal(visitCount({ mode: "drill" }, [], null), null);
  assert.equal(visitCount({ mode: "bulloff" }, [], null), null);
  assert.equal(callerState(visit(dart(20, 3), dart(20, 3), dart(20, 3)), { mode: "drill" }).darts, 0);
});

test("the next player hears what they require whenever a route exists, up to 180 without double out", () => {
  const pulled = callerState(visit(dart(20, 3)), x01({ remaining: 141, visit: ["T20"] }));
  const sam = callerState(visit(), x01({ player: 2, name: "Sam", remaining: 81, route: ["T15", "D18"] }), pulled);
  assert.deepEqual(callerCalls(pulled, sam, all), [
    { kind: "require", name: "Sam", player: 2, players: 2, remaining: 81 },
  ]);
  const single = callerState(
    visit(),
    x01({ player: 2, name: "Sam", remaining: 180, route: ["T20", "T20", "T20"] }),
    pulled
  );
  assert.deepEqual(calls(pulled, single), ["require"]);
  const far = callerState(visit(), x01({ player: 2, remaining: 301, route: [] }), pulled);
  assert.deepEqual(callerCalls(pulled, far, all), []);
  assert.deepEqual(calls(pulled, sam, { ...all, call_checkouts: false }), []);
  const cricket = { mode: "cricket", cricket: { player: 2, won: false, winner: null, numbers: [], visit: [], scores: [] } };
  assert.deepEqual(callerCalls(pulled, callerState(visit(), cricket), all), []);
});

test("dart names follow the integration's hit names", () => {
  assert.deepEqual(
    [dart(20, 3), dart(16, 2), dart(5, 1), dart(25, 1), dart(25, 2), dart(0, 0), dart(7, 0), dart(3, 4)].map(dartKey),
    ["T20", "D16", "S5", "25", "BULL", "MISS", "MISS", "S3"]
  );
});

test("calls read like a caller in the card's language", () => {
  const t = (key) =>
    ({
      say_require: "{name}, you require {remaining}",
      say_require_alone: "You require {remaining}",
      say_bust: "No score",
      say_no_score: "No score",
      say_mark: "One mark",
      say_marks: "{marks} marks",
      say_leg: "Game shot, and the leg!",
      say_match: "Game shot, and the match, {name}!",
      score_player: "Player",
    })[key] ?? key;
  assert.equal(callerText({ kind: "score", score: 180 }, t), "180");
  assert.equal(callerText({ kind: "score", score: 0 }, t), "No score");
  assert.equal(callerText({ kind: "marks", marks: 9 }, t), "9 marks");
  assert.equal(callerText({ kind: "marks", marks: 1 }, t), "One mark");
  assert.equal(callerText({ kind: "marks", marks: 0 }, t), "No score");
  assert.equal(callerText({ kind: "require", name: "Sam", player: 2, players: 2, remaining: 81 }, t), "Sam, you require 81");
  assert.equal(callerText({ kind: "require", name: null, player: 1, players: 2, remaining: 40 }, t), "Player 1, you require 40");
  assert.equal(callerText({ kind: "require", name: "Alex", player: 1, players: 1, remaining: 40 }, t), "You require 40");
  assert.equal(callerText({ kind: "bust" }, t), "No score");
  assert.equal(callerText({ kind: "leg" }, t), "Game shot, and the leg!");
  assert.equal(callerText({ kind: "match", name: "Alex" }, t), "Game shot, and the match, Alex!");
  assert.equal(callerText({ kind: "match", name: null }, t), "Game shot, and the match!");
  assert.equal(callerText({ kind: "fanfare" }, t), "");
});
