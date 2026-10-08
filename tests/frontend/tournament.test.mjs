// Tournaments on the scoreboard: the round in the match view, the table and the
// bracket between matches, the caller, the idle panel and the new game screen.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, DEVICE, READY, entityId, loadCards, makeHass, mount, settle, text, update, window } from "./dom.mjs";

const {
  bracketSlots,
  callerText,
  freshSlots,
  lobbyChange,
  lobbyChoice,
  stageName,
  tournamentCallState,
  tournamentCalls,
  tournamentCountdown,
  tournamentHtml,
  tournamentLabel,
  tournamentStartData,
  tournamentView,
} = await loadCards();

// Sunday, 27 September 2026, 12:00 UTC.
const NOW = Date.UTC(2026, 8, 27, 12, 0);
const at = (seconds) => new Date(NOW + seconds * 1000).toISOString();
const STARTED = at(-600);
const GAMES = ["101", "301", "501", "701", "901", "1001", "cricket"];
const PRACTICE = ["off", ...GAMES, "shanghai", "halve_it", "killer", "around_the_clock", "doubles", "checkout", "bobs_27"];
const EN = {
  tournament: "Tournament",
  tournament_round: "Round {round}",
  tournament_stage_semi_final: "Semi-final",
  tournament_match: "Match {match} of {matches}",
  tournament_on_request: "starts with Next tournament match",
  tournament_countdown: "starts in {time}",
  tournament_after_takeout: "starts when the board is clear",
  say_tournament_next: "Next match: {first} against {second}",
  say_tournament_won: "{name} wins the tournament!",
};
const t = (key) => EN[key] ?? key;

const match = (number, stage, players, extra = {}) => ({
  match: number,
  round: 1,
  stage,
  players,
  winner: null,
  bye: false,
  legs: [0, 0],
  sets: [0, 0],
  ended: null,
  ...extra,
});
const row = (position, name, won, lost, legsFor, legsAgainst, average) => ({
  position,
  name,
  played: won + lost,
  won,
  lost,
  legs_for: legsFor,
  legs_against: legsAgainst,
  leg_difference: legsFor - legsAgainst,
  points: won * 2,
  average,
});
// A round robin of three after its first match: Sam beat Kim 2:1.
const FIRST = match(1, "round_1", ["Kim", "Sam"], { winner: "Sam", legs: [1, 2], sets: [0, 1], ended: at(0) });
const SECOND = match(2, "round_2", ["Alex", "Kim"], { round: 2 });
const THIRD = match(3, "round_3", ["Sam", "Alex"], { round: 3 });
const ROUND_ROBIN = {
  status: "waiting",
  format: "round_robin",
  game: 501,
  legs_to_win: 2,
  sets_to_win: 1,
  players: ["Alex", "Sam", "Kim"],
  round: 2,
  rounds: 3,
  matches_played: 1,
  matches_total: 3,
  current: null,
  next: SECOND,
  last_result: { ...FIRST, average: [45.5, 60.25] },
  pause: 10,
  summary: 5,
  next_at: at(10),
  winner: null,
  started: STARTED,
  fixtures: [FIRST, SECOND, THIRD],
  standings: [row(1, "Sam", 1, 0, 2, 1, 60.25), row(2, "Alex", 0, 0, 0, 0, null), row(3, "Kim", 0, 1, 1, 2, 45.5)],
};
const tournament = (attributes = {}, state = "round_2") => ({
  "sensor.tournament": { state, attributes: { ...ROUND_ROBIN, ...attributes } },
});
// A knockout of five with a match for third place, between the quarter-final and the semi-finals.
const BYE = (name) => match(null, "quarter_final", [name, null], { bye: true, winner: name });
const QUARTER = match(1, "quarter_final", ["Lea", "Max"], { winner: "Lea", legs: [3, 2], sets: [2, 1], ended: at(0) });
const bracket = (semis, final = [null, null], third = [null, null]) => [
  { stage: "quarter_final", round: 1, matches: [BYE("Alex"), QUARTER, BYE("Sam"), BYE("Kim")] },
  { stage: "semi_final", round: 2, matches: semis },
  { stage: "final", round: 3, matches: [match(5, "final", final, { round: 3 })] },
  { stage: "third_place", round: 3, matches: [match(4, "third_place", third, { round: 3 })] },
];
const KNOCKOUT = {
  ...ROUND_ROBIN,
  format: "knockout",
  game: "cricket",
  legs_to_win: 3,
  sets_to_win: 2,
  players: ["Alex", "Sam", "Kim", "Lea", "Max"],
  matches_total: 5,
  next: match(2, "semi_final", ["Alex", "Lea"], { round: 2 }),
  last_result: QUARTER,
  pause: 0,
  next_at: null,
  standings: undefined,
  bracket: bracket([match(2, "semi_final", ["Alex", "Lea"], { round: 2 }), match(3, "semi_final", ["Sam", "Kim"])]),
};

const ui = (extra = {}) => ({
  t,
  format: (value, digits) => value.toFixed(digits),
  avatar: (name) => (name === "Alex" ? "/api/image/serve/alex/512x512" : null),
  ...extra,
});

