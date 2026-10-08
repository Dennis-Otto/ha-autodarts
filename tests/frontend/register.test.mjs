// Registration with Home Assistant: elements, card picker entries and the dashboard strategy.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Window } from "happy-dom";

// The browser comes first; the module then waits for Home Assistant's app element.
import { READY, makeHass, settle, window as page } from "./dom.mjs";
import {
  createElements,
  dashboardStrategy,
  frontendReady,
  register,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const DOCS = "https://dennis-otto.github.io/ha-autodarts";
const CARDS = [
  ["autodarts-card", "Autodarts", "cards.html#live-card"],
  ["autodarts-training-card", "Autodarts training", "cards.html#training-card"],
  ["autodarts-status-card", "Autodarts board status", "cards.html#board-status-card"],
  ["autodarts-scoreboard-card", "Autodarts scoreboard", "cards.html#scoreboard-card"],
  ["autodarts-players-card", "Autodarts players", "cards.html#players-card"],
  ["autodarts-doubles-card", "Autodarts doubles", "cards.html#doubles-card"],
  ["autodarts-leaderboard-card", "Autodarts leaderboard", "cards.html#leaderboard-card"],
];
const ELEMENTS = [
  "ll-strategy-dashboard-autodarts",
  "autodarts-strategy-editor",
  "autodarts-card",
  "autodarts-training-card",
  "autodarts-status-card",
  "autodarts-scoreboard-card",
  "autodarts-players-card",
  "autodarts-doubles-card",
  "autodarts-leaderboard-card",
];
const STRATEGY = {
  type: "autodarts",
  strategyType: "dashboard",
  name: "Autodarts",
  description: "Live, scoreboard, training, players and board views for every Autodarts board, built automatically.",
  documentationURL: `${DOCS}/cards.html#automatic-dashboard`,
};
// Entries as Home Assistant reads them when it opens a picker.
const read = (entries) => entries.map((entry) => ({ ...entry }));

test("the cards wait for Home Assistant's app element before they register", async () => {
  await new Promise((resolve) => setTimeout(resolve, 120));
  assert.equal(customElements.get("autodarts-card"), undefined);
  assert.equal(page.customCards, undefined);

  customElements.define("home-assistant", class extends HTMLElement {});
  await customElements.whenDefined("autodarts-card");
  for (const type of ELEMENTS) assert.equal(typeof customElements.get(type), "function", type);
  assert.deepEqual(
    read(page.customCards).map(({ type, name, preview, documentationURL }) => [type, name, preview, documentationURL]),
    CARDS.map(([type, name, anchor]) => [type, name, true, `${DOCS}/${anchor}`])
  );
  for (const card of page.customCards) assert.ok(card.description.length > 40, card.type);
  assert.match(page.customCards[3].description, /Cricket, party and training games/);
  assert.deepEqual(read(page.customStrategies), [STRATEGY]);
});

test("the card picker speaks the language Home Assistant has when it opens", () => {
  page.document.documentElement.lang = "de";
  const [live, training, , scoreboard, , doubles, leaderboard] = read(page.customCards);
  assert.deepEqual(
    [live.name, training.name, scoreboard.name, doubles.name, leaderboard.name],
    ["Autodarts", "Autodarts-Training", "Autodarts-Anzeigetafel", "Autodarts-Doubles", "Autodarts-Bestenliste"]
  );
  assert.equal(training.documentationURL, `${DOCS}/de/cards.html#trainingskarte`);
  assert.equal(leaderboard.documentationURL, `${DOCS}/de/cards.html#bestenliste`);
  assert.match(scoreboard.description, /^Eine große Anzeigetafel/);
  const [strategy] = read(page.customStrategies);
  assert.equal(strategy.documentationURL, `${DOCS}/de/cards.html#automatisches-dashboard`);
  assert.match(strategy.description, /^Live-, Anzeigetafel-, Trainings-, Spieler- und Board-Ansicht/);
  page.document.documentElement.lang = "en";
});

test("registering again adds no duplicate cards, strategies or elements", () => {
  const cards = [...page.customCards];
  const live = customElements.get("autodarts-card");
  register();
  assert.deepEqual(page.customCards, cards);
  assert.deepEqual(read(page.customStrategies), [STRATEGY]);
  assert.equal(customElements.get("autodarts-card"), live);
});

test("elements and entries the page already knows are kept", (t) => {
  const other = new Window({ url: "http://localhost:8123/" });
  const own = class extends other.HTMLElement {};
  other.customElements.define("autodarts-card", own);
  other.customCards = [{ type: "autodarts-card", name: "Mine" }];
  other.customStrategies = [{ type: "autodarts", name: "Mine" }];
  globalThis.window = other;
  t.after(async () => {
    globalThis.window = page;
    await other.happyDOM.close();
  });
  register();
  assert.equal(other.customElements.get("autodarts-card"), own);
  assert.equal(typeof other.customElements.get("autodarts-training-card"), "function");
  assert.deepEqual(
    other.customCards.map((card) => [card.type, card.name]),
    [["autodarts-card", "Mine"], ...CARDS.slice(1).map(([type, name]) => [type, name])]
  );
  assert.deepEqual(other.customStrategies, [{ type: "autodarts", name: "Mine" }]);
});

test("other hosts get the cards after thirty seconds", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  // A host without Home Assistant's app element, and one without whenDefined at all.
  globalThis.window = { customElements: { get: () => undefined, whenDefined: () => new Promise(() => {}) } };
  t.after(() => (globalThis.window = page));
  let ready = false;
  const waiting = frontendReady().then(() => (ready = true));
  for (let waited = 0; waited < 29950; waited += 50) {
    t.mock.timers.tick(50);
    await settle();
  }
  assert.equal(ready, false);
  t.mock.timers.tick(50);
  await waiting;
  assert.equal(ready, true);
  globalThis.window = { customElements: { get: () => undefined } };
  const plain = frontendReady(100);
  t.mock.timers.tick(100);
  await plain;
});

