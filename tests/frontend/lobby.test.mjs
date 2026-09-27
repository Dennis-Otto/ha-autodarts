// The new game screen of the scoreboard: choosing a game, players, the format and rules, and starting it.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, DEVICE, READY, loadCards, makeHass, mount, text, update, window } from "./dom.mjs";

const {
  gameGroup,
  gameRules,
  gameState,
  lobbyChange,
  lobbyChoice,
  lobbyGames,
  lobbySuggestions,
  personLinks,
  pictureUrl,
  startGameData,
} = await loadCards();

const OPTIONS = [
  "off",
  "101",
  "301",
  "501",
  "701",
  "901",
  "1001",
  "cricket",
  "shanghai",
  "halve_it",
  "killer",
  "around_the_clock",
  "doubles",
  "checkout",
  "bobs_27",
];
const PICTURE = "/api/image/serve/alex/512x512";
const PROFILES = {
  "sensor.player_profiles": {
    state: "4",
    attributes: {
      players: [
        { name: "Sam", person: null },
        { name: "Lea", person: "person.lea" },
        { name: "Kim", person: "person.kim" },
        { name: "Alex", person: "person.alex" },
      ],
    },
  },
};
const PEOPLE = {
  "person.alex": { state: "home", attributes: { entity_picture: PICTURE } },
  "person.kim": { state: "home", attributes: { entity_picture: "/api/image/serve/kim/512x512" } },
  "person.lea": { state: "not_home", attributes: {} },
};
// The practice game as the board has it between games: two players, three legs per set.
const BOARD = {
  "sensor.local_visit_score": { state: "0", attributes: { throws: [] } },
  "select.practice_game": { state: "off", attributes: { options: OPTIONS } },
  "number.practice_players": "2",
  "number.practice_legs": "3",
  "number.practice_sets": "1",
  "switch.practice_double_out": "on",
  "switch.practice_double_in": "off",
  "switch.practice_bull_off": "off",
};

// The four name fields share one translation key, like the integration's.
function withNames(hass, names) {
  names.forEach((name, index) => {
    const id = `text.dartboard_practice_player_${index + 1}`;
    hass.entities[id] = { entity_id: id, platform: "autodarts", device_id: DEVICE, translation_key: "practice_player" };
    hass.states[id] = { entity_id: id, state: name, attributes: {} };
  });
  return hass;
}

function withPeople(hass, people = PEOPLE) {
  for (const [id, state] of Object.entries(people)) hass.states[id] = { entity_id: id, ...state };
  return hass;
}

const setup = (states = {}, config = {}, options = {}) => {
  const hass = withPeople(
    withNames(makeHass({ states: { ...READY, ...BOARD, ...PROFILES, ...states }, ...options }), [
      "Alex",
      "Sam",
      "",
      "Player 12",
    ])
  );
  return { hass, card: mount("autodarts-scoreboard-card", hass, config) };
};

const tap = (card, selector) => $(card, selector).click();
// Whether the new game screen shows; an element would make a failing comparison unreadable.
const choosing = (card) => Boolean($(card, ".lobby"));
const lobbyTap = (card, action, value) =>
  $(card, `[data-lobby="${action}"]${value === undefined ? "" : `[data-value="${value}"]`}`).click();
const chosenGame = (card) => $$(card, '.game[aria-pressed="true"]').map((button) => button.textContent);
const players = (card) => $$(card, ".lobby-player .who").map((name) => name.textContent);
const suggestions = (card) => $$(card, ".suggestion").map((button) => [button.className, button.textContent]);
const options = (card) =>
  $$(card, ".option").map((button) => [button.dataset.value, button.getAttribute("aria-pressed")]);
const steppers = (card) => $$(card, ".stepper").map((row) => row.textContent);
const started = (hass) => hass.calls.filter(([domain]) => domain === "autodarts");

test("games are grouped, filtered and ruled like the practice game", () => {
  assert.deepEqual(
    ["501", "cricket", "cricket_cut_throat", "cut_throat", "tactics", "killer", "golf", "bobs_27", "catch_40", "bingo"].map(
      gameGroup
    ),
    ["x01", "cricket", "cricket", "cricket", "cricket", "party", "party", "training", "training", "more"]
  );
  assert.deepEqual(gameRules("killer"), {
    x01: false,
    drill: false,
    teams: false,
    bot: false,
    minPlayers: 2,
    maxPlayers: 4,
  });
  assert.deepEqual(gameRules("doubles"), {
    x01: false,
    drill: true,
    teams: false,
    bot: false,
    minPlayers: 1,
    maxPlayers: 1,
  });
  assert.deepEqual([gameRules("701").x01, gameRules("701").teams, gameRules("tactics").teams], [true, true, true]);
  assert.deepEqual(lobbyGames([...OPTIONS, "bingo"], ["501", "bingo", "doubles"]), [
    { group: "x01", games: ["501"] },
    { group: "training", games: ["doubles"] },
    { group: "more", games: ["bingo"] },
  ]);
  assert.deepEqual(lobbyGames(undefined, []), []);
  assert.equal(lobbyGames(OPTIONS, []).length, 4);
  assert.equal(lobbyGames(OPTIONS).length, 4);
});

