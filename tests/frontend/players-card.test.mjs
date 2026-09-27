// The players card in a browser DOM: profiles, head-to-head records, recent matches and escaping.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, loadCards, makeHass, mount, settle, text, update, window } from "./dom.mjs";

await loadCards();

const ALEX = {
  name: "Alex",
  legs_played: 20,
  legs_won: 12,
  matches_played: 5,
  matches_won: 3,
  average: 61.25,
  first_9_average: 70.1,
  checkout_rate: 31.3,
  mpr: 2.4,
  highest_visit: 140,
  highest_checkout: 121,
  best_mpr: 3.1,
  fewest_darts: { 501: 18, 301: 12 },
};
const LEA = { name: "Lea", legs_played: 8, legs_won: 3, matches_played: 2, matches_won: 1 };
const profiles = (...players) => ({
  "sensor.player_profiles": { state: String(players.length), attributes: { players } },
});
const lastMatch = (attributes) => ({
  "sensor.last_match": {
    state: "2026-09-26T20:00:00+00:00",
    attributes: { game: "killer", winner: null, matches: [], head_to_head: [], ...attributes },
  },
});
// Matches as the integration keeps them: the format, the winner, and every
// player's legs of the final set, sets and legs of the whole match.
const MATCHES = [
  {
    ended: "2026-09-26T20:00:00+00:00",
    game: "killer",
    legs_to_win: 1,
    sets_to_win: 1,
    winner: 2,
    players: [
      { name: "Alex", legs: 0, sets: 0, match_legs: 0, points: 0 },
      { name: null, legs: 1, sets: 1, match_legs: 1, points: 0 },
    ],
  },
  {
    ended: "later",
    game: 501,
    legs_to_win: 3,
    sets_to_win: 1,
    winner: 1,
    players: [
      { name: "Lea", legs: 3, sets: 1, match_legs: 3, average: 61.2 },
      { name: "Alex", legs: 2, sets: 0, match_legs: 2, average: 58.3 },
    ],
  },
  {
    ended: "2026-09-25T19:00:00+00:00",
    game: "cricket",
    legs_to_win: 2,
    sets_to_win: 2,
    winner: 2,
    players: [
      { name: "Alex", legs: 1, sets: 1, match_legs: 3, mpr: 2.1 },
      { name: "Sam", legs: 2, sets: 2, match_legs: 4, mpr: 2.4 },
    ],
  },
  // Up to version 1.5, the winner lost the legs of the deciding set again.
  {
    ended: "2026-09-24T19:00:00+00:00",
    game: 301,
    legs_to_win: 3,
    sets_to_win: 1,
    winner: 1,
    players: [
      { name: "Lea", legs: 0, sets: 1 },
      { name: "Alex", legs: 2, sets: 0 },
      { name: "Kim" },
    ],
  },
  { ended: "2026-09-23T19:00:00+00:00", game: null, winner: null, players: [] },
];
const setup = (states, config = {}, options = {}) => {
  const hass = makeHass({ states, ...options });
  return { hass, card: mount("autodarts-players-card", hass, config) };
};
const rows = (profile) =>
  [...profile.querySelectorAll("dt")].map((term) => [term.textContent, term.nextElementSibling.textContent]);

test("the players card shows every profile with its statistics and bests", () => {
  const { card } = setup({ ...profiles(ALEX, LEA), ...lastMatch({}) });
  assert.equal(text(card, ".title"), "Players");
  assert.equal(text(card, ".count"), "2");
  assert.equal($(card, ".empty").hidden, true);
  const [alex, lea] = $$(card, ".profile");
  assert.equal(alex.querySelector(".profile-name").textContent, "Alex");
  assert.equal(alex.querySelector(".muted").textContent, "Legs 12/20 · Matches 3/5");
  assert.deepEqual(rows(alex), [
    ["3-dart avg.", "61.3"],
    ["First 9", "70.1"],
    ["Checkout", "31.3%"],
    ["MPR", "2.40"],
    ["Best MPR", "3.10"],
    ["Highest visit", "140"],
    ["Highest checkout", "121"],
    ["Best 301", "12 darts"],
    ["Best 501", "18 darts"],
  ]);
  assert.deepEqual(rows(lea), [
    ["3-dart avg.", "–"],
    ["First 9", "–"],
    ["Checkout", "–"],
    ["Highest visit", "–"],
    ["Highest checkout", "–"],
  ]);
  assert.equal(card.getCardSize(), 6);
});

test("head-to-head records show the wins and the balance between two players", () => {
  const { hass, card } = setup({
    ...profiles(ALEX, LEA),
    ...lastMatch({ head_to_head: [{ players: ["Alex", "Lea"], wins: [3, 1] }] }),
  });
  assert.equal($(card, ".h2h-section").hidden, false);
  const versus = $(card, ".versus");
  assert.deepEqual(
    [...versus.querySelectorAll("span")].map((part) => part.textContent),
    ["Alex", "3 : 1", "Lea"]
  );
  assert.equal(versus.querySelector(".balance i").style.width, "75%");
  card.hass = update(hass, lastMatch({ head_to_head: [{ players: ["Alex", "Lea"], wins: [0, 0] }] }));
  assert.equal($(card, ".balance i").style.width, "50%");
  card.hass = update(hass, lastMatch({}));
  assert.equal($(card, ".h2h-section").hidden, true);
});

