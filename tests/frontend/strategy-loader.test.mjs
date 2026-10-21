// The dashboard strategy's own small module: registered at once, the card module behind it.
import assert from "node:assert/strict";
import { test } from "node:test";

// The browser comes first; the module then waits for Home Assistant's app element.
import { makeHass, settle, window as page } from "./dom.mjs";
import {
  CARD_MODULE,
  cardModule,
  cardStrategy,
  registerStrategy,
  strategyElement,
} from "../../custom_components/homedarts/frontend/homedarts-strategy.js";

const STRATEGY = "ll-strategy-dashboard-homedarts";
const CARD = new URL("../../custom_components/homedarts/frontend/homedarts-card.js", import.meta.url);

test("the strategy waits for Home Assistant's app element, then registers before the cards", async () => {
  await settle();
  assert.equal(customElements.get(STRATEGY), undefined);

  customElements.define("home-assistant", class extends HTMLElement {});
  await customElements.whenDefined(STRATEGY);
  // Nothing of homedarts-card.js has loaded: the strategy needs none of it to exist.
  assert.equal(customElements.get("homedarts-scoreboard-card"), undefined);
  assert.equal(page.customStrategies, undefined);
});

test("the card module is the one Home Assistant loads, with the same version", () => {
  assert.equal(CARD_MODULE, CARD.href);
  // Home Assistant loads both from the folder of the version, which the import keeps.
  assert.equal(
    cardModule("http://homeassistant.local:8123/homedarts/1.16.0-0123abcd/homedarts-strategy.js"),
    "http://homeassistant.local:8123/homedarts/1.16.0-0123abcd/homedarts-card.js"
  );
  // A resource of an earlier release had the version in its query.
  assert.equal(
    cardModule("http://homeassistant.local:8123/homedarts/homedarts-strategy.js?v=1.12.1-0123abcd"),
    "http://homeassistant.local:8123/homedarts/homedarts-card.js?v=1.12.1-0123abcd"
  );
});

test("a card module that failed to load is loaded again by the next call", async () => {
  await assert.rejects(cardStrategy(() => Promise.reject(new Error("offline"))), /offline/);
  const strategy = await cardStrategy();
  assert.equal(typeof strategy.generate, "function");
  assert.equal(await cardStrategy(), strategy);
});

test("the strategy builds the dashboard of homedarts-card.js and keeps its element", async () => {
  const card = await import(CARD.href);
  const hass = makeHass();
  const element = customElements.get(STRATEGY);
  assert.deepEqual(await element.generate({}, hass), card.dashboardStrategy(hass, {}));
  // The card module registers its cards and leaves the strategy that came first.
  await customElements.whenDefined("homedarts-scoreboard-card");
  assert.equal(customElements.get(STRATEGY), element);
  assert.deepEqual(
    page.customStrategies.map((known) => known.type),
    ["homedarts"]
  );
});

test("the strategy's editor is the one of homedarts-card.js", async () => {
  const editor = await customElements.get(STRATEGY).getConfigElement();
  assert.equal(editor.localName, "homedarts-strategy-editor");
});

test("a strategy the page already knows is kept", () => {
  const known = customElements.get(STRATEGY);
  registerStrategy();
  assert.equal(customElements.get(STRATEGY), known);
  assert.notEqual(strategyElement(HTMLElement), known);
});
