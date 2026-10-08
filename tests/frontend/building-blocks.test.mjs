// The building blocks every card is made of, and the rules they keep on every card:
// what a tap edits shows a pencil, what a tap opens shows an arrow, nothing static looks
// like a control, and the second tap that confirms is red wherever it is asked for.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, READY, camera, loadCards, makeHass, mount, text, update } from "./dom.mjs";

const { lobbyHints } = await loadCards();

const ENTRY = "01JENTRY";
const dart = (number, multiplier, extra = {}) => ({ number, multiplier, segment: "x", ...extra });
const visit = (...throws) => ({
  "sensor.local_visit_score": {
    state: String(throws.reduce((sum, item) => sum + item.number * item.multiplier, 0)),
    attributes: { throws, recent_visits: [] },
  },
});
const THROWS = [dart(20, 3, { dart: 1 }), dart(19, 1, { dart: 2, bot: true })];
const card = (type, states = {}, config = {}, options = {}) =>
  mount(
    type,
    makeHass({ states: { ...READY, ...states }, device: { primary_config_entry: ENTRY }, ...options }),
    config
  );
const cues = (root, selector) => $$(root, selector).map((element) => [...element.querySelectorAll(".cue")].map((cue) => cue.getAttribute("class")));
const CARDS = [
  "autodarts-card",
  "autodarts-training-card",
  "autodarts-status-card",
  "autodarts-scoreboard-card",
  "autodarts-players-card",
  "autodarts-leaderboard-card",
  "autodarts-doubles-card",
];

