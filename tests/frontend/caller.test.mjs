// The caller of the scoreboard: what it says, and when. It calls only what counts.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  callerCalls,
  callerState,
  callerText,
  celebrationHtml,
  celebrationOf,
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

test("in X01 a visit counts from where the integration says it started, also after a state the card missed", () => {
  // Alex alone scores 140; the takeout goes by unseen, and the next visit scores 3, not 143.
  const states = play([
    [visit(), x01({ remaining: 501, visitFrom: 501 })],
    [
      visit(dart(20, 3), dart(20, 3), dart(20, 1)),
      x01({ remaining: 361, visitFrom: 501, visit: ["T20", "T20", "S20"] }),
    ],
    [visit(dart(1, 1), dart(1, 1), dart(1, 1)), x01({ remaining: 358, visitFrom: 361, visit: ["S1", "S1", "S1"] })],
  ]);
  assert.deepEqual(callerCalls(states[0], states[1], all), [{ kind: "score", score: 140 }]);
  assert.deepEqual(callerCalls(states[1], states[2], all), [{ kind: "score", score: 3 }]);
  // A visit first seen with two darts is called when its third dart lands.
  const sam = play([
    [visit(), x01({ remaining: 358, visitFrom: 358 })],
    [
      visit(dart(20, 1), dart(20, 1)),
      x01({ player: 2, name: "Sam", remaining: 261, visitFrom: 301, visit: ["S20", "S20"] }),
    ],
    [
      visit(dart(20, 1), dart(20, 1), dart(20, 1)),
      x01({ player: 2, name: "Sam", remaining: 241, visitFrom: 301, visit: ["S20", "S20", "S20"] }),
    ],
  ]);
  assert.deepEqual(callerCalls(sam[1], sam[2], all), [{ kind: "score", score: 60 }]);
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
  // The bull of Halve-It (25) takes both bull beds.
  assert.deepEqual(visitCount(party("halve_it", "25"), ["25", "BULL", "S20"], null), { kind: "score", score: 75 });
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

test("the scoreboard celebrates a 180, a ton, nine marks, a game shot and the match", () => {
  const state = (overrides) => ({ darts: 0, visit: "", count: null, won: false, winner: null, ...overrides });
  const visit = (count) => state({ darts: 3, visit: "T20 T20 T20", count });
  const score = (value) => ({ kind: "score", score: value });
  assert.equal(celebrationOf(null, visit(score(180))), null);
  assert.equal(celebrationOf(state(), visit(score(180))), "max");
  assert.equal(celebrationOf(state(), visit(score(140))), "ton40");
  assert.equal(celebrationOf(state(), visit(score(100))), "ton");
  assert.equal(celebrationOf(state(), visit(score(99))), null);
  assert.equal(celebrationOf(state(), visit({ kind: "marks", marks: 9 })), "nine");
  assert.equal(celebrationOf(state(), visit({ kind: "marks", marks: 8 })), null);
  assert.equal(celebrationOf(state(), visit({ kind: "runs", runs: 9 })), null);
  // The same visit once more is no new moment, nor is a visit of fewer darts.
  assert.equal(celebrationOf(visit(score(180)), visit(score(180))), null);
  assert.equal(celebrationOf(state(), state({ darts: 2, count: score(120) })), null);
  // A game shot, and the match before the leg that decided it.
  assert.equal(celebrationOf(state(), state({ won: true })), "leg");
  assert.equal(celebrationOf(state(), state({ won: true, winner: 1 })), "match");
  assert.equal(celebrationOf(state({ won: true }), state({ won: true })), null);

  // Confetti flies its own way for every piece, the same in every run.
  const html = celebrationHtml("max", 3);
  assert.match(html, /^<div class="moment max" data-round="3" style="--c:#ffd60a"><div class="glow"><\/div><i /);
  assert.equal((html.match(/<i /g) ?? []).length, 36);
  assert.equal(html, celebrationHtml("max", 3));
  assert.equal((celebrationHtml("match", 1).match(/<i /g) ?? []).length, 48);
  assert.equal((celebrationHtml("leg", 1).match(/<i /g) ?? []).length, 28);
  // A ton glows in the colour of its visits, without confetti.
  assert.equal(celebrationHtml("ton", 1), '<div class="moment ton" data-round="1" style="--c:#43b581"><div class="glow"></div></div>');
  assert.match(celebrationHtml("ton40", 1), /--c:#ff8c42/);
  assert.match(celebrationHtml("nine", 1), /--c:#ffd60a/);
});

test("the caller names the winner of a leg or a match the round limit decides", () => {
  const limit = (name) => ({ ended: "2026-10-14T20:00:00", name });
  const before = callerState(visit(), x01({ limit: null }));
  const leg = callerState(visit(), x01({ limit: limit("Sam") }), before);
  assert.deepEqual(callerCalls(before, leg, all), [{ kind: "limit_leg", name: "Sam" }]);
  // Once called, and not when results are not called.
  assert.deepEqual(calls(leg, callerState(visit(), x01({ limit: limit("Sam") }), leg)), []);
  assert.deepEqual(calls(before, leg, { ...all, call_results: false }), []);
  const won = callerState(visit(), x01({ winner: 2, limit: limit("Sam") }), before);
  assert.deepEqual(callerCalls(before, won, all), [{ kind: "limit_match", name: "Sam" }]);
  const t = (key) =>
    ({
      say_limit_leg: "Round limit, and the leg, {name}!",
      say_limit_match: "Round limit, and the match, {name}!",
    })[key] ?? key;
  assert.equal(callerText({ kind: "limit_leg", name: "Sam" }, t), "Round limit, and the leg, Sam!");
  assert.equal(callerText({ kind: "limit_leg", name: null }, t), "Round limit, and the leg!");
  assert.equal(callerText({ kind: "limit_match", name: "Sam" }, t), "Round limit, and the match, Sam!");
});

// For blind and low-vision players ---------------------------------------------------------

test("every dart is called as it lands, by its bed or its points, before what it decided", () => {
  const bed = { ...all, call_darts: "bed" };
  const from = (remaining, keys, overrides = {}) => x01({ remaining, visitFrom: 501, visit: keys, ...overrides });
  const states = play([
    [visit(), x01({ remaining: 501, visitFrom: 501 })],
    [visit(dart(20, 3)), from(441, ["T20"])],
    [visit(dart(20, 3), dart(25, 2)), from(391, ["T20", "BULL"])],
    [visit(dart(20, 3), dart(25, 2), dart(0, 0)), from(391, ["T20", "BULL", "MISS"])],
  ]);
  assert.deepEqual(callerCalls(states[0], states[1], bed), [{ kind: "dart", key: "T20", by: "bed" }]);
  assert.deepEqual(callerCalls(states[1], states[2], bed), [{ kind: "dart", key: "BULL", by: "bed" }]);
  assert.deepEqual(callerCalls(states[2], states[3], bed), [
    { kind: "dart", key: "MISS", by: "bed" },
    { kind: "score", score: 110 },
  ]);
  assert.deepEqual(callerCalls(states[0], states[1], { ...all, call_darts: "score" }), [
    { kind: "dart", key: "T20", by: "score" },
  ]);
  // Off, as before, also for a value the card does not know.
  for (const option of [undefined, "off", "every", true]) {
    assert.deepEqual(calls(states[0], states[1], { ...all, call_darts: option }), [], String(option));
  }
  // A state seen twice calls nothing again, and darts that came at once are called in order.
  assert.deepEqual(callerCalls(states[1], states[1], bed), []);
  assert.deepEqual(calls(states[0], states[2], bed), ["dart", "dart"]);
  // A corrected dart is called again, with the darts after it; a dart taken back calls nothing.
  const corrected = callerState(visit(), from(431, ["S20", "BULL"]), states[2]);
  assert.deepEqual(callerCalls(states[2], corrected, bed).map((call) => call.key), ["S20", "BULL"]);
  assert.deepEqual(callerCalls(states[2], callerState(visit(), from(441, ["T20"]), states[2]), bed), []);
  // The darts of the next visit are new, also where they start alike: Sam's, or Alex's after a
  // takeout the card missed.
  const sam = callerState(visit(), from(441, ["T20"], { player: 2, name: "Sam" }), states[3]);
  assert.deepEqual(calls(states[3], sam, bed), ["dart"]);
  const again = callerState(visit(), x01({ remaining: 331, visitFrom: 391, visit: ["T20"] }), states[3]);
  assert.deepEqual(calls(states[3], again, bed), ["dart"]);
  // Between games the darts on the board, and in a training game its darts.
  const idle = { mode: "idle" };
  const empty = callerState(visit(), idle);
  assert.deepEqual(callerCalls(empty, callerState(visit(dart(5, 1)), idle, empty), bed), [
    { kind: "dart", key: "S5", by: "bed" },
  ]);
  const drill = (thrown) => ({ mode: "drill", drill: { kind: "doubles", target: "D1", thrown, route: [] } });
  const first = callerState(visit(), drill([]));
  assert.deepEqual(calls(first, callerState(visit(), drill(["D1"]), first), bed), ["dart"]);
  // The darts on the board when a game ends were called in the game already.
  const after = callerState(visit(dart(20, 3), dart(25, 2), dart(0, 0)), idle, states[3]);
  assert.deepEqual(callerCalls(states[3], after, bed).filter((call) => call.kind === "dart"), []);
});

test("a dart, a route and a target read like a caller in the card's language", () => {
  const t = (key) =>
    ({
      say_dart_double: "Double {number}",
      say_dart_treble: "Treble {number}",
      say_dart_bull: "Bull",
      say_bullseye: "Bullseye",
      say_dart_miss: "Miss",
      say_route: "{remaining}: {route}",
      say_target: "Target: {target}",
      any_double: "Any double",
      any_treble: "Any treble",
    })[key] ?? key;
  const beds = ["T20", "D16", "S5", "25", "BULL", "MISS"];
  assert.deepEqual(
    beds.map((key) => callerText({ kind: "dart", key, by: "bed" }, t)),
    ["Treble 20", "Double 16", "5", "25", "Bull", "Miss"]
  );
  assert.deepEqual(
    beds.map((key) => callerText({ kind: "dart", key, by: "score" }, t)),
    ["60", "32", "5", "25", "50", "Miss"]
  );
  assert.equal(callerText({ kind: "route", route: ["T19", "D12"] }, t), "Treble 19, Double 12");
  assert.equal(callerText({ kind: "route", route: ["S20", "BULL"], remaining: 70 }, t), "70: 20, Bull");
  assert.deepEqual(
    ["20", "D16", "T20", "D", "T", "25", "50", "BULL"].map((target) => callerText({ kind: "target", target }, t)),
    [
      "Target: 20",
      "Target: Double 16",
      "Target: Treble 20",
      "Target: Any double",
      "Target: Any treble",
      "Target: Bull",
      "Target: Bullseye",
      "Target: Bullseye",
    ]
  );
});

test("with the route on, the caller says where the checkout goes, after each dart again", () => {
  const route = { ...all, call_route: true };
  const pulled = callerState(visit(dart(20, 3)), x01({ remaining: 141, visit: ["T20"] }));
  const sam = callerState(visit(), x01({ player: 2, name: "Sam", remaining: 81, route: ["T19", "D12"] }), pulled);
  assert.deepEqual(callerCalls(pulled, sam, route), [
    { kind: "require", name: "Sam", player: 2, players: 2, remaining: 81 },
    { kind: "route", route: ["T19", "D12"] },
  ]);
  // Without what the player requires, the route names the score; off, as before.
  assert.deepEqual(callerCalls(pulled, sam, { ...route, call_checkouts: false }), [
    { kind: "route", route: ["T19", "D12"], remaining: 81 },
  ]);
  assert.deepEqual(calls(pulled, sam), ["require"]);
  // A dart that leaves another finish: the route of the darts left, with the score.
  const turn = (remaining, keys, overrides = {}) =>
    x01({ player: 2, name: "Sam", remaining, route: ["T10", "D16"], visit: keys, ...overrides });
  const single = callerState(visit(), turn(62, ["S19"]), sam);
  assert.deepEqual(callerCalls(sam, single, route), [{ kind: "route", route: ["T10", "D16"], remaining: 62 }]);
  // A miss that leaves the route as it was says nothing; one that changes it says the new one.
  const miss = callerState(visit(), turn(62, ["S19", "MISS"]), single);
  assert.deepEqual(callerCalls(single, miss, route), []);
  const last = callerState(visit(), turn(62, ["S19", "MISS"], { route: ["BULL"] }), single);
  assert.deepEqual(calls(single, last, route), ["route"]);
  // Nothing after the third dart, a bust or a game shot, without a route, or for the bot.
  const third = callerState(visit(), turn(30, ["S19", "MISS", "S12"], { route: ["D15"] }), miss);
  assert.deepEqual(calls(miss, third, route), ["score"]);
  const bust = callerState(visit(), turn(62, ["S19", "T20"], { bust: true }), single);
  assert.deepEqual(calls(single, bust, route), ["bust"]);
  const won = callerState(visit(), turn(0, ["S19", "D31"], { winner: 2 }), single);
  assert.deepEqual(calls(single, won, route), ["match"]);
  const none = callerState(visit(), turn(42, ["S19", "S20"], { route: [] }), single);
  assert.deepEqual(calls(single, none, route), []);
  const bot = callerState(
    visit(),
    x01({
      player: 2,
      name: null,
      remaining: 81,
      route: ["T19", "D12"],
      scores: [
        { player: 1, name: "Alex" },
        { player: 2, name: null, bot: true },
      ],
    }),
    pulled
  );
  assert.deepEqual(calls(pulled, bot, route), ["require"]);
  // The checkout training calls its route as X01 does, and has no target besides.
  const idle = callerState(visit(), { mode: "idle" });
  const training = {
    mode: "drill",
    drill: { kind: "checkout", target: "81", remaining: 81, route: ["T19", "D12"], thrown: [] },
  };
  const start = callerState(visit(), training, idle);
  assert.deepEqual(calls(idle, start, { ...route, call_target: true }), ["require", "route"]);
  assert.equal(start.target, null);
});

test("with the target on, training and party games call what to aim at next", () => {
  const target = { ...all, call_target: true };
  const idle = callerState(visit(), { mode: "idle" });
  const clock = (aim, thrown = [], overrides = {}) => ({
    mode: "drill",
    drill: { kind: "around_the_clock", target: aim, finished: false, thrown, route: [], ...overrides },
  });
  const one = callerState(visit(), clock("1"), idle);
  assert.deepEqual(callerCalls(idle, one, target), [{ kind: "target", target: "1" }]);
  assert.deepEqual(calls(idle, one), []);
  // A hit moves the target on at once, after the dart; a miss calls no target again.
  const two = callerState(visit(), clock("2", ["S1"]), one);
  assert.deepEqual(callerCalls(one, two, { ...target, call_darts: "bed" }), [
    { kind: "dart", key: "S1", by: "bed" },
    { kind: "target", target: "2" },
  ]);
  assert.deepEqual(callerCalls(two, callerState(visit(), clock("2", ["S1", "S5"]), two), target), []);
  // A finished training game has no target.
  assert.equal(callerState(visit(), clock("D20", [], { kind: "doubles", finished: true })).target, null);
  assert.equal(callerState(visit(), clock(null)).target, null);
  // In a party game each player hears the target as their turn comes; the bot needs none, and
  // a decided game or one waiting for players has none.
  const party = (overrides = {}) => ({
    mode: "party",
    party: {
      kind: "shanghai",
      target: "3",
      player: 1,
      won: false,
      winner: null,
      needsPlayers: null,
      visit: [],
      scores: [
        { player: 1, name: "Alex" },
        { player: 2, name: "Sam" },
        { player: 3, name: null, bot: true },
      ],
      ...overrides,
    },
  });
  const alex = callerState(visit(), party(), idle);
  const sam = callerState(visit(), party({ player: 2 }), alex);
  assert.deepEqual(callerCalls(alex, sam, target), [{ kind: "target", target: "3" }]);
  assert.deepEqual(callerCalls(sam, callerState(visit(), party({ player: 3 }), sam), target), []);
  for (const overrides of [{ won: true }, { winner: 1 }, { needsPlayers: 2 }, { target: null }]) {
    assert.equal(callerState(visit(), party(overrides)).target, null, JSON.stringify(overrides));
  }
});