test("the choice starts from what the board has set, with every name once", () => {
  const board = {
    game: "cricket",
    players: 3,
    names: ["Alex", " alex ", "Sam", "Kim"],
    legs: 20,
    sets: 0,
    double_out: false,
  };
  assert.deepEqual(lobbyChoice(board, ["501", "cricket"]), {
    game: "cricket",
    players: ["Alex", "", "Sam"],
    starts: [0, 0, 0],
    handicap: false,
    teams: false,
    legs: 11,
    sets: 1,
    double_out: false,
    double_in: false,
    bull_off: false,
    bull_off_distance: false,
    tournament: false,
    format: "round_robin",
    third_place: false,
    random_draw: false,
    draft: "",
  });
  const plain = lobbyChoice({ game: "off", players: null, names: [], legs: 2.5, sets: null }, ["301", "501"]);
  // Players without names need not be chosen.
  assert.deepEqual([plain.game, plain.players, plain.legs, plain.sets, plain.double_out], ["501", [], 1, 1, true]);
  assert.equal(lobbyChoice({ game: undefined, names: [] }, ["cricket", "killer"]).game, "cricket");
});

test("taps change the choice within the limits of the action", () => {
  let choice = lobbyChoice({ game: "501", players: 1, names: ["Alex"], legs: 1, sets: 7 }, ["501"]);
  choice = lobbyChange(choice, "add", "  Sam  ");
  choice = lobbyChange(choice, "add", "sam");
  choice = lobbyChange(choice, "add", "");
  choice = lobbyChange(choice, "add", "A very long name for a dart player");
  choice = lobbyChange(choice, "add");
  choice = lobbyChange(choice, "guest");
  assert.deepEqual(choice.players, ["Alex", "Sam", "A very long name for", ""]);
  // Four players at most.
  assert.deepEqual(lobbyChange(choice, "add", "Kim").players, choice.players);
  assert.deepEqual(lobbyChange(choice, "guest").players, choice.players);
  choice = lobbyChange(choice, "up", "1");
  choice = lobbyChange(choice, "down", "2");
  choice = lobbyChange(choice, "up", "0");
  choice = lobbyChange(choice, "down", "3");
  assert.deepEqual(choice.players, ["Sam", "Alex", "", "A very long name for"]);
  choice = lobbyChange(choice, "remove", "2");
  assert.deepEqual(choice.players, ["Sam", "Alex", "A very long name for"]);
  choice = lobbyChange(choice, "legs", "-1");
  choice = lobbyChange(choice, "sets", "1");
  choice = lobbyChange(choice, "legs", "x");
  assert.deepEqual([choice.legs, choice.sets], [1, 7]);
  choice = lobbyChange(choice, "toggle", "double_in");
  choice = lobbyChange(choice, "toggle", "profiles");
  choice = lobbyChange(choice, "game", "killer");
  choice = lobbyChange(choice, "unknown", "1");
  assert.deepEqual([choice.double_in, choice.profiles, choice.game], [true, undefined, "killer"]);
});

test("suggestions put players at home first and leave out who plays already", () => {
  const hass = withPeople(makeHass({ states: READY }));
  const profiles = { attributes: { players: [...PROFILES["sensor.player_profiles"].attributes.players, null] } };
  const links = personLinks(hass, profiles);
  assert.deepEqual([...links.keys()], ["lea", "kim", "alex"]);
  assert.deepEqual(links.get("alex"), { person: "person.alex", picture: PICTURE, home: true });
  assert.deepEqual(links.get("lea"), { person: "person.lea", picture: null, home: false });
  assert.deepEqual(lobbySuggestions(profiles, ["Tom", "sam", "", "  "], links, ["Alex", ""]), [
    { name: "Kim", picture: "/api/image/serve/kim/512x512", home: true },
    { name: "Sam", picture: null, home: false },
    { name: "Lea", picture: null, home: false },
    { name: "Tom", picture: null, home: false },
  ]);
  assert.deepEqual(lobbySuggestions(undefined, [], new Map(), []), []);
  assert.equal(personLinks(undefined, undefined).size, 0);
  // Only pictures Home Assistant serves or that come from the web.
  assert.deepEqual(
    [PICTURE, "https://example.com/a.png", "//evil.example/a.png", "javascript:alert(1)", "data:image/png;base64,", 7].map(
      pictureUrl
    ),
    [PICTURE, "https://example.com/a.png", null, null, null, null]
  );
});