test("every card is built of the same blocks, so a change to a block reaches every card", () => {
  for (const type of CARDS) {
    const style = $(card(type), "style").textContent;
    for (const block of [
      /\.pill \{\s*display: inline-grid;[^}]*min-height: 28px;[^}]*\}/,
      /\.hint-bubble \{\s*position: absolute;[^}]*pointer-events: none;/,
      /\.cue \{\s*position: absolute;/,
      /\.cue\.inline \{ position: static;/,
      /\.tappable \{ position: relative; border: 1px solid/,
      /\.bed \{ border-radius: 8px;/,
      /\.segmented \{/,
      /\.link \{/,
      /button:not\(:disabled\):active \{\s*background-image: linear-gradient\(var\(--ad-press\), var\(--ad-press\)\); transform: scale\(\.97\);\s*\}/,
      /--ad-fast: 150ms;/,
      /button, \.tappable \{\s*transition: background-color var\(--ad-fast\) var\(--ad-ease\)/,
      /@starting-style \{ \.appear \{ opacity: 0; transform: translateY\(6px\); \} \}/,
      /@media \(prefers-reduced-motion: reduce\) \{\s*\*, \*::before, \*::after \{\s*transition-duration: 0s !important;/,
      /:host button\.confirm \{ color: #fff;/,
      /button:disabled \{ opacity: \.45; cursor: default; \}/,
    ]) {
      assert.match(style, block, `${type} lacks ${block}`);
    }
    // Status is a dot and words, never the fill of a button.
    assert.doesNotMatch(style.match(/\.pill \{[^}]*\}/)[0], /background/, type);
    // Each block exists once, where the building blocks are.
    assert.equal(style.match(/\n {2}\.cue \{/g).length, 1, type);
  }
});

test("what a tap edits shows a pencil: the darts of the visit on the live card and the scoreboard", () => {
  for (const [type, selector] of [
    ["autodarts-card", ".slot"],
    ["autodarts-scoreboard-card", ".visit .dart"],
  ]) {
    const root = card(type, visit(...THROWS));
    const tiles = $$(root, selector);
    // The dart that corrects is a framed button with a pencil; the bot's dart and the
    // empty slot are tinted areas without a cue.
    assert.deepEqual(
      tiles.map((tile) => [tile.localName, tile.classList.contains("tappable"), tile.querySelectorAll(".cue").length]),
      [
        ["button", true, 1],
        ["div", false, 0],
        ["div", false, 0],
      ],
      type
    );
    assert.equal(tiles[0].querySelector(".cue").getAttribute("class"), "cue edit");
    // Being edited, the pencil takes the accent.
    tiles[0].click();
    assert.equal($(root, "[data-dart='1']").classList.contains("picked"), true);
    assert.match($(root, "style").textContent, /\.picked \.cue \{ color: var\(--ad-accent-text\); \}/);
  }
});

test("what a tap opens shows an arrow, and static tiles show none", () => {
  // Training: the tiles are static, the link below them opens the details.
  const training = card("autodarts-training-card");
  assert.deepEqual(cues(training, ".tile").flat(), []);
  assert.deepEqual(cues(training, ".link.details"), [["cue details inline"]]);
  // Status: the measured values, the system line, a camera and an update open theirs.
  const status = card(
    "autodarts-status-card",
    {
      "sensor.cpu_usage": "12.4",
      "sensor.host_os": "Ubuntu 22.04.4 LTS",
      "update.board_software": { state: "on", attributes: { latest_version: "1.5.0" } },
    },
    {},
    { cameras: [camera(1)] }
  );
  assert.deepEqual(cues(status, ".metric"), [["cue details inline"]]);
  assert.deepEqual(cues(status, ".system-info"), [["cue details inline"]]);
  assert.deepEqual(cues(status, ".camera-name"), [["cue details inline"]]);
  assert.deepEqual(cues(status, ".update-badge"), [["cue details inline"]]);
  // Up to date, the badge opens nothing and shows no arrow.
  const current = card("autodarts-status-card", { "update.board_software": { state: "off", attributes: {} } });
  assert.deepEqual(cues(current, ".update-badge"), [[]]);
  assert.equal($(current, ".update-badge").disabled, true);
  // The scoreboard's players and the visit's total are static.
  const scoreboard = card("autodarts-scoreboard-card", {
    ...visit(dart(20, 3, { dart: 1 })),
    "sensor.practice_remaining": {
      state: "441",
      attributes: { game: 501, player: 1, scores: [{ player: 1, name: "Alex", remaining: 441 }] },
    },
  });
  assert.deepEqual(cues(scoreboard, ".player").flat(), []);
  assert.deepEqual(cues(scoreboard, ".sum").flat(), []);
});

test("the status keeps the width of its longest words during a game, so nothing beside it moves", () => {
  for (const type of ["autodarts-card", "autodarts-status-card", "autodarts-scoreboard-card"]) {
    const pill = $(card(type), ".pill");
    assert.deepEqual([pill.textContent, pill.dataset.widest], ["Ready – throw!", "Remove your darts"], type);
    assert.equal(pill.firstElementChild.localName, "span", type);
  }
  const german = card("autodarts-scoreboard-card", {}, {}, { language: "de" });
  assert.deepEqual([text(german, ".pill"), $(german, ".pill").dataset.widest], ["Bereit – wirf!", "Darts werden entnommen"]);
  // On a card narrower than those words, they wrap instead of running over the edge.
  const pill = $(german, "style").textContent.match(/\.pill \{[^}]*\}/)[0];
  assert.match(pill, /flex-shrink: 0; max-width: 100%;/);
});

test("what a tooltip tells shows on a tap with a finger too, in a bubble over the card", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const tap = (element, pointerType = "touch") => {
    element.dispatchEvent(new window.PointerEvent("pointerdown", { bubbles: true, composed: true, pointerType }));
    element.click();
  };
  const live = card("autodarts-card", {
    "sensor.local_visit_score": {
      state: "0",
      attributes: { throws: [], recent_visits: [{ score: 85, segments: ["T20", "S20", "S5"] }] },
    },
  });
  const bubble = () => $(live, ".root > .hint-bubble");
  const shown = () => (bubble() && !bubble().hidden ? [bubble().textContent, bubble().getAttribute("role")] : null);
  // A mouse keeps the browser's own tooltip.
  tap($(live, ".recent-visit"), "mouse");
  assert.equal(shown(), null);
  tap($(live, ".recent-visit"));
  assert.deepEqual(shown(), ["T20 · S20 · S5 = 85", "status"]);
  // Without room above what was tapped, the bubble sits below it, inside the card's sides.
  assert.deepEqual([bubble().style.left, bubble().style.top], ["8px", "8px"]);
  const rect = (left, top, width, height) => () => ({ left, top, width, height, right: left + width, bottom: top + height });
  $(live, ".root").getBoundingClientRect = rect(0, 0, 400, 300);
  $(live, ".recent-visit").getBoundingClientRect = rect(180, 120, 40, 20);
  Object.defineProperties(bubble(), { offsetWidth: { value: 120 }, offsetHeight: { value: 30 } });
  tap($(live, ".recent-visit"));
  assert.deepEqual([bubble().style.left, bubble().style.top], ["140px", "82px"]);
  // Another tap elsewhere, Escape or a few seconds close it; a pen shows it as a finger does.
  tap($(live, ".score"));
  assert.equal(shown(), null);
  tap($(live, ".recent-visit"), "pen");
  $(live, ".recent-visit").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true, composed: true }));
  assert.equal(shown(), null);
  tap($(live, ".recent-visit"));
  $(live, ".recent-visit").dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true, composed: true }));
  t.mock.timers.tick(4999);
  assert.deepEqual(shown(), ["T20 · S20 · S5 = 85", "status"]);
  t.mock.timers.tick(1);
  assert.equal(shown(), null);
  // A control with a title does what it does; the bubble stays away.
  const scoreboard = card("autodarts-scoreboard-card", {}, { caller: true });
  tap($(scoreboard, ".caller-toggle"));
  assert.equal($(scoreboard, ".hint-bubble"), null);
  // A click without a pointer before it, as from a keyboard, shows none either.
  const board = card("autodarts-card", {
    "sensor.local_visit_score": { state: "0", attributes: { throws: [], recent_visits: [{ score: 60, segments: ["T20"] }] } },
  });
  $(board, ".recent-visit").click();
  assert.equal($(board, ".hint-bubble"), null);
  // The card takes the bubble with it.
  tap($(live, ".recent-visit"));
  live.remove();
  assert.equal(shown(), null);
});