test("the tournament sensor reads as a view, and malformed values as defaults", () => {
  const view = tournamentView({ state: "round_2", attributes: ROUND_ROBIN });
  assert.deepEqual(
    [view.stage, view.status, view.format, view.game, view.mpr, view.setsToWin, view.played, view.total],
    ["round_2", "waiting", "round_robin", 501, false, 1, 1, 3]
  );
  assert.deepEqual(
    [view.nextAt, view.pause, view.summary, view.winner, view.started, view.current],
    [NOW + 10000, 10, 5, null, STARTED, null]
  );
  assert.deepEqual(view.last, {
    match: 1,
    round: 1,
    stage: "round_1",
    players: ["Kim", "Sam"],
    winner: "Sam",
    bye: false,
    legs: [1, 2],
    sets: [0, 1],
    ended: at(0),
  });
  assert.deepEqual(view.standings[2], {
    position: 3,
    name: "Kim",
    played: 1,
    won: 0,
    lost: 1,
    legsFor: 1,
    legsAgainst: 2,
    difference: -1,
    points: 0,
    average: 45.5,
  });
  assert.deepEqual(view.bracket, []);

  const odd = tournamentView({
    state: "final",
    attributes: {
      status: "playing",
      format: "swiss",
      game: { name: "501" },
      next_at: "soon",
      current: "the final",
      next: { players: "Alex", legs: [1] },
      standings: [null, { name: "Alex", mpr: 2.5 }, { name: "" }],
      bracket: [null, { stage: "final", matches: [null, { stage: 7 }] }, { stage: "semi_final", matches: "none" }],
    },
  });
  assert.deepEqual(
    [odd.format, odd.game, odd.mpr, odd.setsToWin, odd.played, odd.total, odd.nextAt, odd.pause, odd.summary, odd.current],
    ["round_robin", null, false, 1, 0, 0, null, 0, 8, null]
  );
  assert.deepEqual(odd.next, {
    match: null,
    round: 1,
    stage: "",
    players: [null, null],
    winner: null,
    bye: false,
    legs: [1, 0],
    sets: [0, 0],
    ended: null,
  });
  assert.deepEqual(odd.standings, [
    {
      position: 0,
      name: "Alex",
      played: 0,
      won: 0,
      lost: 0,
      legsFor: 0,
      legsAgainst: 0,
      difference: 0,
      points: 0,
      average: 2.5,
    },
  ]);
  assert.deepEqual(
    odd.bracket.map((round) => [round.stage, round.matches.length]),
    [
      ["final", 1],
      ["semi_final", 0],
    ]
  );
  assert.equal(tournamentView({ state: "final", attributes: { status: "finished", game: "cricket" } }).mpr, true);
  for (const state of [undefined, { state: "unknown" }, { state: "no_tournament", attributes: { status: null } }]) {
    assert.equal(tournamentView(state), null);
  }
  assert.equal(tournamentView({ state: "round_1" }), null);
});

test("stages, labels and the countdown read as players say them", () => {
  assert.equal(stageName(t, "round_3"), "Round 3");
  assert.equal(stageName(t, "semi_final"), "Semi-final");
  const view = tournamentView({ state: "round_2", attributes: ROUND_ROBIN });
  assert.equal(tournamentLabel(view, view.next, t), "Tournament · Round 2 · Match 2 of 3");
  assert.equal(tournamentCountdown(view, NOW, t), "starts in 10 s");
  assert.equal(tournamentCountdown(view, NOW + 8500, t), "starts in 2 s");
  // A clock ahead of Home Assistant never counts beyond the pause, one behind never below zero.
  assert.equal(tournamentCountdown(view, NOW - 60000, t), "starts in 10 s");
  assert.equal(tournamentCountdown(view, NOW + 60000, t), "starts when the board is clear");
  assert.equal(tournamentCountdown({ ...view, pause: 0 }, NOW, t), "starts with Next tournament match");
  // Minutes and seconds from a minute on.
  assert.equal(tournamentCountdown({ ...view, pause: 600, nextAt: NOW + 65000 }, NOW, t), "starts in 1:05 min");
  assert.equal(tournamentCountdown({ ...view, pause: 600, nextAt: NOW + 600000 }, NOW, t), "starts in 10:00 min");
  assert.equal(tournamentCountdown({ ...view, nextAt: null }, NOW, t), "starts with Next tournament match");
  assert.equal(tournamentCountdown({ ...view, status: "playing" }, NOW, t), "");
});

test("the caller follows the matches of a tournament and names the champion", () => {
  const state = (status, number, extra = {}) => ({
    started: STARTED,
    status,
    match: number,
    players: number ? ["Alex", "Kim"] : [],
    winner: null,
    ...extra,
  });
  assert.equal(tournamentCallState(null), null);
  assert.deepEqual(
    tournamentCallState(tournamentView({ state: "round_2", attributes: { ...ROUND_ROBIN, status: "playing", current: SECOND } })),
    state("playing", 2)
  );
  assert.deepEqual(tournamentCallState(tournamentView({ state: "round_2", attributes: ROUND_ROBIN })), state("waiting", null));
  const options = { call_results: true };
  // Nothing at first sight, nothing without a tournament.
  assert.deepEqual(tournamentCalls(undefined, state("playing", 1), options), []);
  assert.deepEqual(tournamentCalls(state("playing", 1), null, options), []);
  // A tournament that starts, and every next match.
  const next = [{ kind: "tournament_next", first: "Alex", second: "Kim" }];
  assert.deepEqual(tournamentCalls(null, state("playing", 1), options), next);
  assert.deepEqual(tournamentCalls(state("waiting", null), state("playing", 2), options), next);
  assert.deepEqual(tournamentCalls(state("playing", 2), state("playing", 2), options), []);
  assert.deepEqual(tournamentCalls(state("playing", 2), state("waiting", null), options), []);
  assert.deepEqual(tournamentCalls(state("playing", 2, { started: "earlier" }), state("playing", 2), options), next);
  const won = state("finished", null, { winner: "Alex" });
  assert.deepEqual(tournamentCalls(state("waiting", null), won, options), [{ kind: "tournament_won", name: "Alex" }]);
  assert.deepEqual(tournamentCalls(won, won, options), []);
  assert.deepEqual(tournamentCalls(null, won, options), []);
  assert.deepEqual(tournamentCalls(state("waiting", null), won, { call_results: false }), []);
  assert.equal(callerText(next[0], t), "Next match: Alex against Kim");
  assert.equal(callerText({ kind: "tournament_won", name: "Alex" }, t), "Alex wins the tournament!");
});