test("the action carries only what the game and the board have", () => {
  const choice = lobbyChoice(
    { game: "501", players: 2, names: ["Alex", "Sam"], legs: 3, sets: 2, bull_off: true, bull_off_distance: true },
    ["501"]
  );
  assert.deepEqual(startGameData(choice, { entry: "entry-1", distance: true }), {
    game: "501",
    players: ["Alex", "Sam"],
    config_entry_id: "entry-1",
    legs: 3,
    sets: 2,
    bull_off: true,
    bull_off_distance: true,
    double_out: true,
    double_in: false,
  });
  // A board before bull-off by distance does not know the field.
  assert.equal("bull_off_distance" in startGameData(choice, { distance: false }), false);
  assert.deepEqual(startGameData({ ...choice, game: "cricket", bull_off: false }, { distance: true }), {
    game: "cricket",
    players: ["Alex", "Sam"],
    legs: 3,
    sets: 2,
    bull_off: false,
  });
  // Training games are for one player; nobody chosen is one player without a name.
  assert.deepEqual(startGameData({ ...choice, game: "doubles" }), { game: "doubles", players: ["Alex"] });
  assert.deepEqual(startGameData({ ...choice, players: [] }), {
    game: "501",
    players: [""],
    double_out: true,
    double_in: false,
  });
});

test("the state of the game decides when the screen and idle mode may come", () => {
  const x01 = (winner) => ({ mode: "x01", practice: { winner } });
  assert.deepEqual(
    [
      { mode: "idle" },
      { mode: "drill", drill: { finished: true } },
      { mode: "drill", drill: { finished: false } },
      { mode: "bulloff", bullOff: {} },
      x01(null),
      x01(1),
      { mode: "cricket", cricket: { winner: 2 } },
      { mode: "party", party: { winner: null } },
    ].map(gameState),
    ["none", "over", "running", "running", "running", "over", "over", "running"]
  );
});

test("between games a big button opens the new game screen with the board's settings", () => {
  const { card } = setup();
  assert.equal($(card, ".lobby-toggle").hidden, false);
  assert.equal(text(card, ".lobby-toggle"), "＋New game");
  assert.equal(text(card, ".main .lobby-cta"), "New game");
  assert.equal(choosing(card), false);
  tap(card, ".main .lobby-cta");

  assert.equal(text(card, ".title"), "New game");
  assert.equal(text(card, ".meta"), "");
  assert.equal($(card, ".lobby-toggle").hidden, true);
  assert.equal($(card, ".visit").hidden, true);
  assert.equal($(card, ".scoreboard").classList.contains("choosing"), true);
  assert.equal($(card, ".lobby").getAttribute("aria-label"), "Choose the game, the players and the format");
  assert.deepEqual(
    $$(card, ".lobby-group .section-label").map((label) => label.textContent),
    ["X01", "Cricket", "Party games", "Training games"]
  );
  assert.equal($$(card, ".game").length, 14);
  assert.deepEqual(chosenGame(card), ["501"]);
  assert.deepEqual(players(card), ["Alex", "Sam"]);
  // Alex is linked to a person with a picture.
  assert.deepEqual(
    $$(card, ".lobby-player .avatar").map((image) => image.getAttribute("src")),
    [PICTURE]
  );
  // Kim is at home and comes first; the empty field and the numbered one are names too.
  assert.deepEqual(suggestions(card), [
    ["suggestion home", "Kim⌂"],
    ["suggestion", "Lea"],
    ["suggestion", "Player 12"],
    ["suggestion guest", "+ Guest"],
    ["suggestion bot", "+ Bot"],
  ]);
  assert.equal($(card, ".suggestion.home .home").getAttribute("aria-label"), "at home");
  assert.deepEqual(steppers(card), ["Legs per set−3+", "Sets to win−1+"]);
  assert.equal($(card, '[data-lobby="sets"][data-value="-1"]').disabled, true);
  assert.equal($(card, '[data-lobby="legs"][data-value="-1"]').getAttribute("aria-label"), "Fewer: Legs per set");
  assert.deepEqual(options(card), [
    ["double_out", "true"],
    ["double_in", "false"],
    ["bull_off", "false"],
  ]);
  assert.equal(text(card, ".lobby .start"), "Start 501");
  // Without a game there is nothing to end.
  assert.equal($(card, '[data-lobby="end"]'), null);
  assert.equal($(card, ".lobby-hint").textContent, "");
});