test("the second tap that confirms is red on every card", () => {
  // The live card's controls, the scoreboard's keypad, its lone undo and the new game screen.
  const live = card("autodarts-card", { "button.reset_detection": "unknown" });
  $(live, '[data-action="reset"]').click();
  assert.equal($(live, '[data-action="reset"]').classList.contains("confirm"), true);
  const keypad = card("autodarts-scoreboard-card", { "switch.practice_manual_entry": "on" }, { keypad: true });
  $(keypad, '[data-pad="next"]').click();
  assert.deepEqual([text(keypad, '[data-pad="next"]'), $(keypad, '[data-pad="next"]').className], ["Confirm?", "secondary confirm"]);
  const undo = card("autodarts-scoreboard-card", {
    "sensor.practice_remaining": { state: "301", attributes: { game: 301, player: 1, scores: [{ player: 1, remaining: 301 }], undo: true } },
  });
  $(undo, '.visit [data-pad="undo"]').click();
  assert.equal($(undo, '.visit [data-pad="undo"]').className, "sum last tappable confirm");
  const running = card("autodarts-scoreboard-card", {
    "select.practice_game": { state: "501", attributes: { options: ["off", "501"] } },
  });
  $(running, ".lobby-toggle").click();
  $(running, '[data-lobby="end"]').click();
  assert.equal($(running, '[data-lobby="end"]').className, "secondary confirm");
});

test("the pad says why it waits while the bot throws", () => {
  const root = card("autodarts-scoreboard-card", {
    ...visit(dart(20, 3, { dart: 1 })),
    "sensor.practice_remaining": {
      state: "301",
      attributes: {
        game: 301,
        player: 2,
        scores: [
          { player: 1, name: "Alex", remaining: 241 },
          { player: 2, name: null, remaining: 301, bot: true },
        ],
      },
    },
  });
  $(root, "[data-dart='1']").click();
  assert.equal(text(root, ".pad-wait"), "The bot is throwing; the pad waits for your turn.");
  assert.equal($(root, '[data-pad="multiplier"]').disabled, true);
});

test("the new game screen says why a player sits out and why suggestions fade", () => {
  const t = (key) => ({ lobby_resting: "{game} is for {count}: the others sit out.", lobby_full: "{count} players at most." })[key] ?? key;
  const ui = { t, name: (game) => `Game ${game}`, suggestions: ["Kim"] };
  // With the bot, a match seats three; a fourth player sits out.
  assert.deepEqual(lobbyHints({ game: "501", players: ["A", "B", "C", "D"], bot: 60 }, ui), ["Game 501 is for 3: the others sit out."]);
  // Four players fill a match: the suggestions fade, and the screen says why.
  assert.deepEqual(lobbyHints({ game: "501", players: ["A", "B", "C", "D"] }, ui), ["4 players at most."]);
  assert.deepEqual(lobbyHints({ game: "501", players: ["A", "B", "C", "D"] }, { ...ui, suggestions: [] }), []);
  // A training game already says who plays.
  assert.deepEqual(lobbyHints({ game: "around_the_clock", players: ["A", "B"] }, ui), ["lobby_one_player"]);
});

