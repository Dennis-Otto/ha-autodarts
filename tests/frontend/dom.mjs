// A browser for the card elements: a happy-dom window as globals and a fake Home Assistant.
import { after } from "node:test";

import { Window } from "happy-dom";

// Dates read the same on every machine.
process.env.TZ = "UTC";

export const window = new Window({ url: "http://localhost:8123/lovelace/0" });
globalThis.window = window;
for (const name of ["document", "customElements", "HTMLElement", "CustomEvent"]) globalThis[name] = window[name];

// happy-dom drops a numeric 0 written to textContent; browsers write "0" like any other number.
const textContent = Object.getOwnPropertyDescriptor(window.Element.prototype, "textContent");
Object.defineProperty(window.Element.prototype, "textContent", {
  ...textContent,
  set(value) {
    textContent.set.call(this, value === null ? "" : String(value));
  },
});

// happy-dom walks past the document when the focused element sits in another card's shadow
// root and fails; a browser answers that no element of this shadow root has the focus.
const activeElement = Object.getOwnPropertyDescriptor(window.ShadowRoot.prototype, "activeElement");
Object.defineProperty(window.ShadowRoot.prototype, "activeElement", {
  ...activeElement,
  get() {
    try {
      return activeElement.get.call(this);
    } catch {
      return null;
    }
  },
});

export const DEVICE = "8d6c1f2e0a9b4c3d";

// Registry ids read like Home Assistant's: sensor.local_status becomes sensor.dartboard_local_status.
export const entityId = (key) => (key.includes(".dartboard_") ? key : key.replace(".", ".dartboard_"));

// A board that is connected, detects darts and waits for the next visit.
export const READY = {
  "binary_sensor.local_connected": "on",
  "binary_sensor.realtime_connected": "on",
  "binary_sensor.cameras_active": "on",
  "binary_sensor.calibrating": "off",
  "binary_sensor.camera_problem": "off",
  "binary_sensor.hand_detected": "off",
  "binary_sensor.takeout_partial": "off",
  "sensor.local_status": "Throw",
  "sensor.num_throws": "0",
  "switch.detection": "on",
  "button.start": "unknown",
  "button.stop": "unknown",
  "button.reset": "unknown",
  "button.calibrate": "unknown",
};

const toState = (id, value) =>
  value !== null && typeof value === "object"
    ? { entity_id: id, attributes: {}, ...value, state: String(value.state) }
    : { entity_id: id, state: String(value), attributes: {} };

// The entities of one camera, grouped by the camera attribute like the integration does.
export function camera(number, { problem = "off", fps = "30", calibrate = "unknown", image = "idle" } = {}) {
  const entities = {
    "binary_sensor.individual_camera_problem": problem,
    "sensor.camera_fps": fps,
    "button.calibrate_camera": calibrate,
    "camera.board_camera": image,
  };
  return Object.entries(entities)
    .filter(([, state]) => state !== null)
    .map(([key, state]) => ({
      key,
      id: `${key.split(".")[0]}.dartboard_camera_${number}_${key.split(".")[1]}`,
      state: { state, attributes: { camera: number } },
    }));
}

// hass as a card sees it: registry entries of one board, their states and service calls.
export function makeHass({ language = "en", states = {}, cameras = [], device = {}, callWS, connection } = {}) {
  const entities = {};
  const all = {};
  const add = (key, id, value) => {
    entities[id] = { entity_id: id, platform: "autodarts", device_id: DEVICE, translation_key: key.split(".")[1] };
    if (value !== undefined) all[id] = toState(id, value);
  };
  for (const [key, value] of Object.entries(states)) add(key, entityId(key), value);
  for (const entry of cameras.flat()) add(entry.key, entry.id, entry.state);
  const calls = [];
  return {
    language,
    locale: { language },
    devices: { [DEVICE]: { id: DEVICE, name: "Dartboard", name_by_user: null, sw_version: "1.4.2", ...device } },
    entities,
    states: all,
    calls,
    callService(domain, service, data) {
      calls.push([domain, service, data]);
      return Promise.resolve();
    },
    ...(callWS ? { callWS } : {}),
    ...(connection ? { connection } : {}),
  };
}

// The next hass object after state changes; unchanged states keep their identity.
export function update(hass, states) {
  const changed = Object.fromEntries(
    Object.entries(states).map(([key, value]) => [entityId(key), toState(entityId(key), value)])
  );
  return { ...hass, states: { ...hass.states, ...changed } };
}

export const withLanguage = (hass, language) => ({ ...hass, language, locale: { ...hass.locale, language } });

// Home Assistant's app element lets the module register its cards.
export async function loadCards() {
  if (!customElements.get("home-assistant")) customElements.define("home-assistant", class extends HTMLElement {});
  const module = await import("../../custom_components/autodarts/frontend/autodarts-card.js");
  await customElements.whenDefined("autodarts-card");
  return module;
}

// The cards leave the page after the tests of a file, which ends their timers.
after(() => document.body.replaceChildren());

export function mount(type, hass, config = {}) {
  const card = document.createElement(type);
  card.setConfig({ type: `custom:${type}`, ...config });
  if (hass) card.hass = hass;
  document.body.append(card);
  return card;
}

export const $ = (card, selector) => card.shadowRoot.querySelector(selector);
export const $$ = (card, selector) => [...card.shadowRoot.querySelectorAll(selector)];
export const text = (card, selector) => $(card, selector)?.textContent.replace(/\s+/g, " ").trim();

// Entity ids of the more-info dialogs a card asks for.
export function moreInfo(card) {
  const opened = [];
  card.addEventListener("hass-more-info", (event) => opened.push(event.detail.entityId));
  return opened;
}

// Lets pending promises of the card settle.
export const settle = () => new Promise((resolve) => setImmediate(resolve));