test("with nobody chosen, one player throws without a name", () => {
  const { hass, card } = setup({ "number.practice_players": "1" });
  card.hass = withNames({ ...hass, entities: { ...hass.entities }, states: { ...hass.states } }, ["", "", "", ""]);
  tap(card, ".lobby-toggle");
  assert.equal($(card, ".lobby-players"), null);
  assert.equal(text(card, ".lobby-nobody"), "Nobody chosen: one player throws without a name.");
  lobbyTap(card, "start");
  assert.deepEqual(started(hass)[0][2], { game: "501", players: [""], double_out: true, double_in: false });
});

test("the format stops at the limits of a match, and a name field without a state is empty", () => {
  const { card } = setup({ "number.practice_legs": "11", "number.practice_sets": "7" });
  card.hass = {
    ...card._hass,
    states: {
      ...card._hass.states,
      "text.dartboard_practice_player_2": { entity_id: "text.dartboard_practice_player_2", state: "unavailable", attributes: {} },
    },
  };
  tap(card, ".lobby-toggle");
  assert.deepEqual(players(card), ["Alex", "Player 2"]);
  assert.equal($(card, '[data-lobby="legs"][data-value="1"]').disabled, true);
  assert.equal($(card, '[data-lobby="sets"][data-value="1"]').disabled, true);
  assert.equal($(card, '[data-lobby="legs"][data-value="1"]').getAttribute("aria-label"), "More: Legs per set");
  assert.deepEqual(steppers(card), ["Legs per set−11+", "Sets to win−7+"]);
});

test("a card that reaches the page before Home Assistant waits for it", () => {
  const card = document.createElement("autodarts-scoreboard-card");
  card.setConfig({ type: "custom:autodarts-scoreboard-card" });
  document.body.append(card);
  card.remove();
  assert.equal(card.shadowRoot.innerHTML, "");
});

test("the new game screen starts the chosen game with players, format and rules", () => {
  const { hass, card } = setup();
  tap(card, ".lobby-toggle");
  lobbyTap(card, "game", "cricket");
  assert.deepEqual(chosenGame(card), ["Cricket"]);
  // Cricket has no double in or out.
  assert.deepEqual(options(card), [["bull_off", "false"]]);
  lobbyTap(card, "add", "Kim");
  assert.deepEqual(players(card), ["Alex", "Sam", "Kim"]);
  assert.deepEqual(suggestions(card)[0], ["suggestion", "Lea"]);
  lobbyTap(card, "up", "2");
  lobbyTap(card, "remove", "2");
  assert.deepEqual(players(card), ["Alex", "Kim"]);
  assert.equal($(card, '[data-lobby="up"][data-value="0"]').disabled, true);
  assert.equal($(card, '[data-lobby="down"][data-value="1"]').disabled, true);
  assert.equal($(card, '[data-lobby="remove"][data-value="1"]').getAttribute("aria-label"), "Remove Kim");
  lobbyTap(card, "down", "0");
  lobbyTap(card, "legs", "1");
  lobbyTap(card, "sets", "1");
  lobbyTap(card, "toggle", "bull_off");
  assert.deepEqual(steppers(card), ["Legs per set−4+", "Sets to win−2+"]);
  assert.deepEqual(options(card), [["bull_off", "true"]]);
  // Without the switch for it, the board has no bull-off by distance.
  assert.equal($(card, '[data-value="bull_off_distance"]'), null);
  lobbyTap(card, "start");
  assert.deepEqual(started(hass), [
    [
      "autodarts",
      "start_game",
      { game: "cricket", players: ["Kim", "Alex"], legs: 4, sets: 2, bull_off: true },
    ],
  ]);
  assert.equal(choosing(card), false);
  assert.equal($(card, ".lobby-toggle").hidden, false);
});

