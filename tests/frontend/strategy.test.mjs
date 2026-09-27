// The dashboard strategy builds live, scoreboard, training and board views for every board.
import assert from "node:assert/strict";
import { test } from "node:test";

import { dashboardStrategy } from "../../custom_components/autodarts/frontend/autodarts-card.js";

const entity = (entity_id, translation_key, device_id) => ({
  entity_id,
  translation_key,
  device_id,
  platform: "autodarts",
});

function board(device, prefix) {
  return [
    entity(`sensor.${prefix}_darts`, "training_darts", device),
    entity(`sensor.${prefix}_average`, "training_average", device),
    entity(`switch.${prefix}_calibrate_on_start`, "auto_calibrate_on_start", device),
    entity(`select.${prefix}_standby`, "standby_minutes", device),
    entity(`update.${prefix}_software`, "board_software", device),
  ];
}

// Every board of the entities is in the device registry unless the test says otherwise.
const registered = (entities) => Object.fromEntries(entities.map((item) => [item.device_id, { id: item.device_id }]));
const hass = (entities, devices = registered(entities)) => ({
  locale: { language: "en" },
  entities: Object.fromEntries(entities.map((item) => [item.entity_id, item])),
  devices,
  states: {},
});

test("one board gets a live, a scoreboard, a training and a board view", () => {
  const config = dashboardStrategy(hass(board("dev1", "b")));
  assert.equal(config.title, "Autodarts");
  assert.deepEqual(
    config.views.map((view) => view.path),
    ["live", "scoreboard", "training", "board"]
  );
  const [live, scoreboard, training, maintenance] = config.views;
  assert.deepEqual(live.sections[0].cards[0], {
    type: "custom:autodarts-card",
    device_id: "dev1",
    grid_options: { columns: "full" },
  });
  assert.equal(scoreboard.panel, true);
  assert.deepEqual(scoreboard.cards, [
    { type: "custom:autodarts-scoreboard-card", device_id: "dev1", full_height: true },
  ]);
  const trends = training.sections[1].cards;
  assert.deepEqual(
    trends.map((card) => [card.type, card.entities]),
    [
      ["statistics-graph", ["sensor.b_darts"]],
      ["history-graph", ["sensor.b_average"]],
    ]
  );
  assert.equal(trends[0].stat_types[0], "change");
  const settings = maintenance.sections[1].cards;
  assert.deepEqual(settings[1].entities, ["switch.b_calibrate_on_start", "select.b_standby"]);
  assert.equal(settings[2].entity, "update.b_software");
});

test("several boards get their own named views", () => {
  const config = dashboardStrategy(
    hass([...board("dev1", "a"), ...board("dev2", "b")], {
      dev1: { name: "Autodarts Board", name_by_user: "Club board" },
      dev2: { name: "Garage" },
    })
  );
  assert.deepEqual(
    config.views.map((view) => view.path),
    ["live-1", "scoreboard-1", "training-1", "board-1", "live-2", "scoreboard-2", "training-2", "board-2"]
  );
  assert.equal(config.views[0].title, "Live · Club board");
  assert.equal(config.views[5].title, "Scoreboard · Garage");
  assert.equal(config.views[6].sections[0].cards[0].device_id, "dev2");
});

test("a chosen board and title are respected, and missing entities are left out", () => {
  const config = dashboardStrategy(hass([entity("sensor.x_darts", "training_darts", "dev1")]), {
    device_id: "dev1",
    title: "Darts",
  });
  assert.equal(config.title, "Darts");
  assert.equal(config.views[2].sections[1].cards.length, 1);
  // Without settings or update entities, the board view shows only the status card.
  assert.equal(config.views[3].sections.length, 1);
});

test("without boards the dashboard explains what to do", () => {
  const config = dashboardStrategy({ locale: { language: "de" }, entities: {} });
  assert.match(config.views[0].cards[0].content, /^Kein Autodarts-Board gefunden\. Richte die Autodarts-Integration ein/);
});

test("a board that no longer exists gets no empty views, but its own message", () => {
  const entities = [...board("dev1", "a"), ...board("gone", "b")];
  // A board the device registry no longer knows is skipped.
  const config = dashboardStrategy(hass(entities, { dev1: { name: "Garage" } }));
  assert.deepEqual(
    config.views.map((view) => view.path),
    ["live", "scoreboard", "training", "board"]
  );
  const stale = dashboardStrategy(hass(entities, { dev1: { name: "Garage" } }), { device_id: "gone", title: "Darts" });
  assert.equal(stale.title, "Darts");
  assert.deepEqual(stale.views, [
    {
      title: "Autodarts",
      cards: [
        {
          type: "markdown",
          content:
            "The board of this dashboard no longer exists. Edit the dashboard and choose another board, or clear the board to show every board.",
        },
      ],
    },
  ]);
  // Without a device registry, a chosen board is trusted.
  const trusted = dashboardStrategy({ ...hass(entities), devices: undefined }, { device_id: "dev1" });
  assert.equal(trusted.views[0].sections[0].cards[0].device_id, "dev1");
});

