// Teams, start scores, the Cricket variants, Golf, Baseball, Count-Up and the
// new training games in the shared game views, the caller and the history.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  aimBeds,
  callerCalls,
  callerState,
  callerText,
  cricketTable,
  cricketView,
  dashboardStrategy,
  drillBeds,
  drillView,
  gameView,
  livePanel,
  partyView,
  playersHtml,
  playersView,
  practiceView,
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
const board = (states) => scoreboardHtml(gameView((name) => states[name]), ui);
const TEAMS = [
  { team: 1, name: "Alex & Kim", players: [1, 3] },
  { team: 2, name: null, players: [2, 4] },
];
const teamScores = (remaining, extra = {}) =>
  [
    { player: 1, name: "Alex", remaining: remaining[0], average: 60.5 },
    { player: 2, name: "Sam", remaining: remaining[1], average: null },
    { player: 3, name: "Kim", remaining: remaining[0], average: 45 },
    { player: 4, name: null, remaining: remaining[1], average: null },
  ].map((score) => ({ legs: 1, sets: 0, team: 2 - (score.player % 2), start: 301, ...score, ...extra }));

test("a team match shows two teams with the partner at the board", () => {
  const practice = {
    state: "141",
    attributes: {
      game: 301,
      player: 3,
      name: "Kim",
      checkout: "T20 T15 D18",
      legs_to_win: 3,
      teams: [...TEAMS, { team: "x" }, null],
      scores: teamScores([141, 201]),
    },
  };
  const view = practiceView(practice);
  assert.deepEqual(view.teams, [
    { team: 1, players: [1, 3] },
    { team: 2, players: [2, 4] },
  ]);
  assert.deepEqual([view.scores[2].team, view.scores[2].start], [1, 301]);
  const html = board({ practice });
  assert.match(html.main, /<div class="players n2 teams">/);
  assert.match(
    html.main,
    /<div class="player active" aria-current="true"><div class="name">Alex &#38; Kim<\/div><div class="big">141<\/div><div class="route"><span class="bed">T20<\/span>/
  );
  assert.match(html.main, /<div class="members"><span>Alex Ø 60\.5<\/span> · <b>Kim Ø 45\.0<\/b><\/div>/);
  assert.match(html.main, /<div class="name">Sam &#38; score_player 4<\/div><div class="big">201<\/div>/);
  assert.match(html.main, /<div class="details">score_legs 1<\/div>/);
  // Everybody starts from 301: no start scores to show.
  assert.doesNotMatch(html.main, /badge/);
  // The live card lists the teams and says who throws.
  const panel = livePanel(gameView((name) => ({ practice })[name]), ui);
  assert.equal(panel.meta, "Kim score_turn");
  assert.match(panel.rows, /<span class="who">Alex &#38; Kim<\/span>/);
});

test("the winning team gets the banner, and a team without players is left out", () => {
  const practice = {
    state: "0",
    attributes: { game: 301, player: 1, winner: 1, teams: TEAMS, scores: teamScores([0, 40]) },
  };
  const html = board({ practice });
  assert.equal(html.banner, "Alex & Kim score_winners");
  assert.match(html.main, /<div class="player winner"><div class="name">Alex &#38; Kim/);
  const panel = livePanel(gameView((name) => ({ practice })[name]), ui);
  assert.equal(panel.route, '<span class="note won">Alex &#38; Kim score_winners</span>');
  // Teams whose players are missing from the scores show every player instead.
  const lonely = {
    state: "40",
    attributes: { game: 301, teams: [{ team: 1, players: [7] }], scores: teamScores([40, 40]).slice(0, 2) },
  };
  assert.match(board({ practice: lonely }).main, /<div class="players n2">.*Alex.*Sam/);
});

test("start scores of their own show beside the names", () => {
  const scores = [
    { player: 1, name: "Alex", remaining: 501, start: 501, legs: 0, sets: 0 },
    { player: 2, name: "Sam", remaining: 301, start: 301, legs: 0, sets: 0 },
    { player: 3, name: "Kim", remaining: 501, start: null, legs: 0, sets: 0 },
  ];
  const practice = { state: "501", attributes: { game: 501, scores } };
  const html = board({ practice });
  assert.match(html.main, /<div class="name">Alex <span class="badge">501<\/span><\/div>/);
  assert.match(html.main, /<div class="name">Sam <span class="badge">301<\/span><\/div>/);
  assert.match(html.main, /<div class="name">Kim<\/div>/);
  const panel = livePanel(gameView((name) => ({ practice })[name]), ui);
  assert.match(panel.rows, /<span class="who">Sam <span class="badge">301<\/span><\/span>/);
  // A team with a start score of its own shows it on the team.
  const teams = {
    state: "301",
    attributes: {
      game: 501,
      teams: TEAMS,
      scores: teamScores([501, 301]).map((score) => ({ ...score, start: score.remaining })),
    },
  };
  assert.match(board({ practice: teams }).main, /Sam &#38; score_player 4 <span class="badge">301<\/span>/);
});

test("Tactics and Cut-Throat Cricket play their own numbers and rules", () => {
  const numbers = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 25];
  const tactics = {
    state: "unknown",
    attributes: {
      game: "tactics",
      target: "T10",
      numbers,
      scores: [{ player: 1, marks: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0], points: 0 }],
    },
  };
  const view = cricketView(tactics);
  assert.equal(view.kind, "tactics");
  assert.deepEqual(view.numbers, numbers);
  const html = board({ practice: tactics });
  assert.equal(html.title, "cricket_tactics");
  assert.match(html.main, /<table class="cricket many">/);
  assert.equal((html.main.match(/<tr/g) ?? []).length, 1 + 12 + 1);
  assert.deepEqual(aimBeds(gameView((name) => ({ practice: tactics })[name])), ["T10"]);
  const cut = { state: "unknown", attributes: { ...tactics.attributes, game: "cut_throat", numbers: undefined } };
  const cutHtml = board({ practice: { ...cut, attributes: { ...cut.attributes, scores: [] } } });
  assert.equal(cutHtml.title, "cricket_cut_throat");
  assert.equal(cutHtml.meta, "cut_throat_hint");
  assert.match(cricketTable(cricketView(cut), ui), /<table class="cricket">/);
  assert.equal(livePanel(gameView((name) => ({ practice: cut })[name]), ui).title, "cricket_cut_throat");
});

test("team Cricket shows a column per team, the partner at the board in bold", () => {
  const marks = [3, 1, 0, 0, 0, 0, 0];
  const scores = [
    { player: 1, name: "Alex", marks, points: 20, mpr: 2.5, team: 1 },
    { player: 2, name: "Sam", marks: [0, 0, 0, 0, 0, 0, 0], points: 0, mpr: null, team: 2 },
    { player: 3, name: "Kim", marks, points: 20, mpr: 1.25, team: 1 },
    { player: 4, name: "Lea", marks: [0, 0, 0, 0, 0, 0, 0], points: 0, mpr: 0, team: 2 },
  ];
  const cricket = { state: "unknown", attributes: { game: "cricket", player: 3, teams: TEAMS, scores } };
  const html = board({ practice: cricket });
  assert.match(html.main, /<th class="active" aria-current="true">Alex &#38; <b>Kim<\/b><\/th><th class="">Sam &#38; Lea<\/th>/);
  assert.match(html.main, /<tr class="total"><th>cricket_points<\/th><td class="active">20<\/td><td class="">0<\/td>/);
  assert.match(html.main, /<td class="active">2\.50 · 1\.25<\/td><td class="">– · 0\.00<\/td>/);
  const won = board({ practice: { ...cricket, attributes: { ...cricket.attributes, winner: 2 } } });
  assert.equal(won.banner, "Sam & Lea score_winners");
  assert.match(won.main, /<th class="winner">Sam &#38; Lea <span class="visually-hidden">winner<\/span><\/th>/);
});

const party = (game, attributes) => ({ state: "unknown", attributes: { game, player: 1, ...attributes } });

test("Golf and Baseball keep a scorecard of every hole and inning", () => {
  const golf = party("golf", {
    round: 3,
    rounds: 9,
    target: "3",
    player: 2,
    visit: ["T3"],
    scores: [
      { player: 1, name: "Alex", points: 7, scorecard: [3, 4, 0.5] },
      { player: 2, name: "Sam", points: 10, scorecard: [5, 4] },
    ],
  });
  const view = partyView(golf);
  assert.deepEqual(view.scores[0].scorecard, [3, 4]);
  assert.equal(view.playoff, null);
  const html = board({ practice: golf });
  assert.equal(html.title, "party_golf");
  assert.equal(html.meta, "golf_hole 3/9 · golf_hint");
  assert.match(html.main, /<table class="scorecard"><thead><tr><th><\/th><th>1<\/th><th>2<\/th><th class="now">3<\/th>/);
  // The visit at the board counts for the hole being played.
  assert.match(html.main, /<tr class="active"><th>Sam<\/th><td>5<\/td><td>4<\/td><td class="now">1<\/td>/);
  assert.match(html.main, /<tr><th>Alex<\/th><td>3<\/td><td>4<\/td><td class="now"><\/td>.*<td class="total">7<\/td>/);
  assert.deepEqual(
    aimBeds(gameView((name) => ({ practice: golf })[name])),
    ["SI3", "SO3", "T3", "D3"]
  );
  // Extra holes after a tie: the others are out.
  const playoff = party("golf", {
    round: 10,
    rounds: 9,
    target: "10",
    playoff: [1, "x"],
    scores: [
      { player: 1, points: 30, scorecard: [3, 3, 3, 3, 3, 3, 3, 3, 3] },
      { player: 2, points: 40, scorecard: "none" },
    ],
  });
  const playing = board({ practice: playoff });
  assert.equal(playing.meta, "playoff · golf_hole 10 · golf_hint");
  assert.match(playing.main, /<div class="player out">/);
  assert.match(playing.main, /<th class="now">10<\/th>/);
  assert.equal(partyView(playoff).scores[1].scorecard.length, 0);
  // Alone, the scorecard has no names; a won game marks the winner.
  const alone = party("baseball", {
    round: 9,
    rounds: 9,
    winner: 1,
    scores: [{ player: 1, points: 12, scorecard: [1, 2, 3, 0, 0, 0, 0, 3, 3, 1, 5, 2, 0, 4, 1, 1, 1, 1, 1, 1, 2] }],
  });
  const done = board({ practice: alone });
  assert.equal(done.meta, "baseball_inning 9/9");
  assert.match(done.main, /<tr class="winner"><th><\/th>/);
  // Past 20 extra rounds, the numbers start from 1 again.
  assert.match(done.main, /<th>20<\/th><th>1<\/th><th class="total">total<\/th>/);
});

test("Count-Up counts rounds, and a party game without rounds none", () => {
  const countUp = party("count_up", { round: 2, rounds: 8, points: 60, scores: [{ player: 1, points: 60 }] });
  const html = board({ practice: countUp });
  assert.equal(html.meta, "drill_round 2/8");
  assert.doesNotMatch(html.main, /scorecard/);
  const panel = livePanel(gameView((name) => ({ practice: countUp })[name]), ui);
  assert.equal(panel.meta, "drill_round 2/8");
  assert.equal(panel.big, "60");
  const extra = party("count_up", { round: 9, rounds: 8, playoff: [1], scores: [{ player: 1 }] });
  assert.equal(board({ practice: extra }).meta, "playoff · drill_round 9");
  const killer = party("killer", { rounds: null, scores: [{ player: 1 }] });
  assert.equal(board({ practice: killer }).meta, "");
  assert.equal(board({ practice: party("shanghai", { rounds: 7, round: null, scores: [] }) }).meta, "");
});

const drill = (target, attributes) => ({ drill: { state: target, attributes } });

test("the new training games show their target, points and beds", () => {
  const ladder = drill("121", {
    drill: "checkout_121",
    remaining: 81,
    checkout: "T19 D12",
    attempt_visit: 2,
    attempt_visits: 3,
    attempts: 4,
    successes: 1,
    rate: 25,
    best: 124,
    visit: ["S20", 5],
  });
  const view = drillView(ladder.drill);
  assert.deepEqual([view.kind, view.best, view.thrown, view.part], ["checkout_121", 124, ["S20"], null]);
  const html = board(ladder);
  assert.equal(html.title, "drill_checkout_121");
  assert.match(html.main, /<div class="big">81<\/div>/);
  assert.match(html.main, /<span>drill_visit <b>2 \/ 3<\/b><\/span><span><b>1 \/ 4<\/b> drill_checked<\/span><span><b>25 %<\/b> <\/span><span>drill_best <b>124<\/b><\/span>/);
  assert.deepEqual(drillBeds(view), ["T19"]);

  const catch40 = drill("63", {
    drill: "catch_40",
    remaining: 63,
    checkout: "T13 D12",
    progress: 2,
    targets: 40,
    attempt_visit: 1,
    attempt_visits: 2,
    score: 5,
  });
  assert.match(
    board(catch40).main,
    /drill_round <b>3 \/ 40<\/b><\/span><span>drill_visit <b>1 \/ 2<\/b><\/span><span><b>5<\/b> drill_points/
  );
  const caught = drill("unknown", { drill: "catch_40", finished: true, score: 88, progress: 40, targets: 40 });
  assert.match(board(caught).main, /<div class="big">✓<\/div><div class="route"><span class="note won">drill_bobs_done<\/span>/);
  assert.match(board(caught).main, /<b>88<\/b> drill_points/);
  const empty = drill("unknown", { drill: "catch_40", finished: true });
  assert.match(board(empty).main, /<b>0<\/b> drill_points/);

  const jdc = drill("D7", { drill: "jdc_challenge", part: 2, progress: 12, targets: 33, score: 455, best: 980 });
  assert.match(board(jdc).main, /<div class="big">D7<\/div>.*drill_part <b>2 \/ 3<\/b>.*<b>455<\/b> drill_points.*drill_best <b>980<\/b>/);
  assert.deepEqual(drillBeds(drillView(jdc.drill)), ["D7"]);
  const shanghai = drill("12", { drill: "jdc_challenge", progress: 2, targets: 33 });
  assert.match(board(shanghai).main, /drill_part <b>1 \/ 3<\/b>.*<b>0<\/b> drill_points/);
  assert.deepEqual(drillBeds(drillView(shanghai.drill)), ["SI12", "SO12", "T12", "D12"]);

  const singles = drill("25", { drill: "singles", progress: 20, targets: 21, score: 40 });
  // The bull, where both bull beds count, reads "Bull (25/50)" in smaller type.
  assert.match(board(singles).main, /<div class="big long">bull_target<\/div>.*drill_round <b>21 \/ 21<\/b>.*<b>40<\/b> drill_points/);
  assert.deepEqual(drillBeds(drillView(singles.drill)), ["Bull", "25"]);
  const finished = drill("unknown", { drill: "singles", finished: true, progress: 21, targets: 21, score: 63 });
  assert.match(board(finished).main, /drill_round <b>21 \/ 21<\/b>/);
  // The live card shows the facts in a line.
  const panel = livePanel(gameView((name) => jdc[name]), ui);
  assert.equal(panel.meta, "drill_part 2 / 3 · 455 drill_points · drill_best 980");
});

const dart = (number, multiplier) => ({ number, multiplier });
const visit = (...darts) => ({ state: "0", attributes: { throws: darts } });
const all = { call_scores: true, call_checkouts: true, call_results: true, call_sounds: true };

test("the caller calls runs in Baseball, points in Count-Up and nothing in Golf", () => {
  const view = (kind, target, won = false) => ({
    mode: "party",
    party: { kind, target, player: 1, won, winner: null, visit: [], scores: [] },
  });
  assert.deepEqual(visitCount(view("baseball", "4"), ["T4", "S4", "D5"], null), { kind: "runs", runs: 4 });
  assert.deepEqual(visitCount(view("baseball", "4"), ["BULL"], null), { kind: "runs", runs: 0 });
  assert.deepEqual(visitCount(view("count_up", null), ["T20", "25", "MISS"], null), { kind: "score", score: 85 });
  assert.equal(visitCount(view("golf", "4"), ["T4", "T4", "T4"], null), null);
  assert.equal(visitCount(view("count_up", null, true), ["T20"], null), null);
  const t = (key) => ({ say_no_score: "No score", say_run: "One run", say_runs: "{runs} runs" })[key];
  assert.deepEqual(
    [0, 1, 5].map((runs) => callerText({ kind: "runs", runs }, t)),
    ["No score", "One run", "5 runs"]
  );
});

test("the checkout trainings call what the next attempt requires", () => {
  const training = (remaining, keys, route = ["T20", "T11", "D14"]) => ({
    mode: "drill",
    drill: { kind: "checkout_121", remaining, route, thrown: keys },
  });
  const throwing = callerState(visit(dart(20, 3)), training(61, ["T20"]));
  assert.equal(throwing.darts, 1);
  const next = callerState(visit(), training(122, []), throwing);
  assert.deepEqual(callerCalls(throwing, next, all), [
    { kind: "require", name: null, player: null, players: 0, remaining: 122 },
  ]);
  // Darts of the visit call nothing; a training without a route neither.
  assert.deepEqual(callerCalls(next, callerState(visit(dart(20, 3)), training(62, ["T20"]), next), all), []);
  const target = { mode: "drill", drill: { kind: "singles", remaining: null, route: [], thrown: [] } };
  assert.deepEqual(callerCalls(throwing, callerState(visit(), target, throwing), all), []);
});

test("the history names the new games and both winners of a team match", () => {
  const lastMatch = {
    attributes: {
      matches: [
        {
          ended: "2026-09-27T20:00:00+00:00",
          game: "tactics",
          winner: 1,
          winners: [1, 3],
          players: [
            { name: "Alex", legs: 2, team: 1 },
            { name: "Sam", legs: 1, team: 2 },
            { name: "Kim", legs: 2, team: 1 },
            { name: "Lea", legs: 1, team: 2 },
          ],
        },
        { ended: "2026-09-26T20:00:00+00:00", game: "golf", winner: 2, players: [{ name: "A" }, { name: "B" }] },
        { ended: "2026-09-25T20:00:00+00:00", game: "cut_throat", players: [{ name: "A" }] },
      ],
    },
  };
  const html = playersHtml(playersView(null, lastMatch), ui).matches;
  assert.match(html, /cricket_tactics<\/span><span><b>Alex 2<\/b> · <span>Sam 1<\/span> · <b>Kim 2<\/b> · <span>Lea 1<\/span>/);
  // A winner without legs is a match stored before 1.6: it had the legs it needed.
  assert.match(html, /party_golf<\/span><span><span>A 0<\/span> · <b>B 1<\/b>/);
  assert.match(html, /cricket_cut_throat<\/span><span><span>A 0<\/span>/);
});

test("the live view offers the team switch, the Golf and Count-Up options and the start scores", () => {
  const entity = (entity_id, translation_key) => ({ entity_id, translation_key, device_id: "dev", platform: "autodarts" });
  const entities = [
    entity("select.board_practice_game", "practice_game"),
    entity("switch.board_teams", "practice_teams"),
    entity("select.board_golf_holes", "practice_golf_holes"),
    entity("number.board_count_up_rounds", "practice_count_up_rounds"),
    entity("number.board_start_1", "practice_start"),
    entity("number.board_start_2", "practice_start"),
  ];
  const hass = {
    locale: { language: "en" },
    entities: Object.fromEntries(entities.map((item) => [item.entity_id, item])),
    devices: { dev: { id: "dev" } },
    states: {},
  };
  const [live] = dashboardStrategy(hass).views;
  assert.deepEqual(live.sections[1].cards.slice(1), [
    {
      type: "entities",
      entities: [
        "select.board_practice_game",
        "switch.board_teams",
        "select.board_golf_holes",
        "number.board_count_up_rounds",
      ],
    },
    { type: "entities", title: "Start scores (handicap)", entities: ["number.board_start_1", "number.board_start_2"] },
  ]);
});

test("a team names a missing player by number, and a scorecard needs no round count", () => {
  const practice = {
    state: "40",
    attributes: {
      game: 301,
      winner: 1,
      teams: [{ team: 1, players: [1, 5] }],
      scores: [{ player: 1, name: "Alex", remaining: 0 }],
    },
  };
  assert.equal(board({ practice }).banner, "Alex & score_player 5 score_winners");
  const golf = party("golf", { winner: 1, scores: [{ player: 1, points: 3, scorecard: [3] }] });
  assert.match(board({ practice: golf }).main, /<thead><tr><th><\/th><th>1<\/th><th class="total">/);
});

test("a checkout training without a route shows the setup, aims at it and calls the score to leave", () => {
  // 159 in the 121 ladder: one visit cannot finish it, three darts leave a finish.
  const ladder = drill("159", {
    drill: "checkout_121",
    remaining: 159,
    checkout: null,
    setup: { route: "T20 T19 S10", leave: 32 },
    attempt_visit: 1,
    attempt_visits: 3,
  });
  const view = drillView(ladder.drill);
  assert.deepEqual(view.setup, { route: ["T20", "T19", "S10"], leave: 32 });
  assert.match(
    board(ladder).main,
    /<div class="big">159<\/div><div class="route"><span class="setup" title="setup_hint"><span class="bed">T20<\/span><span class="bed">T19<\/span><span class="bed">S10<\/span><span class="leave">setup_leave<\/span><\/span><\/div>/
  );
  // The board outlines the setup's first dart, as in X01.
  assert.deepEqual(drillBeds(view), ["T20"]);
  // A route wins over a setup, a bust over both; an unusable setup is none.
  const routed = drill("81", { drill: "checkout", remaining: 81, checkout: "T15 D18", setup: { route: "S1", leave: 80 } });
  assert.match(board(routed).main, /<div class="route"><span class="bed">T15<\/span><span class="bed">D18<\/span><\/div>/);
  const bust = drill("159", { drill: "checkout", remaining: 159, bust: true, setup: { route: "T20", leave: 99 } });
  assert.match(board(bust).main, /<span class="note bust">bust<\/span>/);
  assert.equal(drillView(drill("159", { drill: "checkout", setup: { route: "Z9", leave: 1 } }).drill).setup, null);
  assert.equal(drillView(drill("159", { drill: "checkout" }).drill).setup, null);
  // The caller names the score to leave, like in X01.
  const state = (keys, setup) => ({
    mode: "drill",
    drill: { kind: "checkout_121", remaining: 159, route: [], setup, thrown: keys },
  });
  const throwing = callerState(visit(dart(20, 1)), state(["S20"], null));
  const next = callerState(visit(), state([], { route: ["T20", "T19", "S10"], leave: 32 }), throwing);
  assert.deepEqual(callerCalls(throwing, next, all), [{ kind: "setup", name: null, player: null, players: 0, leave: 32 }]);
});