test("recent matches show when they ended, the game and the winner in bold", () => {
  const { card } = setup({ ...profiles(ALEX), ...lastMatch({ matches: MATCHES }) });
  assert.equal($(card, ".matches-section").hidden, false);
  const matches = $$(card, ".match");
  assert.deepEqual(
    matches.map((match) => [...match.children].map((part) => part.textContent.replace(/\s/g, " "))),
    [
      ["09/26, 8:00 PM", "Killer", "Alex 0 · Player 2 1"],
      // A first to three legs ends 3 : 2, a match of sets tells the sets.
      ["", "501", "Lea 3 · Alex 2"],
      ["09/25, 7:00 PM", "Cricket · Sets", "Alex 1 · Sam 2"],
      ["09/24, 7:00 PM", "301", "Lea 3 · Alex 2 · Kim 0"],
      ["09/23, 7:00 PM", "", ""],
    ]
  );
  assert.deepEqual(
    matches.map((match) => match.querySelector("b")?.textContent),
    ["Player 2 1", "Lea 3", "Sam 2", "Lea 3", undefined]
  );
});

test("without profiles the card explains how players get one", () => {
  const { hass, card } = setup({ ...profiles(), ...lastMatch({}) });
  assert.equal($(card, ".empty").hidden, false);
  assert.equal(
    text(card, ".empty"),
    "No player profiles yet. Give the players of a practice game a name, and every leg counts for them."
  );
  assert.equal(text(card, ".count"), "");
  assert.equal(text(card, ".profiles"), "");
  assert.equal($(card, ".matches-section").hidden, true);
  card.hass = update(hass, profiles(LEA));
  assert.equal($(card, ".empty").hidden, true);
  assert.equal(text(card, ".count"), "1");
});

test("head-to-head records and matches can be hidden and the title changed", () => {
  const states = {
    ...profiles(ALEX, LEA),
    ...lastMatch({ matches: MATCHES, head_to_head: [{ players: ["Alex", "Lea"], wins: [3, 1] }] }),
  };
  const { card } = setup(states, { show_head_to_head: false, show_matches: false, title: "League" });
  assert.equal($(card, ".h2h-section"), null);
  assert.equal($(card, ".matches-section"), null);
  assert.equal(text(card, ".title"), "League");
  assert.equal($$(card, ".profile").length, 2);
});

test("player names are shown as text, never as markup", () => {
  const evil = '<img src=x onerror="alert(1)">';
  const { card } = setup({
    ...profiles({ ...ALEX, name: evil }),
    ...lastMatch({
      head_to_head: [{ players: [evil, "Lea"], wins: [1, 0] }],
      matches: [{ ended: "2026-09-26T20:00:00+00:00", game: evil, winner: 1, players: [{ name: evil, legs: 1 }] }],
    }),
  });
  assert.equal($$(card, "img").length, 0);
  assert.equal(text(card, ".profile-name"), evil);
  assert.equal(text(card, ".versus .who"), evil);
  assert.equal(text(card, ".match .game"), evil);
  assert.equal(text(card, ".match b"), `${evil} 1`);
  assert.ok(!$(card, ".profiles").innerHTML.includes("<img"));
});

test("the players card speaks German, also without a locale", () => {
  const hass = makeHass({ states: { ...profiles(ALEX), ...lastMatch({ matches: MATCHES.slice(0, 1) }) } });
  const card = mount("autodarts-players-card", { ...hass, locale: undefined, language: "de" });
  assert.equal(text(card, ".title"), "Spieler");
  assert.equal($(card, ".profile .muted").textContent, "Legs 12/20 · Matches 3/5");
  assert.deepEqual(rows($(card, ".profile")).slice(0, 3), [
    ["3-Dart-Average", "61,3"],
    ["First 9", "70,1"],
    ["Checkout", "31,3 %"],
  ]);
  assert.deepEqual(rows($(card, ".profile")).slice(3, 5), [
    ["MPR", "2,40"],
    ["Beste MPR", "3,10"],
  ]);
  assert.deepEqual(rows($(card, ".profile")).slice(-2), [
    ["Bestes 301-Leg", "12 Darts"],
    ["Bestes 501-Leg", "18 Darts"],
  ]);
  assert.equal(text(card, ".match .muted"), "26.09., 20:00");
});

// Export ---------------------------------------------------------------------

const NAME = "autodarts-all-20260927-201500-0123456789abcdef.zip";
const DOWNLOAD = `/api/autodarts/export/${NAME}`;

// Home Assistant's answers: the response of the action, then a signed path.
function connection(response) {
  const requests = [];
  const callWS = (message) => {
    requests.push(message);
    if (message.type === "auth/sign_path") return Promise.resolve({ path: `${message.path}?authSig=signed` });
    return Promise.resolve({ context: {}, response });
  };
  return { requests, callWS };
}