test("the training view adds the training settings, the board view the detection quality", () => {
  const config = dashboardStrategy(
    hass([
      ...board("dev1", "b"),
      entity("switch.b_auto_start", "training_auto_start", "dev1"),
      entity("number.b_idle", "training_idle_timeout", "dev1"),
      entity("sensor.b_corrected", "correction_rate", "dev1"),
    ])
  );
  const training = config.views.find((view) => view.path === "training");
  assert.deepEqual(training.sections[1].cards.at(-1), {
    type: "entities",
    title: "Training settings",
    entities: ["switch.b_auto_start", "number.b_idle"],
  });
  const maintenance = config.views.find((view) => view.path === "board").sections[1].cards;
  assert.deepEqual(maintenance.slice(-2), [
    { type: "tile", entity: "update.b_software" },
    { type: "tile", entity: "sensor.b_corrected" },
  ]);
});

test("the training view offers the daily goal, the streak and personal bests", () => {
  const config = dashboardStrategy(
    hass([
      ...board("dev1", "b"),
      entity("number.b_goal", "training_daily_goal", "dev1"),
      entity("sensor.b_today", "darts_today", "dev1"),
      entity("sensor.b_streak", "training_streak", "dev1"),
      entity("sensor.b_best", "personal_best", "dev1"),
    ])
  );
  const training = config.views.find((view) => view.path === "training");
  assert.deepEqual(training.sections[1].cards[0], {
    type: "entities",
    title: "Goals and personal bests",
    entities: ["number.b_goal", "sensor.b_today", "sensor.b_streak", "sensor.b_best"],
  });
});

test("rows leave out the board and the section they sit in", () => {
  const entities = [
    entity("select.b_game", "practice_game", "dev1"),
    entity("number.b_players", "practice_players", "dev1"),
    entity("switch.b_routes", "practice_personal_routes", "dev1"),
    entity("button.b_leg", "practice_new_leg", "dev1"),
    entity("text.b_player_1", "practice_player", "dev1"),
    entity("number.b_goal", "training_daily_goal", "dev1"),
    entity("sensor.b_darts", "training_darts", "dev1"),
    entity("update.b_software", "board_software", "dev1"),
    entity("switch.b_custom", "auto_calibrate", "dev1"),
  ];
  const names = {
    "select.b_game": "Autodarts Board Übungsspiel",
    "number.b_players": "Autodarts Board Übungsspiel Spieler",
    "switch.b_routes": "Autodarts Board Übungsspiel persönliche Checkout-Wege",
    "button.b_leg": "Autodarts Board Neues Übungsleg",
    "text.b_player_1": "Autodarts Board Übungsspiel Spieler 1",
    "number.b_goal": "Autodarts Board Tagesziel",
    "sensor.b_darts": "Autodarts Board Training: Darts",
    "update.b_software": "Autodarts Board Board-Software",
    // A name of the user's own stays as it is.
    "switch.b_custom": "Nachkalibrieren im Keller",
  };
  const config = dashboardStrategy({
    locale: { language: "de" },
    entities: Object.fromEntries(entities.map((item) => [item.entity_id, item])),
    devices: { dev1: { name: "Autodarts Board" } },
    states: Object.fromEntries(
      Object.entries(names).map(([id, name]) => [id, { entity_id: id, state: "on", attributes: { friendly_name: name } }])
    ),
  });
  const [live, , training, maintenance] = config.views;
  const [, practice, players] = live.sections[1].cards;
  assert.deepEqual(practice.entities, [
    { entity: "select.b_game", name: "Spiel" },
    { entity: "number.b_players", name: "Spieler" },
    { entity: "switch.b_routes", name: "Persönliche Checkout-Wege" },
    { entity: "button.b_leg", name: "Neues Übungsleg" },
  ]);
  assert.deepEqual(players.entities, [{ entity: "text.b_player_1", name: "Spieler 1" }]);
  const [goals, darts] = training.sections[1].cards;
  assert.deepEqual(goals.entities, [{ entity: "number.b_goal", name: "Tagesziel" }]);
  assert.deepEqual(darts.entities, [{ entity: "sensor.b_darts", name: "Training: Darts" }]);
  const [, settings, software] = maintenance.sections[1].cards;
  assert.deepEqual(settings.entities, [{ entity: "switch.b_custom", name: "Nachkalibrieren im Keller" }]);
  assert.deepEqual(software, { type: "tile", entity: "update.b_software", name: "Board-Software" });
});