test("the cards register as soon as Home Assistant's app element exists", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const cleared = t.mock.method(globalThis, "clearTimeout");
  let define;
  globalThis.window = {
    customElements: { get: () => undefined, whenDefined: () => new Promise((resolve) => (define = resolve)) },
  };
  try {
    const waiting = frontendReady();
    define();
    await waiting;
    // No thirty-second timer is left behind: the one that was set is cleared.
    assert.equal(cleared.mock.callCount(), 1);
    assert.notEqual(cleared.mock.calls[0].arguments[0], undefined);
  } finally {
    globalThis.window = page;
  }
});

test("the element factory builds every card, editor and the strategy on the given base class", () => {
  class Base {}
  const elements = createElements(Base);
  assert.deepEqual(Object.keys(elements), ELEMENTS);
  for (const element of Object.values(elements)) assert.ok(element.prototype instanceof Base);
});

test("the strategy element generates the dashboard of every board", async () => {
  const Strategy = customElements.get("ll-strategy-dashboard-autodarts");
  const hass = makeHass({ states: READY });
  const dashboard = await Strategy.generate({ title: "Darts" }, hass);
  assert.deepEqual(dashboard, dashboardStrategy(hass, { title: "Darts" }));
  assert.equal(dashboard.title, "Darts");
  assert.deepEqual(
    dashboard.views.map((view) => view.path),
    ["live", "scoreboard", "training", "board"]
  );
});

test("every card asks for a board in its own style when there is none", () => {
  const styles = CARDS.map(([type]) => {
    const card = document.createElement(type);
    card.setConfig({});
    card.hass = makeHass({ language: "de" });
    assert.equal(
      card.shadowRoot.querySelector("ha-card .message").textContent,
      "Kein Autodarts-Board gefunden. Wähle ein Gerät in den Karteneinstellungen.",
      type
    );
    return card.shadowRoot.querySelector("style").textContent;
  });
  assert.equal(new Set(styles).size, CARDS.length);
});

test("a card without its own style shows its message with the base style", () => {
  const Live = customElements.get("autodarts-card");
  class BareCard extends Object.getPrototypeOf(Live) {}
  customElements.define("bare-autodarts-card", BareCard);
  const bare = document.createElement("bare-autodarts-card");
  bare.setConfig({});
  bare.hass = makeHass();
  const live = document.createElement("autodarts-card");
  live.setConfig({});
  live.hass = makeHass();
  const base = bare.shadowRoot.querySelector("style").textContent;
  const full = live.shadowRoot.querySelector("style").textContent;
  assert.equal(
    bare.shadowRoot.querySelector(".message").textContent,
    "No Autodarts board found. Select a device in the card settings."
  );
  assert.ok(full.startsWith(base) && full.length > base.length);
  assert.deepEqual(bare.getGridOptions(), { columns: 12, min_columns: 6 });
});