test("the start action carries the players, the format and the rules of the game", () => {
  const choice = {
    ...lobbyChoice(
      { game: "501", players: 2, names: ["Alex", "Sam"], legs: 2, sets: 1, bull_off: true, format: "knockout" },
      ["501"]
    ),
    tournament: true,
    players: ["Alex", "", "Sam", "Kim", "Lea"],
    third_place: true,
    bull_off_distance: true,
  };
  assert.deepEqual(tournamentStartData(choice, { entry: "entry-1", distance: true }), {
    players: ["Alex", "Sam", "Kim", "Lea"],
    format: "knockout",
    game: "501",
    legs: 2,
    sets: 1,
    bull_off: true,
    random_draw: false,
    config_entry_id: "entry-1",
    bull_off_distance: true,
    double_out: true,
    double_in: false,
    third_place: true,
  });
  // Cricket has no double out, a round robin no third place, three players none either.
  assert.deepEqual(tournamentStartData({ ...choice, game: "cricket", format: "round_robin", bull_off: false }), {
    players: ["Alex", "Sam", "Kim", "Lea"],
    format: "round_robin",
    game: "cricket",
    legs: 2,
    sets: 1,
    bull_off: false,
    random_draw: false,
  });
  assert.equal(tournamentStartData({ ...choice, players: ["Alex", "Sam", "Kim"] }).third_place, false);
  assert.equal(lobbyChoice({ names: [], format: "swiss" }, ["501"]).format, "round_robin");
});

test("in tournament mode the choice takes eight named players", () => {
  let choice = lobbyChoice({ game: "501", players: 3, names: ["Alex", "", "Sam"] }, ["501"]);
  choice = lobbyChange(choice, "mode", "tournament");
  assert.deepEqual([choice.tournament, choice.players], [true, ["Alex", "Sam"]]);
  for (const name of ["Kim", "Lea", "Max", "Tom", "Ida", "Ben", "Zoe"]) choice = lobbyChange(choice, "add", name);
  assert.deepEqual(choice.players, ["Alex", "Sam", "Kim", "Lea", "Max", "Tom", "Ida", "Ben"]);
  // Guests have no name for the table.
  assert.equal(lobbyChange(lobbyChange(choice, "remove", "7"), "guest").players.length, 7);
  choice = lobbyChange(choice, "format", "knockout");
  choice = lobbyChange(choice, "format", "swiss");
  choice = lobbyChange(choice, "toggle", "third_place");
  choice = lobbyChange(choice, "toggle", "random_draw");
  assert.deepEqual([choice.format, choice.third_place, choice.random_draw], ["knockout", true, true]);
  // Back to a match: four players at most.
  choice = lobbyChange(choice, "mode", "match");
  assert.deepEqual([choice.tournament, choice.players], [false, ["Alex", "Sam", "Kim", "Lea"]]);
});

test("slots of the bracket that got a player or a result are fresh", () => {
  const before = tournamentView({ state: "semi_final", attributes: KNOCKOUT });
  const slots = bracketSlots(before);
  assert.equal(slots.get("quarter_final-1-0"), "Lea|true");
  assert.equal(slots.get("quarter_final-0-1"), "null|false");
  assert.equal(slots.get("final-0-0"), "null|false");
  assert.equal(bracketSlots(null).size, 0);
  assert.equal(freshSlots(undefined, slots).size, 0);
  const after = tournamentView({
    state: "semi_final",
    attributes: {
      ...KNOCKOUT,
      bracket: bracket(
        [match(2, "semi_final", ["Alex", "Lea"], { winner: "Alex", ended: at(5) }), match(3, "semi_final", ["Sam", "Kim"])],
        ["Alex", null],
        ["Lea", null]
      ),
    },
  });
  // The winner and the players who go on; the loser keeps the place.
  assert.deepEqual([...freshSlots(slots, bracketSlots(after))], ["semi_final-0-0", "final-0-0", "third_place-0-0"]);
});

test("between matches the round robin shows who plays next and the table", () => {
  const view = tournamentView({ state: "round_2", attributes: ROUND_ROBIN });
  const html = tournamentHtml(view, ui({ startNow: true }));
  assert.equal(html.title, "Tournament");
  assert.equal(html.meta, "tournament_round_robin · 501 · tournament_progress");
  assert.equal(html.banner, "");
  const page = new window.DOMParser().parseFromString(html.main, "text/html");
  assert.equal(page.querySelector(".tournament").className, "tournament round_robin");
  assert.equal(page.querySelector(".next-up .section-label").textContent, "tournament_next · Round 2");
  assert.equal(page.querySelector(".pairing").textContent, "Alextournament_vsKim");
  assert.equal(page.querySelector(".pairing .avatar").getAttribute("src"), "/api/image/serve/alex/512x512");
  assert.equal(page.querySelector(".start-next").dataset.tournament, "next");
  assert.deepEqual(
    [...page.querySelectorAll(".standings tbody tr")].map((line) => [
      line.className,
      ...[...line.children].map((cell) => cell.textContent),
    ]),
    [
      ["", "1", "Sam", "1", "1", "0", "2:1", "+1", "60.3", "2"],
      ["next", "2", "Alex", "0", "0", "0", "0:0", "0", "–", "0"],
      ["next", "3", "Kim", "1", "0", "1", "1:2", "−1", "45.5", "0"],
    ]
  );
  assert.deepEqual(
    [...page.querySelectorAll(".standings thead abbr")].map((abbr) => abbr.getAttribute("title")),
    [
      "tournament_played_long",
      "tournament_won_long",
      "tournament_lost_long",
      "tournament_legs_long",
      "tournament_difference_long",
      "average_long",
      "tournament_points_long",
    ]
  );
  // Finished: the champion and no next match; Cricket ranks by marks per round.
  const finished = tournamentView({
    state: "finished",
    attributes: { ...ROUND_ROBIN, status: "finished", game: "cricket", winner: "Sam", next: null },
  });
  const done = tournamentHtml(finished, ui());
  assert.equal(done.meta, "tournament_round_robin · cricket");
  assert.equal(done.banner, "tournament_winner");
  const table = new window.DOMParser().parseFromString(done.main, "text/html");
  assert.equal(table.querySelector(".next-up"), null);
  assert.equal(table.querySelector("tbody tr").className, "champion");
  assert.equal(table.querySelectorAll("thead th")[7].textContent, "cricket_mpr");
  assert.equal(table.querySelectorAll("tbody tr")[2].children[7].textContent, "45.50");
});