test("a renamed board is left out of the row names too", () => {
  const config = dashboardStrategy({
    locale: { language: "en" },
    entities: { "number.b_players": entity("number.b_players", "practice_players", "dev1") },
    devices: { dev1: { name: "Autodarts Board", name_by_user: "Garage" } },
    states: { "number.b_players": { state: "2", attributes: { friendly_name: "Garage Practice players" } } },
  });
  assert.deepEqual(config.views[0].sections[1].cards[1].entities, [{ entity: "number.b_players", name: "Players" }]);
});

test("the live view sets up and starts tournaments, with the tournament's stage as a tile", () => {
  const keys = [
    ["sensor.b_tournament", "tournament", "Autodarts Board Tournament"],
    ["select.b_format", "tournament_format", "Autodarts Board Tournament format"],
    ["text.b_players", "tournament_players", "Autodarts Board Tournament players"],
    ["button.b_start", "tournament_start", "Autodarts Board Start tournament"],
  ];
  const withEntities = (list) =>
    dashboardStrategy({
      locale: { language: "en" },
      entities: Object.fromEntries(list.map(([id, key]) => [id, entity(id, key, "dev1")])),
      devices: { dev1: { name: "Autodarts Board" } },
      states: Object.fromEntries(
        list.map(([id, , name]) => [id, { entity_id: id, state: "on", attributes: { friendly_name: name } }])
      ),
    }).views[0].sections;
  const [, tournament] = withEntities(keys);
  assert.deepEqual(tournament, {
    type: "grid",
    column_span: 2,
    cards: [
      { type: "heading", heading: "Tournament" },
      { type: "tile", entity: "sensor.b_tournament" },
      {
        type: "entities",
        entities: [
          { entity: "select.b_format", name: "Format" },
          { entity: "text.b_players", name: "Players" },
          { entity: "button.b_start", name: "Start tournament" },
        ],
      },
    ],
  });
  // Without the sensor, the settings stand alone; without any, there is no section.
  assert.deepEqual(withEntities(keys.slice(1))[1].cards.map((card) => card.type), ["heading", "entities"]);
  assert.equal(withEntities(keys.slice(0, 1)).length, 1);
});

test("rows leave out the section at the end of French and Spanish names, too", () => {
  const entities = [
    entity("select.b_game", "practice_game", "dev1"),
    entity("number.b_players", "practice_players", "dev1"),
    entity("switch.b_routes", "practice_personal_routes", "dev1"),
    entity("button.b_leg", "practice_new_leg", "dev1"),
    entity("select.b_format", "tournament_format", "dev1"),
    entity("button.b_start", "tournament_start", "dev1"),
  ];
  for (const [language, names, rows, tournamentRows] of [
    [
      "fr",
      [
        "Partie",
        "Nombre de joueurs de la partie",
        "Combinaisons de finish personnelles de la partie",
        "Nouvelle manche de la partie",
        "Format du tournoi",
        "Démarrer le tournoi",
      ],
      ["Jeu", "Nombre de joueurs", "Combinaisons de finish personnelles", "Nouvelle manche"],
      ["Format", "Démarrer le tournoi"],
    ],
    [
      "es",
      // A name without the section stays as it is.
      [
        "Partida",
        "Jugadores de la partida",
        "Rutas de cierre personales de la partida",
        "Nuevo leg",
        "Formato del torneo",
        "Iniciar torneo",
      ],
      ["Juego", "Jugadores", "Rutas de cierre personales", "Nuevo leg"],
      ["Formato", "Iniciar torneo"],
    ],
  ]) {
    const config = dashboardStrategy({
      locale: { language },
      entities: Object.fromEntries(entities.map((item) => [item.entity_id, item])),
      devices: { dev1: { name: "Autodarts Board" } },
      states: Object.fromEntries(
        entities.map(({ entity_id }, index) => [
          entity_id,
          { entity_id, state: "on", attributes: { friendly_name: `Autodarts Board ${names[index]}` } },
        ])
      ),
    });
    const [, practice, tournament] = config.views[0].sections;
    assert.deepEqual(
      practice.cards[1].entities.map((row) => row.name),
      rows,
      language
    );
    assert.deepEqual(
      tournament.cards[1].entities.map((row) => row.name),
      tournamentRows,
      language
    );
  }
});
