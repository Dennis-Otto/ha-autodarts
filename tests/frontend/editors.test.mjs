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
    ],
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
  assert.deepEqual(form.schema[5].schema, [ACCENT_FIELD, { name: "highlight_color", selector: { ui_color: {} } }]);
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
    "history_size",
    ["show_heatmap", "show_stats", "show_bests", "show_top", "show_history", "show_sessions", "show_reset"],
    "accent_color",
  ]);
  const [mode, style] = training.schema[2].schema;
  assert.deepEqual(labels(mode), ["Beds", "Numbers"]);
  assert.deepEqual(labels(style), ["Muted", "Classic", "Autodarts"]);
  assert.deepEqual(training.schema[3], {
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
    ["show_head_to_head", "show_matches", "export"],
    "export_format",
    "accent_color",
  ]);
  // The export writes player names into a file: off unless asked for.
  assert.equal(players.schema[2].schema[2].default, false);
  assert.deepEqual(labels(players.schema[3]), ["CSV (a ZIP file with one table each)", "JSON"]);
  assert.equal(players.computeHelper({ name: "export_format" }), "Default: CSV (a ZIP file with one table each)");
});

test("the caller's calls wait in a section of their own", () => {
  const form = formOf("autodarts-scoreboard-card");
  assert.deepEqual(names(form.schema), [
    "device_id",
    "title",
    ["full_height", "show_visit", "show_status", "caller"],
    [["call_scores", "call_checkouts", "call_results", "call_sounds"]],
    "accent_color",
  ]);
  const section = form.schema[3];
  assert.deepEqual([section.type, section.name, section.flatten], ["expandable", "caller_options", true]);
  assert.equal(form.computeLabel(section), "Caller options");
  assert.equal(form.computeHelper(section), "These calls are made while the caller is on.");
  assert.equal(form.schema[2].schema[3].default, false);
  assert.equal(section.schema[0].schema[0].default, true);
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
