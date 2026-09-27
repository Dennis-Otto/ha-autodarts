// The visual editors: Home Assistant's forms for the cards, and the editor of the dashboard strategy.
import assert from "node:assert/strict";
import { test } from "node:test";

import { DEVICE, READY, loadCards, makeHass, mount, settle, window, withLanguage } from "./dom.mjs";

await loadCards();

const CARDS = ["", "training-", "status-", "scoreboard-", "players-", "doubles-"].map((name) => `autodarts-${name}card`);
const formOf = (type) => customElements.get(type).getConfigForm();
// Field names of a schema, with grids and sections as nested lists.
const names = (schema) => schema.map((field) => (field.schema ? names(field.schema) : field.name));
const labels = (field) => field.selector.select.options.map((option) => option.label);
const DEVICE_FIELD = { name: "device_id", selector: { device: { filter: { integration: "autodarts" } } } };
const TITLE_FIELD = { name: "title", selector: { text: {} } };
const ACCENT_FIELD = { name: "accent_color", selector: { ui_color: { default_color: "primary" } } };

test("every card brings a form of Home Assistant and no editor element of its own", () => {
  for (const type of CARDS) {
    const card = customElements.get(type);
    assert.equal(card.getConfigElement, undefined, type);
    const form = card.getConfigForm();
    assert.deepEqual(form.schema.slice(0, 2), [DEVICE_FIELD, TITLE_FIELD], type);
    // Every card has its accent colour in the editor.
    assert.ok(JSON.stringify(form.schema).includes('"accent_color"'), type);
  }
  class BareCard extends Object.getPrototypeOf(customElements.get("autodarts-card")) {}
  assert.equal(BareCard.getConfigForm(), undefined);
});

test("the live card form offers layout, board style, highlight, every switch and both colours", () => {
  const form = formOf("autodarts-card");
  assert.deepEqual(names(form.schema), [
    "device_id",
    "title",
    ["layout", "board_style"],
    "highlight",
    [
      "blink",
      "show_markers",
      "show_numbers",
      "show_stats",
      "show_recent",
      "show_practice",
      "show_connection",
      "show_controls",
      "show_summary",
    ],
    "summary_seconds",
    ["accent_color", "highlight_color"],
  ]);
  const [layout, style] = form.schema[2].schema;
  assert.deepEqual(labels(layout), ["Automatic", "Board on the right", "Board below", "Board only"]);
  assert.deepEqual(layout.selector.select.options[0], { value: "auto", label: "Automatic" });
  assert.equal(layout.selector.select.mode, "dropdown");
  assert.deepEqual(labels(style), ["Classic", "Autodarts"]);
  assert.deepEqual(labels(form.schema[3]), ["All darts of the visit", "Last dart only", "Off"]);
  // Switches show their default until the configuration sets them.
  assert.deepEqual(form.schema[4].schema[0], { name: "blink", selector: { boolean: {} }, default: true });
  assert.deepEqual(form.schema[6].schema, [ACCENT_FIELD, { name: "highlight_color", selector: { ui_color: {} } }]);
  // The summary of a finished match shows until the next game, unless seconds are set.
  assert.deepEqual(form.schema[5], {
    name: "summary_seconds",
    selector: { number: { min: 0, max: 600, step: 1, mode: "box", unit_of_measurement: "s" } },
    default: 0,
  });
  assert.equal(form.computeLabel(form.schema[5]), "Match summary (seconds)");
  assert.match(form.computeHelper(form.schema[5]), /0 keeps it until the next game starts/);
  assert.throws(() => form.assertConfig({ summary_seconds: "long" }), /summary_seconds/);
});