// Clicks on download links, instead of navigating the test browser.
function downloads() {
  const clicked = [];
  const original = window.HTMLAnchorElement.prototype.click;
  window.HTMLAnchorElement.prototype.click = function click() {
    clicked.push({ href: this.getAttribute("href"), download: this.download, connected: this.isConnected });
  };
  return { clicked, restore: () => (window.HTMLAnchorElement.prototype.click = original) };
}

function notices(card) {
  const messages = [];
  card.addEventListener("hass-notification", (event) => messages.push(event.detail.message));
  return messages;
}

test("the export button is off by default", () => {
  const { card } = setup({ ...profiles(ALEX), ...lastMatch({}) });
  assert.equal($(card, ".export"), null);
});

test("the export button writes every table and downloads the file with the user's login", async () => {
  const { requests, callWS } = connection({
    path: `/config/www/autodarts/${NAME}`,
    url: `/local/autodarts/${NAME}`,
    download: DOWNLOAD,
  });
  const { card } = setup(
    { ...profiles(ALEX), ...lastMatch({}) },
    { export: true },
    { callWS, device: { primary_config_entry: "entry-1", config_entries: ["other", "entry-1"] } }
  );
  const { clicked, restore } = downloads();
  try {
    const button = $(card, ".export");
    assert.equal(button.textContent, "Export");
    button.click();
    assert.equal(button.disabled, true);
    assert.equal(button.textContent, "Exporting …");
    // A second tap while the file is written does nothing.
    button.click();
    await settle();
    assert.deepEqual(requests, [
      {
        type: "call_service",
        domain: "autodarts",
        service: "export",
        service_data: { format: "csv", what: "all", config_entry_id: "entry-1" },
        return_response: true,
      },
      { type: "auth/sign_path", path: DOWNLOAD, expires: 60 },
    ]);
    assert.deepEqual(clicked, [{ href: `${DOWNLOAD}?authSig=signed`, download: NAME, connected: true }]);
    assert.equal($(card, "a"), null);
    assert.equal(button.disabled, false);
    assert.equal(button.textContent, "Export");
  } finally {
    restore();
  }
});

test("the export can be JSON and picks the board's entry", async () => {
  const { requests, callWS } = connection({ download: DOWNLOAD.replace(".zip", ".json") });
  const { clicked, restore } = downloads();
  try {
    for (const [config, device] of [
      [{ export: true, export_format: "json" }, { config_entries: ["entry-2"] }],
      [{ export: true, export_format: "xml" }, {}],
    ]) {
      const { card } = setup({ ...profiles(ALEX), ...lastMatch({}) }, config, { callWS, device });
      $(card, ".export").click();
      await settle();
    }
    assert.deepEqual(
      requests.filter((request) => request.service_data).map((request) => request.service_data),
      [
        { format: "json", what: "all", config_entry_id: "entry-2" },
        { format: "csv", what: "all" },
      ]
    );
    assert.deepEqual(
      clicked.map((link) => link.download),
      [NAME.replace(".zip", ".json"), NAME.replace(".zip", ".json")]
    );
  } finally {
    restore();
  }
});

test("a failed export shows why and leaves the button ready", async () => {
  const answers = [
    () => Promise.reject(new Error("The export could not be written: disk full")),
    () => Promise.resolve({ response: { url: null, path: "/config/exports/x.csv" } }),
    () => Promise.reject({}),
    // Only exports of the integration are downloaded.
    () => Promise.resolve({ response: { download: "https://example.com/x.zip" } }),
  ];
  const callWS = () => answers.shift()();
  const { card } = setup({ ...profiles(ALEX), ...lastMatch({}) }, { export: true }, { callWS });
  const messages = notices(card);
  const { clicked, restore } = downloads();
  try {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      $(card, ".export").click();
      await settle();
    }
    assert.deepEqual(messages, [
      "Export failed: The export could not be written: disk full",
      "Export failed: /config/exports/x.csv",
      "Export failed",
      "Export failed",
    ]);
    assert.deepEqual(clicked, []);
    assert.equal($(card, ".export").disabled, false);
  } finally {
    restore();
  }
});


test("the export needs Home Assistant's connection and no preview", async () => {
  const { card } = setup({ ...profiles(ALEX), ...lastMatch({}) }, { export: true });
  const messages = notices(card);
  card.preview = true;
  $(card, ".export").click();
  await settle();
  assert.deepEqual(messages, []);
  card.preview = false;
  $(card, ".export").click();
  await settle();
  assert.equal(messages.length, 1);
  assert.match(messages[0], /^Export failed: /);
});

test("the export button speaks German", () => {
  const hass = makeHass({ language: "de", states: { ...profiles(ALEX), ...lastMatch({}) } });
  const card = mount("autodarts-players-card", hass, { export: true });
  assert.equal(text(card, ".export"), "Exportieren");
});