test("names are typed in, and a player can play only once and four at most", () => {
  const { hass, card } = setup();
  tap(card, ".lobby-toggle");
  const input = () => $(card, ".lobby-name");
  assert.equal(input().getAttribute("maxlength"), "20");
  assert.equal(input().getAttribute("placeholder"), "Name");
  assert.equal(input().getAttribute("aria-label"), "Name of another player");
  input().value = "Tom";
  input().dispatchEvent(new window.Event("input", { bubbles: true }));
  // Other keys do nothing; Enter adds the name.
  input().dispatchEvent(new window.KeyboardEvent("keydown", { key: "a", bubbles: true }));
  assert.deepEqual(players(card), ["Alex", "Sam"]);
  input().dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  assert.deepEqual(players(card), ["Alex", "Sam", "Tom"]);
  assert.equal(input().value, "");
  // A name that plays already stays in the field.
  input().value = "alex";
  input().dispatchEvent(new window.Event("input", { bubbles: true }));
  lobbyTap(card, "add-name");
  assert.deepEqual(players(card), ["Alex", "Sam", "Tom"]);
  assert.equal(input().value, "alex");
  lobbyTap(card, "guest");
  assert.deepEqual(players(card), ["Alex", "Sam", "Tom", "Player 4"]);
  // Full: nothing more can be added.
  assert.equal(input().disabled, true);
  assert.ok($$(card, ".suggestion").every((button) => button.disabled));
  assert.equal($(card, '[data-lobby="add-name"]').disabled, true);
  $(card, ".suggestion").click();
  assert.deepEqual(players(card), ["Alex", "Sam", "Tom", "Player 4"]);
  // Other elements do not count as the name field.
  $(card, ".lobby-player .who").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  $(card, ".lobby-player .who").dispatchEvent(new window.Event("input", { bubbles: true }));
  lobbyTap(card, "start");
  assert.deepEqual(started(hass)[0][2].players, ["Alex", "Sam", "Tom", ""]);
});

test("Killer asks for two players, and training games take the first player only", () => {
  const { hass, card } = setup();
  tap(card, ".lobby-toggle");
  lobbyTap(card, "game", "killer");
  lobbyTap(card, "remove", "1");
  assert.equal(text(card, ".lobby-hint"), "Killer needs at least two players");
  assert.equal($(card, ".lobby .start").disabled, true);
  // Alone there is no match: no format and no bull-off.
  assert.equal($(card, ".stepper"), null);
  assert.equal($(card, ".options"), null);
  lobbyTap(card, "start");
  assert.deepEqual(started(hass), []);

  lobbyTap(card, "add", "Lea");
  lobbyTap(card, "game", "around_the_clock");
  assert.equal(text(card, ".lobby-hint"), "Training games are for one player: Alex plays.");
  assert.deepEqual(
    $$(card, ".lobby-player").map((row) => row.className),
    ["lobby-player", "lobby-player resting"]
  );
  assert.equal(text(card, ".lobby .start"), "Start Around the Clock");
  lobbyTap(card, "start");
  assert.deepEqual(started(hass), [["autodarts", "start_game", { game: "around_the_clock", players: ["Alex"] }]]);
});

test("X01 rules, bull-off by distance and the board's config entry go with the start", () => {
  const { hass, card } = setup(
    { "switch.practice_bull_off": "on", "switch.practice_bull_off_distance": "off" },
    {},
    { device: { primary_config_entry: "entry-7", config_entries: ["entry-7"] } }
  );
  tap(card, ".lobby-toggle");
  assert.deepEqual(options(card), [
    ["double_out", "true"],
    ["double_in", "false"],
    ["bull_off", "true"],
    ["bull_off_distance", "false"],
  ]);
  assert.equal(text(card, '[data-value="bull_off_distance"]'), "Bull-off by distance");
  lobbyTap(card, "toggle", "bull_off_distance");
  lobbyTap(card, "toggle", "double_in");
  lobbyTap(card, "toggle", "double_out");
  lobbyTap(card, "game", "301");
  lobbyTap(card, "start");
  assert.deepEqual(started(hass)[0][2], {
    game: "301",
    players: ["Alex", "Sam"],
    config_entry_id: "entry-7",
    legs: 3,
    sets: 1,
    bull_off: true,
    bull_off_distance: true,
    double_out: false,
    double_in: true,
  });
  // Without a primary entry, the first entry of the device.
  const other = setup({}, {}, { device: { config_entries: ["entry-9"] } });
  tap(other.card, ".lobby-toggle");
  lobbyTap(other.card, "start");
  assert.equal(started(other.hass)[0][2].config_entry_id, "entry-9");
});