test("the knockout bracket shows byes, open places, results and the match to play", () => {
  const view = tournamentView({ state: "semi_final", attributes: KNOCKOUT });
  const html = tournamentHtml(view, ui({ fresh: new Set(["quarter_final-1-0"]) }));
  const page = new window.DOMParser().parseFromString(html.main, "text/html");
  assert.equal(page.querySelector(".next-up .start-next"), null);
  assert.deepEqual(
    [...page.querySelectorAll(".round")].map((round) => [round.className, round.querySelector(".section-label").textContent]),
    [
      ["round quarter_final", "tournament_stage_quarter_final"],
      ["round semi_final", "Semi-final"],
      ["round final", "tournament_stage_final"],
    ]
  );
  const duels = [...page.querySelectorAll(".duel")].map((duel) => [
    duel.className,
    [...duel.querySelectorAll(".slot")].map((slot) => `${slot.className}:${slot.textContent}`),
  ]);
  assert.deepEqual(duels, [
    ["duel bye", ["slot:Alex", "slot open:tournament_bye"]],
    // Sets decide: Lea won 2:1.
    ["duel", ["slot won fresh:Lea2", "slot lost:Max1"]],
    ["duel bye", ["slot:Sam", "slot open:tournament_bye"]],
    ["duel bye", ["slot:Kim", "slot open:tournament_bye"]],
    ["duel live", ["slot:Alex", "slot:Lea"]],
    ["duel", ["slot:Sam", "slot:Kim"]],
    ["duel", ["slot open:tournament_open", "slot open:tournament_open"]],
    ["duel", ["slot open:tournament_open", "slot open:tournament_open"]],
  ]);
  assert.equal(page.querySelector(".section-label.third").textContent, "tournament_stage_third_place");
  // The champion's final wears the crown; one set to win shows the legs.
  const final = match(5, "final", ["Alex", "Sam"], { winner: "Alex", legs: [3, 1], ended: at(60) });
  const crowned = tournamentView({
    state: "finished",
    attributes: {
      ...KNOCKOUT,
      status: "finished",
      winner: "Alex",
      sets_to_win: 1,
      next: null,
      bracket: [{ stage: "semi_final", matches: [] }, { stage: "final", matches: [final] }],
    },
  });
  // A final whose second player is still to be decided.
  const open = tournamentView({
    state: "final",
    attributes: { ...KNOCKOUT, next: match(5, "final", ["Alex", null], { round: 3 }) },
  });
  const pairing = new window.DOMParser().parseFromString(tournamentHtml(open, ui()).main, "text/html");
  assert.equal(pairing.querySelector(".pairing").textContent, "Alextournament_vstournament_open");
  const done = new window.DOMParser().parseFromString(tournamentHtml(crowned, ui()).main, "text/html");
  assert.equal(done.querySelector(".final .duel").className, "duel crowned");
  assert.equal(done.querySelector(".final .slot.won").textContent, "Alex3");
  assert.equal(done.querySelector(".section-label.third"), null);
});

// The scoreboard at the board --------------------------------------------------------

// Two players of X01, the one to throw, the winner once decided.
const practice = (names, winner = null) => ({
  "sensor.practice_remaining": {
    state: winner ? "0" : "501",
    attributes: {
      game: 501,
      player: 1,
      name: names[0],
      winner,
      legs_to_win: 2,
      scores: names.map((name, index) => ({
        player: index + 1,
        name,
        remaining: winner === index + 1 ? 0 : 501,
        legs: 0,
        sets: 0,
      })),
    },
  },
});
const BOARD = {
  "sensor.local_visit_score": { state: "0", attributes: { throws: [] } },
  "select.practice_game": { state: "501", attributes: { options: PRACTICE } },
  "number.practice_players": "2",
  "number.practice_legs": "2",
  "number.practice_sets": "1",
  "switch.practice_double_out": "on",
  "switch.practice_double_in": "off",
  "switch.practice_bull_off": "off",
  "select.tournament_game": { state: "501", attributes: { options: GAMES } },
  "select.tournament_format": "round_robin",
  "switch.tournament_third_place": "off",
  "switch.tournament_random_draw": "off",
  "button.tournament_next_match": "unknown",
  "button.tournament_stop": "unknown",
  "sensor.player_profiles": {
    state: "1",
    attributes: { players: [{ name: "Alex", person: "person.alex" }] },
  },
};
const PLAYING = tournament({ status: "playing", current: SECOND, next: THIRD, next_at: null });
// The summary the practice game keeps of its finished match.
function summarized(states) {
  const state = states["sensor.practice_remaining"];
  const { attributes } = state;
  const summary = {
    game: attributes.game,
    winner: attributes.winner,
    ended: at(0),
    legs_to_win: 2,
    sets_to_win: 1,
    players: attributes.scores.map((score) => ({ player: score.player, name: score.name, legs: 0, sets: 0, average: 50 })),
  };
  return { "sensor.practice_remaining": { ...state, attributes: { ...attributes, summary } } };
}
// The first match at the board, before any result.
const OPENING = tournament(
  {
    status: "playing",
    current: match(1, "round_1", ["Kim", "Sam"]),
    next: SECOND,
    last_result: null,
    matches_played: 0,
    next_at: null,
  },
  "round_1"
);

