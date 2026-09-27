// The players card: profiles, head-to-head records and recent matches.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dashboardStrategy,
  playersHtml,
  playersView,
} from "../../custom_components/autodarts/frontend/autodarts-card.js";

const profiles = {
  state: "2",
  attributes: {
    players: [
      {
        name: "Alex",
        legs_played: 20,
        legs_won: 12,
        matches_played: 5,
        matches_won: 3,
        average: 61.25,
        first_9_average: 70.1,
        checkout_rate: 31.3,
        mpr: 2.4,
        best_mpr: 3.1,
        highest_visit: 140,
        highest_checkout: 121,
        fewest_darts: { 501: 18, 301: 12, x: 3 },
      },
      { name: "Lea", legs_played: 8, legs_won: 3, average: null, fewest_darts: null },
      { name: "", legs_played: 1 },
      null,
    ],
  },
};
const lastMatch = {
  state: "2026-09-26T20:00:00+00:00",
  attributes: {
    head_to_head: [{ players: ["Alex", "Lea"], wins: [3, 1] }, { players: ["A"], wins: [1] }],
    matches: [
      {
        ended: "2026-09-26T20:00:00+00:00",
        game: "killer",
        winner: 2,
        players: [{ name: "Alex", legs: 0, sets: 0 }, { name: null, legs: 1, sets: 0 }],
      },
      { ended: 5, players: [] },
    ],
  },
};
const ui = {
  t: (key) => ({ best_leg: "Best {game}", unit_darts: "{value} darts" })[key] ?? key,
  format: (value, digits) => value.toFixed(digits),
  percent: (value, digits) => (value === null ? "–" : `${value.toFixed(digits)}%`),
  date: () => "26.09., 22:00",
};

test("the players view keeps valid profiles, records and matches", () => {
  const view = playersView(profiles, lastMatch);
  assert.deepEqual(
    view.players.map((player) => player.name),
    ["Alex", "Lea"]
  );
  assert.deepEqual(view.players[0].fewestDarts, [
    { game: 301, darts: 12 },
    { game: 501, darts: 18 },
  ]);
  assert.equal(view.players[1].average, null);
  assert.equal(view.headToHead.length, 1);
  assert.equal(view.matches.length, 1);
  assert.deepEqual(playersView(undefined, undefined), { players: [], headToHead: [], matches: [] });
});

test("a profile without statistics counts no legs and no matches yet", () => {
  const [player] = playersView({ attributes: { players: [{ name: "Kim" }] } }, undefined).players;
  assert.deepEqual(
    [player.legsPlayed, player.legsWon, player.matchesPlayed, player.matchesWon, player.average, player.fewestDarts],
    [0, 0, 0, 0, null, []]
  );
});

test("the players card shows statistics, the balance and who won", () => {
  const html = playersHtml(playersView(profiles, lastMatch), ui);
  assert.match(html.players, /<div class="profile-name"><span>Alex<\/span><\/div><div class="muted">profile_legs 12\/20 · profile_matches 3\/5<\/div>/);
  assert.match(html.players, /<dt>average<\/dt><dd>61\.3<\/dd>/);
  assert.match(html.players, /<dt>checkout_short<\/dt><dd>31\.3%<\/dd>/);
  assert.match(html.players, /<dt>cricket_mpr<\/dt><dd>2\.40<\/dd><dt>best_mpr<\/dt><dd>3\.10<\/dd>/);
  assert.match(html.players, /<dt>Best 301<\/dt><dd>12 darts<\/dd><dt>Best 501<\/dt>/);
  // Lea never played Cricket: no MPR rows, and missing numbers read as dashes.
  assert.doesNotMatch(html.players.split("Lea")[1], /mpr/);
  assert.match(html.players.split("Lea")[1], /<dt>checkout_short<\/dt><dd>–<\/dd>/);
  assert.match(html.players.split("Lea")[1], /<dt>average<\/dt><dd>–<\/dd>/);
  assert.match(html.headToHead, /<span class="tally">3 : 1<\/span>.*<i style="width:75%">/);
  assert.match(html.matches, /<span class="game">party_killer<\/span><span><span>Alex 0<\/span> · <b>score_player 2 1<\/b><\/span>/);
});

test("the dashboard gets a players view once profiles exist", () => {
  const entity = (entity_id, translation_key) => ({ entity_id, translation_key, device_id: "dev1", platform: "autodarts" });
  const hass = (items) => ({
    locale: { language: "en" },
    entities: Object.fromEntries(items.map((item) => [item.entity_id, item])),
    devices: { dev1: { id: "dev1" } },
    states: {},
  });
  const without = dashboardStrategy(hass([entity("sensor.b_darts", "training_darts")]));
  assert.equal(without.views.some((view) => view.path === "players"), false);
  const withProfiles = dashboardStrategy(
    hass([entity("sensor.b_darts", "training_darts"), entity("sensor.b_profiles", "player_profiles")])
  );
  const players = withProfiles.views.find((view) => view.path === "players");
  assert.equal(players.title, "Players");
  assert.equal(players.sections[0].cards[0].type, "custom:autodarts-players-card");
});