test("during a game the screen opens with it chosen and can end it with a second tap", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: 0 });
  const running = {
    "select.practice_game": { state: "shanghai", attributes: { options: OPTIONS } },
    "switch.practice_double_out": "off",
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: { game: "shanghai", round: 1, rounds: 7, target: "1", player: 1, scores: [{ player: 1 }] },
    },
  };
  const { hass, card } = setup(running);
  assert.equal($(card, ".main .lobby-cta"), null);
  tap(card, ".lobby-toggle");
  assert.deepEqual(chosenGame(card), ["Shanghai"]);
  const end = () => $(card, '[data-lobby="end"]');
  assert.equal(end().textContent, "End game");
  end().click();
  assert.equal(end().textContent, "Confirm?");
  assert.deepEqual(hass.calls, []);
  // Without the second tap, the question goes away again.
  t.mock.timers.tick(4000);
  assert.equal(end().textContent, "End game");
  end().click();
  end().click();
  assert.deepEqual(hass.calls, [["select", "select_option", { entity_id: "select.dartboard_practice_game", option: "off" }]]);
  // The screen stays for the next game.
  card.hass = update(hass, {
    "select.practice_game": { state: "off", attributes: { options: OPTIONS } },
    "sensor.practice_remaining": "unknown",
  });
  assert.equal(end(), null);
  assert.equal(text(card, ".title"), "New game");
  lobbyTap(card, "close");
  assert.equal(choosing(card), false);
  assert.equal(text(card, ".main .lobby-cta"), "New game");
  // Taps on the screen without a lobby do nothing.
  card._lobbyAction("start");
  assert.equal(hass.calls.length, 1);
});

test("the screen can be switched off, limited to some games, and never opens in the preview", () => {
  const off = setup({}, { lobby: false }).card;
  assert.equal($(off, ".lobby-toggle").hidden, true);
  assert.equal($(off, ".lobby-cta"), null);
  off._lobbyAction("open");
  assert.equal(choosing(off), false);

  const some = setup({}, { lobby_games: ["cricket", "killer", "tactics", 301] }).card;
  tap(some, ".lobby-toggle");
  // YAML reads 301 as a number; it is offered all the same.
  assert.deepEqual(
    $$(some, ".game").map((button) => button.textContent),
    ["301", "Cricket", "Killer"]
  );
  // Without 501 among the games, the first game is chosen.
  assert.deepEqual(chosenGame(some), ["301"]);

  const preview = setup().card;
  preview.preview = true;
  tap(preview, ".lobby-toggle");
  tap(preview, ".main .lobby-cta");
  assert.equal(choosing(preview), false);

  // A board without the practice game has no screen.
  const bare = mount("autodarts-scoreboard-card", makeHass({ states: READY }));
  assert.equal($(bare, ".lobby-toggle").hidden, true);
});

test("a game that ends opens the screen by itself, and throwing darts closes it again", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: 0 });
  const match = (attributes) => ({
    "select.practice_game": { state: "501", attributes: { options: OPTIONS } },
    "sensor.practice_remaining": {
      state: "0",
      attributes: {
        game: 501,
        player: 1,
        name: "Alex",
        scores: [
          { player: 1, name: "Alex", remaining: 0, legs: 1, sets: 1 },
          { player: 2, name: "Sam", remaining: 40, legs: 0, sets: 0 },
        ],
        ...attributes,
      },
    },
  });
  const { hass, card } = setup(match({ winner: null }));
  let next = update(hass, match({ won: true, winner: 1 }));
  card.hass = next;
  assert.equal(text(card, ".banner"), "Alex wins the match!");
  t.mock.timers.tick(7999);
  assert.equal(choosing(card), false);
  t.mock.timers.tick(1);
  assert.equal(text(card, ".title"), "New game");
  // The result stays above the screen.
  assert.equal(text(card, ".banner"), "Alex wins the match!");
  assert.deepEqual(chosenGame(card), ["501"]);
  // The next dart starts the rematch, so the screen that opened by itself goes.
  next = update(next, {
    "sensor.local_visit_score": { state: "60", attributes: { throws: [{ number: 20, multiplier: 3 }] } },
  });
  card.hass = next;
  assert.equal(choosing(card), false);

  // A game that starts again before the pause keeps the screen closed.
  card.hass = next = update(next, match({ winner: null }));
  card.hass = next = update(next, match({ winner: 1 }));
  card.hass = next = update(next, match({ winner: null }));
  t.mock.timers.tick(10000);
  assert.equal(choosing(card), false);

  // A screen opened by a tap stays while darts land.
  tap(card, ".lobby-toggle");
  card.hass = update(next, {
    "sensor.local_visit_score": { state: "120", attributes: { throws: [{ number: 20, multiplier: 3 }, { number: 20, multiplier: 3 }] } },
  });
  assert.equal(text(card, ".title"), "New game");
});