function names(hass, list) {
  list.forEach((name, index) => {
    const id = `text.dartboard_practice_player_${index + 1}`;
    hass.entities[id] = { entity_id: id, platform: "autodarts", device_id: DEVICE, translation_key: "practice_player" };
    hass.states[id] = { entity_id: id, state: name, attributes: {} };
  });
  return hass;
}

const setup = (states = {}, config = {}, options = {}) => {
  const hass = names(makeHass({ states: { ...READY, ...BOARD, ...states }, ...options }), ["Alex", "Kim"]);
  hass.states["person.alex"] = {
    entity_id: "person.alex",
    state: "home",
    attributes: { entity_picture: "/api/image/serve/alex/512x512" },
  };
  return { hass, card: mount("autodarts-scoreboard-card", hass, config) };
};
const clock = (context) => context.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: NOW });
const shown = (card) => Boolean($(card, ".tournament"));
const pressed = (hass) => hass.calls.filter(([domain]) => domain === "button").map(([, , data]) => data.entity_id);

test("the match view names the round of the tournament", () => {
  const { hass, card } = setup({ ...PLAYING, ...practice(["Alex", "Kim"]) });
  assert.equal(text(card, ".meta"), "Tournament · Round 2 · Match 2 of 3 · 2 legs per set");
  assert.equal(shown(card), false);
  // The result of the match keeps its round until the darts are pulled.
  card.hass = update(hass, practice(["Alex", "Kim"], 1));
  assert.match(text(card, ".banner"), /^Alex wins the match/);
  assert.match(text(card, ".meta"), /^Tournament · Round 2 · Match 2 of 3/);
  // Another game on the board is no match of the tournament.
  card.hass = update(hass, practice(["Sam", "Lea"]));
  assert.equal(text(card, ".meta"), "2 legs per set");
});

test("between matches the result shows, then the table with the next match and a countdown", (context) => {
  clock(context);
  const { hass, card } = setup({ ...OPENING, ...practice(["Kim", "Sam"]) });
  assert.equal(text(card, ".meta"), "Tournament · Round 1 · Match 1 of 3 · 2 legs per set");
  card.hass = update(hass, { ...summarized(practice(["Kim", "Sam"], 2)), ...tournament() });
  // First the summary of the match, with its round.
  assert.equal(shown(card), false);
  assert.match(text(card, ".banner"), /^Sam wins the match/);
  assert.ok($(card, ".main table.summary"));
  assert.match(text(card, ".meta"), /^Tournament · Round 1 · Match 1 of 3/);
  context.mock.timers.tick(4999);
  assert.equal(shown(card), false);
  context.mock.timers.tick(1);
  assert.equal(shown(card), true);
  assert.equal(text(card, ".title"), "Tournament");
  assert.equal(text(card, ".meta"), "Round robin · 501 · 1 of 3 matches played");
  assert.equal($(card, ".banner").hidden, true);
  assert.equal($(card, ".visit").hidden, true);
  assert.equal(text(card, ".next-up .section-label"), "Next up · Round 2");
  assert.equal(text(card, ".pairing"), "AlexvsKim");
  assert.equal(text(card, ".countdown"), "starts in 5 s");
  assert.deepEqual(
    $$(card, ".standings tbody .who").map((cell) => cell.textContent),
    ["Sam", "Alex", "Kim"]
  );
  context.mock.timers.tick(1000);
  assert.equal(text(card, ".countdown"), "starts in 4 s");
  context.mock.timers.tick(4000);
  assert.equal(text(card, ".countdown"), "starts when the board is clear");
  // The new game screen stays away between the matches of a tournament.
  context.mock.timers.tick(8000);
  assert.equal($(card, ".lobby"), null);
  assert.equal(shown(card), true);
  // Start now presses the button of the next match.
  $(card, ".start-next").click();
  assert.deepEqual(pressed(hass), [entityId("button.tournament_next_match")]);
  // The next match starts: its view comes back and the countdown stops.
  card.hass = update(card._hass, { ...practice(["Alex", "Kim"]), ...PLAYING });
  assert.equal(shown(card), false);
  assert.equal(card._tournamentTick, null);
  assert.equal($(card, ".visit").hidden, false);
});

test("Cricket and party games or no game at all are no match of the tournament", () => {
  const cricket = {
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: {
        game: "cricket",
        player: 1,
        winner: null,
        numbers: [20, 19, 18, 17, 16, 15, 25],
        scores: ["Alex", "Kim"].map((name, index) => ({
          player: index + 1,
          name,
          marks: [0, 0, 0, 0, 0, 0, 0],
          points: 0,
          legs: 0,
          sets: 0,
          mpr: null,
        })),
      },
    },
  };
  const { hass, card } = setup({ ...PLAYING, ...cricket });
  assert.match(text(card, ".meta"), /^Tournament · Round 2 · Match 2 of 3/);
  card.hass = update(hass, {
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: { game: "shanghai", player: 1, winner: null, round: 1, rounds: 7, scores: [{ player: 1, name: "Alex", points: 0 }] },
    },
  });
  assert.doesNotMatch(text(card, ".meta"), /Tournament/);
  // Without a game, a waiting tournament shows at once when the result needs no time.
  const idle = setup({ ...tournament({ summary: 0 }), "sensor.practice_remaining": "unknown" }).card;
  assert.equal(shown(idle), true);
});

