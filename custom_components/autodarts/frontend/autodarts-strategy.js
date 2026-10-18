/*
 * The dashboard strategy "custom:autodarts", registered at once.
 *
 * Home Assistant waits five seconds for the element of a dashboard strategy and then
 * shows "Timeout waiting for strategy element" until the page loads again. Loading
 * autodarts-card.js with all its cards can take longer than that, on a phone with an
 * empty cache or a slow connection. This small module, which Home Assistant loads
 * beside it, defines the element as soon as Home Assistant's app is there, and hands
 * every call on to the strategy of autodarts-card.js once that has loaded: building
 * the dashboard may take as long as it needs.
 */

const STRATEGY_ELEMENT = "ll-strategy-dashboard-autodarts";
// autodarts-card.js beside a module, with the same version in its address, so that the
// import finds the module Home Assistant is loading already.
const cardModule = (url) => new URL(`autodarts-card.js${new URL(url).search}`, url).href;
const CARD_MODULE = cardModule(import.meta.url);

let loading = null;

// The strategy of autodarts-card.js; a failed load is tried again by the next call.
function cardStrategy(load = () => import(CARD_MODULE)) {
  loading ??= load().then(
    (card) => card.createElements(window.HTMLElement)[STRATEGY_ELEMENT],
    (error) => {
      loading = null;
      throw error;
    }
  );
  return loading;
}

function strategyElement(Base) {
  return class AutodartsDashboardStrategy extends Base {
    static async generate(config, hass) {
      return (await cardStrategy()).generate(config, hass);
    }

    static async getConfigElement() {
      return (await cardStrategy()).getConfigElement();
    }
  };
}

// Home Assistant swaps in a scoped custom element registry once its app element is
// defined; an element defined before stays invisible to dashboards (see frontendReady
// in autodarts-card.js, which also defines the element when this module is missing).
function registerStrategy() {
  const registry = window.customElements;
  if (!registry.get(STRATEGY_ELEMENT)) registry.define(STRATEGY_ELEMENT, strategyElement(window.HTMLElement));
}

// Home Assistant's app element, or hc-main of the receiver of Home Assistant Cast, which
// shows dashboards on a TV and loads this module as a dashboard resource once it runs.
const appReady = (registry) => Promise.race(["home-assistant", "hc-main"].map((name) => registry.whenDefined(name)));

if (globalThis.window?.customElements) appReady(window.customElements).then(registerStrategy);

export { CARD_MODULE, appReady, cardModule, cardStrategy, registerStrategy, strategyElement };