test("the screen that opens by itself waits the idle time before idle mode takes over", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"], now: 0 });
  const decided = (winner) => ({
    "sensor.practice_remaining": {
      state: "0",
      attributes: { game: 501, player: 1, winner, scores: [{ player: 1, remaining: 0 }, { player: 2, remaining: 60 }] },
    },
  });
  const { hass, card } = setup(decided(null), { idle_after: 10 });
  card.hass = update(hass, decided(1));
  t.mock.timers.tick(8000);
  assert.equal(text(card, ".title"), "New game");
  // Ten seconds from the opening, not from the end of the game.
  t.mock.timers.tick(9999);
  assert.equal(choosing(card), true);
  t.mock.timers.tick(1);
  assert.equal(choosing(card), false);
  assert.equal($(card, ".idle-panel").dataset.panel, "clock");

  // Once idle mode has begun, nobody is there to choose: the screen stays closed.
  const early = setup(decided(null), { idle_after: 5 });
  early.card.hass = update(early.hass, decided(1));
  t.mock.timers.tick(5000);
  assert.equal($(early.card, ".idle-panel").dataset.panel, "clock");
  t.mock.timers.tick(5000);
  assert.equal(choosing(early.card), false);
});

test("the new game screen speaks German and names newer games as Home Assistant does", () => {
  const { hass, card } = setup(
    { "select.practice_game": { state: "off", attributes: { options: [...OPTIONS, "bingo"] } } },
    {},
    { language: "de" }
  );
  hass.formatEntityState = (state, option) => (option === "bingo" ? "Bingo" : option);
  card.hass = { ...hass };
  tap(card, ".lobby-toggle");
  assert.equal(text(card, ".title"), "Neues Spiel");
  assert.deepEqual(
    $$(card, ".lobby-group .section-label").map((label) => label.textContent),
    ["X01", "Cricket", "Partyspiele", "Trainingsspiele", "Weitere Spiele"]
  );
  assert.equal($$(card, ".game").at(-1).textContent, "Bingo");
  assert.equal(text(card, ".lobby .start"), "501 starten");
  assert.deepEqual(options(card).map(([option]) => text(card, `[data-value="${option}"]`)), [
    "Double-Out",
    "Double-In",
    "Ausbullen",
  ]);
  assert.deepEqual(
    suggestions(card)
      .slice(-2)
      .map(([, label]) => label),
    ["+ Gast", "+ Bot"]
  );
  assert.deepEqual(
    $$(card, ".lobby-block > .section-label").map((label) => label.textContent),
    ["Spieler", "Format", "Optionen"]
  );
  // Without Home Assistant's names, a newer game reads as its option.
  delete hass.formatEntityState;
  card.hass = update(hass, { "number.practice_legs": "4" });
  assert.equal($$(card, ".game").at(-1).textContent, "bingo");
});

test("in X01 every player can start from a score of their own, in steps of 100", () => {
  let choice = lobbyChoice(
    { game: "501", players: 2, names: ["Alex", "Sam"], starts: [0, 301, "x", 0] },
    ["501", "cricket"]
  );
  assert.deepEqual([choice.starts, choice.handicap], [[0, 301], true]);
  choice = lobbyChange(choice, "raise", "0");
  choice = lobbyChange(choice, "lower", "1");
  assert.deepEqual(choice.starts, [601, 201]);
  // Back at the game's start, a start of its own is 0 again; 101 and 1001 are the limits.
  choice = lobbyChange(choice, "lower", "0");
  assert.deepEqual(choice.starts, [0, 201]);
  for (let step = 0; step < 3; step += 1) choice = lobbyChange(choice, "lower", "1");
  for (let step = 0; step < 6; step += 1) choice = lobbyChange(choice, "raise", "0");
  assert.deepEqual(choice.starts, [1001, 101]);
  // The start scores move and go with their players.
  choice = lobbyChange(choice, "guest");
  choice = lobbyChange(choice, "up", "1");
  assert.deepEqual([choice.players, choice.starts], [["Sam", "Alex", ""], [101, 1001, 0]]);
  choice = lobbyChange(choice, "remove", "0");
  assert.deepEqual(choice.starts, [1001, 0]);
  // Nobody at that place, or a game other than X01, changes nothing.
  assert.deepEqual(lobbyChange(choice, "raise", "5").starts, [1001, 0]);
  assert.deepEqual(lobbyChange({ ...choice, game: "cricket" }, "raise", "1").starts, [1001, 0]);
  assert.deepEqual(startGameData(choice), {
    game: "501",
    players: ["Alex", ""],
    legs: 1,
    sets: 1,
    bull_off: false,
    double_out: true,
    double_in: false,
    start_scores: [1001, 0],
  });
  // Once the board had start scores, the game's start goes back with the start.
  const reset = lobbyChoice({ game: "301", players: 1, names: ["Alex"], starts: [0, 201] }, ["301"]);
  assert.deepEqual(startGameData(reset).start_scores, [0]);
  // A choice from older cards without start scores starts from the game's.
  const { starts, ...older } = reset;
  assert.deepEqual(lobbyChange(older, "raise", "0").starts, [401]);
  const pair = { ...older, players: ["Alex", "Sam"] };
  assert.deepEqual(lobbyChange(pair, "down", "0").starts, [0, 0]);
  assert.equal("start_scores" in startGameData({ ...older, handicap: false }), false);
});