test("a screen that comes to a waiting tournament shows it at once, and taps elsewhere press nothing", () => {
  const { hass, card } = setup({ ...tournament({ pause: 0, next_at: null }), ...practice(["Kim", "Sam"], 2) });
  assert.equal(shown(card), true);
  assert.equal(text(card, ".countdown"), "starts with Next tournament match");
  $(card, ".standings").click();
  assert.deepEqual(pressed(hass), []);
  // Another game played meanwhile hides the tournament.
  card.hass = update(hass, practice(["Sam", "Lea"]));
  assert.equal(shown(card), false);
  card.remove();
  assert.equal(card._tournamentTick, null);
});

test("the champion shows until a new match begins after the final", (context) => {
  clock(context);
  const finished = tournament({ status: "finished", winner: "Sam", next: null, next_at: null }, "finished");
  const { hass, card } = setup({ ...finished, ...practice(["Sam", "Alex"], 1) });
  assert.equal(text(card, ".banner"), "Sam wins the tournament!");
  assert.equal(text(card, ".meta"), "Round robin · 501");
  assert.equal($(card, ".standings tbody tr").className, "champion");
  assert.equal($(card, ".next-up"), null);
  // A new practice match after the final: the tournament has had its day.
  card.hass = update(hass, practice(["Sam", "Alex"]));
  assert.equal(shown(card), false);
  card.hass = update(card._hass, practice(["Sam", "Alex"], 2));
  assert.equal(shown(card), false);
  context.mock.timers.tick(8000);
  assert.equal(text(card, ".title"), "New game");
});

test("the knockout bracket fills up, the new places animated", (context) => {
  clock(context);
  const { hass, card } = setup({ ...tournament(KNOCKOUT, "semi_final"), ...practice(["Lea", "Max"], 1) });
  assert.equal(shown(card), true);
  assert.equal(text(card, ".meta"), "Knockout · Cricket · 1 of 5 matches played");
  assert.equal($$(card, ".round").length, 3);
  assert.equal($$(card, ".slot.fresh").length, 0);
  assert.equal($(card, ".duel.live").textContent, "AlexLea");
  assert.equal(text(card, ".countdown"), "starts with Next tournament match");
  // Alex wins the first semi-final: the final and the match for third place fill up.
  const decided = tournament(
    {
      ...KNOCKOUT,
      matches_played: 2,
      next: match(3, "semi_final", ["Sam", "Kim"], { round: 2 }),
      last_result: match(2, "semi_final", ["Alex", "Lea"], { winner: "Alex", ended: at(5) }),
      bracket: bracket(
        [match(2, "semi_final", ["Alex", "Lea"], { winner: "Alex", sets: [2, 0] }), match(3, "semi_final", ["Sam", "Kim"])],
        ["Alex", null],
        ["Lea", null]
      ),
    },
    "semi_final"
  );
  card.hass = update(hass, { ...decided, ...practice(["Alex", "Lea"], 1) });
  assert.equal(shown(card), false);
  context.mock.timers.tick(5000);
  assert.deepEqual(
    $$(card, ".slot.fresh").map((slot) => slot.textContent),
    ["Alex2", "Alex", "Lea"]
  );
  // The same bracket again animates nothing anew: the markup stays as it is.
  const markup = $(card, ".main").innerHTML;
  card.hass = update(card._hass, { "sensor.training_darts": "3" });
  assert.equal($(card, ".main").innerHTML, markup);
});

test("the caller announces every tournament match and the champion", () => {
  const spoken = [];
  window.speechSynthesis = { speak: (utterance) => spoken.push(utterance.text), cancel: () => {} };
  globalThis.SpeechSynthesisUtterance = class {
    constructor(words) {
      this.text = words;
    }
  };
  const { hass, card } = setup({ ...tournament(), ...practice(["Kim", "Sam"], 2) }, { caller: true });
  $(card, ".caller-toggle").click();
  spoken.length = 0;
  card.hass = update(hass, { ...PLAYING, ...practice(["Alex", "Kim"]) });
  assert.deepEqual(spoken, ["Next match: Alex against Kim"]);
  card.hass = update(card._hass, {
    ...tournament({ status: "finished", winner: "Alex", next: null }, "finished"),
    ...practice(["Alex", "Kim"], 1),
  });
  assert.deepEqual(spoken.slice(1), ["Game shot, and the match, Alex!", "Alex wins the tournament!"]);
  $(card, ".caller-toggle").click();
});

test("idle mode shows the tournament first", (context) => {
  clock(context);
  const { card } = setup(
    { ...tournament(KNOCKOUT, "semi_final"), ...practice(["Lea", "Max"], 1) },
    { idle_after: 10, idle_panels: ["tournament", "clock"] }
  );
  context.mock.timers.tick(10000);
  assert.equal($(card, ".idle-panel").dataset.panel, "tournament");
  assert.equal(text(card, ".meta"), "Tournament");
  assert.equal($$(card, ".idle-panel .duel").length, 8);
  // Without a tournament, the panel has nothing to show.
  const none = setup({}, { idle_after: 10, idle_panels: ["tournament", "clock"] }).card;
  none.hass = update(none._hass, { "sensor.tournament": { state: "no_tournament", attributes: { status: null } } });
  context.mock.timers.tick(10000);
  assert.equal($(none, ".idle-panel").dataset.panel, "clock");
  const table = setup({ ...tournament(), ...practice(["Kim", "Sam"], 2) }, { idle_after: 10, idle_panels: ["tournament"] });
  context.mock.timers.tick(10000);
  assert.equal($$(table.card, ".idle-panel .standings tbody tr").length, 3);
});

// The new game screen in tournament mode.
const lobbyTap = (card, action, value) =>
  $(card, `[data-lobby="${action}"]${value === undefined ? "" : `[data-value="${value}"]`}`).click();