test("the pad chooses its keys or its board with the segmented control of every card", () => {
  const root = card("autodarts-scoreboard-card", visit(dart(20, 3, { dart: 1 })));
  $(root, "[data-dart='1']").click();
  const view = $(root, ".pad .segmented.view");
  assert.deepEqual(
    [...view.querySelectorAll("button")].map((button) => [button.dataset.pad, button.textContent, button.getAttribute("aria-pressed")]),
    [
      ["keys", "Keys", "true"],
      ["board", "Board", "false"],
    ]
  );
  $(root, '[data-pad="board"]').click();
  $(root, '[data-pad="board"]').click();
  assert.equal($(root, '[data-pad="board"]').getAttribute("aria-pressed"), "true");
  $(root, '[data-pad="keys"]').click();
  assert.equal($(root, ".pad-board"), null);
  // Updates keep the choice.
  root.hass = update(makeHass({ states: { ...READY, ...visit(dart(20, 3, { dart: 1 })) } }), {});
  assert.equal($(root, '[data-pad="keys"]').getAttribute("aria-pressed"), "true");
});

test("a balanced grid keeps a tile from standing alone in the last row", () => {
  const style = $(card("autodarts-players-card"), "style").textContent;
  const rule = (query, body) => assert.ok(style.includes(`@container ${query} { ${body}`), `${query} ${body}`);
  // Where three player tiles fit, four stand two by two instead of three and one.
  rule("(min-width: 686px) and (max-width: 905.98px)", ".profiles.balanced.n4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }");
  // Where four fit, five stand three and two, the last tile filling its row.
  rule(
    "(min-width: 906px) and (max-width: 1125.98px)",
    ".profiles.balanced.n5 { grid-template-columns: repeat(3, minmax(0, 1fr)); } .profiles.balanced.n5 > :last-child { grid-column-end: -1; }"
  );
  // Seven in three columns: the last one stands in the middle.
  rule(
    "(min-width: 686px) and (max-width: 905.98px)",
    ".profiles.balanced.n7 { grid-template-columns: repeat(3, minmax(0, 1fr)); } .profiles.balanced.n7 > :nth-child(7) { grid-column-start: 2; }"
  );
  // A narrow card has one column, a wide one all tiles in a row.
  rule("(max-width: 465.98px)", ".profiles.balanced.n2 { grid-template-columns: repeat(1, minmax(0, 1fr)); }");
  rule("(min-width: 466px)", ".profiles.balanced.n2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }");
  // The grids of the cards say how many tiles they have.
  const players = card("autodarts-players-card", {
    "sensor.player_profiles": { state: "3", attributes: { players: [{ name: "A" }, { name: "B" }, { name: "C" }] } },
  });
  assert.equal($(players, ".profiles").className, "profiles balanced n3");
  const status = card("autodarts-status-card", {}, {}, { cameras: [camera(1), camera(2), camera(3)] });
  assert.equal($(status, ".camera-grid").className, "camera-grid balanced n3");
  assert.match($(status, ".info").className, /^info balanced n\d$/);
});

test("what appears as a whole fades in, and parts drawn with every tap do not", () => {
  // The pad below the darts and a result's banner fade in when they appear.
  for (const type of ["autodarts-card", "autodarts-scoreboard-card"]) {
    assert.equal($(card(type), ".pad-area").classList.contains("appear"), true, type);
  }
  assert.equal($(card("autodarts-scoreboard-card"), ".banner").classList.contains("appear"), true);
  // The keys of the pad are drawn with every tap: they do not fade in.
  const root = card("autodarts-scoreboard-card", visit(dart(20, 3, { dart: 1 })));
  $(root, "[data-dart='1']").click();
  assert.equal($$(root, ".pad .appear").length, 0);
  // The loupe grows out of the finger's spot.
  assert.match($(root, "style").textContent, /@starting-style \{ \.loupe \{ opacity: 0; transform: scale\(\.8\); \} \}/);
});

test("muted words on the tint of a badge take the muted text of the blocks, readable at WCAG AA", () => {
  // The secondary text of the theme alone falls below a contrast of 4.5 : 1 on the
  // gold tint in the dark theme; the muted text mixes in some of the primary text.
  const style = $(card("autodarts-players-card"), "style").textContent;
  assert.match(style, /\.badge-text > span \{ color: var\(--ad-muted-text\); \}/);
  assert.match(style, /--ad-muted-text: color-mix\(in srgb, var\(--secondary-text-color\) 80%, var\(--primary-text-color/);
});
