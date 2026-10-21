// Bermuda, Round the World and Gotcha, the games of play.autodarts.io, on the
// scoreboard, at the aim, in the caller and in the new game screen.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  aimBeds,
  callerCalls,
  callerState,
  gameRules,
  gameView,
  lobbyGames,
  partyView,
  scoreboardHtml,
  visitCount,
} from "../../custom_components/homedarts/frontend/homedarts-card.js";

const ui = {
  t: (key) => ({ gotcha_left: "{points} to go" })[key] ?? key,
  format: (value, digits) => (Number.isFinite(value) ? value.toFixed(digits) : "–"),
  percent: (value, digits = 0) => (Number.isFinite(value) ? `${value.toFixed(digits)} %` : "–"),
  label: (key) => (key === "BULL" ? "Bull" : key),
  date: (value) => value,
  name: "Dartboard",
  stats: {},
};
const party = (game, attributes) => ({ state: "unknown", attributes: { game, player: 1, ...attributes } });
const view = (state) => gameView((name) => ({ practice: state })[name]);
const board = (state) => scoreboardHtml(view(state), ui);

test("Bermuda aims at the bullseye alone in its last round", () => {
  const last = party("bermuda", {
    round: 13,
    rounds: 13,
    target: "50",
    scores: [{ player: 1, points: 120 }],
  });
  assert.deepEqual(aimBeds(view(last)), ["Bull"]);
  const html = board(last);
  assert.equal(html.title, "party_bermuda");
  assert.equal(html.meta, "drill_round 13/13");
  assert.match(html.main, /<span class="bed">bullseye_target<\/span>/);
  // The round before, both bulls count, as in Halve-It.
  assert.deepEqual(aimBeds(view(party("bermuda", { target: "25", scores: [] }))), ["Bull", "25"]);
  // Bermuda finds the score of a visit by its target, a miss halving nothing for the caller.
  const counting = view(party("bermuda", { target: "D", visit: ["D20", "S20", "BULL"], scores: [] }));
  assert.deepEqual(visitCount(counting, ["D20", "S20", "BULL"], null), { kind: "score", score: 90 });
});

test("Round the World shows how far every player has come round the board", () => {
  const world = party("round_the_world", {
    target: "4",
    scored: 6,
    scores: [
      { player: 1, name: "Alex", points: 6, progress: 3 },
      { player: 2, name: "Sam", points: 0, progress: 0 },
      { player: 3, name: "Kim", points: 0, progress: "far" },
    ],
  });
  const parsed = partyView(world);
  assert.deepEqual(
    parsed.scores.map((score) => score.progress),
    [3, 0, null]
  );
  assert.equal(parsed.scored, 6);
  const html = board(world);
  assert.match(html.main, /3\/21/);
  assert.match(html.main, /0\/21/);
  assert.match(html.main, /<span class="bed">4<\/span>/);
  // The caller says what the integration counted, as the target moves with every hit.
  assert.deepEqual(visitCount(view(world), ["S1", "S2", "S3"], null), { kind: "score", score: 6 });
  assert.equal(visitCount(view(party("round_the_world", { scores: [] })), ["S1"], null), null);
});

test("Gotcha shows the points to go and calls a visit that went too far", () => {
  const scores = [
    { player: 1, name: "Alex", points: 280, left: 21 },
    { player: 2, name: "Sam", points: 100, left: 201 },
  ];
  const gotcha = party("gotcha", { scored: 60, visit: ["T20"], scores });
  const parsed = partyView(gotcha);
  assert.equal(parsed.bust, false);
  assert.deepEqual(
    parsed.scores.map((score) => score.left),
    [21, 201]
  );
  const html = board(gotcha);
  // The player at the board sees it in the note, the others beside their names.
  assert.match(html.main, /21 to go/);
  assert.match(html.main, /201 to go/);
  assert.deepEqual(visitCount(view(gotcha), ["T20"], null), { kind: "score", score: 60 });
  const bust = party("gotcha", { scored: 0, bust: true, visit: ["T20", "T20"], scores });
  assert.equal(visitCount(view(bust), ["T20", "T20"], null), null);
  const before = callerState({}, view(party("gotcha", { scored: 60, visit: ["T20"], scores })));
  const after = callerState({}, view(bust), before);
  assert.equal(after.bust, true);
  assert.deepEqual(callerCalls(before, after, {}), [{ kind: "bust" }]);
  // The winner has nothing to go.
  const won = party("gotcha", {
    winner: 2,
    won: true,
    scores: [
      { player: 1, name: "Alex", points: 86, left: 15 },
      { player: 2, name: "Sam", points: 101, left: 0 },
    ],
  });
  assert.match(board(won).main, /15 to go/);
  assert.doesNotMatch(board(won).main, /0 to go/);
});

test("the new game screen offers the three games among the party games", () => {
  const groups = lobbyGames(["501", "bermuda", "round_the_world", "gotcha", "killer"], []);
  assert.deepEqual(groups, [
    { group: "x01", games: ["501"] },
    { group: "party", games: ["bermuda", "round_the_world", "gotcha", "killer"] },
  ]);
  for (const game of ["bermuda", "round_the_world", "gotcha"]) {
    assert.equal(gameRules(game).maxPlayers, 8);
    assert.equal(gameRules(game).minPlayers, 1);
  }
});