test("fields are labelled and explained in the page's language, with the default of every list", () => {
  const form = formOf("autodarts-card");
  assert.equal(form.computeLabel({ name: "board_style" }), "Board style");
  assert.equal(form.computeLabel({ name: "" }), undefined);
  // A field without a text of its own reads as its name, and Home Assistant may add its own.
  assert.equal(form.computeLabel({ name: "grid_options" }), "grid_options");
  assert.equal(
    form.computeHelper({ name: "device_id" }),
    "Optional. Without a selection, the card uses the first Autodarts board."
  );
  assert.match(form.computeHelper({ name: "accent_color" }), /^A theme color from the list, or any CSS color such as #00e5ff\./);
  assert.match(form.computeHelper({ name: "highlight_color" }), /gold \(#ffd60a\)/);
  assert.equal(form.computeHelper({ name: "layout" }), "Default: Automatic");
  assert.equal(form.computeHelper({ name: "highlight" }), "Default: All darts of the visit");
  assert.equal(form.computeHelper({ name: "title" }), undefined);
  assert.equal(form.computeHelper({ name: "blink" }), undefined);
  assert.equal(formOf("autodarts-training-card").computeHelper({ name: "board_style" }), "Default: Muted");

  // Home Assistant sets the page language; the form follows it.
  window.document.documentElement.lang = "de";
  const german = formOf("autodarts-card");
  assert.deepEqual(labels(german.schema[2].schema[0]), ["Automatisch", "Scheibe rechts", "Scheibe unten", "Nur Scheibe"]);
  assert.equal(german.computeLabel({ name: "layout" }), "Anordnung");
  assert.equal(german.computeHelper({ name: "layout" }), "Standard: Automatisch");
  window.document.documentElement.lang = "";
});

test("every card has the form of its own options", () => {
  const training = formOf("autodarts-training-card");
  assert.deepEqual(names(training.schema), [
    "device_id",
    "title",
    ["mode", "board_style"],
    "player",
    "history_size",
    [
      "show_heatmap",
      "show_heatmap_controls",
      "show_stats",
      "show_bests",
      "show_top",
      "show_history",
      "show_sessions",
      "show_reset",
    ],
    "accent_color",
  ]);
  const [mode, style] = training.schema[2].schema;
  assert.deepEqual(labels(mode), ["Beds", "Numbers", "Positions"]);
  assert.deepEqual(labels(style), ["Muted", "Classic", "Autodarts"]);
  // The heatmap's player has help of its own.
  assert.match(training.computeHelper(training.schema[3]), /this player's darts instead of the session's/);
  assert.deepEqual(training.schema[4], {
    name: "history_size",
    selector: { number: { min: 5, max: 60, step: 1, mode: "slider" } },
    default: 20,
  });
  assert.deepEqual(names(formOf("autodarts-status-card").schema), [
    "device_id",
    "title",
    ["show_connection", "show_system", "show_cameras", "show_controls"],
    "accent_color",
  ]);
  const players = formOf("autodarts-players-card");
  assert.deepEqual(names(players.schema), [
    "device_id",
    "title",
    ["show_head_to_head", "show_matches", "show_badges", "show_locked", "show_trends", "show_spread", "export"],
    "trend_weeks",
    "export_format",
    "accent_color",
  ]);
  // The export writes player names into a file: off unless asked for.
  assert.equal(players.schema[2].schema[6].default, false);
  assert.deepEqual(players.schema[3].selector, { number: { min: 4, max: 12, step: 1, mode: "slider" } });
  assert.deepEqual(labels(players.schema[4]), ["CSV (a ZIP file with one table each)", "JSON"]);
  assert.equal(players.computeHelper({ name: "export_format" }), "Default: CSV (a ZIP file with one table each)");
  const leaderboard = formOf("autodarts-leaderboard-card");
  assert.deepEqual(names(leaderboard.schema), [
    "device_id",
    "title",
    ["period", "limit"],
    ["show_period"],
    "accent_color",
  ]);
  assert.deepEqual(labels(leaderboard.schema[2].schema[0]), ["All time", "Last 4 weeks", "This week"]);
  assert.equal(leaderboard.computeHelper({ name: "period" }), "Default: All time");
  assert.throws(() => leaderboard.assertConfig({ period: "year" }), /The option period does not accept "year"/);
  leaderboard.assertConfig({ period: "week", limit: 5, show_period: false });
});

test("the caller's calls, the new game screen and idle mode wait in sections of their own", () => {
  const form = formOf("autodarts-scoreboard-card");
  assert.deepEqual(names(form.schema), [
    "device_id",
    "title",
    ["full_height", "show_visit", "show_status", "caller", "show_summary"],
    "summary_seconds",
    [["call_scores", "call_checkouts", "call_results", "call_sounds"]],
    [["lobby"], "lobby_games"],
    ["tournament_summary"],
    [["idle"], ["idle_after", "idle_interval"], "idle_panels"],
    "accent_color",
  ]);
  assert.equal(form.schema[2].schema[4].default, true);
  const [caller, lobby, tournament, idle] = form.schema.slice(4, 8);
  assert.deepEqual([caller.type, caller.name, caller.flatten], ["expandable", "caller_options", true]);
  assert.equal(form.computeLabel(caller), "Caller options");
  assert.equal(form.computeHelper(caller), "These calls are made while the caller is on.");
  assert.equal(form.schema[2].schema[3].default, false);
  assert.equal(caller.schema[0].schema[0].default, true);

  // The new game screen is on by default and offers every game, unless the card names some.
  assert.deepEqual([lobby.type, lobby.name, lobby.flatten], ["expandable", "lobby_section", true]);
  assert.equal(form.computeLabel(lobby), "New game screen");
  assert.match(form.computeHelper(lobby), /^Tap New game to choose the game/);
  assert.equal(lobby.schema[0].schema[0].default, true);
  const games = lobby.schema[1];
  assert.deepEqual([games.selector.select.multiple, games.selector.select.mode], [true, "dropdown"]);
  // Without a board on the page, the form offers every game the card knows.
  assert.deepEqual(labels(games).slice(5, 11), [
    "1001",
    "Cricket",
    "Cut-Throat Cricket",
    "Tactics",
    "Shanghai",
    "Halve-It",
  ]);
  assert.equal(labels(games).at(-1), "Singles training");
  assert.equal(form.computeLabel(games), "Games offered");
  assert.equal(form.computeHelper(games), "Empty offers every game of the board.");

  assert.deepEqual([idle.type, idle.name, idle.flatten], ["expandable", "idle_section", true]);
  assert.equal(form.computeLabel(idle), "Idle mode");
  assert.equal(idle.schema[0].schema[0].default, true);
  const seconds = (min, max) => ({ number: { min, max, step: 1, mode: "box", unit_of_measurement: "s" } });
  assert.deepEqual(idle.schema[1].schema, [
    { name: "idle_after", selector: seconds(10, 3600), default: 180 },
    { name: "idle_interval", selector: seconds(3, 120), default: 10 },
  ]);
  assert.deepEqual(labels(idle.schema[2]), [
    "Tournament",
    "Leaderboard",
    "Personal bests",
    "Today",
    "Last match",
    "Clock",
  ]);

  // The result of a tournament match shows for a few seconds, then the table or the bracket.
  assert.deepEqual([tournament.type, tournament.name, tournament.flatten], ["expandable", "tournament_section", true]);
  assert.equal(form.computeLabel(tournament), "Tournament");
  assert.deepEqual(tournament.schema, [{ name: "tournament_summary", selector: seconds(0, 60), default: 5 }]);
  assert.equal(form.computeLabel(tournament.schema[0]), "Summary before the tournament view");
  assert.match(form.computeHelper(tournament.schema[0]), /^After a tournament match, its summary stays/);
  assert.equal(idle.schema[2].selector.select.mode, "list");
  assert.equal(form.computeHelper(idle.schema[2]), "Empty shows every panel.");

  // Lists accept the games and panels they offer, and nothing else.
  assert.doesNotThrow(() => form.assertConfig({ lobby_games: [501, "cricket"], idle_panels: [], idle_after: 60 }));
  assert.throws(() => form.assertConfig({ lobby_games: ["pool"] }), /lobby_games/);
  assert.throws(() => form.assertConfig({ idle_panels: "clock" }), /idle_panels/);
  assert.throws(() => form.assertConfig({ idle_after: "soon" }), /idle_after/);
});

test("the editor offers the games of the board on the page", () => {
  const hass = makeHass({
    states: {
      ...READY,
      "select.practice_game": { state: "off", attributes: { options: ["off", "501", "cricket", "bingo"] } },
    },
  });
  // The practice game of another integration does not count.
  const other = { entity_id: "select.other_game", platform: "other", translation_key: "practice_game" };
  hass.entities = { "select.other_game": other, ...hass.entities };
  mount("autodarts-scoreboard-card", hass).remove();
  const games = formOf("autodarts-scoreboard-card").schema[5].schema[1];
  assert.deepEqual(games.selector.select.options, [
    { value: "501", label: "501" },
    { value: "cricket", label: "Cricket" },
    { value: "bingo", label: "bingo" },
  ]);
  // A board without the practice game leaves the list of every game the card knows.
  mount("autodarts-scoreboard-card", makeHass({ states: READY })).remove();
  assert.equal(formOf("autodarts-scoreboard-card").schema[5].schema[1].selector.select.options.length, 23);
});

test("the doubles form offers the named players and takes any other name", () => {
  let form = formOf("autodarts-doubles-card");
  assert.deepEqual(form.schema[2], {
    name: "player",
    selector: { select: { mode: "dropdown", custom_value: true, options: [] } },
  });
  assert.equal(
    form.computeHelper({ name: "player" }),
    "Optional. Pick or type a player name for that player's doubles; empty shows everybody's."
  );
  // A card on the page brings Home Assistant, and with it the profiles of every board.
  const profiles = { state: "2", attributes: { players: [{ name: "Sam" }, { name: "Alex" }, { name: "" }, null] } };
  const hass = makeHass({ states: { ...READY, "sensor.player_profiles": profiles } });
  hass.entities["sensor.other_profiles"] = { entity_id: "sensor.other_profiles", platform: "other", translation_key: "player_profiles" };
  hass.entities["sensor.empty_profiles"] = { entity_id: "sensor.empty_profiles", platform: "autodarts", translation_key: "player_profiles" };
  mount("autodarts-doubles-card", hass).remove();
  form = formOf("autodarts-doubles-card");
  assert.deepEqual(form.schema[2].selector.select.options, [
    { value: "Alex", label: "Alex" },
    { value: "Sam", label: "Sam" },
  ]);
  // The language of that Home Assistant wins over the page's.
  mount("autodarts-doubles-card", withLanguage(hass, "de")).remove();
  assert.equal(formOf("autodarts-doubles-card").computeLabel({ name: "player" }), "Spieler");
  mount("autodarts-doubles-card", hass).remove();
});

test("options the form cannot show send the editor to the code view", () => {
  const form = formOf("autodarts-card");
  for (const config of [
    { type: "custom:autodarts-card" },
    { layout: "vertical", blink: false, accent_color: "#00e5ff", device_id: "", title: null },
    { highlight_color: "anything" },
  ]) {
    assert.doesNotThrow(() => form.assertConfig(config));
  }
  assert.throws(() => form.assertConfig({ layout: "diagonal" }), {
    message: 'The option layout does not accept "diagonal".',
  });
  assert.throws(() => form.assertConfig({ blink: "yes" }), { message: 'The option blink does not accept "yes".' });
  const training = formOf("autodarts-training-card");
  assert.throws(() => training.assertConfig({ history_size: "many" }), /history_size/);
  assert.doesNotThrow(() => training.assertConfig({ history_size: 40 }));
  // The doubles card takes any player name.
  assert.doesNotThrow(() => formOf("autodarts-doubles-card").assertConfig({ player: "Somebody new" }));
  assert.doesNotThrow(() => form.assertConfig(undefined));
});

// Home Assistant's form element, reduced to the properties the strategy editor sets.
class FakeForm extends HTMLElement {}

test("the dashboard strategy has an editor with the board and the title", async () => {
  const Strategy = customElements.get("ll-strategy-dashboard-autodarts");
  // Without card helpers the editor just waits for the form.
  delete window.loadCardHelpers;
  const waiting = await Strategy.getConfigElement();
  assert.equal(waiting.localName, "autodarts-strategy-editor");
  window.loadCardHelpers = async () => {
    throw new Error("helpers unavailable");
  };
  const failing = await Strategy.getConfigElement();
  const hass = makeHass({ states: READY });
  for (const element of [waiting, failing]) {
    element.setConfig({ type: "custom:autodarts" });
    element.hass = hass;
    document.body.append(element);
    assert.equal(element.querySelector("ha-form"), null);
  }
  // A built-in card editor defines the form, as it does in Home Assistant.
  const created = [];
  window.loadCardHelpers = async () => ({
    createCardElement: async (config) => {
      created.push(config);
      return new (class EntitiesCard {
        static getConfigElement() {
          customElements.define("ha-form", FakeForm);
        }
      })();
    },
  });
  const loading = await Strategy.getConfigElement();
  assert.deepEqual(created, [{ type: "entities", entities: [] }]);
  await settle();
  for (const element of [waiting, failing]) assert.ok(element.querySelector("ha-form") instanceof FakeForm);
  // Once the form exists, nothing needs loading any more.
  window.loadCardHelpers = async () => assert.fail("loaded twice");
  await Strategy.getConfigElement();
  delete window.loadCardHelpers;

  loading.setConfig({ type: "custom:autodarts", title: "Darts" });
  document.body.append(loading);
  assert.equal(loading.querySelector("ha-form"), null);
  loading.hass = hass;
  const form = loading.querySelector("ha-form");
  assert.deepEqual(form.schema, [DEVICE_FIELD, TITLE_FIELD]);
  assert.deepEqual(form.data, { type: "custom:autodarts", title: "Darts" });
  assert.equal(form.hass, hass);
  assert.equal(form.computeLabel({ name: "device_id" }), "Board");
  assert.equal(
    form.computeHelper({ name: "device_id" }),
    "Optional. Without a selection, the dashboard shows every Autodarts board."
  );
  assert.equal(form.computeHelper({ name: "title" }), undefined);
  assert.equal(form.computeLabel({ name: "theme" }), "theme");

  const changes = [];
  loading.addEventListener("config-changed", (event) => changes.push(event.detail.config));
  const outside = [];
  document.addEventListener("value-changed", () => outside.push(true), { once: true });
  form.dispatchEvent(
    new CustomEvent("value-changed", {
      bubbles: true,
      detail: { value: { type: "custom:autodarts", title: "", device_id: DEVICE } },
    })
  );
  assert.deepEqual(changes, [{ type: "custom:autodarts", device_id: DEVICE }]);
  assert.deepEqual(outside, []);
  // A new configuration keeps the form.
  loading.setConfig({ type: "custom:autodarts" });
  assert.equal(loading.querySelector("ha-form"), form);
  assert.deepEqual(form.data, { type: "custom:autodarts" });
  loading.hass = withLanguage(hass, "de");
  assert.equal(form.computeLabel({ name: "title" }), "Titel");
});