const lobbyPlayers = (card) => $$(card, ".lobby-player .who").map((name) => name.textContent);
const options = (card) => $$(card, ".option").map((button) => [button.dataset.value, button.getAttribute("aria-pressed")]);
const started = (hass) => hass.calls.filter(([domain]) => domain === "autodarts");

test("the new game screen starts a tournament of up to eight players", () => {
  const { hass, card } = setup({ "select.practice_game": { state: "shanghai", attributes: { options: PRACTICE } } });
  $(card, ".lobby-toggle").click();
  assert.deepEqual(
    $$(card, ".lobby-mode .mode").map((button) => [button.textContent, button.getAttribute("aria-pressed")]),
    [
      ["Match", "true"],
      ["Tournament", "false"],
    ]
  );
  assert.equal($(card, ".lobby-mode").getAttribute("aria-label"), "Match or tournament");
  lobbyTap(card, "mode", "tournament");
  // X01 and Cricket only; a party game gives way to 501.
  assert.deepEqual(
    $$(card, ".lobby-group > .section-label").map((label) => label.textContent),
    ["X01", "Cricket"]
  );
  assert.deepEqual($$(card, '.game[aria-pressed="true"]').map((button) => button.textContent), ["501"]);
  assert.equal($(card, ".suggestion.guest"), null);
  assert.equal(text(card, ".lobby-hint"), "A tournament needs three to eight players.");
  assert.equal($(card, ".lobby .start").disabled, true);
  assert.equal(text(card, ".lobby .start"), "Start tournament");
  for (const name of ["Sam", "Lea", "Max", "Tom", "Ida", "Ben"]) {
    const input = $(card, ".lobby-name");
    input.value = name;
    input.dispatchEvent(new window.Event("input", { bubbles: true }));
    lobbyTap(card, "add-name");
  }
  assert.deepEqual(lobbyPlayers(card), ["Alex", "Kim", "Sam", "Lea", "Max", "Tom", "Ida", "Ben"]);
  assert.equal($(card, ".lobby-name").disabled, true);
  assert.equal($(card, ".lobby-player.resting"), null);
  assert.equal($(card, ".lobby-hint"), null);
  assert.deepEqual(
    $$(card, ".formats .option").map((button) => [button.textContent, button.getAttribute("aria-pressed")]),
    [
      ["Round robin", "true"],
      ["Knockout", "false"],
    ]
  );
  assert.deepEqual(options(card).slice(2), [
    ["double_out", "true"],
    ["double_in", "false"],
    ["bull_off", "false"],
    ["random_draw", "false"],
  ]);
  lobbyTap(card, "format", "knockout");
  lobbyTap(card, "toggle", "third_place");
  lobbyTap(card, "toggle", "random_draw");
  lobbyTap(card, "game", "cricket");
  assert.deepEqual(options(card).slice(2), [
    ["bull_off", "false"],
    ["third_place", "true"],
    ["random_draw", "true"],
  ]);
  lobbyTap(card, "start");
  assert.deepEqual(started(hass), [
    [
      "autodarts",
      "start_tournament",
      {
        players: ["Alex", "Kim", "Sam", "Lea", "Max", "Tom", "Ida", "Ben"],
        format: "knockout",
        game: "cricket",
        legs: 2,
        sets: 1,
        bull_off: false,
        random_draw: true,
        third_place: true,
      },
    ],
  ]);
  assert.equal($(card, ".lobby"), null);
});

test("back to a match, the screen offers every game and four players again", () => {
  const { card } = setup({ "select.tournament_format": "knockout" });
  $(card, ".lobby-toggle").click();
  lobbyTap(card, "mode", "tournament");
  assert.equal($(card, '.formats [aria-pressed="true"]').textContent, "Knockout");
  lobbyTap(card, "game", "701");
  lobbyTap(card, "mode", "match");
  assert.equal($$(card, ".lobby-group").length, 4);
  assert.deepEqual($$(card, '.game[aria-pressed="true"]').map((button) => button.textContent), ["701"]);
  // Only Cricket offered: the tournament plays Cricket.
  const cricket = setup({}, { lobby_games: ["cricket", "killer"] }).card;
  $(cricket, ".lobby-toggle").click();
  lobbyTap(cricket, "mode", "tournament");
  assert.deepEqual($$(cricket, ".game").map((button) => button.textContent), ["Cricket"]);
  // Without the tournament entities the screen offers matches only.
  const plain = setup({ "select.tournament_game": "unavailable" }).card;
  $(plain, ".lobby-toggle").click();
  assert.equal($(plain, ".lobby-mode"), null);
});

test("ending the game during a tournament stops the tournament too", () => {
  const { hass, card } = setup({ ...PLAYING, ...practice(["Alex", "Kim"]) });
  $(card, ".lobby-toggle").click();
  assert.equal(text(card, '[data-lobby="end"]'), "Stop tournament");
  lobbyTap(card, "end");
  assert.equal(text(card, '[data-lobby="end"]'), "Confirm?");
  lobbyTap(card, "end");
  assert.deepEqual(
    hass.calls.map(([domain, service, data]) => [domain, service, data.entity_id]),
    [
      ["button", "press", entityId("button.tournament_stop")],
      ["select", "select_option", entityId("select.practice_game")],
    ]
  );
});