test("four players of X01 or Cricket can play as two teams", () => {
  const names = ["Alex", "Sam", "Kim", "Lea"];
  let choice = lobbyChoice({ game: "cricket", players: 4, names, teams: true }, ["cricket", "golf"]);
  assert.equal(startGameData(choice).teams, true);
  choice = lobbyChange(choice, "toggle", "teams");
  assert.equal(startGameData(choice).teams, false);
  // Teams need four players and a game for teams.
  assert.equal("teams" in startGameData({ ...choice, players: names.slice(0, 3) }), false);
  assert.equal("teams" in startGameData({ ...choice, game: "golf" }), false);
});

test("the new game screen offers teams and start scores of their own", () => {
  const teams = {
    "switch.practice_teams": "off",
    "number.practice_players": "4",
    "select.practice_game": { state: "501", attributes: { options: OPTIONS } },
  };
  const { hass, card } = setup(teams);
  ["Alex", "Sam", "Kim", "Lea"].forEach((name, index) => {
    const id = `text.dartboard_practice_player_${index + 1}`;
    hass.states[id] = { ...hass.states[id], state: name };
  });
  // The four start scores share one translation key, like the names.
  hass.entities = { ...hass.entities };
  [0, 301, 0, "unavailable"].forEach((start, index) => {
    const id = `number.dartboard_practice_start_score_player_${index + 1}`;
    hass.entities[id] = { entity_id: id, platform: "autodarts", device_id: DEVICE, translation_key: "practice_start" };
    hass.states[id] = { entity_id: id, state: String(start), attributes: {} };
  });
  card.hass = { ...hass };
  tap(card, ".lobby-toggle");
  assert.deepEqual(
    $$(card, ".lobby-start").map((start) => [start.className, start.querySelector("b").textContent]),
    [
      ["lobby-start", "501"],
      ["lobby-start own", "301"],
      ["lobby-start", "501"],
      ["lobby-start", "501"],
    ]
  );
  assert.equal($(card, '[data-lobby="raise"][data-value="0"]').getAttribute("aria-label"), "Higher start score: Alex");
  lobbyTap(card, "raise", "0");
  // 101 and 1001 are the limits of the steps.
  for (let step = 0; step < 5; step += 1) lobbyTap(card, "raise", "2");
  for (let step = 0; step < 4; step += 1) lobbyTap(card, "lower", "3");
  assert.deepEqual(
    ["raise", "lower"].map((action) => $(card, `[data-lobby="${action}"][data-value="${action === "raise" ? 2 : 3}"]`).disabled),
    [true, true]
  );
  assert.deepEqual(options(card), [
    ["double_out", "true"],
    ["double_in", "false"],
    ["bull_off", "false"],
    ["teams", "false"],
  ]);
  assert.equal(text(card, '[data-value="teams"]'), "Teams (1 + 3 against 2 + 4)");
  lobbyTap(card, "toggle", "teams");
  tap(card, ".lobby .start");
  const [[, , data]] = started(hass);
  assert.deepEqual([data.start_scores, data.teams], [[601, 301, 1001, 101], true]);
  // Cricket has no start scores; without the team switch, no teams are offered.
  const cricket = setup({ "number.practice_players": "4" });
  tap(cricket.card, ".lobby-toggle");
  lobbyTap(cricket.card, "game", "cricket");
  assert.deepEqual([$$(cricket.card, ".lobby-start").length, options(cricket.card).length], [0, 1]);
});
