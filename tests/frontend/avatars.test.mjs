// Players linked to persons of Home Assistant: their pictures on the scoreboard and the players card.
import assert from "node:assert/strict";
import { test } from "node:test";

import { $, $$, READY, loadCards, makeHass, mount, text, update } from "./dom.mjs";

await loadCards();

const PICTURE = "/api/image/serve/alex/512x512";
const profiles = (players) => ({ "sensor.player_profiles": { state: String(players.length), attributes: { players } } });
const LINKED = profiles([
  { name: "Alex", person: "person.alex", legs_played: 2, legs_won: 1 },
  { name: "Sam", person: "person.sam", legs_played: 2, legs_won: 1 },
  { name: "Kim", person: null, legs_played: 0, legs_won: 0 },
]);
const PEOPLE = {
  "person.alex": { state: "home", attributes: { entity_picture: PICTURE, latitude: 50.1 } },
  // A picture from somewhere else than Home Assistant or the web never shows.
  "person.sam": { state: "not_home", attributes: { entity_picture: "javascript:alert(1)" } },
};
const X01 = {
  "sensor.local_visit_score": { state: "0", attributes: { throws: [] } },
  "sensor.practice_remaining": {
    state: "501",
    attributes: {
      game: 501,
      player: 1,
      name: "alex",
      scores: [
        { player: 1, name: "alex", remaining: 501, legs: 0, sets: 0 },
        { player: 2, name: "Sam", remaining: 501, legs: 0, sets: 0 },
      ],
    },
  },
};

function withPeople(hass, people = PEOPLE) {
  return { ...hass, states: { ...hass.states, ...Object.fromEntries(Object.entries(people).map(([id, state]) => [id, { entity_id: id, ...state }])) } };
}

const avatars = (card, selector) => $$(card, `${selector} .avatar`).map((image) => image.getAttribute("src"));

test("the scoreboard shows the picture of a linked person on the player's tile", () => {
  const hass = withPeople(makeHass({ states: { ...READY, ...X01, ...LINKED } }));
  const card = mount("autodarts-scoreboard-card", hass);
  // Names match regardless of upper and lower case.
  assert.deepEqual(avatars(card, ".player .name"), [PICTURE]);
  assert.equal(text(card, ".player .name"), "alex");
  assert.equal($(card, ".player .avatar").getAttribute("alt"), "");

  // A new picture shows at once; the person moving around does not redraw the card.
  const html = $(card, ".main").innerHTML;
  const moved = withPeople(hass, { ...PEOPLE, "person.alex": { ...PEOPLE["person.alex"], attributes: { entity_picture: PICTURE, latitude: 50.2 } } });
  card.hass = moved;
  assert.equal($(card, ".main").innerHTML, html);
  card.hass = withPeople(moved, { ...PEOPLE, "person.alex": { state: "home", attributes: { entity_picture: "/new.jpg" } } });
  assert.deepEqual(avatars(card, ".player .name"), ["/new.jpg"]);
  // A link to a person Home Assistant does not know shows no picture.
  card.hass = update(hass, profiles([{ name: "Alex", person: "person.gone" }]));
  assert.deepEqual(avatars(card, ".player .name"), []);
});

test("the Cricket chalkboard and the bull-off show the pictures, the live card does not", () => {
  const cricket = {
    "sensor.practice_remaining": {
      state: "unknown",
      attributes: {
        game: "cricket",
        target: "T20",
        player: 1,
        scores: [
          { player: 1, name: "Alex", marks: [0, 0, 0, 0, 0, 0, 0], points: 0 },
          { player: 2, name: "Kim", marks: [0, 0, 0, 0, 0, 0, 0], points: 0 },
        ],
      },
    },
  };
  const hass = withPeople(makeHass({ states: { ...READY, ...cricket, ...LINKED } }));
  const card = mount("autodarts-scoreboard-card", hass);
  assert.deepEqual(avatars(card, ".cricket thead"), [PICTURE]);
  card.hass = update(card._hass, {
    "sensor.practice_remaining": {
      state: "501",
      attributes: { game: 501, bull_off: { player: 1, throws: [{ player: 1, name: "Alex", distance: 4 }] } },
    },
  });
  assert.deepEqual(avatars(card, ".player .name"), [PICTURE]);

  const live = mount("autodarts-card", hass);
  assert.equal($$(live, ".avatar").length, 0);
});

test("the players card shows the picture next to the name", () => {
  const hass = withPeople(makeHass({ states: { ...READY, ...LINKED } }));
  const card = mount("autodarts-players-card", hass);
  assert.deepEqual(
    $$(card, ".profile-name").map((name) => [name.querySelector(".avatar")?.getAttribute("src") ?? null, name.textContent]),
    [
      [PICTURE, "Alex"],
      [null, "Sam"],
      [null, "Kim"],
    ]
  );
  // Only the cards with pictures follow the persons.
  const doubles = mount("autodarts-doubles-card", hass);
  assert.equal(doubles._watched().some((id) => String(id).startsWith("person.")), false);
  assert.deepEqual(card._watched().filter((id) => String(id).startsWith("person.")), ["person.alex", "person.sam"]);
  // Profiles without a list, and persons without a state, leave the card as it is.
  card.hass = update(hass, { "sensor.player_profiles": { state: "0", attributes: {} } });
  assert.equal($$(card, ".avatar").length, 0);
  assert.equal(card._relevant("person.nobody", undefined), undefined);
});