test("a preview shows the tournament without its button, and German reads German", () => {
  const card = document.createElement("autodarts-scoreboard-card");
  card.setConfig({ type: "custom:autodarts-scoreboard-card" });
  card.preview = true;
  card.hass = setup({ ...tournament(), ...practice(["Kim", "Sam"], 2) }).hass;
  document.body.append(card);
  assert.equal($(card, ".start-next"), null);
  assert.equal($(card, ".tournament") !== null, true);
  const german = setup({ ...tournament(KNOCKOUT, "semi_final"), ...practice(["Lea", "Max"], 1) }, {}, { language: "de" }).card;
  assert.equal(text(german, ".title"), "Turnier");
  assert.equal(text(german, ".meta"), "K.-o.-System · Cricket · 1 von 5 Matches gespielt");
  assert.equal(text(german, ".next-up .section-label"), "Als Nächstes · Halbfinale");
  assert.equal(text(german, ".pairing"), "AlexgegenLea");
  assert.equal(text(german, ".countdown"), "beginnt mit „Nächstes Turniermatch“");
  assert.equal(text(german, ".start-next"), "Jetzt starten");
  assert.deepEqual(
    $$(german, ".round > .section-label").map((label) => label.textContent),
    ["Viertelfinale", "Halbfinale", "Finale"]
  );
  assert.equal(text(german, ".section-label.third"), "Spiel um Platz 3");
  assert.equal(text(german, ".duel.bye .slot.open"), "Freilos");
});

test("start scores go with their players into a tournament", () => {
  let choice = lobbyChoice(
    { game: "501", players: 3, names: ["Alex", "", "Sam"], starts: [301, 0, 701] },
    ["501", "cricket"]
  );
  assert.deepEqual([choice.players, choice.starts, choice.handicap], [["Alex", "", "Sam"], [301, 0, 701], true]);
  choice = lobbyChange({ ...choice, starts: [301] }, "mode", "tournament");
  assert.deepEqual([choice.players, choice.starts], [["Alex", "Sam"], [301, 0]]);
  choice = lobbyChange(choice, "add", "Kim");
  assert.deepEqual(tournamentStartData(choice).start_scores, [301, 0, 0]);
  // Back to the game's start score for everybody: the start scores still go along.
  assert.deepEqual(tournamentStartData({ ...choice, starts: [0, 0, 0] }).start_scores, [0, 0, 0]);
  assert.equal("start_scores" in tournamentStartData({ ...choice, handicap: false, starts: undefined }), false);
  assert.equal("start_scores" in tournamentStartData({ ...choice, game: "cricket" }), false);
});

test("a stage the sensor names is escaped like every other text of the bracket", () => {
  const stage = '"><img src=x onerror=alert(1)>';
  const view = tournamentView({
    state: "semi_final",
    attributes: { ...KNOCKOUT, bracket: [{ stage, matches: [match(1, stage, ["Alex", "Sam"])] }] },
  });
  const html = tournamentHtml(view, ui()).main;
  assert.doesNotMatch(html, /<img src=x/);
  const page = new window.DOMParser().parseFromString(html, "text/html");
  assert.equal(page.querySelector(".round").className, `round ${stage}`);
});

// A name typed into the new game screen and added.
function typeName(card, name) {
  const input = $(card, ".lobby-name");
  input.value = name;
  input.dispatchEvent(new window.Event("input", { bubbles: true }));
  lobbyTap(card, "add-name");
}

test("a new tournament stops the one being played first, after a second tap", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const { hass, card } = setup(
    { ...PLAYING, ...practice(["Alex", "Kim"]) },
    {},
    { device: { primary_config_entry: "entry-1" } }
  );
  $(card, ".lobby-toggle").click();
  lobbyTap(card, "mode", "tournament");
  typeName(card, "Sam");
  // The screen says beforehand what the start does.
  assert.deepEqual(
    $$(card, ".lobby-hint").map((hint) => hint.textContent),
    ["A tournament is being played: the start stops it first, after a second tap."]
  );
  lobbyTap(card, "start");
  assert.equal(text(card, ".lobby .start"), "Confirm?");
  assert.deepEqual(started(hass), []);
  // Without the second tap, the start goes back to what it was.
  context.mock.timers.tick(4000);
  assert.equal(text(card, ".lobby .start"), "Start tournament");
  lobbyTap(card, "start");
  lobbyTap(card, "start");
  assert.equal($(card, ".lobby"), null);
  // The stop has to succeed before the new tournament starts.
  assert.deepEqual(started(hass), [["autodarts", "stop_tournament", { config_entry_id: "entry-1" }]]);
  await settle();
  assert.deepEqual(
    started(hass).map(([, service, data]) => [service, data.players]),
    [
      ["stop_tournament", undefined],
      ["start_tournament", ["Alex", "Kim", "Sam"]],
    ]
  );
});

test("a stop that fails leaves the tournament being played, and a match starts at once", async () => {
  const { hass, card } = setup({ ...PLAYING, ...practice(["Alex", "Kim"]) });
  // Home Assistant shows the failure of an action as a toast of its own.
  hass.callService = (domain, service, data) => {
    hass.calls.push([domain, service, data]);
    return service === "stop_tournament" ? Promise.reject(new Error("board unavailable")) : Promise.resolve();
  };
  $(card, ".lobby-toggle").click();
  lobbyTap(card, "mode", "tournament");
  typeName(card, "Sam");
  lobbyTap(card, "start");
  lobbyTap(card, "start");
  await settle();
  assert.deepEqual(started(hass).map(([, service, data]) => [service, data]), [["stop_tournament", {}]]);
  // A match during a tournament needs no second tap; nothing to stop for it.
  $(card, ".lobby-toggle").click();
  lobbyTap(card, "start");
  await settle();
  assert.deepEqual(
    started(hass).map(([, service]) => service),
    ["stop_tournament", "start_game"]
  );
  // Without a running tournament, the start of one needs no second tap either.
  const idle = setup();
  $(idle.card, ".lobby-toggle").click();
  lobbyTap(idle.card, "mode", "tournament");
  typeName(idle.card, "Sam");
  assert.equal($(idle.card, ".lobby-hint"), null);
  lobbyTap(idle.card, "start");
  await settle();
  assert.deepEqual(started(idle.hass).map(([, service]) => service), ["start_tournament"]);
});
