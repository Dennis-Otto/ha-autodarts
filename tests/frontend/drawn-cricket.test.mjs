// Random and Hidden Cricket on the chalkboard, in the caller and in the lobby: six
// numbers drawn for every leg and the bull, which Hidden Cricket shows once hit.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  callerCalls,
  callerState,
  callerText,
  cricketBeds,
  cricketView,
  gameGroup,
  gameRules,
  gameView,
  lobbyGames,
  scoreboardHtml,
  visitCount,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const ui = {
  t: (key) => key,
  format: (value, digits) => (Number.isFinite(value) ? value.toFixed(digits) : "–"),
  percent: (value, digits = 0) => (Number.isFinite(value) ? `${value.toFixed(digits)} %` : "–"),
  label: (key) => (key === "BULL" ? "Bull" : key),
  date: (value) => value,
  name: "Dartboard",
  stats: {},
};
const OPEN = [0, 0, 0, 0, 0, 0, 0];
const all = { call_scores: true, call_checkouts: true, call_results: true, call_sounds: true };
const visit = () => ({ state: "0", attributes: { throws: [] } });

// The practice game of a drawn Cricket game between two players.
const practice = (game, numbers, extra = {}) => ({
  state: "unknown",
  attributes: {
    game,
    numbers,
    player: 1,
    target: "T14",
    visit: [],
    counted: [],
    scores: [
      { player: 1, marks: [0, 0, 0, 1, 0, 0, 0], points: 0 },
      { player: 2, marks: OPEN, points: 0 },
    ],
    ...extra,
  },
});
const view = (state) => gameView((name) => ({ practice: state })[name]);

test("Hidden Cricket shows a question mark for every number that does not show yet", () => {
  const hidden = practice("hidden_cricket", [null, null, null, 14, null, null, 25]);
  const cricket = cricketView(hidden);
  assert.deepEqual(cricket.numbers, [null, null, null, 14, null, null, 25]);
  const html = scoreboardHtml(view(hidden), ui);
  assert.equal(html.title, "cricket_hidden_cricket");
  assert.equal(html.meta, "hidden_cricket_hint");
  const marks = '<span role="img" aria-label="cricket_hidden">?</span>';
  assert.equal(html.main.split(marks).length - 1, 5);
  // The number a dart showed is the target, and the hidden ones are never one.
  assert.match(html.main, /<tr class="target"><th>14<\/th>/);
  assert.match(html.main, /<tr class=""><th>Bull<\/th>/);
  assert.deepEqual(cricketBeds(cricket), ["T14"]);
  // Only marks on the numbers that show count for the caller.
  assert.deepEqual(visitCount({ mode: "cricket", cricket }, ["S14", "T20", "MISS"], null), {
    kind: "marks",
    marks: 1,
  });
});

test("Random Cricket shows the numbers it drew, and no other game hides any", () => {
  const drawn = practice("random_cricket", [18, 14, 11, 7, 5, 2, 25]);
  const html = scoreboardHtml(view(drawn), ui);
  assert.equal(html.title, "cricket_random_cricket");
  assert.equal(html.meta, "random_cricket_hint");
  for (const number of [18, 14, 11, 7, 5, 2]) assert.match(html.main, new RegExp(`<th>${number}</th>`));
  assert.doesNotMatch(html.main, /cricket_hidden/);
  // A hidden number in another game is no draw: the numbers of Cricket stand in.
  const odd = cricketView(practice("random_cricket", [null, 14, 11, 7, 5, 2, 25]));
  assert.deepEqual(odd.numbers, [20, 19, 18, 17, 16, 15, 25]);
});

test("the caller names the numbers of a leg of Random Cricket and every number Hidden Cricket shows", () => {
  const idle = callerState(visit(), { mode: "idle" });
  const first = callerState(visit(), view(practice("random_cricket", [18, 14, 11, 7, 5, 2, 25])), idle);
  assert.deepEqual(callerCalls(idle, first, all), [{ kind: "numbers", numbers: [18, 14, 11, 7, 5, 2] }]);
  // The same numbers are not called again; those of the next leg are.
  const again = callerState(visit(), view(practice("random_cricket", [18, 14, 11, 7, 5, 2, 25])), first);
  assert.deepEqual(callerCalls(first, again, all), []);
  const next = callerState(visit(), view(practice("random_cricket", [20, 13, 9, 6, 4, 1, 25])), again);
  assert.deepEqual(callerCalls(again, next, all), [{ kind: "numbers", numbers: [20, 13, 9, 6, 4, 1] }]);
  // Hidden Cricket says nothing of its numbers at the start, and names one once it shows.
  const hidden = callerState(visit(), view(practice("hidden_cricket", [null, null, null, null, null, null, 25])), next);
  assert.deepEqual(callerCalls(next, hidden, all), []);
  const shown = callerState(visit(), view(practice("hidden_cricket", [null, 9, null, 14, null, null, 25])), hidden);
  assert.deepEqual(callerCalls(hidden, shown, all), [
    { kind: "shown", number: 9 },
    { kind: "shown", number: 14 },
  ]);
  // Without the calls of the visits, it stays silent.
  assert.deepEqual(callerCalls(hidden, shown, { ...all, call_scores: false }), []);
  const t = (key) => ({ say_numbers: "Numbers {numbers} and the bull", say_shown: "{number} is in" })[key];
  assert.equal(callerText({ kind: "numbers", numbers: [18, 14, 2] }, t), "Numbers 18, 14, 2 and the bull");
  assert.equal(callerText({ kind: "shown", number: 9 }, t), "9 is in");
});

test("the lobby offers Random and Hidden Cricket with the Cricket games, teams and the bot", () => {
  const groups = lobbyGames(["off", "501", "cricket", "random_cricket", "hidden_cricket", "killer"]);
  assert.deepEqual(groups.find((group) => group.group === "cricket").games, [
    "cricket",
    "random_cricket",
    "hidden_cricket",
  ]);
  for (const game of ["random_cricket", "hidden_cricket"]) {
    assert.equal(gameGroup(game), "cricket");
    const rules = gameRules(game);
    assert.deepEqual([rules.teams, rules.bot, rules.maxPlayers], [true, true, 4]);
  }
});
