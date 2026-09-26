/*
 * Autodarts cards for Home Assistant, served by the Autodarts integration.
 *
 * - autodarts-card: the current visit on a dartboard drawn with the geometry of
 *   the Autodarts Board Manager. Hit beds blink, darts appear at their detected
 *   position and the board glows in the detection status colour.
 * - autodarts-training-card: the local training session with a hit heatmap,
 *   statistics, personal bests, the most hit beds and the recent visits.
 * - autodarts-status-card: detection, connections, cameras, the board PC and
 *   maintenance controls at a glance.
 * - autodarts-scoreboard-card, autodarts-players-card and autodarts-doubles-card:
 *   the game at the board, the player profiles and the hit rate per double.
 * - The dashboard strategy "custom:autodarts" builds a complete dashboard with
 *   live, scoreboard, training, players and board views for every board.
 *
 * Card editors are forms of Home Assistant (getConfigForm); only the strategy,
 * which Home Assistant offers no form for, brings its own editor element.
 */

const CARD_TYPE = "autodarts-card";
const TRAINING_TYPE = "autodarts-training-card";
const STATUS_TYPE = "autodarts-status-card";
const SCOREBOARD_TYPE = "autodarts-scoreboard-card";
const PLAYERS_TYPE = "autodarts-players-card";
const DOUBLES_TYPE = "autodarts-doubles-card";
const STRATEGY_TYPE = "autodarts";
const STRATEGY_ELEMENT = `ll-strategy-dashboard-${STRATEGY_TYPE}`;
const STRATEGY_EDITOR_TYPE = "autodarts-strategy-editor";
const REPOSITORY = "https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs";

// Board Manager geometry in millimetres; dart coordinates are normalised to
// the outer edge of the double ring (170 mm) with y pointing to the 20.
const NORM = 170;
const R = {
  bull: 7,
  outerBull: 17,
  trebleIn: 97,
  trebleOut: 107,
  doubleIn: 160,
  doubleOut: 170,
  numbers: 197,
  board: 225,
};
const NUMBERS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5];
const BEDS = {
  SI: [R.outerBull, R.trebleIn],
  T: [R.trebleIn, R.trebleOut],
  SO: [R.trebleOut, R.doubleIn],
  D: [R.doubleIn, R.doubleOut],
  M: [R.doubleOut, R.board],
};

const STYLES = {
  autodarts: {
    black: "#212121",
    white: "#fffde7",
    red: "#ef5350",
    green: "#66bb6a",
    surround: "#212121",
    wire: "none",
    numbers: "#ffffff",
  },
  classic: {
    black: "#1b1b1b",
    white: "#f1e4c3",
    red: "#d42f2f",
    green: "#1d9150",
    surround: "#101010",
    wire: "#b8bcc2",
    numbers: "#f5f5f5",
  },
  // A quiet board that lets a heatmap stand out.
  muted: {
    black: "#2a2d33",
    white: "#3b3f47",
    red: "#34373e",
    green: "#303339",
    surround: "#1c1e22",
    wire: "#4f545d",
    numbers: "#d6d9de",
  },
};

// The theme's colours for success, warnings and errors, with the former colours as fallback.
const STATUS_COLORS = {
  ready: "var(--success-color, #43a047)",
  takeout: "var(--amber-color, #fbc02d)",
  stopped: "var(--warning-color, #fb8c00)",
  calibrating: "var(--purple-color, #8e24aa)",
  problem: "var(--error-color, #e53935)",
  offline: "var(--error-color, #e53935)",
};

const GOLD = "#ffd60a";

const VISIT_COLORS = {
  max: GOLD,
  high: "#ff8c42",
  ton: "#43b581",
  good: "var(--ad-accent)",
  low: "#8a8f98",
};

// Colour names of Home Assistant's colour picker; they follow the theme.
const THEME_COLORS = new Set([
  "primary",
  "accent",
  "red",
  "pink",
  "purple",
  "deep-purple",
  "indigo",
  "blue",
  "light-blue",
  "cyan",
  "teal",
  "green",
  "light-green",
  "lime",
  "yellow",
  "amber",
  "orange",
  "deep-orange",
  "brown",
  "light-grey",
  "grey",
  "dark-grey",
  "blue-grey",
  "black",
  "white",
]);

const TEXT = {
  en: {
    visit: "Current visit",
    points: "points",
    dart: "Dart",
    of: "of",
    miss: "Miss",
    session: "Training session",
    since: "since",
    darts: "Darts",
    average: "3-dart avg.",
    triples: "Triples",
    bulls: "Bulls",
    max: "180s",
    board: "Board Manager",
    realtime: "Realtime",
    cameras: "Cameras",
    camera_problem: "Check cameras",
    start: "Start detection",
    stop: "Stop detection",
    reset: "Reset detection",
    calibrate: "Calibrate",
    confirm: "Confirm?",
    status_offline: "Board unreachable",
    status_calibrating: "Calibrating",
    status_problem: "Check cameras",
    status_starting: "Starting detection",
    status_stopping: "Stopping detection",
    status_stopped: "Detection stopped",
    status_takeout: "Removing darts",
    status_hand: "Hand at the board",
    status_full: "Remove your darts",
    status_ready: "Ready – throw!",
    no_board: "No Autodarts board found. Select a device in the card settings.",
    board_label: "Dartboard with the current visit",
    // Card editors
    device_id: "Board",
    device_helper: "Optional. Without a selection, the card uses the first Autodarts board.",
    title: "Title",
    layout: "Layout",
    layout_auto: "Automatic",
    layout_horizontal: "Board on the right",
    layout_vertical: "Board below",
    layout_board: "Board only",
    board_style: "Board style",
    style_classic: "Classic",
    style_autodarts: "Autodarts",
    style_muted: "Muted",
    highlight: "Highlight",
    highlight_visit: "All darts of the visit",
    highlight_last: "Last dart only",
    highlight_none: "Off",
    blink: "Blink hit beds",
    show_markers: "Show dart positions",
    show_numbers: "Show numbers",
    show_stats: "Show training statistics",
    show_connection: "Show connection status",
    show_controls: "Show controls",
    show_recent: "Show last visits",
    show_practice: "Show practice game",
    accent_color: "Accent color",
    highlight_color: "Highlight color",
    color_helper: "A theme color from the list, or any CSS color such as #00e5ff. Empty uses the theme's primary color.",
    highlight_color_helper: "A theme color from the list, or any CSS color such as #00e5ff. Empty uses gold (#ffd60a).",
    default_hint: "Default: {value}",
    invalid_option: "The option {name} does not accept {value}.",
    recent: "Last visits",
    practice: "Practice",
    leg_darts: "darts",
    checkout: "Checkout",
    bust: "Bust – the score stays",
    game_shot: "Game shot!",
    no_checkout: "No checkout possible",
    score_player: "Player",
    score_turn: "to throw",
    score_winner: "wins the match!",
    score_legs: "Legs",
    score_sets: "Sets",
    practice_names: "Player names",
    practice_game_row: "Game",
    practice_legs_per_day: "Practice legs per day",
    practice_trend: "First 9, checkout and doubles rate",
    streak_day: "day in a row",
    streak_days: "days in a row",
    darts_today: "darts today",
    goals_and_bests: "Goals and personal bests",
    drill_around_the_clock: "Around the Clock",
    drill_doubles: "Doubles training",
    drill_checkout: "Checkout training",
    drill_bobs_27: "Bob's 27",
    drill_hits: "hits",
    drill_round: "Round",
    drill_points: "points",
    drill_visit: "Visit",
    drill_checked: "checked out",
    drill_done: "Done in {darts} darts",
    drill_bobs_done: "Done with {points} points",
    drill_bobs_lost: "Below zero – the next dart starts again",
    cricket: "Cricket",
    cricket_mpr: "MPR",
    cricket_points: "Points",
    mark_0: "No marks",
    mark_1: "1 mark",
    mark_2: "2 marks",
    mark_3: "Closed",
    bull_off: "Bull-off",
    bull_off_hint: "Closest to the bull starts",
    party_shanghai: "Shanghai",
    party_halve_it: "Halve-It",
    party_killer: "Killer",
    any_double: "Any double",
    any_treble: "Any treble",
    killer_choose: "Throw for your number",
    killer_hunt: "Killer – hit the others' doubles",
    needs_players: "Killer needs at least two players",
    double_in_needed: "Start with a double",
    out: "out",
    // Scoreboard card
    view_scoreboard: "Scoreboard",
    view_players: "Players",
    players_title: "Players",
    no_profiles: "No player profiles yet. Give the players of a practice game a name, and every leg counts for them.",
    profile_legs: "Legs",
    profile_matches: "Matches",
    first_9: "First 9",
    checkout_short: "Checkout",
    highest_checkout: "Highest checkout",
    best_leg: "Best {game}",
    best_mpr: "Best MPR",
    head_to_head: "Head-to-head",
    recent_matches: "Recent matches",
    show_head_to_head: "Show head-to-head",
    show_matches: "Show recent matches",
    doubles_title: "Doubles",
    doubles_darts: "darts at a double",
    doubles_empty: "Throw at doubles in X01, the doubles training or Bob's 27 to see your hit rate on every double.",
    doubles_unknown_player:
      "No doubles of {player} yet. Check the name in the card settings, or throw at doubles in a practice game as {player}.",
    doubles_routes: "Personal checkout routes use doubles with at least 10 darts.",
    player: "Player",
    player_helper: "Optional. Pick or type a player name for that player's doubles; empty shows everybody's.",
    full_height: "Fill the screen",
    show_visit: "Show the current visit",
    show_status: "Show the board status",
    legs_per_set: "legs per set",
    sets_to_win: "sets to win",
    visit_short: "Visit",
    caller: "Caller",
    caller_on: "Caller on",
    caller_hint: "Tap to switch the caller on or off",
    caller_options: "Caller options",
    caller_options_helper: "These calls are made while the caller is on.",
    call_scores: "Call every visit",
    call_checkouts: "Call what a player requires",
    call_results: "Call game shots and busts",
    call_sounds: "Play a fanfare for a 180",
    say_require: "{name}, you require {remaining}",
    say_require_alone: "You require {remaining}",
    say_bust: "No score",
    say_no_score: "No score",
    say_mark: "One mark",
    say_marks: "{marks} marks",
    say_leg: "Game shot, and the leg!",
    say_match: "Game shot, and the match, {name}!",
    // Training card
    training: "Training",
    average_long: "3-dart average",
    visits: "Visits",
    highest: "Highest visit",
    scores_100: "100+",
    scores_140: "140+",
    doubles: "Doubles",
    misses: "Misses",
    triple_rate: "Triple rate",
    heatmap: "Hit map",
    heatmap_label: "Dartboard colored by how often each bed was hit",
    top: "Most hit",
    history: "Recent visits",
    history_empty: "Completed visits appear here.",
    no_darts: "No darts in this session yet. Start throwing!",
    new_session: "New session",
    hits: "hits",
    mode: "Heatmap",
    mode_beds: "Beds",
    mode_numbers: "Numbers",
    show_heatmap: "Show heatmap",
    show_top: "Show most hit beds",
    show_history: "Show recent visits",
    show_reset: "Show session controls",
    show_bests: "Show personal bests",
    history_size: "Visits in the history",
    start_session: "Start session",
    end_session: "End session",
    session_running: "Session running",
    session_ended: "Session ended",
    no_session: "No session running",
    no_session_hint: "Start a session to count your darts.",
    past_sessions: "Past sessions",
    session_end: "Ended",
    duration: "Duration",
    highest_short: "Highest",
    show_sessions: "Show past sessions",
    statistics_label: "Training statistics, open the details",
    personal_bests: "Personal bests",
    best_session_average: "Best session average",
    best_cricket_mpr: "Best Cricket MPR",
    best_streak: "Longest streak",
    unit_darts: "{value} darts",
    unit_points: "{value} points",
    unit_day: "{value} day",
    unit_days: "{value} days",
    unit_minutes: "{value} min",
    under_a_minute: "<1 min",
    // Status card
    detection: "Detection",
    connections: "Connections",
    cloud: "Cloud",
    version: "Version",
    update_available: "Update to",
    up_to_date: "Up to date",
    system: "Board PC",
    cpu: "CPU",
    memory: "Memory",
    detection_fps: "Detection",
    corrected: "Corrected",
    camera: "Camera",
    camera_ok: "OK",
    camera_failure: "Problem",
    restart: "Restart",
    show_cameras: "Show cameras",
    show_system: "Show board PC",
    vision_short: "Detection",
    // Dashboard strategy
    view_live: "Live",
    view_training: "Training",
    view_board: "Board",
    darts_per_day: "Darts per day",
    average_trend: "3-dart average, last 7 days",
    board_settings: "Board settings",
    training_settings: "Training settings",
    strategy_device_helper: "Optional. Without a selection, the dashboard shows every Autodarts board.",
    strategy_no_board: "No Autodarts board found. Set up the Autodarts integration, then reload this dashboard.",
    strategy_board_missing:
      "The board of this dashboard no longer exists. Edit the dashboard and choose another board, or clear the board to show every board.",
    // Card picker
    picker_live: "Autodarts",
    picker_live_description:
      "The current visit on a live dartboard with hit beds, dart positions, the practice game, training statistics and controls.",
    picker_training: "Autodarts training",
    picker_training_description:
      "The training session with a hit heatmap, 3-dart average, statistics, personal bests and recent visits.",
    picker_status: "Autodarts board status",
    picker_status_description: "Detection, connections, cameras, board PC and maintenance controls of an Autodarts board.",
    picker_scoreboard: "Autodarts scoreboard",
    picker_scoreboard_description:
      "A large scoreboard for a tablet or TV at the board: X01, Cricket, party and training games, the visit and a caller.",
    picker_players: "Autodarts players",
    picker_players_description:
      "Statistics and personal bests of every named player, head-to-head records and recent matches.",
    picker_doubles: "Autodarts doubles",
    picker_doubles_description:
      "The hit rate of every double on the board, for everybody or one player, with the favorite double.",
    picker_strategy_description:
      "Live, scoreboard, training, players and board views for every Autodarts board, built automatically.",
  },
  de: {
    visit: "Aktuelle Aufnahme",
    points: "Punkte",
    dart: "Dart",
    of: "von",
    miss: "Miss",
    session: "Trainingssession",
    since: "seit",
    darts: "Darts",
    average: "3-Dart-Average",
    triples: "Triple",
    bulls: "Bulls",
    max: "180er",
    board: "Board Manager",
    realtime: "Echtzeit",
    cameras: "Kameras",
    camera_problem: "Kameras prüfen",
    start: "Erkennung starten",
    stop: "Erkennung stoppen",
    reset: "Erkennung zurücksetzen",
    calibrate: "Kalibrieren",
    confirm: "Bestätigen?",
    status_offline: "Board nicht erreichbar",
    status_calibrating: "Kalibrierung läuft",
    status_problem: "Kameras prüfen",
    status_starting: "Erkennung startet",
    status_stopping: "Erkennung stoppt",
    status_stopped: "Erkennung gestoppt",
    status_takeout: "Darts werden entnommen",
    status_hand: "Hand am Board",
    status_full: "Darts entnehmen",
    status_ready: "Bereit – wirf!",
    no_board: "Kein Autodarts-Board gefunden. Wähle ein Gerät in den Karteneinstellungen.",
    board_label: "Dartscheibe mit der aktuellen Aufnahme",
    device_id: "Board",
    device_helper: "Optional. Ohne Auswahl nutzt die Karte das erste Autodarts-Board.",
    title: "Titel",
    layout: "Anordnung",
    layout_auto: "Automatisch",
    layout_horizontal: "Scheibe rechts",
    layout_vertical: "Scheibe unten",
    layout_board: "Nur Scheibe",
    board_style: "Scheibenstil",
    style_classic: "Klassisch",
    style_autodarts: "Autodarts",
    style_muted: "Dezent",
    highlight: "Hervorhebung",
    highlight_visit: "Alle Darts der Aufnahme",
    highlight_last: "Nur letzter Dart",
    highlight_none: "Aus",
    blink: "Getroffene Felder blinken",
    show_markers: "Dart-Positionen anzeigen",
    show_numbers: "Zahlen anzeigen",
    show_stats: "Trainingsstatistik anzeigen",
    show_connection: "Verbindungsstatus anzeigen",
    show_controls: "Steuerung anzeigen",
    show_recent: "Vorige Aufnahmen anzeigen",
    show_practice: "Übungsspiel anzeigen",
    accent_color: "Akzentfarbe",
    highlight_color: "Farbe der Hervorhebung",
    color_helper: "Eine Theme-Farbe aus der Liste oder eine CSS-Farbe wie #00e5ff. Leer nutzt die Primärfarbe des Themes.",
    highlight_color_helper: "Eine Theme-Farbe aus der Liste oder eine CSS-Farbe wie #00e5ff. Leer nutzt Gold (#ffd60a).",
    default_hint: "Standard: {value}",
    invalid_option: "Die Option {name} erlaubt den Wert {value} nicht.",
    recent: "Vorige Aufnahmen",
    practice: "Übungsspiel",
    leg_darts: "Darts",
    checkout: "Checkout",
    bust: "Überworfen – der Rest bleibt",
    game_shot: "Game shot!",
    no_checkout: "Kein Checkout möglich",
    score_player: "Spieler",
    score_turn: "ist dran",
    score_winner: "gewinnt das Match!",
    score_legs: "Legs",
    score_sets: "Sätze",
    practice_names: "Spielernamen",
    practice_game_row: "Spiel",
    practice_legs_per_day: "Übungslegs pro Tag",
    practice_trend: "First 9, Checkout- und Doppelquote",
    streak_day: "Tag in Folge",
    streak_days: "Tage in Folge",
    darts_today: "Darts heute",
    goals_and_bests: "Ziele und Bestleistungen",
    drill_around_the_clock: "Around the Clock",
    drill_doubles: "Doppeltraining",
    drill_checkout: "Checkout-Training",
    drill_bobs_27: "Bob's 27",
    drill_hits: "Treffer",
    drill_round: "Runde",
    drill_points: "Punkte",
    drill_visit: "Aufnahme",
    drill_checked: "gecheckt",
    drill_done: "Geschafft in {darts} Darts",
    drill_bobs_done: "Geschafft mit {points} Punkten",
    drill_bobs_lost: "Unter null – der nächste Dart startet neu",
    cricket: "Cricket",
    cricket_mpr: "MPR",
    cricket_points: "Punkte",
    mark_0: "Keine Marks",
    mark_1: "1 Mark",
    mark_2: "2 Marks",
    mark_3: "Geschlossen",
    bull_off: "Ausbullen",
    bull_off_hint: "Wer am nächsten am Bull liegt, beginnt",
    party_shanghai: "Shanghai",
    party_halve_it: "Halve-It",
    party_killer: "Killer",
    any_double: "Beliebiges Double",
    any_treble: "Beliebiges Triple",
    killer_choose: "Wirf für deine Zahl",
    killer_hunt: "Killer – triff die Doubles der anderen",
    needs_players: "Killer braucht mindestens zwei Spieler",
    double_in_needed: "Mit einem Double beginnen",
    out: "raus",
    view_scoreboard: "Anzeigetafel",
    view_players: "Spieler",
    players_title: "Spieler",
    no_profiles: "Noch keine Spielerprofile. Gib den Spielern eines Übungsspiels einen Namen, dann zählt jedes Leg für sie.",
    profile_legs: "Legs",
    profile_matches: "Matches",
    first_9: "First 9",
    checkout_short: "Checkout",
    highest_checkout: "Höchster Checkout",
    best_leg: "Bestes {game}-Leg",
    best_mpr: "Beste MPR",
    head_to_head: "Direkter Vergleich",
    recent_matches: "Letzte Matches",
    show_head_to_head: "Direkten Vergleich anzeigen",
    show_matches: "Letzte Matches anzeigen",
    doubles_title: "Doubles",
    doubles_darts: "Darts aufs Double",
    doubles_empty: "Wirf im X01, im Doppeltraining oder bei Bob's 27 auf Doubles, dann siehst du hier die Quote jedes Doubles.",
    doubles_unknown_player:
      "Noch keine Doubles von {player}. Prüfe den Namen in den Karteneinstellungen oder wirf in einem Übungsspiel als {player} auf Doubles.",
    doubles_routes: "Persönliche Checkout-Wege nutzen Doubles mit mindestens 10 Darts.",
    player: "Spieler",
    player_helper: "Optional. Wähle oder tippe einen Spielernamen für die Doubles dieses Spielers; leer zeigt die aller.",
    full_height: "Bildschirm füllen",
    show_visit: "Aktuelle Aufnahme anzeigen",
    show_status: "Board-Status anzeigen",
    legs_per_set: "Legs pro Satz",
    sets_to_win: "Sätze zum Sieg",
    visit_short: "Aufnahme",
    caller: "Caller",
    caller_on: "Caller an",
    caller_hint: "Tippen schaltet den Caller ein oder aus",
    caller_options: "Caller-Optionen",
    caller_options_helper: "Diese Ansagen macht der Caller, solange er an ist.",
    call_scores: "Jede Aufnahme ansagen",
    call_checkouts: "Ansagen, was ein Spieler braucht",
    call_results: "Game shot und Überwerfen ansagen",
    call_sounds: "Fanfare bei einer 180",
    say_require: "{name}, du brauchst {remaining}",
    say_require_alone: "Du brauchst {remaining}",
    say_bust: "Überworfen",
    say_no_score: "Keine Punkte",
    say_mark: "Ein Mark",
    say_marks: "{marks} Marks",
    say_leg: "Game shot, und das Leg!",
    say_match: "Game shot, und das Match, {name}!",
    training: "Training",
    average_long: "3-Dart-Average",
    visits: "Aufnahmen",
    highest: "Höchste Aufnahme",
    scores_100: "100+",
    scores_140: "140+",
    doubles: "Doubles",
    misses: "Fehlwürfe",
    triple_rate: "Triple-Quote",
    heatmap: "Trefferbild",
    heatmap_label: "Dartscheibe, eingefärbt nach Trefferhäufigkeit je Feld",
    top: "Häufigste Felder",
    history: "Letzte Aufnahmen",
    history_empty: "Abgeschlossene Aufnahmen erscheinen hier.",
    no_darts: "Noch keine Darts in dieser Session. Leg los!",
    new_session: "Neue Session",
    hits: "Treffer",
    mode: "Heatmap",
    mode_beds: "Felder",
    mode_numbers: "Zahlen",
    show_heatmap: "Heatmap anzeigen",
    show_top: "Häufigste Felder anzeigen",
    show_history: "Letzte Aufnahmen anzeigen",
    show_reset: "Session-Steuerung anzeigen",
    show_bests: "Bestleistungen anzeigen",
    history_size: "Aufnahmen im Verlauf",
    start_session: "Session starten",
    end_session: "Session beenden",
    session_running: "Session läuft",
    session_ended: "Session beendet",
    no_session: "Keine Session aktiv",
    no_session_hint: "Starte eine Session, damit deine Darts zählen.",
    past_sessions: "Vergangene Sessions",
    session_end: "Ende",
    duration: "Dauer",
    highest_short: "Höchste",
    show_sessions: "Vergangene Sessions anzeigen",
    statistics_label: "Trainingsstatistik, Details öffnen",
    personal_bests: "Bestleistungen",
    best_session_average: "Bester Session-Average",
    best_cricket_mpr: "Beste MPR im Cricket",
    best_streak: "Längste Serie",
    unit_darts: "{value} Darts",
    unit_points: "{value} Punkte",
    unit_day: "{value} Tag",
    unit_days: "{value} Tage",
    unit_minutes: "{value} Min.",
    under_a_minute: "<1 Min.",
    detection: "Erkennung",
    connections: "Verbindungen",
    cloud: "Cloud",
    version: "Version",
    update_available: "Update auf",
    up_to_date: "Aktuell",
    system: "Board-PC",
    cpu: "CPU",
    memory: "Speicher",
    detection_fps: "Erkennung",
    corrected: "Korrigiert",
    camera: "Kamera",
    camera_ok: "OK",
    camera_failure: "Störung",
    restart: "Neu starten",
    show_cameras: "Kameras anzeigen",
    show_system: "Board-PC anzeigen",
    vision_short: "Erkennung",
    view_live: "Live",
    view_training: "Training",
    view_board: "Board",
    darts_per_day: "Darts pro Tag",
    average_trend: "3-Dart-Average, letzte 7 Tage",
    board_settings: "Board-Einstellungen",
    training_settings: "Trainingseinstellungen",
    strategy_device_helper: "Optional. Ohne Auswahl zeigt das Dashboard jedes Autodarts-Board.",
    strategy_no_board: "Kein Autodarts-Board gefunden. Richte die Autodarts-Integration ein und lade dieses Dashboard dann neu.",
    strategy_board_missing:
      "Das Board dieses Dashboards gibt es nicht mehr. Bearbeite das Dashboard und wähle ein anderes Board oder leere die Auswahl, um jedes Board zu zeigen.",
    picker_live: "Autodarts",
    picker_live_description:
      "Die aktuelle Aufnahme auf einer Live-Dartscheibe mit getroffenen Feldern, Dart-Positionen, dem Übungsspiel, Trainingsstatistik und Steuerung.",
    picker_training: "Autodarts Training",
    picker_training_description:
      "Die Trainingssession mit Heatmap der Treffer, 3-Dart-Average, Statistik, Bestleistungen und letzten Aufnahmen.",
    picker_status: "Autodarts Board-Status",
    picker_status_description: "Erkennung, Verbindungen, Kameras, Board-PC und Wartung eines Autodarts-Boards.",
    picker_scoreboard: "Autodarts Anzeigetafel",
    picker_scoreboard_description:
      "Eine große Anzeigetafel für Tablet oder Fernseher am Board: X01, Cricket, Party- und Trainingsspiele, die Aufnahme und ein Caller.",
    picker_players: "Autodarts Spieler",
    picker_players_description:
      "Statistik und Bestleistungen jedes Spielers mit Namen, direkte Vergleiche und die letzten Matches.",
    picker_doubles: "Autodarts Doubles",
    picker_doubles_description:
      "Die Quote jedes Doubles der Scheibe, für alle oder einen Spieler, mit dem Lieblingsdouble.",
    picker_strategy_description:
      "Live-, Anzeigetafel-, Trainings-, Spieler- und Board-Ansicht für jedes Autodarts-Board, automatisch erstellt.",
  },
};

const DEFAULTS = {
  layout: "auto",
  board_style: "classic",
  highlight: "visit",
  blink: true,
  show_markers: true,
  show_numbers: true,
  show_stats: true,
  show_connection: true,
  show_controls: true,
  show_recent: true,
  show_practice: true,
};

const TRAINING_DEFAULTS = {
  mode: "beds",
  board_style: "muted",
  show_heatmap: true,
  show_stats: true,
  show_bests: true,
  show_top: true,
  show_history: true,
  show_reset: true,
  show_sessions: true,
  history_size: 20,
};

const STATUS_DEFAULTS = {
  show_connection: true,
  show_cameras: true,
  show_system: true,
  show_controls: true,
};

const DOUBLES_DEFAULTS = {};

const PLAYERS_DEFAULTS = {
  show_head_to_head: true,
  show_matches: true,
};

const SCOREBOARD_DEFAULTS = {
  full_height: false,
  show_visit: true,
  show_status: true,
  // The caller speaks only when switched on, and a tap unlocks the sound.
  caller: false,
  call_scores: true,
  call_checkouts: true,
  call_results: true,
  call_sounds: true,
};

// Entities a card reads, by domain and translation key of the integration.
const BOARD_KEYS = {
  status: "sensor.local_status",
  numThrows: "sensor.num_throws",
  connected: "binary_sensor.local_connected",
  realtime: "binary_sensor.realtime_connected",
  cameras: "binary_sensor.cameras_active",
  calibrating: "binary_sensor.calibrating",
  cameraProblem: "binary_sensor.camera_problem",
  hand: "binary_sensor.hand_detected",
  takeoutPartial: "binary_sensor.takeout_partial",
  detection: "switch.detection",
  start: "button.start",
  stop: "button.stop",
  reset: "button.reset",
  calibrate: "button.calibrate",
};

const KEYS = {
  ...BOARD_KEYS,
  visit: "sensor.local_visit_score",
  lastThrow: "sensor.last_throw",
  darts: "sensor.training_darts",
  points: "sensor.training_points",
  average: "sensor.training_average",
  triples: "sensor.training_triples",
  bulls: "sensor.training_bulls",
  max: "sensor.training_scores_180",
  started: "sensor.training_started",
  practice: "sensor.practice_remaining",
  drill: "sensor.practice_target",
};

const TRAINING_KEYS = {
  darts: "sensor.training_darts",
  points: "sensor.training_points",
  average: "sensor.training_average",
  visits: "sensor.training_visits",
  highest: "sensor.training_highest_visit",
  scores_100: "sensor.training_scores_100",
  scores_140: "sensor.training_scores_140",
  max: "sensor.training_scores_180",
  triples: "sensor.training_triples",
  doubles: "sensor.training_doubles",
  bulls: "sensor.training_bulls",
  misses: "sensor.training_misses",
  started: "sensor.training_started",
  events: "event.board_events",
  newSession: "button.reset_training",
  session: "switch.training_session",
  lastSession: "sensor.training_last_session",
  streak: "sensor.training_streak",
  today: "sensor.darts_today",
  bests: "sensor.personal_best",
};

const STATUS_KEYS = {
  ...BOARD_KEYS,
  restart: "button.restart",
  cloudLink: "binary_sensor.cloud_link",
  upstream: "switch.upstream",
  cpu: "sensor.cpu_usage",
  memory: "sensor.memory_usage",
  fps: "sensor.detection_fps",
  corrected: "sensor.correction_rate",
  update: "update.board_software",
  hostOs: "sensor.host_os",
  processor: "sensor.host_processor",
  vision: "sensor.vision_version",
};

const DOUBLES_KEYS = {
  doubles: "sensor.favourite_double",
  profiles: "sensor.player_profiles",
};

const PLAYERS_KEYS = {
  profiles: "sensor.player_profiles",
  lastMatch: "sensor.last_match",
};

const SCOREBOARD_KEYS = {
  ...BOARD_KEYS,
  visit: "sensor.local_visit_score",
  practice: "sensor.practice_remaining",
  drill: "sensor.practice_target",
  darts: "sensor.training_darts",
  average: "sensor.training_average",
  highest: "sensor.training_highest_visit",
  max: "sensor.training_scores_180",
  streak: "sensor.training_streak",
  today: "sensor.darts_today",
};

// Per-camera entities carry their camera number as an attribute.
const CAMERA_KEYS = {
  problem: "binary_sensor.individual_camera_problem",
  fps: "sensor.camera_fps",
  calibrate: "button.calibrate_camera",
  image: "camera.board_camera",
};

const language = (hass) =>
  String(hass?.locale?.language || hass?.language || "en").startsWith("de") ? "de" : "en";

// Both languages have every key; an unknown key reads as itself.
const translate = (hass, key) => TEXT[language(hass)][key] ?? key;

// "{name} requires {remaining}" with its values.
const fill = (text, values) => text.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));

// The caller speaks the card's language, in Home Assistant's regional variant where it has one.
function voiceLanguage(hass) {
  const lang = language(hass);
  const own = String(hass?.locale?.language || hass?.language || "");
  return own.toLowerCase().startsWith(lang) ? own : lang;
}

// Home Assistant asks for card forms without hass. The last hass a card saw, or
// the page language that Home Assistant sets, stands in for it.
let pageHass = null;
const pageLanguage = () =>
  language(pageHass ?? { language: globalThis.document?.documentElement?.lang || "en" });
const pageText = (key) => TEXT[pageLanguage()][key] ?? key;

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);

// Card options reach the style only as real colours, never as url() or broken values.
// Colour names of Home Assistant's picker, such as "primary" or "red", follow the theme.
function cssColor(value, fallback) {
  if (typeof value !== "string") return fallback;
  if (THEME_COLORS.has(value)) return `var(--${value}-color)`;
  return !/url\(/i.test(value) && globalThis.CSS?.supports?.("color", value) ? value : fallback;
}

const usable = (state) => state && !["unknown", "unavailable"].includes(state.state);
const finite = (value) => (Number.isFinite(value) ? value : null);
const named = (value) => (typeof value === "string" && value ? value : null);

// Darts of a visit sensor that name a bed.
const visitThrows = (state) =>
  (Array.isArray(state?.attributes?.throws) ? state.attributes.throws : []).filter(
    (dart) => dart && Number.isInteger(dart.number) && Number.isInteger(dart.multiplier)
  );

// The integration's name of the bed a dart hit: S20, D16, T19, 25, BULL or MISS.
function dartKey(dart) {
  if (dart.number === 0 || dart.multiplier === 0) return "MISS";
  if (dart.number === 25) return dart.multiplier >= 2 ? "BULL" : "25";
  return `${"SDT"[dart.multiplier - 1] ?? "S"}${dart.number}`;
}

// Points of a bed by its name.
function keyScore(key) {
  if (key === "BULL") return 50;
  if (key === "25") return 25;
  const match = /^([SDT])(\d{1,2})$/.exec(key);
  return match ? { S: 1, D: 2, T: 3 }[match[1]] * Number(match[2]) : 0;
}

// Formatting ----------------------------------------------------------------

// Intl formatters are expensive to build, so every locale and option set keeps one.
const formatters = new Map();
function formatter(kind, locale, options) {
  const key = JSON.stringify([kind, locale, options]);
  let cached = formatters.get(key);
  if (!cached) {
    cached = kind === "date" ? new Intl.DateTimeFormat(locale, options) : new Intl.NumberFormat(locale, options);
    formatters.set(key, cached);
  }
  return cached;
}

// Number formats of the user profile, as Home Assistant maps them to locales.
const NUMBER_LOCALES = {
  comma_decimal: ["en-US", "en"],
  decimal_comma: ["de", "es", "it"],
  space_comma: ["fr", "sv", "cs"],
  quote_decimal: ["de-CH"],
  system: undefined,
};

function formatNumber(hass, value, digits = 0) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  const locale = hass?.locale || {};
  const options = { minimumFractionDigits: digits, maximumFractionDigits: digits };
  if (locale.number_format === "none") {
    return formatter("number", "en-US", { ...options, useGrouping: false }).format(value);
  }
  const target = Object.hasOwn(NUMBER_LOCALES, locale.number_format)
    ? NUMBER_LOCALES[locale.number_format]
    : locale.language || hass?.language;
  return formatter("number", target, options).format(value);
}

// "45 %" in German, "45%" in English, as Home Assistant writes percentages.
const PERCENT_SPACE = ["cs", "de", "fi", "fr", "sk", "sv"];
function formatPercent(hass, value, digits = 0) {
  const number = formatNumber(hass, value, digits);
  if (number === "–") return number;
  return `${number}${PERCENT_SPACE.includes(hass?.locale?.language ?? hass?.language) ? " " : ""}%`;
}

// The 12- or 24-hour clock of the user profile; by default, that of the language.
const clocks = new Map();
function amPm(locale) {
  const format = locale.time_format ?? "language";
  const key = `${format}|${locale.language}`;
  if (!clocks.has(key)) {
    let twelve = format === "12";
    if (format === "language" || format === "system") {
      const lang = format === "language" ? locale.language : undefined;
      twelve = new Date("January 1, 2023 22:00:00").toLocaleString(lang).includes("10");
    }
    clocks.set(key, twelve);
  }
  return clocks.get(key);
}

// Day, month and time like "26.09., 14:05", in the server's or the browser's time zone.
function formatDateTime(hass, time) {
  const moment = new Date(time);
  if (Number.isNaN(moment.getTime())) return "";
  const locale = hass?.locale || {};
  const twelve = amPm(locale);
  const server = hass?.config?.time_zone;
  return formatter("date", locale.language || hass?.language, {
    day: "2-digit",
    month: "2-digit",
    hour: twelve ? "numeric" : "2-digit",
    minute: "2-digit",
    hourCycle: twelve ? "h12" : "h23",
    ...(server && locale.time_zone !== "local" ? { timeZone: server } : {}),
  }).format(moment);
}

// Entity lookup ------------------------------------------------------------

// hass.entities is replaced whenever the registry changes, so it keys a cache
// that spares every card from scanning all entities on each state update.
const deviceCache = new WeakMap();
const indexCache = new WeakMap();

function autodartsDevices(hass) {
  const entities = hass?.entities || {};
  let devices = deviceCache.get(entities);
  if (!devices) {
    const found = new Set();
    for (const entity of Object.values(entities)) {
      if (entity.platform === "autodarts" && entity.device_id) found.add(entity.device_id);
    }
    devices = [...found];
    deviceCache.set(entities, devices);
  }
  return devices;
}

// A device the card or dashboard names must still exist; without a device registry, it may.
const knownDevice = (hass, deviceId) => !hass?.devices || Boolean(hass.devices[deviceId]);

function entityIndex(hass, deviceId) {
  const entities = hass?.entities || {};
  let byDevice = indexCache.get(entities);
  if (!byDevice) {
    byDevice = new Map();
    indexCache.set(entities, byDevice);
  }
  let index = byDevice.get(deviceId);
  if (!index) {
    index = {};
    for (const entity of Object.values(entities)) {
      if (entity.platform !== "autodarts" || entity.device_id !== deviceId) continue;
      if (!entity.translation_key) continue;
      const key = `${entity.entity_id.split(".")[0]}.${entity.translation_key}`;
      (index[key] ||= []).push(entity.entity_id);
    }
    byDevice.set(deviceId, index);
  }
  return index;
}

function resolveKeys(index, keys) {
  return Object.fromEntries(Object.entries(keys).map(([name, key]) => [name, index[key]?.[0]]));
}

function cameraEntities(hass, index) {
  const cameras = new Map();
  for (const [role, key] of Object.entries(CAMERA_KEYS)) {
    for (const id of index[key] || []) {
      const number = Number(hass.states[id]?.attributes?.camera);
      if (!Number.isInteger(number) || number < 1) continue;
      if (!cameras.has(number)) cameras.set(number, { number });
      cameras.get(number)[role] ??= id;
    }
  }
  return [...cameras.values()].sort((a, b) => a.number - b.number);
}

// Geometry ----------------------------------------------------------------

function point(radius, degrees) {
  const angle = (degrees * Math.PI) / 180;
  return [radius * Math.sin(angle), -radius * Math.cos(angle)];
}

const fmt = (value) => Number(value.toFixed(2));

function sectorPath(inner, outer, start, end) {
  const [x1, y1] = point(outer, start);
  const [x2, y2] = point(outer, end);
  const [x3, y3] = point(inner, end);
  const [x4, y4] = point(inner, start);
  return (
    `M${fmt(x1)} ${fmt(y1)}A${outer} ${outer} 0 0 1 ${fmt(x2)} ${fmt(y2)}` +
    `L${fmt(x3)} ${fmt(y3)}A${inner} ${inner} 0 0 0 ${fmt(x4)} ${fmt(y4)}Z`
  );
}

function ringPath(inner, outer) {
  const circle = (r) => `M${r} 0A${r} ${r} 0 1 0 ${-r} 0A${r} ${r} 0 1 0 ${r} 0Z`;
  return inner > 0 ? circle(outer) + circle(inner) : circle(outer);
}

function bedPath(id) {
  if (id === "Bull") return ringPath(0, R.bull);
  if (id === "25") return ringPath(R.bull, R.outerBull);
  if (id === "Miss") return ringPath(R.doubleOut, R.board);
  const match = /^(SI|SO|T|D|M)(\d+)$/.exec(id);
  const index = match ? NUMBERS.indexOf(Number(match[2])) : -1;
  if (index < 0) return null;
  const [inner, outer] = BEDS[match[1]];
  return sectorPath(inner, outer, index * 18 - 9, index * 18 + 9);
}

function sectorAt(dart) {
  if (!Number.isFinite(dart.x) || !Number.isFinite(dart.y)) return null;
  const degrees = (Math.atan2(dart.x, dart.y) * 180) / Math.PI;
  return NUMBERS[((Math.round(degrees / 18) % 20) + 20) % 20];
}

function beds(dart) {
  const { number, multiplier, bed } = dart;
  if (number === 25) return [multiplier >= 2 ? "Bull" : "25"];
  if (multiplier === 0 || bed === "Outside") {
    const sector = NUMBERS.includes(number) ? number : sectorAt(dart);
    return [sector ? `M${sector}` : "Miss"];
  }
  if (!NUMBERS.includes(number)) return [];
  if (bed === "Triple" || multiplier === 3) return [`T${number}`];
  if (bed === "Double" || multiplier === 2) return [`D${number}`];
  if (bed === "SingleInner") return [`SI${number}`];
  if (bed === "SingleOuter") return [`SO${number}`];
  if (Number.isFinite(dart.x) && Number.isFinite(dart.y)) {
    return [Math.hypot(dart.x, dart.y) * NORM < R.trebleIn ? `SI${number}` : `SO${number}`];
  }
  return [`SI${number}`, `SO${number}`];
}

function kind(dart) {
  if (dart.number === 25) return dart.multiplier >= 2 ? "bull" : "outer-bull";
  if (dart.multiplier === 0 || dart.bed === "Outside") return "miss";
  return { 3: "triple", 2: "double" }[dart.multiplier] || "single";
}

function label(hass, dart) {
  if (dart.number === 25) return dart.multiplier >= 2 ? "Bull" : "25";
  if (kind(dart) === "miss") return translate(hass, "miss");
  return `${{ 3: "T", 2: "D" }[dart.multiplier] || "S"}${dart.number}`;
}

function parseSegment(name) {
  // Fallback for integrations without dart details: the last segment name only.
  const text = String(name || "").trim();
  if (/^(bull|db|d25)$/i.test(text)) return { number: 25, multiplier: 2 };
  if (text === "25" || /^s25$/i.test(text)) return { number: 25, multiplier: 1 };
  const match = /^([SDTM])(\d{1,2})$/i.exec(text);
  if (!match) return null;
  const multiplier = { S: 1, D: 2, T: 3, M: 0 }[match[1].toUpperCase()];
  return { number: Number(match[2]), multiplier };
}

function boardSvg(style) {
  const colors = STYLES[style] || STYLES.classic;
  const wire = colors.wire === "none" ? "" : ` stroke="${colors.wire}" stroke-width="0.7"`;
  const parts = [`<circle r="${R.board}" fill="${colors.surround}"/>`];
  NUMBERS.forEach((number, index) => {
    const even = index % 2 === 0;
    const single = even ? colors.black : colors.white;
    const ring = even ? colors.red : colors.green;
    const start = index * 18 - 9;
    for (const [bed, fill] of [["SI", single], ["T", ring], ["SO", single], ["D", ring]]) {
      const [inner, outer] = BEDS[bed];
      parts.push(`<path d="${sectorPath(inner, outer, start, start + 18)}" fill="${fill}"${wire}/>`);
    }
  });
  parts.push(`<circle r="${R.outerBull}" fill="${colors.green}"${wire}/>`);
  parts.push(`<circle r="${R.bull}" fill="${colors.red}"${wire}/>`);
  if (colors.wire !== "none") {
    parts.push(
      `<circle r="${R.doubleOut}" fill="none" stroke="${colors.wire}" stroke-width="1.2"/>`
    );
  }
  return parts.join("");
}

function numbersSvg(style) {
  // Drawn above highlights, so a hit outside the double ring keeps its number readable.
  const color = (STYLES[style] || STYLES.classic).numbers;
  return NUMBERS.map((number, index) => {
    const [x, y] = point(R.numbers, index * 18);
    return `<text x="${fmt(x)}" y="${fmt(y)}" fill="${color}" class="number">${number}</text>`;
  }).join("");
}

// Training analytics ------------------------------------------------------

// Hits are counted per bed as S20, D16, T19, 25, BULL or MISS by the integration.
function hitBeds(key) {
  const text = String(key);
  if (text === "BULL") return ["Bull"];
  if (text === "25") return ["25"];
  const match = /^([SDT])(\d{1,2})$/.exec(text);
  if (!match || !NUMBERS.includes(Number(match[2]))) return [];
  const number = match[2];
  return { S: [`SI${number}`, `SO${number}`], D: [`D${number}`], T: [`T${number}`] }[match[1]];
}

function validHits(hits) {
  return Object.entries(hits && typeof hits === "object" ? hits : {})
    .map(([key, count]) => [key, Number(count)])
    .filter(([key, count]) => Number.isInteger(count) && count > 0 && (key === "MISS" || hitBeds(key).length));
}

function heatLevels(hits, mode = "beds") {
  const levels = new Map();
  const add = (bed, count) => levels.set(bed, (levels.get(bed) || 0) + count);
  for (const [key, count] of validHits(hits)) {
    const beds = hitBeds(key);
    if (mode !== "numbers") {
      beds.forEach((bed) => add(bed, count));
      continue;
    }
    // Numbers mode sums singles, doubles and triples of a sector.
    const number = /^[SDT](\d{1,2})$/.exec(key)?.[1];
    const group = number ? ["SI", "T", "SO", "D"].map((bed) => `${bed}${number}`) : beds.length ? ["Bull", "25"] : [];
    group.forEach((bed) => add(bed, count));
  }
  return levels;
}

function heatRatio(count, max) {
  return max > 1 ? Math.min(1, Math.max(0, (count - 1) / (max - 1))) : 1;
}

function heatColor(ratio) {
  // Thermal scale from blue (rarely hit) through green and yellow to red (most hit).
  const value = Math.min(1, Math.max(0, Number(ratio) || 0));
  return `hsl(${Math.round(220 * (1 - value))}, 90%, 55%)`;
}

function topHits(hits, limit = 5) {
  return validHits(hits)
    .filter(([key]) => key !== "MISS")
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit);
}

function hitLabel(hass, key) {
  if (key === "BULL") return "Bull";
  if (key === "MISS") return translate(hass, "miss");
  return key;
}

function visitBucket(score) {
  if (score >= 180) return "max";
  if (score >= 140) return "high";
  if (score >= 100) return "ton";
  if (score >= 60) return "good";
  return "low";
}

// "Intel(R) Core(TM) i3-9100T CPU @ 3.10GHz" reads as "Intel Core i3-9100T".
function shortProcessor(name) {
  if (typeof name !== "string") return "";
  return name
    .replace(/\((R|TM)\)/gi, "")
    .replace(/\s+CPU\b.*$|\s*@.*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Completed visits of the visit sensor, newest first; malformed entries are skipped.
function recentVisits(visits, limit = 5) {
  if (!Array.isArray(visits)) return [];
  return visits
    .filter((visit) => visit && Number.isFinite(visit.score) && visit.score >= 0 && Array.isArray(visit.segments))
    .slice(0, limit)
    .map((visit) => ({
      score: Math.round(visit.score),
      segments: visit.segments.filter((segment) => typeof segment === "string"),
    }));
}

// Finished sessions of the last-session sensor, newest first.
function pastSessions(sessions, limit = 5) {
  if (!Array.isArray(sessions)) return [];
  return sessions
    .filter((session) => session && Number.isFinite(Date.parse(session.ended)) && session.darts > 0)
    .slice(0, limit)
    .map((session) => ({
      ended: Date.parse(session.ended),
      minutes: finite(session.duration_minutes),
      darts: finite(session.darts),
      average: finite(session.average),
      best: finite(session.highest_visit),
    }));
}

// Rows of history/history_during_period for the board events entity.
function visitsFromHistory(rows, since = 0) {
  let visits = [];
  for (const row of Array.isArray(rows) ? rows : []) {
    const attributes = row?.a || row?.attributes;
    const time = Date.parse(row?.s ?? row?.state);
    // The start sensor has whole seconds, so a visit of the previous session
    // can fall into the same second; the start event itself is precise.
    if (attributes?.event_type === "session_started" && time >= since) {
      visits = [];
      continue;
    }
    if (attributes?.event_type !== "visit_completed") continue;
    const score = Number(attributes.score);
    if (!Number.isFinite(time) || !Number.isFinite(score) || time < since) continue;
    visits.push({
      time,
      score,
      darts: Number(attributes.darts) || 0,
      segments: Array.isArray(attributes.segments) ? attributes.segments.map(String) : [],
    });
  }
  return visits;
}

// Personal bests -------------------------------------------------------------

// Records of the personal-best sensor in reading order, and how each value reads.
const RECORD_ORDER = [
  ["highest_visit", "highest", "count"],
  ["highest_checkout", "highest_checkout", "count"],
  ["fewest_darts", "best_leg", "darts"],
  ["best_cricket_mpr", "best_cricket_mpr", "mpr"],
  ["best_session_average", "best_session_average", "average"],
  ["around_the_clock", "drill_around_the_clock", "darts"],
  ["doubles", "drill_doubles", "darts"],
  ["bobs_27", "drill_bobs_27", "points"],
];

// Every personal best that has a value, and the longest training streak.
function bestsView(bests, streak) {
  const attributes = bests?.attributes || {};
  const value = (key) => (finite(attributes[key]) !== null && attributes[key] > 0 ? attributes[key] : null);
  const records = [];
  for (const [key, name, kind] of RECORD_ORDER) {
    if (key !== "fewest_darts") {
      if (value(key) !== null) records.push({ record: key, name, kind, value: value(key) });
      continue;
    }
    // One fewest-darts record per start score, the shortest game first.
    Object.keys(attributes)
      .map((item) => /^fewest_darts_(\d+)$/.exec(item))
      .filter((match) => match && value(match[0]) !== null)
      .map((match) => ({ record: match[0], name, kind, value: value(match[0]), game: Number(match[1]) }))
      .sort((a, b) => a.game - b.game)
      .forEach((record) => records.push(record));
  }
  const longest = finite(streak?.attributes?.best_streak);
  if (longest > 0) records.push({ record: "best_streak", name: "best_streak", kind: "days", value: longest });
  return records;
}

function bestsHtml(records, ui) {
  const { t, format } = ui;
  const shown = (record) => {
    if (record.kind === "mpr") return format(record.value, 2);
    if (record.kind === "average") return format(record.value, 1);
    if (record.kind === "count") return format(record.value, 0);
    const key = { darts: "unit_darts", points: "unit_points" }[record.kind] ?? (record.value === 1 ? "unit_day" : "unit_days");
    return fill(t(key), { value: format(record.value, 0) });
  };
  return records
    .map(
      (record) =>
        `<div><dt>${escapeHtml(fill(t(record.name), { game: record.game }))}</dt>` +
        `<dd data-record="${escapeHtml(record.record)}">${escapeHtml(shown(record))}</dd></div>`
    )
    .join("");
}

// Games ----------------------------------------------------------------------

// The darts a game counted in the current visit, by bed name.
const gameVisit = (attributes) =>
  (Array.isArray(attributes.visit) ? attributes.visit : []).filter((key) => typeof key === "string");

// The practice leg of the remaining-score sensor, or null without a game.
function practiceView(state) {
  if (!usable(state)) return null;
  const remaining = Number(state.state);
  if (!Number.isInteger(remaining) || remaining < 0) return null;
  const attributes = state.attributes || {};
  const route = typeof attributes.checkout === "string" ? attributes.checkout.split(/\s+/) : [];
  const scores = (Array.isArray(attributes.scores) ? attributes.scores : [])
    .filter((score) => score && Number.isInteger(score.player) && Number.isInteger(score.remaining))
    .map((score) => ({
      player: score.player,
      name: named(score.name),
      remaining: score.remaining,
      legs: finite(score.legs) ?? 0,
      sets: finite(score.sets) ?? 0,
      average: finite(score.average),
    }));
  return {
    game: finite(attributes.game),
    remaining,
    route: route.filter((bed) => hitBeds(bed).length),
    bust: attributes.bust === true,
    won: attributes.won === true,
    darts: finite(attributes.darts) ?? 0,
    average: finite(attributes.average),
    player: finite(attributes.player) ?? 1,
    name: named(attributes.name),
    winner: finite(attributes.winner),
    legsToWin: finite(attributes.legs_to_win) ?? 1,
    setsToWin: finite(attributes.sets_to_win) ?? 1,
    // Without double in, every player is in from the first dart.
    opened: attributes.opened !== false,
    doubleOut: attributes.double_out !== false,
    visit: gameVisit(attributes),
    scores,
  };
}

// The highest score that ends a leg: two trebles 20 and the bull, or three trebles 20.
const highestCheckout = (practice) => (practice.doubleOut ? 170 : 180);

const DRILLS = ["around_the_clock", "doubles", "checkout", "bobs_27"];

// The training game of the target sensor; a finished game has no target.
function drillView(state) {
  const attributes = state?.attributes || {};
  if (!state || state.state === "unavailable" || !DRILLS.includes(attributes.drill)) return null;
  const route = typeof attributes.checkout === "string" ? attributes.checkout.split(/\s+/) : [];
  return {
    kind: attributes.drill,
    target: usable(state) ? String(state.state) : null,
    finished: attributes.finished === true,
    progress: finite(attributes.progress) ?? 0,
    targets: finite(attributes.targets) ?? 21,
    darts: finite(attributes.darts) ?? 0,
    hitRate: finite(attributes.hit_rate),
    score: finite(attributes.score),
    remaining: finite(attributes.remaining),
    route: route.filter((bed) => hitBeds(bed).length),
    bust: attributes.bust === true,
    won: attributes.won === true,
    visit: finite(attributes.attempt_visit),
    visits: finite(attributes.attempt_visits),
    attempts: finite(attributes.attempts) ?? 0,
    successes: finite(attributes.successes) ?? 0,
    rate: finite(attributes.rate),
    completed: Array.isArray(attributes.results) ? attributes.results[0]?.completed === true : false,
  };
}

// Beds to aim at in a training game: every bed of the number in Around the Clock.
function drillBeds(drill) {
  if (!drill || drill.finished) return [];
  if (drill.kind === "checkout") return hitBeds(drill.route[0] ?? "");
  const target = drill.target ?? "";
  if (drill.kind !== "around_the_clock") return hitBeds(target);
  if (target === "BULL") return [...hitBeds("BULL"), ...hitBeds("25")];
  return ["S", "T", "D"].flatMap((bed) => hitBeds(`${bed}${target}`));
}

const CRICKET_NUMBERS = [20, 19, 18, 17, 16, 15, 25];
// No mark, one, two, and a closed number, as on a Cricket chalkboard.
const CRICKET_MARKS = ["", "/", "X", "Ⓧ"];

// The Cricket leg of the remaining-score sensor, which has no state then.
function cricketView(state) {
  const attributes = state?.attributes || {};
  if (!state || state.state === "unavailable" || attributes.game !== "cricket") return null;
  const numbers =
    Array.isArray(attributes.numbers) &&
    attributes.numbers.length === CRICKET_NUMBERS.length &&
    attributes.numbers.every(Number.isInteger)
      ? attributes.numbers
      : CRICKET_NUMBERS;
  const scores = (Array.isArray(attributes.scores) ? attributes.scores : [])
    .filter(
      (score) =>
        score && Number.isInteger(score.player) && Array.isArray(score.marks) && score.marks.length === numbers.length
    )
    .map((score) => ({
      player: score.player,
      name: named(score.name),
      marks: score.marks.map((mark) => (Number.isInteger(mark) ? Math.min(Math.max(mark, 0), 3) : 0)),
      points: finite(score.points) ?? 0,
      legs: finite(score.legs) ?? 0,
      sets: finite(score.sets) ?? 0,
      mpr: finite(score.mpr),
    }));
  return {
    numbers,
    target: typeof attributes.target === "string" && hitBeds(attributes.target).length ? attributes.target : null,
    won: attributes.won === true,
    darts: finite(attributes.darts) ?? 0,
    points: finite(attributes.points) ?? 0,
    mpr: finite(attributes.mpr),
    player: finite(attributes.player) ?? 1,
    name: named(attributes.name),
    winner: finite(attributes.winner),
    legsToWin: finite(attributes.legs_to_win) ?? 1,
    setsToWin: finite(attributes.sets_to_win) ?? 1,
    visit: gameVisit(attributes),
    scores,
  };
}

// Beds to aim at in Cricket: the treble of the next open number, or the whole bull.
function cricketBeds(cricket) {
  if (!cricket || cricket.won || cricket.winner !== null || !cricket.target) return [];
  if (cricket.target === "BULL") return [...hitBeds("BULL"), ...hitBeds("25")];
  return hitBeds(cricket.target);
}

const PARTY_GAMES = ["shanghai", "halve_it", "killer"];
const BOARD_NUMBERS = Array.from({ length: 20 }, (_, index) => index + 1);

// A party game of the remaining-score sensor, which has no state then.
function partyView(state) {
  const attributes = state?.attributes || {};
  if (!state || state.state === "unavailable" || !PARTY_GAMES.includes(attributes.game)) return null;
  const scores = (Array.isArray(attributes.scores) ? attributes.scores : [])
    .filter((score) => score && Number.isInteger(score.player))
    .map((score) => ({
      player: score.player,
      name: named(score.name),
      points: finite(score.points) ?? 0,
      legs: finite(score.legs) ?? 0,
      sets: finite(score.sets) ?? 0,
      number: Number.isInteger(score.number) ? score.number : null,
      lives: Number.isInteger(score.lives) ? score.lives : null,
      killer: score.killer === true,
    }));
  return {
    kind: attributes.game,
    round: finite(attributes.round),
    rounds: finite(attributes.rounds),
    target: typeof attributes.target === "string" && attributes.target ? attributes.target : null,
    phase: attributes.phase === "choose" ? "choose" : "play",
    needsPlayers: finite(attributes.needs_players),
    points: finite(attributes.points) ?? 0,
    won: attributes.won === true,
    darts: finite(attributes.darts) ?? 0,
    player: finite(attributes.player) ?? 1,
    name: named(attributes.name),
    winner: finite(attributes.winner),
    legsToWin: finite(attributes.legs_to_win) ?? 1,
    setsToWin: finite(attributes.sets_to_win) ?? 1,
    visit: gameVisit(attributes),
    scores,
  };
}

// The bull-off before a match, while it runs.
function bullOffView(state) {
  const bullOff = state?.attributes?.bull_off;
  if (!state || state.state === "unavailable" || !bullOff || typeof bullOff !== "object") return null;
  return {
    player: Number.isInteger(bullOff.player) ? bullOff.player : 1,
    name: named(bullOff.name),
    throws: (Array.isArray(bullOff.throws) ? bullOff.throws : [])
      .filter((item) => item && Number.isInteger(item.player))
      .map((item) => ({ player: item.player, name: named(item.name), distance: finite(item.distance) })),
  };
}

// Beds of a target: a number, any double (with the bull) or treble, or the whole bull.
function targetBeds(target) {
  if (!target) return [];
  if (target === "BULL") return [...hitBeds("BULL"), ...hitBeds("25")];
  if (target === "D") return [...BOARD_NUMBERS.flatMap((n) => hitBeds(`D${n}`)), ...hitBeds("BULL")];
  if (target === "T") return BOARD_NUMBERS.flatMap((n) => hitBeds(`T${n}`));
  return ["S", "T", "D"].flatMap((bed) => hitBeds(`${bed}${target}`));
}

// Beds to aim at in a party game: a number, any double or treble, the bull, or
// the doubles a killer hunts.
function partyBeds(party) {
  if (!party || party.won || party.winner !== null || party.needsPlayers) return [];
  if (party.kind === "killer") {
    if (party.phase === "choose") return [];
    if (party.target) return hitBeds(party.target);
    return party.scores
      .filter((score) => score.player !== party.player && score.lives > 0 && score.number)
      .flatMap((score) => hitBeds(`D${score.number}`));
  }
  return targetBeds(party.target);
}

// How a target reads: "Any double" for D, "Bull" for BULL, D7 for D7.
function targetText(ui, target) {
  if (target === "D") return ui.t("any_double");
  if (target === "T") return ui.t("any_treble");
  return ui.label(target);
}

const hearts = (lives) => (lives > 0 ? "♥".repeat(lives) : "✕");

// What the board shows: a training game, a bull-off, Cricket, a party game, X01, or none.
function gameView(stateOf) {
  const drill = drillView(stateOf("drill"));
  if (drill) return { mode: "drill", drill };
  const bullOff = bullOffView(stateOf("practice"));
  if (bullOff) return { mode: "bulloff", bullOff };
  const cricket = cricketView(stateOf("practice"));
  if (cricket) return { mode: "cricket", cricket };
  const party = partyView(stateOf("practice"));
  if (party) return { mode: "party", party };
  const practice = practiceView(stateOf("practice"));
  if (practice) return { mode: "x01", practice };
  return { mode: "idle" };
}

// Beds to aim at next, outlined on the live board.
function aimBeds(view) {
  const { mode, practice } = view;
  if (mode === "drill") return drillBeds(view.drill);
  if (mode === "bulloff") return [...hitBeds("BULL"), ...hitBeds("25")];
  if (mode === "cricket") return cricketBeds(view.cricket);
  if (mode === "party") return partyBeds(view.party);
  if (mode !== "x01" || practice.winner !== null) return [];
  // Before double in, every double opens the leg.
  if (!practice.opened) return targetBeds("D");
  return practice.won ? [] : hitBeds(practice.route[0] ?? "");
}

// Scoreboard -----------------------------------------------------------------

// Players without a name are numbered in a match; alone, nobody needs a name.
const playerName = (ui, score, match) =>
  score.name || (match ? `${ui.t("score_player")} ${score.player}` : "");

const note = (text, kind = "") => `<span class="note${kind ? ` ${kind}` : ""}">${escapeHtml(text)}</span>`;

const bedChips = (ui, route) =>
  route.map((bed) => `<span class="bed">${escapeHtml(ui.label(bed))}</span>`).join("");

// Legs and sets of a player, where the match has them.
const matchScore = (game, score, t) => [
  game.legsToWin > 1 ? `${t("score_legs")} ${score.legs}` : "",
  game.setsToWin > 1 ? `${t("score_sets")} ${score.sets}` : "",
];

// What the player at the board needs in X01: the route, a bust or the game shot.
function x01Note(practice, ui) {
  const { t } = ui;
  if (practice.won) return note(t("game_shot"), "won");
  if (practice.bust) return note(t("bust"), "bust");
  if (practice.route.length) return bedChips(ui, practice.route);
  if (!practice.opened) return note(t("double_in_needed"));
  // Single out finishes up to 180; double out only up to 170.
  return practice.remaining <= highestCheckout(practice) ? note(t("no_checkout")) : "";
}

// A player of the scoreboard and of the live card's match list.
function x01Players(practice, ui) {
  const { t, format } = ui;
  const scores = practice.scores.length
    ? practice.scores
    : [{ player: 1, name: practice.name, remaining: practice.remaining, legs: 0, sets: 0, average: null }];
  const match = scores.length > 1;
  return scores.map((score) => {
    const active = practice.winner === null && score.player === practice.player;
    return {
      name: playerName(ui, score, match),
      value: String(score.remaining),
      state: practice.winner === score.player ? "winner" : active && match ? "active" : "",
      note: active ? x01Note(practice, ui) : "",
      details: match
        ? [...matchScore(practice, score, t), score.average === null ? "" : `Ø ${format(score.average, 1)}`]
        : [
            practice.darts ? `${practice.darts} ${t("leg_darts")}` : "",
            practice.average === null ? "" : `Ø ${format(practice.average, 1)}`,
          ],
    };
  });
}

// What the player at the board aims at in a party game.
function partyNote(party, ui) {
  const { t } = ui;
  const killer = party.kind === "killer";
  const current = party.scores.find((score) => score.player === party.player);
  if (party.won) return note(t("game_shot"), "won");
  if (party.needsPlayers) return note(t("needs_players"));
  if (killer && party.phase === "choose") return note(t("killer_choose"));
  if (party.target) return `<span class="bed">${escapeHtml(targetText(ui, party.target))}</span>`;
  if (killer && current?.killer) return note(t("killer_hunt"));
  return "";
}

function partyPlayers(party, ui) {
  const { t } = ui;
  const match = party.scores.length > 1;
  const killer = party.kind === "killer";
  return party.scores.map((score) => {
    const active = party.winner === null && score.player === party.player;
    const out = killer && score.lives === 0;
    return {
      name: playerName(ui, score, match),
      value: killer ? hearts(score.lives ?? 0) : String(score.points),
      lives: killer,
      state: party.winner === score.player ? "winner" : active && match ? "active" : out ? "out" : "",
      note: active ? partyNote(party, ui) : "",
      details: [
        ...(match ? matchScore(party, score, t) : []),
        killer && score.number ? String(score.number) : "",
        killer && score.killer ? t("party_killer") : "",
        out ? t("out") : "",
      ],
    };
  });
}

function bullOffPlayers(bullOff, ui) {
  const match = bullOff.throws.length > 1;
  return bullOff.throws.map((item) => ({
    name: playerName(ui, item, match),
    value: item.distance === null ? "–" : `${ui.format(item.distance, 0)} mm`,
    state: item.player === bullOff.player ? "active" : "",
    note: "",
    details: [],
  }));
}

// Players as large tiles on the scoreboard.
function playerTiles(players) {
  const tiles = players.map(
    (player) =>
      `<div class="player${player.state ? ` ${player.state}` : ""}"><div class="name">${escapeHtml(player.name)}</div>` +
      `<div class="big${player.lives ? " lives" : ""}">${escapeHtml(player.value)}</div>` +
      `<div class="route">${player.note}</div>` +
      `<div class="details">${escapeHtml(player.details.filter(Boolean).join(" · "))}</div></div>`
  );
  return `<div class="players n${Math.max(players.length, 1)}">${tiles.join("")}</div>`;
}

// Players as rows in the live card.
const playerRows = (players) =>
  players
    .map(
      (player) =>
        `<div class="player-score${player.state ? ` ${player.state}` : ""}">` +
        `<span class="who">${escapeHtml(player.name)}</span>` +
        `<span class="muted">${escapeHtml(player.details.filter(Boolean).join(" · "))}</span>` +
        `<span class="rest${player.lives ? " lives" : ""}">${escapeHtml(player.value)}</span></div>`
    )
    .join("");

// The Cricket chalkboard: marks, points, marks per round, legs and sets. The
// scoreboard shows the next number in its corner; the live card has it beside.
function cricketTable(cricket, ui, { aim = true } = {}) {
  const { t, format } = ui;
  const match = cricket.scores.length > 1;
  const column = (score) =>
    cricket.winner === score.player
      ? "winner"
      : match && cricket.winner === null && cricket.player === score.player
        ? "active"
        : "";
  const row = (kind, heading, content) =>
    `<tr class="${kind}"><th>${escapeHtml(heading)}</th>${cricket.scores
      .map((score) => `<td class="${column(score)}">${content(score)}</td>`)
      .join("")}</tr>`;
  const marks = (count) =>
    `<span role="img" aria-label="${escapeHtml(t(`mark_${count}`))}">${CRICKET_MARKS[count]}</span>`;
  const rows = cricket.numbers.map((number, slot) => {
    const bed = number === 25 ? "BULL" : `T${number}`;
    const kind = cricket.scores.every((score) => score.marks[slot] >= 3)
      ? "closed"
      : bed === cricket.target
        ? "target"
        : "";
    return row(kind, number === 25 ? "Bull" : String(number), (score) => marks(score.marks[slot]));
  });
  const text = (value) => (score) => escapeHtml(value(score));
  if (match) rows.push(row("total", t("cricket_points"), text((score) => String(score.points))));
  rows.push(row("detail", t("cricket_mpr"), text((score) => (score.mpr === null ? "–" : format(score.mpr, 2)))));
  if (match && cricket.legsToWin > 1) rows.push(row("detail", t("score_legs"), text((score) => String(score.legs))));
  if (match && cricket.setsToWin > 1) rows.push(row("detail", t("score_sets"), text((score) => String(score.sets))));
  const names = cricket.scores.map((score) => playerName(ui, score, match));
  const head = cricket.scores
    .map((score, index) => `<th class="${column(score)}">${escapeHtml(names[index])}</th>`)
    .join("");
  const next = aim && cricket.target && !cricket.won && cricket.winner === null ? bedChips(ui, [cricket.target]) : "";
  const shot = aim && cricket.won && cricket.winner === null ? note(t("game_shot"), "won") : "";
  const corner = shot || next;
  // The next number sits above the numbers, so the chalkboard fits a landscape screen.
  return (
    `<table class="cricket">${
      corner || names.some(Boolean) ? `<thead><tr><th class="aim">${corner}</th>${head}</tr></thead>` : ""
    }<tbody>${rows.join("")}</tbody></table>`
  );
}

// A training game: the target, what happened and the facts about the game.
// A fact reads "12 darts", or with its name first "Round 3 / 21".
function drillParts(drill, ui) {
  const { t, percent, label } = ui;
  const fact = (value, name = "", lead = false) => ({ value, name, lead });
  const big = drill.finished ? "✓" : label(drill.target ?? "–");
  if (drill.kind === "bobs_27") {
    const outcome = drill.completed
      ? note(fill(t("drill_bobs_done"), { points: drill.score }), "won")
      : note(t("drill_bobs_lost"), "bust");
    return {
      big,
      note: drill.finished ? outcome : "",
      facts: [
        fact(String(drill.score ?? "–"), t("drill_points")),
        fact(`${Math.min(drill.progress + 1, drill.targets)} / ${drill.targets}`, t("drill_round"), true),
      ],
    };
  }
  if (drill.kind === "checkout") {
    return {
      big: String(drill.remaining ?? drill.target ?? "–"),
      note: drill.won ? note(t("game_shot"), "won") : drill.bust ? note(t("bust"), "bust") : bedChips(ui, drill.route),
      facts: [
        fact(`${drill.visit ?? 1} / ${drill.visits ?? 3}`, t("drill_visit"), true),
        fact(`${drill.successes} / ${drill.attempts}`, t("drill_checked")),
        ...(drill.rate === null ? [] : [fact(percent(drill.rate))]),
      ],
    };
  }
  return {
    big,
    note: drill.finished ? note(fill(t("drill_done"), { darts: drill.darts }), "won") : "",
    facts: [
      fact(`${drill.progress} / ${drill.targets}`),
      fact(String(drill.darts), t("leg_darts")),
      fact(percent(drill.hitRate), t("drill_hits")),
    ],
  };
}

// Facts in large type, their values bold.
const factsHtml = (facts) =>
  facts
    .map(({ value, name, lead }) => {
      const bold = `<b>${escapeHtml(value)}</b>`;
      return `<span>${lead ? `${escapeHtml(name)} ${bold}` : `${bold} ${escapeHtml(name)}`}</span>`;
    })
    .join("");

// Facts in a line of text.
const factsText = (facts) =>
  facts.map(({ value, name, lead }) => (lead ? `${name} ${value}` : `${value} ${name}`).trim()).join(" · ");

function drillBoard(drill, ui) {
  const parts = drillParts(drill, ui);
  return (
    `<div class="single"><div class="big">${escapeHtml(parts.big)}</div><div class="route">${parts.note}</div>` +
    `<div class="facts">${factsHtml(parts.facts)}</div></div>`
  );
}

function idleBoard(stats, ui) {
  const { t, format } = ui;
  const fact = (value, name) => ({ value, name });
  const facts = [
    fact(format(stats.darts, 0), t("darts")),
    fact(format(stats.average, 1), t("average")),
    fact(format(stats.highest, 0), t("highest")),
    fact(format(stats.max, 0), t("max")),
  ];
  if (stats.streak > 0) facts.push(fact(format(stats.streak, 0), t(stats.streak === 1 ? "streak_day" : "streak_days")));
  if (stats.today !== null && stats.today !== undefined) {
    facts.push(
      fact(stats.goal ? `${format(stats.today, 0)} / ${format(stats.goal, 0)}` : format(stats.today, 0), t("darts_today"))
    );
  }
  return (
    `<div class="single"><div class="label">${escapeHtml(t("visit"))}</div>` +
    `<div class="big">${escapeHtml(stats.visit ?? "–")}</div><div class="facts">${factsHtml(facts)}</div></div>`
  );
}

// Legs per set and sets to win of a match.
const matchFormat = (game, t) =>
  game.scores.length > 1
    ? [
        game.legsToWin > 1 ? `${game.legsToWin} ${t("legs_per_set")}` : "",
        game.setsToWin > 1 ? `${game.setsToWin} ${t("sets_to_win")}` : "",
      ]
    : [];

// Title, format, winner banner and main markup of the scoreboard.
function scoreboardHtml(view, ui) {
  const { t } = ui;
  if (view.mode === "drill") {
    return { title: t(`drill_${view.drill.kind}`), meta: "", banner: "", main: drillBoard(view.drill, ui) };
  }
  if (view.mode === "idle") {
    return { title: ui.name, meta: t("training"), banner: "", main: idleBoard(ui.stats, ui) };
  }
  if (view.mode === "bulloff") {
    return {
      title: t("bull_off"),
      meta: t("bull_off_hint"),
      banner: "",
      main: playerTiles(bullOffPlayers(view.bullOff, ui)),
    };
  }
  const game = { cricket: view.cricket, party: view.party }[view.mode] ?? view.practice;
  const winner = game.scores.find((score) => score.player === game.winner);
  const round = view.mode === "party" && game.rounds ? `${t("drill_round")} ${game.round}/${game.rounds}` : "";
  const main = {
    cricket: () => cricketTable(game, ui),
    party: () => playerTiles(partyPlayers(game, ui)),
    x01: () => playerTiles(x01Players(game, ui)),
  }[view.mode]();
  return {
    title: { cricket: t("cricket"), party: view.party ? t(`party_${view.party.kind}`) : "" }[view.mode] ??
      `${t("practice")} ${game.game ?? ""}`.trim(),
    meta: [round, ...matchFormat(game, t)].filter(Boolean).join(" · "),
    banner: winner ? `${playerName(ui, winner, true)} ${t("score_winner")}` : "",
    main,
  };
}

// Players -------------------------------------------------------------------

// Profiles, head-to-head records and recent matches from their two sensors.
function playersView(profiles, lastMatch) {
  const players = (Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : [])
    .filter((player) => player && named(player.name))
    .map((player) => ({
      name: player.name,
      legsPlayed: finite(player.legs_played) ?? 0,
      legsWon: finite(player.legs_won) ?? 0,
      matchesPlayed: finite(player.matches_played) ?? 0,
      matchesWon: finite(player.matches_won) ?? 0,
      average: finite(player.average),
      first9: finite(player.first_9_average),
      checkoutRate: finite(player.checkout_rate),
      mpr: finite(player.mpr),
      bestMpr: finite(player.best_mpr),
      highestVisit: finite(player.highest_visit),
      highestCheckout: finite(player.highest_checkout),
      fewestDarts: Object.entries(
        player.fewest_darts && typeof player.fewest_darts === "object" ? player.fewest_darts : {}
      )
        .filter(([game, darts]) => /^\d+$/.test(game) && Number.isInteger(darts))
        .map(([game, darts]) => ({ game: Number(game), darts }))
        .sort((a, b) => a.game - b.game),
    }));
  const attributes = lastMatch?.attributes || {};
  const headToHead = (Array.isArray(attributes.head_to_head) ? attributes.head_to_head : []).filter(
    (item) =>
      item &&
      Array.isArray(item.players) &&
      item.players.length === 2 &&
      Array.isArray(item.wins) &&
      item.wins.length === 2 &&
      item.wins.every(Number.isInteger)
  );
  const matches = (Array.isArray(attributes.matches) ? attributes.matches : [])
    .filter((match) => match && typeof match.ended === "string" && Array.isArray(match.players))
    .map((match) => ({
      ended: match.ended,
      game: match.game,
      winner: finite(match.winner),
      players: match.players.filter((player) => player && typeof player === "object"),
    }));
  return { players, headToHead, matches };
}

// A game as players call it: 501, Cricket, Killer.
function gameName(t, game) {
  if (Number.isInteger(game)) return String(game);
  if (game === "cricket") return t("cricket");
  if (PARTY_GAMES.includes(game)) return t(`party_${game}`);
  return String(game ?? "");
}

function playersHtml(view, ui) {
  const { t, format, percent, date } = ui;
  const value = (number, digits = 0) => (number === null ? "–" : format(number, digits));
  const players = view.players
    .map((player) => {
      const rows = [
        [t("average"), value(player.average, 1)],
        [t("first_9"), value(player.first9, 1)],
        [t("checkout_short"), percent(player.checkoutRate, 1)],
        ...(player.mpr === null ? [] : [[t("cricket_mpr"), value(player.mpr, 2)]]),
        ...(player.bestMpr === null ? [] : [[t("best_mpr"), value(player.bestMpr, 2)]]),
        [t("highest"), value(player.highestVisit)],
        [t("highest_checkout"), value(player.highestCheckout)],
        ...player.fewestDarts.map((best) => [
          fill(t("best_leg"), { game: best.game }),
          fill(t("unit_darts"), { value: best.darts }),
        ]),
      ];
      return (
        `<div class="profile"><div class="profile-name">${escapeHtml(player.name)}</div>` +
        `<div class="muted">${escapeHtml(
          `${t("profile_legs")} ${player.legsWon}/${player.legsPlayed} · ` +
            `${t("profile_matches")} ${player.matchesWon}/${player.matchesPlayed}`
        )}</div><dl>${rows
          .map(([name, shown]) => `<dt>${escapeHtml(name)}</dt><dd>${escapeHtml(shown)}</dd>`)
          .join("")}</dl></div>`
      );
    })
    .join("");
  const headToHead = view.headToHead
    .map((item) => {
      const total = item.wins[0] + item.wins[1];
      const share = total ? Math.round((item.wins[0] * 100) / total) : 50;
      return (
        `<div class="versus"><span class="who">${escapeHtml(item.players[0])}</span>` +
        `<span class="tally">${item.wins[0]} : ${item.wins[1]}</span>` +
        `<span class="who right">${escapeHtml(item.players[1])}</span>` +
        `<div class="balance"><i style="width:${share}%"></i></div></div>`
      );
    })
    .join("");
  const matches = view.matches
    .map((match) => {
      const players = match.players
        .map((player, index) => {
          const shown = `${player.name || `${t("score_player")} ${index + 1}`} ${player.sets || player.legs || 0}`;
          const tag = index + 1 === match.winner ? "b" : "span";
          return `<${tag}>${escapeHtml(shown)}</${tag}>`;
        })
        .join(" · ");
      return (
        `<div class="match"><span class="muted">${escapeHtml(date(match.ended))}</span>` +
        `<span class="game">${escapeHtml(gameName(t, match.game))}</span><span>${players}</span></div>`
      );
    })
    .join("");
  return { players, headToHead, matches };
}

// Doubles --------------------------------------------------------------------

const DOUBLE_ORDER = [...BOARD_NUMBERS.map((number) => `D${number}`), "BULL"];

function doubleCounts(source) {
  const doubles = (Array.isArray(source?.doubles) ? source.doubles : [])
    .filter(
      (item) =>
        item &&
        DOUBLE_ORDER.includes(item.double) &&
        Number.isInteger(item.attempts) &&
        Number.isInteger(item.hits) &&
        item.attempts > 0
    )
    .map((item) => ({
      double: item.double,
      attempts: item.attempts,
      hits: item.hits,
      rate: finite(item.rate) ?? Math.round((item.hits * 1000) / item.attempts) / 10,
    }));
  return {
    attempts: finite(source?.attempts) ?? 0,
    hits: finite(source?.hits) ?? 0,
    rate: finite(source?.rate),
    favourite: typeof source?.favourite === "string" ? source.favourite : null,
    doubles,
  };
}

// Names of every player profile, for the player picker of the doubles card.
function profileNames(hass) {
  const names = new Set();
  for (const id of Object.values(hass?.entities || {})) {
    if (id.platform !== "autodarts" || id.translation_key !== "player_profiles") continue;
    const players = hass.states?.[id.entity_id]?.attributes?.players;
    for (const player of Array.isArray(players) ? players : []) if (named(player?.name)) names.add(player.name);
  }
  return [...names].sort((a, b) => a.localeCompare(b));
}

// Everybody's doubles, or one player's from the profiles.
function doublesView(doubles, profiles, player = "") {
  const wanted = String(player || "").trim().toLowerCase();
  if (wanted) {
    const profile = (Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : []).find(
      (item) => typeof item?.name === "string" && item.name.trim().toLowerCase() === wanted
    );
    return { player: profile?.name ?? player, known: Boolean(profile), ...doubleCounts(profile?.doubles) };
  }
  const attributes = doubles?.attributes || {};
  const favourite = usable(doubles) ? doubles.state : null;
  return { player: null, known: true, ...doubleCounts({ ...attributes, favourite }) };
}

// Red for rarely hit doubles, green from about one hit in two.
function doubleColor(rate) {
  const hue = Math.round(Math.min(Math.max(rate, 0), 50) * 2.6);
  return `hsl(${hue} 70% 46%)`;
}

function doublesHtml(view, ui) {
  const { format, percent, label } = ui;
  // Every double of the list is a bed of the board.
  const ring = view.doubles
    .map(
      (item) =>
        `<path d="${bedPath(hitBeds(item.double)[0])}" style="fill:${doubleColor(item.rate)}"><title>${escapeHtml(
          `${label(item.double)}: ${item.hits}/${item.attempts}`
        )}</title></path>`
    )
    .join("");
  const list = [...view.doubles]
    .sort((a, b) => b.rate - a.rate || b.attempts - a.attempts)
    .map(
      (item) =>
        `<div class="double${item.double === view.favourite ? " favourite" : ""}">` +
        `<span class="bed" style="--c:${doubleColor(item.rate)}">${escapeHtml(label(item.double))}</span>` +
        `<span class="bar"><i style="width:${Math.min(item.rate, 100)}%;background:${doubleColor(item.rate)}"></i></span>` +
        `<span class="count">${escapeHtml(`${format(item.hits, 0)}/${format(item.attempts, 0)}`)}</span>` +
        `<span class="rate">${escapeHtml(percent(item.rate, 0))}</span></div>`
    )
    .join("");
  return { ring, list };
}

// Caller ---------------------------------------------------------------------

// Marks of a Cricket dart: a treble is three, the outer bull one, the bull two.
function cricketMarks(key, numbers) {
  if (key === "BULL" || key === "25") return numbers.includes(25) ? (key === "BULL" ? 2 : 1) : 0;
  const match = /^([SDT])(\d{1,2})$/.exec(key);
  return match && numbers.includes(Number(match[2])) ? "SDT".indexOf(match[1]) + 1 : 0;
}

// What a finished visit counted: the X01 score, Cricket marks or party points.
// Null where nothing fits: busts and game shots have calls of their own, Killer
// and the training games count no points, and a visit joined halfway is unknown.
function visitCount(view, keys, start) {
  const points = (list) => list.reduce((sum, key) => sum + keyScore(key), 0);
  if (view.mode === "idle") return { kind: "score", score: points(keys) };
  if (view.mode === "x01") {
    const { practice } = view;
    if (practice.bust || practice.won || start === null) return null;
    // Darts before the opening double score nothing, so the remaining score tells.
    return { kind: "score", score: start - practice.remaining };
  }
  if (view.mode === "cricket" && !view.cricket.won) {
    return { kind: "marks", marks: keys.reduce((sum, key) => sum + cricketMarks(key, view.cricket.numbers), 0) };
  }
  if (view.mode === "party" && view.party.kind !== "killer" && !view.party.won) {
    const aim = new Set(targetBeds(view.party.target));
    return { kind: "score", score: points(keys.filter((key) => hitBeds(key).some((bed) => aim.has(bed)))) };
  }
  return null;
}

// What the caller listens to: the darts a game counted, or the visit on the board between games.
function callerState(visit, view, previous = null) {
  const current = view ?? { mode: "idle" };
  const game = current.practice ?? current.cricket ?? current.party ?? null;
  const winner = game?.scores?.find((score) => score.player === game.winner);
  // Darts after a bust or a game shot are not among the darts of the game.
  const keys = game ? game.visit : current.mode === "idle" ? visitThrows(visit).map(dartKey) : [];
  const remaining = current.practice?.remaining ?? null;
  const player = game?.player ?? null;
  // The remaining score before the visit, which the visit's score is counted from.
  const start = !keys.length
    ? remaining
    : previous?.mode === current.mode && previous?.player === player
      ? previous.start
      : null;
  return {
    darts: keys.length,
    visit: keys.join(" "),
    count: visitCount(current, keys, start),
    mode: current.mode,
    player,
    name: game?.name ?? null,
    players: game?.scores?.length ?? 0,
    remaining,
    start,
    route: current.practice?.route ?? [],
    bust: game?.bust === true,
    won: game?.won === true,
    winner: game?.winner ?? null,
    winnerName: winner?.name ?? null,
  };
}

// The calls between two states: a visit, a requirement, a bust or a game shot.
function callerCalls(previous, current, options) {
  if (!previous) return [];
  const calls = [];
  const on = (key) => options[key] !== false;
  const finished = current.darts === 3 && (previous.darts !== 3 || previous.visit !== current.visit);
  if (on("call_scores") && finished && current.count) {
    calls.push({ ...current.count });
    if (current.count.score === 180 && on("call_sounds")) calls.push({ kind: "fanfare" });
  }
  if (on("call_results") && current.bust && !previous.bust) calls.push({ kind: "bust" });
  if (on("call_results") && current.winner !== null && previous.winner === null) {
    calls.push({ kind: "match", name: current.winnerName });
  } else if (on("call_results") && current.won && !previous.won && current.winner === null) {
    calls.push({ kind: "leg" });
  }
  const turn =
    current.player !== previous.player || current.remaining !== previous.remaining || previous.darts > 0;
  // The route exists only for a score the darts of a visit can finish.
  if (
    on("call_checkouts") &&
    current.mode === "x01" &&
    current.darts === 0 &&
    turn &&
    current.winner === null &&
    current.route.length &&
    current.remaining !== null
  ) {
    calls.push({
      kind: "require",
      name: current.name,
      player: current.player,
      players: current.players,
      remaining: current.remaining,
    });
  }
  return calls;
}

// A call as the caller says it.
function callerText(call, t) {
  if (call.kind === "score") return call.score === 0 ? t("say_no_score") : String(call.score);
  if (call.kind === "marks") {
    if (call.marks === 0) return t("say_no_score");
    return call.marks === 1 ? t("say_mark") : fill(t("say_marks"), { marks: call.marks });
  }
  if (call.kind === "bust") return t("say_bust");
  if (call.kind === "leg") return t("say_leg");
  if (call.kind === "match") return fill(t("say_match"), { name: call.name }).replace(", !", "!");
  if (call.kind === "require") {
    // Alone, nobody needs a name; in a match, unnamed players have a number.
    const name = call.players > 1 ? call.name || `${t("score_player")} ${call.player}` : null;
    return name
      ? fill(t("say_require"), { name, remaining: call.remaining })
      : fill(t("say_require_alone"), { remaining: call.remaining });
  }
  return "";
}

// One audio context for every card; browsers allow sound only after a tap.
const callerAudio = { unlocked: false, context: null };

function playFanfare() {
  const context = callerAudio.context;
  if (!context) return;
  const start = context.currentTime;
  [523.25, 659.25, 783.99, 1046.5].forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "triangle";
    oscillator.frequency.value = frequency;
    const at = start + index * 0.14;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + (index === 3 ? 0.9 : 0.3));
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(at);
    oscillator.stop(at + 1);
  });
}

// Board status shared by the live and status cards.
function boardStatus(stateOf) {
  const on = (name) => stateOf(name)?.state === "on";
  const connected = stateOf("connected");
  const detection = stateOf("detection")?.state;
  const status = String(stateOf("status")?.state || "").toLowerCase();
  if (!connected || connected.state !== "on") return ["offline", "status_offline"];
  if (on("calibrating") || status === "calibrating") return ["calibrating", "status_calibrating"];
  if (on("cameraProblem")) return ["problem", "status_problem"];
  if (status === "starting") return ["stopped", "status_starting"];
  if (status === "stopping") return ["stopped", "status_stopping"];
  if (detection === "off" || status === "stopped") return ["stopped", "status_stopped"];
  if (status.includes("takeout") || on("takeoutPartial")) return ["takeout", "status_takeout"];
  if (on("hand")) return ["takeout", "status_hand"];
  if (Number(stateOf("numThrows")?.state) >= 3) return ["takeout", "status_full"];
  return ["ready", "status_ready"];
}

// Whether detection runs: the detection switch tells, or without it the board status.
function detectionRunning(stateOf, status) {
  const detection = stateOf("detection");
  return detection ? detection.state === "on" : !["stopped", "offline"].includes(status);
}

// Dashboard strategy -------------------------------------------------------

const SETTING_KEYS = [
  "switch.auto_calibrate_on_start",
  "switch.auto_calibrate",
  "switch.auto_distortion",
  "select.standby_minutes",
];

const PRACTICE_KEYS = [
  "select.practice_game",
  "number.practice_players",
  "number.practice_legs",
  "number.practice_sets",
  "switch.practice_double_out",
  "switch.practice_double_in",
  "switch.practice_bull_off",
  "switch.practice_personal_routes",
  "button.practice_new_leg",
  "button.practice_new_match",
];

// An entity's name without its board and without the section it sits in, so
// "Autodarts Board Practice players" reads "Players" under "Practice".
function rowName(hass, entityId, prefixes) {
  let name = hass?.states?.[entityId]?.attributes?.friendly_name;
  if (typeof name !== "string") return null;
  for (const prefix of prefixes) {
    if (prefix && name.toLowerCase().startsWith(`${prefix.toLowerCase()} `)) name = name.slice(prefix.length + 1);
  }
  name = name.trim();
  return name ? name[0].toUpperCase() + name.slice(1) : null;
}

// What the views of one board share: its entities, their rows and the view names.
function boardContext(hass, t, deviceId, number, count) {
  const index = entityIndex(hass, deviceId);
  const id = (key) => index[key]?.[0];
  const device = hass.devices?.[deviceId];
  const name = device?.name_by_user || device?.name || "Autodarts";
  // Rows and graphs name their entities briefly, the board is the view's.
  const row = (entity, section) => {
    const text = rowName(hass, entity, [name, section]);
    if (!text) return entity;
    // The game select is the practice section itself.
    return { entity, name: section && text.toLowerCase() === section.toLowerCase() ? t("practice_game_row") : text };
  };
  return {
    t,
    index,
    id,
    row,
    rows: (keys, section) => keys.map(id).filter(Boolean).map((entity) => row(entity, section)),
    // Several boards get their own set of views.
    suffix: count > 1 ? ` · ${name}` : "",
    slug: count > 1 ? `-${number + 1}` : "",
    card: (type, options = {}) => ({ type: `custom:${type}`, device_id: deviceId, ...options }),
  };
}

const FULL = { grid_options: { columns: "full" } };
const tile = (row) => ({ type: "tile", ...(typeof row === "string" ? { entity: row } : row) });

function liveDashboardView(board) {
  const { t } = board;
  const practice = board.rows(PRACTICE_KEYS, t("practice"));
  const names = (board.index["text.practice_player"] ?? []).map((entity) => board.row(entity, t("practice")));
  const controls = [
    { type: "heading", heading: t("practice") },
    { type: "entities", entities: practice },
    ...(names.length ? [{ type: "entities", title: t("practice_names"), entities: names }] : []),
  ];
  return {
    title: `${t("view_live")}${board.suffix}`,
    path: `live${board.slug}`,
    icon: "mdi:bullseye-arrow",
    type: "sections",
    max_columns: 2,
    sections: [
      { type: "grid", column_span: 2, cards: [board.card(CARD_TYPE, FULL)] },
      ...(practice.length ? [{ type: "grid", column_span: 2, cards: controls }] : []),
    ],
  };
}

// The scoreboard fills the screen of a tablet or TV at the board.
function scoreboardDashboardView(board) {
  return {
    title: `${board.t("view_scoreboard")}${board.suffix}`,
    path: `scoreboard${board.slug}`,
    icon: "mdi:scoreboard-outline",
    panel: true,
    cards: [board.card(SCOREBOARD_TYPE, { full_height: true })],
  };
}

// Goals, graphs of darts, averages and practice legs, and the training settings.
function trainingTrends(board) {
  const { t, id, rows } = board;
  const bars = (title, key) => ({
    type: "statistics-graph",
    title,
    entities: rows([key]),
    stat_types: ["change"],
    period: "day",
    chart_type: "bar",
    days_to_show: 30,
  });
  const week = (title, entities) => ({ type: "history-graph", title, entities, hours_to_show: 168 });
  const trends = [];
  const goals = rows(["number.training_daily_goal", "sensor.darts_today", "sensor.training_streak", "sensor.personal_best"]);
  if (goals.length) trends.push({ type: "entities", title: t("goals_and_bests"), entities: goals });
  if (id("sensor.training_darts")) trends.push(bars(t("darts_per_day"), "sensor.training_darts"));
  if (id("sensor.training_average")) trends.push(week(t("average_trend"), rows(["sensor.training_average"])));
  if (id("sensor.practice_legs_played")) trends.push(bars(t("practice_legs_per_day"), "sensor.practice_legs_played"));
  const practice = rows([
    "sensor.practice_first_9_average",
    "sensor.practice_checkout_rate",
    "sensor.practice_doubles_rate",
  ]);
  if (practice.length) trends.push(week(t("practice_trend"), practice));
  const settings = rows(["switch.training_auto_start", "number.training_idle_timeout"]);
  if (settings.length) trends.push({ type: "entities", title: t("training_settings"), entities: settings });
  return trends;
}

function trainingDashboardView(board) {
  const trends = trainingTrends(board);
  return {
    title: `${board.t("view_training")}${board.suffix}`,
    path: `training${board.slug}`,
    icon: "mdi:chart-box-outline",
    type: "sections",
    max_columns: 2,
    sections: [
      { type: "grid", column_span: 2, cards: [board.card(TRAINING_TYPE, FULL)] },
      ...(board.id("sensor.favourite_double")
        ? [{ type: "grid", column_span: 2, cards: [board.card(DOUBLES_TYPE, FULL)] }]
        : []),
      ...(trends.length ? [{ type: "grid", column_span: 2, cards: trends }] : []),
    ],
  };
}

function playersDashboardView(board) {
  if (!board.id("sensor.player_profiles")) return null;
  return {
    title: `${board.t("view_players")}${board.suffix}`,
    path: `players${board.slug}`,
    icon: "mdi:account-group",
    type: "sections",
    max_columns: 2,
    sections: [{ type: "grid", column_span: 2, cards: [board.card(PLAYERS_TYPE, FULL)] }],
  };
}

// The status card, the board settings, the software update and the detection quality.
function boardDashboardView(board) {
  const settings = board.rows(SETTING_KEYS);
  const maintenance = [{ type: "heading", heading: board.t("board_settings") }];
  if (settings.length) maintenance.push({ type: "entities", entities: settings });
  maintenance.push(...board.rows(["update.board_software", "sensor.correction_rate"]).map(tile));
  return {
    title: `${board.t("view_board")}${board.suffix}`,
    path: `board${board.slug}`,
    icon: "mdi:cog-outline",
    type: "sections",
    max_columns: 2,
    sections: [
      { type: "grid", cards: [board.card(STATUS_TYPE, FULL)] },
      ...(maintenance.length > 1 ? [{ type: "grid", cards: maintenance }] : []),
    ],
  };
}

// A complete dashboard for every board: live play, the scoreboard, training, players and maintenance.
function dashboardStrategy(hass, config = {}) {
  const t = (key) => translate(hass, key);
  const title = config.title || "Autodarts";
  // A board removed since the dashboard was set up must not leave views without entities.
  const devices = (config.device_id ? [config.device_id] : autodartsDevices(hass)).filter((id) =>
    knownDevice(hass, id)
  );
  if (!devices.length) {
    const content = t(config.device_id ? "strategy_board_missing" : "strategy_no_board");
    return { title, views: [{ title: "Autodarts", cards: [{ type: "markdown", content }] }] };
  }
  const views = devices.flatMap((deviceId, number) => {
    const board = boardContext(hass, t, deviceId, number, devices.length);
    return [
      liveDashboardView(board),
      scoreboardDashboardView(board),
      trainingDashboardView(board),
      playersDashboardView(board),
      boardDashboardView(board),
    ].filter(Boolean);
  });
  return { title, views };
}

// Editor forms ---------------------------------------------------------------

const deviceField = { name: "device_id", selector: { device: { filter: { integration: "autodarts" } } } };
const titleField = { name: "title", selector: { text: {} } };
const toggles = (names, defaults) => ({
  type: "grid",
  name: "",
  schema: names.map((name) => ({ name, selector: { boolean: {} }, default: defaults[name] })),
});
const dropdown = (name, prefix, values) => ({
  name,
  selector: {
    select: { mode: "dropdown", options: values.map((value) => ({ value, label: pageText(`${prefix}_${value}`) })) },
  },
});
// The colour picker of Home Assistant: theme colours, or any colour typed in.
const colorField = (name, defaultColor) => ({
  name,
  selector: { ui_color: defaultColor ? { default_color: defaultColor } : {} },
});
const accentField = colorField("accent_color", "primary");

const FORM_HELPERS = {
  device_id: "device_helper",
  player: "player_helper",
  accent_color: "color_helper",
  highlight_color: "highlight_color_helper",
  caller_options: "caller_options_helper",
};

// Every field of a form, also those inside grids and expandable sections.
const formFields = (schema) => schema.flatMap((field) => (field.schema ? formFields(field.schema) : [field]));

// The editor form of a card: its fields in the page language, labels and help,
// and a check that sends options the form cannot show to the code editor.
function cardForm(schema, defaults) {
  const fields = formFields(schema);
  const options = new Map(
    fields
      .filter((field) => field.selector.select && !field.selector.select.custom_value)
      .map((field) => [field.name, field.selector.select.options])
  );
  return {
    schema,
    computeLabel: (field) => (field.name ? pageText(field.name) : undefined),
    computeHelper: (field) => {
      if (FORM_HELPERS[field.name]) return pageText(FORM_HELPERS[field.name]);
      const standard = options.get(field.name)?.find((option) => option.value === defaults[field.name]);
      return standard ? fill(pageText("default_hint"), { value: standard.label }) : undefined;
    },
    assertConfig: (config) => {
      for (const field of fields) {
        const value = config?.[field.name];
        if (value === undefined || value === null || value === "") continue;
        const valid = options.has(field.name)
          ? options.get(field.name).some((option) => option.value === value)
          : field.selector.boolean
            ? typeof value === "boolean"
            : !field.selector.number || Number.isFinite(value);
        if (!valid) {
          throw new Error(fill(pageText("invalid_option"), { name: field.name, value: JSON.stringify(value) }));
        }
      }
    },
  };
}

const FORMS = {
  live: () => [
    deviceField,
    titleField,
    {
      type: "grid",
      name: "",
      schema: [
        dropdown("layout", "layout", ["auto", "horizontal", "vertical", "board"]),
        dropdown("board_style", "style", ["classic", "autodarts"]),
      ],
    },
    dropdown("highlight", "highlight", ["visit", "last", "none"]),
    toggles(
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
      DEFAULTS
    ),
    { type: "grid", name: "", schema: [accentField, colorField("highlight_color")] },
  ],
  training: () => [
    deviceField,
    titleField,
    {
      type: "grid",
      name: "",
      schema: [dropdown("mode", "mode", ["beds", "numbers"]), dropdown("board_style", "style", ["muted", "classic", "autodarts"])],
    },
    {
      name: "history_size",
      selector: { number: { min: 5, max: 60, step: 1, mode: "slider" } },
      default: TRAINING_DEFAULTS.history_size,
    },
    toggles(
      ["show_heatmap", "show_stats", "show_bests", "show_top", "show_history", "show_sessions", "show_reset"],
      TRAINING_DEFAULTS
    ),
    accentField,
  ],
  status: () => [
    deviceField,
    titleField,
    toggles(["show_connection", "show_system", "show_cameras", "show_controls"], STATUS_DEFAULTS),
    accentField,
  ],
  scoreboard: () => [
    deviceField,
    titleField,
    toggles(["full_height", "show_visit", "show_status", "caller"], SCOREBOARD_DEFAULTS),
    // The calls matter only with the caller on, so they wait in a closed section.
    {
      type: "expandable",
      name: "caller_options",
      flatten: true,
      schema: [toggles(["call_scores", "call_checkouts", "call_results", "call_sounds"], SCOREBOARD_DEFAULTS)],
    },
    accentField,
  ],
  players: () => [deviceField, titleField, toggles(["show_head_to_head", "show_matches"], PLAYERS_DEFAULTS), accentField],
  // Named players to pick from; any other name can be typed in.
  doubles: () => [
    deviceField,
    titleField,
    {
      name: "player",
      selector: {
        select: {
          mode: "dropdown",
          custom_value: true,
          options: profileNames(pageHass).map((name) => ({ value: name, label: name })),
        },
      },
    },
    accentField,
  ],
};

const STRATEGY_FORM = [deviceField, titleField];

// Styles ----------------------------------------------------------------------

// Coloured text is mixed with the theme's text colour: darker on light themes,
// lighter on dark ones, so it stays readable on both.
const BASE_CSS = `
  :host {
    display: block;
    --ad-ok-text: color-mix(in srgb, ${STATUS_COLORS.ready} 65%, var(--primary-text-color, #212121));
    --ad-error-text: color-mix(in srgb, ${STATUS_COLORS.problem} 75%, var(--primary-text-color, #212121));
    --ad-warn-text: color-mix(in srgb, ${STATUS_COLORS.takeout} 45%, var(--primary-text-color, #212121));
    --ad-gold-text: color-mix(in srgb, ${GOLD} 45%, var(--primary-text-color, #212121));
  }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; height: 100%; }
  .root { container-type: inline-size; height: 100%; }
  header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .title {
    font-size: 16px; font-weight: 600; color: var(--primary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .pill {
    display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0;
    padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;
    color: color-mix(in srgb, var(--ad-status) 45%, var(--primary-text-color, #212121));
    background: color-mix(in srgb, var(--ad-status) 14%, transparent);
    transition: color .4s, background .4s;
  }
  .pill::before {
    content: ""; width: 8px; height: 8px; border-radius: 50%;
    background: var(--ad-status); box-shadow: 0 0 8px var(--ad-status);
  }
  .section-label {
    font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    color: var(--ad-accent);
  }
  .muted { font-size: 11px; color: var(--secondary-text-color); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px;
    font: inherit; font-size: 12px; color: var(--secondary-text-color); cursor: pointer;
    border: 1px solid var(--divider-color, rgba(127,127,127,.25)); background: none;
  }
  .chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--chip, #9e9e9e); }
  .chip.on { --chip: ${STATUS_COLORS.ready}; }
  .chip.off { --chip: #9e9e9e; }
  .chip.alert { --chip: ${STATUS_COLORS.problem}; color: var(--ad-error-text); }
  .controls { display: flex; flex-wrap: wrap; gap: 8px; }
  .controls button, button.action {
    flex: 1 1 auto; min-height: 40px; padding: 0 14px; border-radius: 12px; cursor: pointer;
    font: inherit; font-size: 13px; font-weight: 600; color: var(--primary-text-color);
    border: 1px solid var(--divider-color, rgba(127,127,127,.3)); background: none;
    transition: background .2s, border-color .2s, color .2s;
  }
  :is(.controls button, button.action):hover { background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); }
  :is(.controls button, button.action).primary {
    color: var(--text-primary-color, #fff); background: var(--ad-accent); border-color: var(--ad-accent);
  }
  :is(.controls button, button.action).primary.stop { background: none; color: var(--ad-accent); }
  :is(.controls button, button.action).confirm {
    color: #fff; background: ${STATUS_COLORS.problem}; border-color: ${STATUS_COLORS.problem};
  }
  :is(.controls button, button.action):disabled { opacity: .45; cursor: default; }
  :is(button, [tabindex]):focus-visible { outline: 2px solid var(--ad-accent); outline-offset: 2px; }
  svg { display: block; width: 100%; height: 100%; overflow: visible; }
  .number {
    font-size: 22px; font-weight: 700; line-height: 1; text-anchor: middle; dominant-baseline: central;
    pointer-events: none;
  }
  .note { font-weight: 800; color: var(--secondary-text-color); }
  .note.won { color: var(--ad-ok-text); }
  .note.bust { color: var(--ad-error-text); }
  .message { padding: 18px; color: var(--secondary-text-color); }
`;

const CSS = `${BASE_CSS}
  .layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas: "header board" "visit board" "session board" "footer board";
    align-content: center;
    column-gap: 24px;
    row-gap: 16px;
    padding: 18px;
    box-sizing: border-box;
    height: 100%;
  }
  .layout.vertical {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: "header" "visit" "board" "session" "footer";
  }
  .layout.board-only { grid-template-columns: minmax(0, 1fr); grid-template-areas: "header" "board"; }
  .layout.board-only :is(.visit, .session, .footer) { display: none; }
  @container (max-width: 520px) {
    .layout.auto {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas: "header" "visit" "board" "session" "footer";
    }
  }
  header { grid-area: header; }
  .visit { grid-area: visit; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .session { grid-area: session; min-width: 0; }
  .footer { grid-area: footer; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .board { grid-area: board; align-self: center; }
  .visit-label {
    font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    color: var(--ad-accent);
  }
  .score-row { display: flex; align-items: baseline; gap: 10px; margin-top: 2px; }
  .score {
    font-size: clamp(48px, 16cqw, 84px); font-weight: 800; line-height: 1;
    letter-spacing: -0.04em; color: var(--primary-text-color); font-variant-numeric: tabular-nums;
  }
  .score-unit { font-size: 14px; color: var(--secondary-text-color); }
  .progress { margin-left: auto; font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; }
  .slots { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  .practice {
    display: grid; gap: 8px; padding: 10px 12px; border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--ad-accent) 45%, transparent);
    background: color-mix(in srgb, var(--ad-accent) 8%, transparent);
  }
  .practice-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .practice-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
  .practice-remaining {
    font-size: 34px; font-weight: 800; line-height: 1; letter-spacing: -0.03em;
    color: var(--primary-text-color); font-variant-numeric: tabular-nums;
  }
  .practice-route { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 13px; }
  .practice-route .bed {
    padding: 3px 9px; border-radius: 8px; font-weight: 700;
    color: var(--ad-accent); border: 1px solid var(--ad-accent);
  }
  .practice-route .bed:first-child { color: var(--text-primary-color, #fff); background: var(--ad-accent); }
  .practice-route .note { font-weight: 700; }
  .practice-route .note:not(.won, .bust) { font-size: 11px; font-weight: 400; }
  .scoreboard { display: grid; gap: 4px; }
  .player-score {
    display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: baseline;
    gap: 12px; padding: 4px 8px; border-radius: 8px;
  }
  .player-score.active { background: color-mix(in srgb, var(--ad-accent) 18%, transparent); }
  .player-score.out { opacity: .45; }
  .player-score .rest.lives { color: var(--ad-error-text); letter-spacing: .05em; }
  .player-score.winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 20%, transparent); }
  .player-score .who { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .player-score .rest { font-weight: 800; font-variant-numeric: tabular-nums; }
  .cricket { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; table-layout: fixed; }
  .cricket th, .cricket td { padding: 3px 6px; text-align: center; }
  .cricket thead th {
    font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .cricket th.aim .bed { font-size: 11px; padding: 1px 6px; }
  .cricket tr > :first-child { width: 4.2em; text-align: left; }
  .cricket tbody th { font-weight: 700; color: var(--secondary-text-color); }
  .cricket td { font-size: 17px; font-weight: 800; line-height: 1.1; color: var(--ad-accent); }
  .cricket tr.closed > * { opacity: 0.35; }
  .cricket tr.target th { color: var(--ad-accent); }
  .cricket tr.total td {
    font-size: 15px; color: var(--primary-text-color);
    border-top: 1px solid var(--divider-color, rgba(127,127,127,.25));
  }
  .cricket tr.detail td { font-size: 12px; font-weight: 600; color: var(--secondary-text-color); }
  .cricket .active { background: color-mix(in srgb, var(--ad-accent) 18%, transparent); }
  .cricket .winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 20%, transparent); }
  .aim path {
    fill: color-mix(in srgb, var(--ad-accent) 35%, transparent);
    stroke: var(--ad-accent); stroke-width: 3; stroke-dasharray: 6 3;
  }
  .recent { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
  .recent-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .recent-visit {
    min-width: 2.4em; padding: 3px 8px; border-radius: 999px; text-align: center;
    font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--primary-text-color);
    border: 1px solid var(--bucket); background: color-mix(in srgb, var(--bucket) 16%, transparent);
  }
  .slot {
    position: relative; padding: 10px 8px 9px; border-radius: 14px; text-align: center;
    border: 1px solid var(--divider-color, rgba(127,127,127,.25));
    background: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    transition: border-color .3s, box-shadow .3s, background .3s;
  }
  .slot.empty { border-style: dashed; background: none; }
  .slot.latest {
    border-color: var(--ad-highlight);
    box-shadow: 0 0 0 1px var(--ad-highlight), 0 0 18px color-mix(in srgb, var(--ad-highlight) 35%, transparent);
  }
  .slot .index { font-size: 11px; color: var(--secondary-text-color); }
  .slot .segment { font-size: 22px; font-weight: 800; margin: 2px 0; color: var(--primary-text-color); }
  .slot .value { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .slot.triple .segment { color: color-mix(in srgb, #ef6c57 80%, var(--primary-text-color)); }
  .slot.double .segment { color: color-mix(in srgb, #43b581 70%, var(--primary-text-color)); }
  .slot.bull .segment, .slot.outer-bull .segment { color: color-mix(in srgb, #e5484d 80%, var(--primary-text-color)); }
  .slot.miss .segment { color: var(--secondary-text-color); }
  .stats { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
  .stat { min-width: 0; }
  .stat .value {
    font-size: 18px; font-weight: 700; color: var(--primary-text-color);
    font-variant-numeric: tabular-nums; white-space: nowrap;
  }
  .stat .name {
    font-size: 11px; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .section-head { display: flex; justify-content: space-between; gap: 8px; }
  .since { font-size: 11px; color: var(--secondary-text-color); }
  .board { display: flex; justify-content: center; }
  .board-frame {
    width: clamp(180px, 42cqw, 380px); aspect-ratio: 1; border-radius: 50%;
    box-shadow: 0 0 42px 4px color-mix(in srgb, var(--ad-status) 55%, transparent);
    transition: box-shadow .5s;
  }
  .board-frame svg { cursor: pointer; border-radius: 50%; }
  .layout.vertical .board-frame, .layout.board-only .board-frame { width: min(100%, 420px); }
  @container (max-width: 520px) {
    .layout.auto .board-frame { width: min(100%, 360px); }
    .stats { grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: 12px; }
  }
  .hit { fill: var(--ad-highlight); opacity: .88; pointer-events: none; }
  .blink .hit { animation: ad-blink .8s ease-in-out infinite alternate; }
  .dart .pin { fill: #3182ce; stroke: #fff; stroke-width: 2; }
  .dart text { font-size: 11px; font-weight: 700; line-height: 1; fill: #fff; text-anchor: middle; dominant-baseline: central; }
  .dart.latest .halo { fill: none; stroke: var(--ad-highlight); stroke-width: 2; animation: ad-pulse 1.6s ease-out infinite; transform-box: fill-box; transform-origin: center; }
  @keyframes ad-blink { from { opacity: .18; } to { opacity: .95; } }
  @keyframes ad-pulse { from { opacity: .9; transform: scale(.7); } to { opacity: 0; transform: scale(1.8); } }
  @media (prefers-reduced-motion: reduce) {
    .blink .hit, .dart.latest .halo { animation: none; }
  }
`;

const TRAINING_CSS = `${BASE_CSS}
  .training { display: flex; flex-direction: column; gap: 18px; padding: 18px; box-sizing: border-box; }
  .hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .average {
    font-size: clamp(44px, 14cqw, 72px); font-weight: 800; line-height: 1; letter-spacing: -0.04em;
    color: var(--primary-text-color); font-variant-numeric: tabular-nums;
  }
  .average-label { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
  .totals { display: flex; gap: 18px; }
  .daily { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 14px; }
  .streak {
    padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap;
    color: color-mix(in srgb, #ff8a00 55%, var(--primary-text-color, #212121));
    background: color-mix(in srgb, #ff8a00 14%, transparent);
  }
  .goal { flex: 1 1 180px; display: flex; align-items: center; gap: 8px; min-width: 0; }
  .goal-bar {
    flex: 1; height: 6px; border-radius: 999px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 10%, transparent);
  }
  .goal-bar span { display: block; height: 100%; border-radius: inherit; background: var(--ad-accent); transition: width .4s; }
  .goal.reached .goal-bar span { background: ${STATUS_COLORS.ready}; }
  .goal-text { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .total .value { font-size: 22px; font-weight: 700; color: var(--primary-text-color); font-variant-numeric: tabular-nums; text-align: right; }
  .total .name { font-size: 11px; color: var(--secondary-text-color); text-align: right; }
  .body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; align-items: start; }
  .body.single { grid-template-columns: minmax(0, 1fr); }
  @container (max-width: 560px) { .body { grid-template-columns: minmax(0, 1fr); } }
  .heat { display: flex; flex-direction: column; align-items: center; gap: 10px; }
  .heat-frame { width: min(100%, 380px); aspect-ratio: 1; }
  .heat-bed { stroke: rgba(0,0,0,.25); stroke-width: .6; }
  .legend { width: min(100%, 320px); display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; }
  .legend-bar { height: 8px; border-radius: 999px; }
  .side { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
  .tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; cursor: pointer; border-radius: 14px; }
  .tile {
    min-width: 0; padding: 10px 8px; border-radius: 14px; text-align: center;
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .tile .value { font-size: 20px; font-weight: 800; color: var(--primary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .tile .name { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tile.hot .value { color: var(--ad-gold-text); }
  @container (max-width: 380px) { .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .bests dl { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 6px 18px; margin: 8px 0 0; }
  .bests dl > div { display: flex; justify-content: space-between; gap: 10px; min-width: 0; }
  .bests dt { font-size: 12px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bests dd { margin: 0; font-size: 13px; font-weight: 700; color: var(--primary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .top { display: flex; flex-direction: column; gap: 6px; }
  .top-row { display: grid; grid-template-columns: 3.2em 1fr auto; align-items: center; gap: 10px; font-size: 13px; }
  .top-row .key { font-weight: 800; color: var(--primary-text-color); }
  .top-row .bar { height: 8px; border-radius: 999px; background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); overflow: hidden; }
  .top-row .fill { height: 100%; border-radius: inherit; }
  .top-row .count { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .history-chart { position: relative; height: 104px; display: flex; align-items: stretch; gap: 4px; margin-top: 8px; }
  .visit-bar {
    flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; justify-content: flex-end; align-items: center;
  }
  .visit-bar .fill {
    width: 100%; max-width: 30px; min-height: 3px; border-radius: 5px 5px 2px 2px;
    height: calc((100% - 16px) * var(--height));
  }
  .visit-bar .label {
    font-size: 10px; font-weight: 700; line-height: 14px; margin-bottom: 2px;
    color: var(--secondary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap;
  }
  .visit-bar.empty .fill { background: color-mix(in srgb, var(--primary-text-color) 7%, transparent); height: 3px; }
  .average-line {
    position: absolute; left: 0; right: 0; bottom: calc((100% - 16px) * var(--height));
    border-top: 1px dashed var(--secondary-text-color); opacity: .55; pointer-events: none;
  }
  .footer-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  .footer-row button.action { flex: 0 0 auto; }
  .footer-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
  .session-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; font-variant-numeric: tabular-nums; }
  .session-table th {
    padding: 4px 6px; text-align: right; font-size: 11px; font-weight: 600; color: var(--secondary-text-color);
  }
  .session-table td {
    padding: 6px; text-align: right; color: var(--primary-text-color);
    border-top: 1px solid var(--divider-color, rgba(127,127,127,.2));
  }
  .session-table :is(th, td):first-child { text-align: left; }
  .empty-hint { font-size: 13px; color: var(--secondary-text-color); text-align: center; padding: 8px 0; }
`;

const STATUS_CSS = `${BASE_CSS}
  .status-card { display: flex; flex-direction: column; gap: 16px; padding: 18px; box-sizing: border-box; }
  .detection {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 12px 14px; border-radius: 16px;
    background: color-mix(in srgb, var(--ad-status) 10%, transparent);
  }
  .detection .name { font-weight: 700; color: var(--primary-text-color); }
  .detection .state { font-size: 12px; color: var(--secondary-text-color); }
  .toggle {
    position: relative; width: 52px; height: 30px; flex-shrink: 0; border-radius: 999px; cursor: pointer;
    border: none; background: color-mix(in srgb, var(--primary-text-color) 20%, transparent); transition: background .2s;
  }
  .toggle::after {
    content: ""; position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 50%;
    background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.3); transition: transform .2s;
  }
  .toggle[aria-checked="true"] { background: var(--ad-accent); }
  .toggle[aria-checked="true"]::after { transform: translateX(22px); }
  .toggle:disabled { opacity: .45; cursor: default; }
  .info { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
  .info-tile {
    display: flex; flex-direction: column; gap: 6px; min-width: 0; padding: 12px; border-radius: 14px;
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .info-tile .value { font-size: 15px; font-weight: 700; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .info-tile .badge {
    align-self: flex-start; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; cursor: pointer;
    border: none; font-family: inherit;
    color: var(--ad-warn-text); background: color-mix(in srgb, ${STATUS_COLORS.takeout} 16%, transparent);
  }
  .info-tile .badge.ok { color: var(--ad-ok-text); background: color-mix(in srgb, ${STATUS_COLORS.ready} 14%, transparent); cursor: default; }
  .metrics { display: flex; gap: 14px; flex-wrap: wrap; }
  .system-info {
    all: unset; display: block; cursor: pointer; overflow-wrap: anywhere;
  }
  .metric {
    all: unset; display: block; cursor: pointer; border-radius: 6px;
  }
  .metric .value { display: block; font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--primary-text-color); }
  .metric .name { display: block; font-size: 11px; color: var(--secondary-text-color); }
  .camera-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
  .camera {
    display: flex; flex-direction: column; gap: 8px; padding: 12px; border-radius: 14px;
    border: 1px solid var(--divider-color, rgba(127,127,127,.25));
  }
  .camera.problem { border-color: ${STATUS_COLORS.problem}; background: color-mix(in srgb, ${STATUS_COLORS.problem} 8%, transparent); }
  .camera-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .camera-name { font-weight: 700; color: var(--primary-text-color); background: none; border: none; padding: 0; font: inherit; font-weight: 700; cursor: pointer; }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: ${STATUS_COLORS.ready}; box-shadow: 0 0 6px ${STATUS_COLORS.ready}; }
  .camera.problem .dot { background: ${STATUS_COLORS.problem}; box-shadow: 0 0 6px ${STATUS_COLORS.problem}; }
  .camera .fps { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .camera button.action { min-height: 32px; font-size: 12px; }
`;

const SCOREBOARD_CSS = `${BASE_CSS}
  .scoreboard {
    display: flex; flex-direction: column; gap: clamp(12px, 2cqi, 24px);
    padding: clamp(14px, 2.4cqi, 32px); box-sizing: border-box;
  }
  /* The dynamic viewport leaves room for a phone's browser bar; older browsers use vh. */
  .scoreboard.full {
    min-height: calc(100vh - var(--header-height, 56px) - 16px);
    min-height: calc(100dvh - var(--header-height, 56px) - 16px);
  }
  .heading { display: grid; gap: 2px; min-width: 0; }
  .scoreboard .title { font-size: clamp(18px, 3cqi, 36px); font-weight: 700; }
  .scoreboard .meta { font-size: clamp(12px, 1.7cqi, 20px); }
  .scoreboard .pill { font-size: clamp(12px, 1.5cqi, 18px); }
  .banner {
    padding: .5em 1em; border-radius: 16px; text-align: center; font-weight: 800;
    font-size: clamp(18px, 3.4cqi, 44px); color: var(--ad-ok-text);
    background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent);
  }
  .main { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 12px; min-height: 0; }
  .players { display: grid; gap: clamp(8px, 1.6cqi, 24px); }
  .players.n1 { grid-template-columns: minmax(0, 1fr); }
  .players.n2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .players.n3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .players.n4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .player {
    display: flex; flex-direction: column; align-items: center; gap: clamp(4px, .8cqi, 12px); min-width: 0;
    padding: clamp(12px, 2.2cqi, 32px) 12px; border-radius: 20px;
    border: 2px solid var(--divider-color, rgba(127,127,127,.25)); transition: border-color .3s, background .3s;
  }
  .player.active { border-color: var(--ad-accent); background: color-mix(in srgb, var(--ad-accent) 12%, transparent); }
  .player.winner {
    border-color: ${STATUS_COLORS.ready}; background: color-mix(in srgb, ${STATUS_COLORS.ready} 14%, transparent);
  }
  .player.out { opacity: .45; }
  .big.lives { color: var(--ad-error-text); letter-spacing: 0; }
  .player .name {
    max-width: 100%; min-height: 1.2em; font-size: clamp(16px, 2.8cqi, 40px); font-weight: 700;
    color: var(--primary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .player.active .name::before { content: "▶ "; content: "▶ " / ""; color: var(--ad-accent); }
  .big {
    font-weight: 800; line-height: 1; letter-spacing: -0.04em; font-variant-numeric: tabular-nums;
    color: var(--primary-text-color);
  }
  /* Sized by width and height, so a landscape screen shows everything at once. */
  .n1 .big, .single .big { font-size: clamp(80px, min(24cqi, 32vh), 320px); }
  .n2 .big { font-size: clamp(64px, min(15cqi, 26vh), 240px); }
  .n3 .big { font-size: clamp(48px, min(10cqi, 22vh), 170px); }
  .n4 .big { font-size: clamp(44px, min(8cqi, 20vh), 140px); }
  @container (max-width: 640px) {
    .players.n3, .players.n4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .n3 .big, .n4 .big { font-size: clamp(44px, min(15cqi, 14vh), 120px); }
  }
  .route {
    display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: .4em;
    min-height: 1.8em; font-size: clamp(14px, 2.6cqi, 34px);
  }
  .bed {
    padding: .12em .55em; border-radius: 10px; font-weight: 800;
    color: var(--ad-accent); border: 2px solid var(--ad-accent);
  }
  .bed:first-child { color: var(--text-primary-color, #fff); background: var(--ad-accent); }
  .details { font-size: clamp(12px, 1.9cqi, 24px); color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .cricket { width: 100%; border-collapse: collapse; table-layout: fixed; font-variant-numeric: tabular-nums; }
  .cricket th, .cricket td { padding: .1em .3em; text-align: center; }
  .cricket thead th {
    font-size: clamp(14px, min(2.6cqi, 3.4vh), 34px); font-weight: 700; color: var(--primary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .cricket tr > :first-child { width: 20%; }
  .cricket tbody th {
    font-size: clamp(16px, min(3cqi, 3vh), 42px); font-weight: 800; color: var(--secondary-text-color);
  }
  .cricket td { font-size: clamp(20px, min(4.4cqi, 3.6vh), 60px); font-weight: 800; line-height: 1.05; color: var(--ad-accent); }
  .cricket th.aim { font-size: clamp(14px, min(2.4cqi, 3vh), 30px); }
  .cricket th.aim .bed { display: inline-block; }
  .cricket tr.closed > * { opacity: .3; }
  .cricket tr.target th { color: var(--ad-accent); }
  .cricket tr.total > * { border-top: 2px solid var(--divider-color, rgba(127,127,127,.25)); }
  .cricket tr.total td { font-size: clamp(24px, min(5cqi, 4.4vh), 68px); color: var(--primary-text-color); }
  .cricket tr.detail > * {
    font-size: clamp(12px, min(1.9cqi, 2.4vh), 24px); font-weight: 600; color: var(--secondary-text-color);
  }
  .cricket .active { background: color-mix(in srgb, var(--ad-accent) 14%, transparent); }
  .cricket .winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
  .single { display: flex; flex-direction: column; align-items: center; gap: clamp(6px, 1.2cqi, 16px); text-align: center; }
  .single .label {
    font-size: clamp(12px, 1.9cqi, 24px); font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    color: var(--ad-accent);
  }
  .facts {
    display: flex; flex-wrap: wrap; justify-content: center; gap: .3em 1.2em;
    font-size: clamp(14px, 2.4cqi, 32px); color: var(--secondary-text-color); font-variant-numeric: tabular-nums;
  }
  .facts b { color: var(--primary-text-color); }
  .caller-toggle {
    display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; cursor: pointer;
    font: inherit; font-size: clamp(12px, 1.5cqi, 18px); font-weight: 600; color: var(--secondary-text-color);
    border: 1px dashed var(--divider-color, rgba(127,127,127,.4)); background: none;
  }
  .caller-toggle[aria-pressed="true"] {
    color: var(--text-primary-color, #fff); background: var(--ad-accent); border: 1px solid var(--ad-accent);
  }
  .header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
  .visit { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) auto; gap: clamp(6px, 1.2cqi, 16px); }
  .visit.plain { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .dart, .sum {
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
    padding: clamp(6px, 1.2cqi, 16px); border-radius: 14px;
  }
  .dart {
    border: 1px solid var(--divider-color, rgba(127,127,127,.25));
    background: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
  }
  .dart .segment { font-size: clamp(18px, 3.6cqi, 48px); font-weight: 800; color: var(--primary-text-color); }
  .dart.empty .segment { color: var(--secondary-text-color); }
  .dart .points, .sum .muted { font-size: clamp(11px, 1.6cqi, 20px); min-height: 1.2em; }
  .dart .points { color: var(--secondary-text-color); }
  .sum { min-width: 4.5em; color: var(--text-primary-color, #fff); background: var(--ad-accent); }
  .sum .muted { color: inherit; opacity: .85; }
  .sum .value { font-size: clamp(22px, 4.2cqi, 56px); font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
`;

const PLAYERS_CSS = `${BASE_CSS}
  .players-card { display: flex; flex-direction: column; gap: 16px; padding: 18px; box-sizing: border-box; }
  .profiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
  .profile {
    display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 14px; min-width: 0;
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .profile-name {
    font-size: 17px; font-weight: 800; color: var(--primary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .profile dl { display: grid; grid-template-columns: 1fr auto; gap: 3px 10px; margin: 4px 0 0; }
  .profile dt { font-size: 12px; color: var(--secondary-text-color); }
  .profile dd { margin: 0; font-size: 13px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
  .versus { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 4px 10px; padding: 6px 0; }
  .versus .who { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .versus .right { text-align: right; }
  .versus .tally { font-weight: 800; font-variant-numeric: tabular-nums; }
  .balance {
    grid-column: 1 / -1; height: 5px; border-radius: 999px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
  }
  .balance i { display: block; height: 100%; background: var(--ad-accent); }
  .match {
    display: grid; grid-template-columns: auto auto minmax(0, 1fr); gap: 10px; align-items: baseline;
    padding: 6px 0; border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); font-size: 13px;
  }
  .match .game { font-weight: 700; }
  .match b { color: var(--ad-ok-text); }
`;

const DOUBLES_CSS = `${BASE_CSS}
  .doubles-card { display: flex; flex-direction: column; gap: 14px; padding: 18px; box-sizing: border-box; }
  .doubles-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; align-items: start; }
  @container (max-width: 560px) { .doubles-body { grid-template-columns: minmax(0, 1fr); } }
  .doubles-board { max-width: 380px; width: 100%; margin: 0 auto; aspect-ratio: 1; }
  .ring path { stroke: var(--ha-card-background, var(--card-background-color, #1c1c1c)); stroke-width: 1.5; }
  .double-list { display: grid; gap: 6px; }
  .double {
    display: grid; grid-template-columns: 3.4em minmax(0, 1fr) auto 3.4em; gap: 10px; align-items: center;
    font-variant-numeric: tabular-nums;
  }
  .double .bed {
    padding: 2px 0; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 800;
    color: var(--c); border: 1px solid var(--c);
  }
  .double.favourite .bed { color: #fff; background: var(--c); }
  .double .bar {
    height: 6px; border-radius: 999px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 10%, transparent);
  }
  .double .bar i { display: block; height: 100%; border-radius: inherit; }
  .double .count { font-size: 12px; color: var(--secondary-text-color); }
  .double .rate { font-size: 13px; font-weight: 700; text-align: right; }
`;

// Live card panel --------------------------------------------------------------

// The practice panel of the live card: the game, the line under it, the big
// number, what to aim at next and, in a match, a row for every player.
function livePanel(view, ui) {
  const { t, format } = ui;
  const turn = (game) =>
    game.winner === null ? `${playerName(ui, { player: game.player, name: game.name }, true)} ${t("score_turn")}` : "";
  const winner = (game) => {
    const score = game.scores.find((item) => item.player === game.winner) ?? { player: game.winner, name: null };
    return note(`${playerName(ui, score, true)} ${t("score_winner")}`, "won");
  };
  if (view.mode === "drill") {
    const parts = drillParts(view.drill, ui);
    return {
      title: t(`drill_${view.drill.kind}`),
      meta: factsText(parts.facts),
      big: parts.big,
      route: parts.note,
      rows: "",
    };
  }
  if (view.mode === "bulloff") {
    const { bullOff } = view;
    return {
      title: t("bull_off"),
      meta: `${playerName(ui, bullOff, true)} ${t("score_turn")}`,
      big: "Bull",
      route: note(t("bull_off_hint")),
      rows: playerRows(bullOffPlayers(bullOff, ui)),
    };
  }
  if (view.mode === "cricket") {
    const { cricket } = view;
    const match = cricket.scores.length > 1;
    // In a match the points decide; alone, the numbers closed so far.
    const current = cricket.scores.find((score) => score.player === cricket.player);
    const closed = current ? current.marks.filter((mark) => mark >= 3).length : 0;
    const alone = cricket.darts
      ? [`${cricket.darts} ${t("leg_darts")}`, cricket.mpr === null ? "" : `${t("cricket_mpr")} ${format(cricket.mpr, 2)}`]
      : [];
    return {
      title: t("cricket"),
      meta: match ? turn(cricket) : alone.filter(Boolean).join(" · "),
      big: match ? String(cricket.points) : `${closed}/${cricket.numbers.length}`,
      route:
        cricket.winner !== null
          ? winner(cricket)
          : cricket.won
            ? note(t("game_shot"), "won")
            : bedChips(ui, cricket.target ? [cricket.target] : []),
      rows: cricket.scores.length ? cricketTable(cricket, ui, { aim: false }) : "",
    };
  }
  if (view.mode === "party") {
    const { party } = view;
    const match = party.scores.length > 1;
    const current = party.scores.find((score) => score.player === party.player);
    const killer = party.kind === "killer";
    return {
      title: t(`party_${party.kind}`),
      meta: [party.rounds ? `${t("drill_round")} ${party.round}/${party.rounds}` : "", match ? turn(party) : ""]
        .filter(Boolean)
        .join(" · "),
      big: killer ? (party.phase === "choose" ? "?" : String(current?.number ?? "–")) : String(party.points),
      route: party.winner !== null ? winner(party) : partyNote(party, ui),
      rows: match ? playerRows(partyPlayers(party, ui)) : "",
    };
  }
  const { practice } = view;
  const players = x01Players(practice, ui);
  const match = players.length > 1;
  return {
    title: `${t("practice")} ${practice.game ?? ""}`.trim(),
    meta: match ? turn(practice) : players[0].details.filter(Boolean).join(" · "),
    big: String(practice.remaining),
    route: practice.winner !== null ? winner(practice) : x01Note(practice, ui),
    routeTitle: practice.route.length ? `${t("checkout")}: ${practice.route.join(" ")}` : "",
    rows: match ? playerRows(players) : "",
  };
}

// Home Assistant brings its form element with its own editors; the strategy
// editor, which Home Assistant offers no form for, loads it with a card editor.
async function loadForm() {
  if (customElements.get("ha-form") || !window.loadCardHelpers) return;
  try {
    const helpers = await window.loadCardHelpers();
    const card = await helpers.createCardElement({ type: "entities", entities: [] });
    await card.constructor.getConfigElement?.();
  } catch (error) {
    // The editor shows its form as soon as Home Assistant defines it.
  }
}

// Elements ------------------------------------------------------------------

// Elements are created on demand: Home Assistant replaces HTMLElement while it boots.
function createElements(Base) {
  class CardBase extends Base {
    static keys = {};

    static defaults = {};

    // The name of the card's form in FORMS.
    static form = null;

    static getStubConfig(hass) {
      const [deviceId] = autodartsDevices(hass);
      return deviceId ? { device_id: deviceId } : {};
    }

    // The visual editor: a form of Home Assistant, in the language of the page.
    static getConfigForm() {
      return this.form ? cardForm(FORMS[this.form](), this.defaults) : undefined;
    }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._watchedStates = [];
      this._confirm = null;
    }

    setConfig(config) {
      if (!config || typeof config !== "object") throw new Error("Invalid configuration");
      this._config = { ...this.constructor.defaults, ...config };
      this._built = false;
      this._message = null;
      this._watchedStates = [];
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      pageHass = hass;
      this._render();
    }

    // Home Assistant sets this in the card editor and picker, where taps must not act.
    set preview(value) {
      this._preview = Boolean(value);
    }

    get preview() {
      return Boolean(this._preview);
    }

    // A pending confirmation ends with the card, so it shows no "Confirm?" when it returns.
    disconnectedCallback() {
      clearTimeout(this._confirmTimer);
      this._confirm = null;
      this._confirmChanged();
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }

    _css() {
      return BASE_CSS;
    }

    // Entity ids whose state changes redraw the card.
    _watched() {
      return Object.values(this._ids);
    }

    // The state of a watched entity as far as the card cares about it.
    _relevant(id, state) {
      return state;
    }

    _render() {
      if (!this._config || !this._hass) return;
      const hass = this._hass;
      const deviceId = this._config.device_id || autodartsDevices(hass)[0];
      // A deleted device must not be mistaken for an unreachable board.
      if (!deviceId || (this._config.device_id && !knownDevice(hass, deviceId))) {
        const message = translate(hass, "no_board");
        if (this._message !== message) {
          this.shadowRoot.innerHTML = `<style>${this._css()}</style><ha-card><div class="message">${escapeHtml(
            message
          )}</div></ha-card>`;
          this._message = message;
        }
        this._built = false;
        return;
      }
      this._message = null;
      this._index = entityIndex(hass, deviceId);
      this._ids = resolveKeys(this._index, this.constructor.keys);
      const states = this._watched().map((id) => (id ? this._relevant(id, hass.states[id]) : undefined));
      const lang = language(hass);
      const rebuild = !this._built || this._language !== lang || this._deviceId !== deviceId;
      if (
        !rebuild &&
        states.length === this._watchedStates.length &&
        states.every((state, index) => state === this._watchedStates[index])
      ) {
        return;
      }
      if (rebuild) {
        this._language = lang;
        this._deviceId = deviceId;
        this._build();
        this._built = true;
      }
      this._watchedStates = states;
      this._update();
    }

    _t(key) {
      return translate(this._hass, key);
    }

    _state(name) {
      const id = this._ids?.[name];
      return id ? this._hass.states[id] : undefined;
    }

    _number(name) {
      const state = this._state(name);
      const value = usable(state) ? Number(state.state) : NaN;
      return Number.isFinite(value) ? value : null;
    }

    _format(value, digits = 0) {
      return formatNumber(this._hass, value, digits);
    }

    _percent(value, digits = 0) {
      return formatPercent(this._hass, value, digits);
    }

    // Texts, numbers and beds as the shared renderers read them.
    _ui() {
      return {
        t: (key) => this._t(key),
        format: (value, digits) => this._format(value, digits),
        percent: (value, digits) => this._percent(value, digits),
        label: (key) => hitLabel(this._hass, key),
        date: (value) => formatDateTime(this._hass, value),
      };
    }

    _since() {
      const started = this._state("started");
      const shown = usable(started) ? formatDateTime(this._hass, started.state) : "";
      return shown ? `${this._t("since")} ${shown}` : "";
    }

    _deviceName() {
      const device = this._hass.devices?.[this._deviceId];
      return this._config.title || device?.name_by_user || device?.name || "Autodarts";
    }

    _status() {
      return boardStatus((name) => this._state(name));
    }

    _call(domain, service, data) {
      // Home Assistant already shows failures as a toast.
      Promise.resolve(this._hass.callService(domain, service, data)).catch(() => {});
    }

    _press(id) {
      if (id) this._call("button", "press", { entity_id: id });
    }

    // The switch starts and stops detection; boards without it have a button each.
    _toggleDetection() {
      if (this.preview) return;
      const running = detectionRunning((name) => this._state(name), this._status()[0]);
      if (this._ids.detection) {
        this._call("switch", running ? "turn_off" : "turn_on", { entity_id: this._ids.detection });
      } else {
        this._press(this._ids[running ? "stop" : "start"]);
      }
    }

    // Destructive actions need a second tap within a few seconds.
    _confirmed(action) {
      if (this._confirm === action) {
        this._confirm = null;
        clearTimeout(this._confirmTimer);
        return true;
      }
      this._confirm = action;
      clearTimeout(this._confirmTimer);
      this._confirmTimer = setTimeout(() => {
        this._confirm = null;
        this._confirmChanged();
      }, 4000);
      return false;
    }

    _confirmChanged() {}

    _moreInfo(entityId) {
      if (!entityId || this.preview) return;
      this.dispatchEvent(
        new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } })
      );
    }

    // Enter and space act on an element that is a button to assistive technology.
    _onKeys(element, action) {
      element?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        action();
      });
    }

    // Replace markup only when it changes, so animations and focus survive updates.
    // A focused element with data-focus gets the focus back after a change.
    _setHtml(element, html) {
      if (!element || element._adHtml === html) return;
      const active = this.shadowRoot.activeElement;
      const focus = active && element.contains(active) ? active.dataset.focus : undefined;
      element.innerHTML = html;
      element._adHtml = html;
      if (focus) [...element.querySelectorAll("[data-focus]")].find((item) => item.dataset.focus === focus)?.focus();
    }
  }

  // Live visit card ------------------------------------------------------------

  class AutodartsCard extends CardBase {
    static keys = KEYS;

    static defaults = DEFAULTS;

    static form = "live";

    getCardSize() {
      return this._config?.layout === "vertical" ? 10 : 7;
    }

    _css() {
      return CSS;
    }

    _visitHtml(t) {
      const c = this._config;
      const practice = `
        <div class="practice" hidden>
          <div class="practice-head">
            <span class="section-label practice-title"></span>
            <span class="muted practice-meta"></span>
          </div>
          <div class="practice-row">
            <span class="practice-remaining">–</span>
            <div class="practice-route"></div>
          </div>
          <div class="scoreboard" hidden></div>
        </div>`;
      const slots = [1, 2, 3]
        .map(
          (n) =>
            `<div class="slot empty"><div class="index">${t("dart")} ${n}</div>` +
            `<div class="segment">–</div><div class="value">&nbsp;</div></div>`
        )
        .join("");
      const recent = `<div class="recent" hidden><span class="muted">${t("recent")}</span><div class="recent-list"></div></div>`;
      return `
        <div class="visit">
          <div>
            <div class="visit-label">${t("visit")}</div>
            <div class="score-row">
              <span class="score">–</span>
              <span class="score-unit">${t("points")}</span>
              <span class="progress"></span>
            </div>
          </div>
          ${c.show_practice ? practice : ""}
          <div class="slots">${slots}</div>
          ${c.show_recent ? recent : ""}
        </div>`;
    }

    _boardHtml(t) {
      const c = this._config;
      return `
        <div class="board">
          <div class="board-frame">
            <svg viewBox="-230 -230 460 460" role="button" tabindex="0" aria-label="${t("board_label")}">
              <g class="face">${boardSvg(c.board_style)}</g>
              <g class="hits${c.blink ? " blink" : ""}"></g>
              <g class="aim"></g>
              ${c.show_numbers ? `<g class="numbers">${numbersSvg(c.board_style)}</g>` : ""}
              <g class="darts"></g>
            </svg>
          </div>
        </div>`;
    }

    _sessionHtml(t) {
      if (!this._config.show_stats) return "";
      const stats = ["darts", "average", "triples", "bulls", "max"]
        .map((key) => `<div class="stat" data-stat="${key}"><div class="value">–</div><div class="name">${t(key)}</div></div>`)
        .join("");
      return `
        <div class="session">
          <div class="section-head">
            <span class="section-label">${t("session")}</span>
            <span class="since"></span>
          </div>
          <div class="stats">${stats}</div>
        </div>`;
    }

    _footerHtml(t) {
      const c = this._config;
      if (!c.show_connection && !c.show_controls) return "";
      const controls = `
        <div class="controls">
          <button class="primary" data-action="toggle"></button>
          <button data-action="reset">${t("reset")}</button>
          <button data-action="calibrate">${t("calibrate")}</button>
        </div>`;
      return `
        <div class="footer">
          ${c.show_connection ? `<div class="chips"></div>` : ""}
          ${c.show_controls ? controls : ""}
        </div>`;
    }

    _build() {
      const c = this._config;
      const t = (key) => escapeHtml(this._t(key));
      const layout = c.layout === "board" ? "board-only" : c.layout;
      this.shadowRoot.innerHTML = `
        <style>${CSS}</style>
        <ha-card>
          <div class="root">
            <div class="layout ${escapeHtml(layout)}">
              <header>
                <div class="title"></div>
                <div class="pill" role="status"></div>
              </header>
              ${this._visitHtml(t)}
              ${this._boardHtml(t)}
              ${this._sessionHtml(t)}
              ${this._footerHtml(t)}
            </div>
          </div>
        </ha-card>`;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        pill: root.querySelector(".pill"),
        score: root.querySelector(".score"),
        progress: root.querySelector(".progress"),
        recent: root.querySelector(".recent"),
        recentList: root.querySelector(".recent-list"),
        practice: root.querySelector(".practice"),
        practiceTitle: root.querySelector(".practice-title"),
        practiceMeta: root.querySelector(".practice-meta"),
        practiceRemaining: root.querySelector(".practice-remaining"),
        practiceRoute: root.querySelector(".practice-route"),
        scoreboard: root.querySelector(".scoreboard"),
        aim: root.querySelector(".aim"),
        slots: [...root.querySelectorAll(".slot")],
        since: root.querySelector(".since"),
        stats: Object.fromEntries(
          [...root.querySelectorAll(".stat")].map((el) => [el.dataset.stat, el.querySelector(".value")])
        ),
        chips: root.querySelector(".chips"),
        controls: root.querySelector(".controls"),
        hits: root.querySelector(".hits"),
        darts: root.querySelector(".darts"),
        svg: root.querySelector("svg"),
      };
      this._el.controls?.addEventListener("click", (event) => this._onControl(event));
      this._el.chips?.addEventListener("click", (event) => {
        const id = event.target.closest(".chip")?.dataset.entity;
        if (id) this._moreInfo(id);
      });
      this._el.svg.addEventListener("click", () => this._moreInfo(this._ids.visit));
      this._onKeys(this._el.svg, () => this._moreInfo(this._ids.visit));
    }

    _darts() {
      const visit = this._state("visit");
      if (Array.isArray(visit?.attributes?.throws)) return visitThrows(visit);
      // Older integration versions only report the last segment.
      const last = this._state("lastThrow");
      const count = Number(this._state("numThrows")?.state);
      const parsed = usable(last) ? parseSegment(last.state) : null;
      if (!parsed || !(count > 0)) return [];
      return [...Array(Math.min(count, 3) - 1).fill(null), parsed];
    }

    _update() {
      const hass = this._hass;
      const c = this._config;
      const el = this._el;
      const t = (key) => this._t(key);
      el.title.textContent = this._deviceName();

      const [status, statusText] = this._status();
      this.style.setProperty("--ad-status", STATUS_COLORS[status]);
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      this.style.setProperty("--ad-highlight", cssColor(c.highlight_color, GOLD));
      el.pill.textContent = t(statusText);

      const darts = this._darts();
      const known = darts.filter(Boolean);
      const visit = this._state("visit");
      const total = usable(visit)
        ? visit.state
        : known.reduce((sum, dart) => sum + dart.number * dart.multiplier, 0);
      el.score.textContent = darts.length || usable(visit) ? total : "–";
      el.progress.textContent = darts.length ? `${t("dart")} ${darts.length} ${t("of")} 3` : "";
      if (el.recent) {
        const visits = recentVisits(visit?.attributes?.recent_visits);
        el.recent.hidden = !visits.length;
        this._setHtml(
          el.recentList,
          visits
            .map(
              (item) =>
                `<span class="recent-visit" style="--bucket:${VISIT_COLORS[visitBucket(item.score)]}" ` +
                `title="${escapeHtml(`${item.segments.join(" · ")} = ${item.score}`)}">${item.score}</span>`
            )
            .join("")
        );
      }

      el.slots.forEach((slot, index) => {
        const dart = darts[index];
        const [segment, value] = [slot.querySelector(".segment"), slot.querySelector(".value")];
        if (!dart) {
          slot.className = `slot ${index < darts.length ? "unknown" : "empty"}`;
          segment.textContent = index < darts.length ? "?" : "–";
          value.innerHTML = "&nbsp;";
          return;
        }
        slot.className = `slot ${kind(dart)}${index === darts.length - 1 ? " latest" : ""}`;
        segment.textContent = label(hass, dart);
        value.textContent = `${dart.number * dart.multiplier} ${t("points")}`;
      });

      // The practice sensor carries one game at a time; a training game comes first.
      const view = c.show_practice ? gameView((name) => this._state(name)) : { mode: "idle" };
      this._updatePractice(view);
      this._updateBoard(darts, view);
      this._updateStats();
      this._updateChips();
      this._updateControls(status);
    }

    _updatePractice(view) {
      const el = this._el;
      if (!el.practice) return;
      el.practice.hidden = view.mode === "idle";
      if (view.mode === "idle") return;
      const panel = livePanel(view, this._ui());
      el.practiceTitle.textContent = panel.title;
      el.practiceMeta.textContent = panel.meta;
      el.practiceRemaining.textContent = panel.big;
      el.practiceRoute.title = panel.routeTitle ?? "";
      this._setHtml(el.practiceRoute, panel.route);
      el.scoreboard.hidden = !panel.rows;
      this._setHtml(el.scoreboard, panel.rows);
    }

    _updateBoard(darts, view) {
      const c = this._config;
      const latest = darts.length - 1;
      const highlighted =
        c.highlight === "none"
          ? []
          : darts
              .map((dart, index) => (dart && (c.highlight !== "last" || index === latest) ? dart : null))
              .filter(Boolean);
      const paths = new Set(highlighted.flatMap(beds));
      this._setHtml(
        this._el.hits,
        [...paths]
          .map((id) => bedPath(id))
          .filter(Boolean)
          .map((d) => `<path class="hit" d="${d}"/>`)
          .join("")
      );
      // The bed the player aims at next: the route, the target or the doubles that open a leg.
      this._setHtml(
        this._el.aim,
        aimBeds(view)
          .map((id) => bedPath(id))
          .filter(Boolean)
          .map((d) => `<path d="${d}"/>`)
          .join("")
      );

      this._setHtml(
        this._el.darts,
        c.show_markers
          ? darts
              .map((dart, index) => {
                if (!dart || !Number.isFinite(dart.x) || !Number.isFinite(dart.y)) return "";
                const radius = Math.hypot(dart.x, dart.y) * NORM;
                const scale = radius > R.board - 4 ? (R.board - 4) / radius : 1;
                const x = fmt(dart.x * NORM * scale);
                const y = fmt(-dart.y * NORM * scale);
                return (
                  `<g class="dart${index === latest ? " latest" : ""}" transform="translate(${x} ${y})">` +
                  `<circle class="halo" r="11"/><circle class="pin" r="9.5"/><text>${index + 1}</text></g>`
                );
              })
              .join("")
          : ""
      );
      const summary = darts
        .filter(Boolean)
        .map((dart) => label(this._hass, dart))
        .join(", ");
      this._el.svg.setAttribute(
        "aria-label",
        summary ? `${this._t("board_label")}: ${summary}` : this._t("board_label")
      );
    }

    _updateStats() {
      const stats = this._el.stats;
      if (!stats.darts) return;
      const darts = this._number("darts");
      const points = this._number("points");
      // Older integration versions have no average sensor.
      const average = this._ids.average
        ? this._number("average")
        : darts > 0 && points !== null
          ? (points / darts) * 3
          : null;
      stats.darts.textContent = this._format(darts);
      stats.average.textContent = this._format(average, 1);
      stats.triples.textContent = this._format(this._number("triples"));
      stats.bulls.textContent = this._format(this._number("bulls"));
      stats.max.textContent = this._format(this._number("max"));
      this._el.since.textContent = this._since();
    }

    _updateChips() {
      if (!this._el.chips) return;
      const t = (key) => escapeHtml(this._t(key));
      const chip = (name, text, alert = false) => {
        const id = this._ids[name];
        if (!id) return "";
        const state = this._hass.states[id]?.state;
        const cls = alert ? "alert" : state === "on" ? "on" : "off";
        return `<button class="chip ${cls}" data-entity="${escapeHtml(id)}" data-focus="${escapeHtml(id)}">${text}</button>`;
      };
      const problem = this._state("cameraProblem")?.state === "on";
      this._setHtml(
        this._el.chips,
        [
          chip("connected", t("board")),
          chip("realtime", t("realtime")),
          problem ? chip("cameraProblem", t("camera_problem"), true) : chip("cameras", t("cameras")),
        ].join("")
      );
    }

    _updateControls(status) {
      const controls = this._el.controls;
      if (!controls) return;
      // Without a detection switch, the board status tells whether detection runs.
      const running = detectionRunning((name) => this._state(name), status);
      const toggle = controls.querySelector('[data-action="toggle"]');
      toggle.textContent = this._t(running ? "stop" : "start");
      toggle.classList.toggle("stop", running);
      toggle.disabled = status === "offline" || !(this._ids.detection || this._ids[running ? "stop" : "start"]);
      for (const action of ["reset", "calibrate"]) {
        const button = controls.querySelector(`[data-action="${action}"]`);
        const confirming = this._confirm === action;
        button.textContent = this._t(confirming ? "confirm" : action);
        button.classList.toggle("confirm", confirming);
        button.disabled = status === "offline" || !this._ids[action];
      }
    }

    _confirmChanged() {
      if (this._el) this._updateControls(this._status()[0]);
    }

    _onControl(event) {
      const action = event.target.closest("button")?.dataset.action;
      if (!action || this.preview) return;
      if (action === "toggle") {
        this._toggleDetection();
        return;
      }
      // Reset and calibration discard detected darts, so they need a second tap.
      if (this._confirmed(action)) this._press(this._ids[action]);
      this._confirmChanged();
    }
  }

  // Training card ---------------------------------------------------------------

  const TRAINING_TILES = ["highest", "scores_100", "scores_140", "max", "triple_rate", "doubles", "bulls", "misses"];

  class AutodartsTrainingCard extends CardBase {
    static keys = TRAINING_KEYS;

    static defaults = TRAINING_DEFAULTS;

    static form = "training";

    constructor() {
      super();
      this._visits = [];
      this._seen = new Set();
    }

    getCardSize() {
      return 9;
    }

    _css() {
      return TRAINING_CSS;
    }

    // Only visits and session starts change the card; other board events leave it alone.
    _relevant(id, state) {
      if (id !== this._ids.events) return state;
      const type = state?.attributes?.event_type;
      if (this._event?.id !== id || type === "visit_completed" || type === "session_started") {
        this._event = { id, state };
      }
      return this._event.state;
    }

    _heatHtml(t) {
      const c = this._config;
      const legend = [0, 0.25, 0.5, 0.75, 1].map(heatColor).join(", ");
      return `
        <div class="heat">
          <div class="section-label">${t("heatmap")}</div>
          <div class="heat-frame">
            <svg viewBox="-230 -230 460 460" role="img" aria-label="${t("heatmap_label")}">
              <g class="face">${boardSvg(c.board_style)}</g>
              <g class="heat-layer"></g>
              <g class="numbers">${numbersSvg(c.board_style)}</g>
            </svg>
          </div>
          <div class="legend">
            <span class="muted">1</span>
            <div class="legend-bar" style="background: linear-gradient(90deg, ${legend})"></div>
            <span class="muted legend-max">–</span>
          </div>
        </div>`;
    }

    _sideHtml(t) {
      const c = this._config;
      const tiles = TRAINING_TILES.map(
        (key) => `<div class="tile" data-tile="${key}"><div class="value">–</div><div class="name">${t(key)}</div></div>`
      ).join("");
      return `
        <div class="side">
          ${
            c.show_stats
              ? `<div class="tiles" role="button" tabindex="0" aria-label="${t("statistics_label")}">${tiles}</div>`
              : ""
          }
          ${
            c.show_top
              ? `<div class="top-section"><div class="section-label">${t("top")}</div><div class="top"></div></div>`
              : ""
          }
        </div>`;
    }

    _bodyHtml(t) {
      const c = this._config;
      const side = c.show_stats || c.show_top;
      if (!c.show_heatmap && !side) return "";
      return `
        <div class="body${c.show_heatmap && side ? "" : " single"}">
          ${c.show_heatmap ? this._heatHtml(t) : ""}
          ${side ? this._sideHtml(t) : ""}
        </div>`;
    }

    _sessionsHtml(t) {
      return `
        <div class="sessions" hidden>
          <div class="section-label">${t("past_sessions")}</div>
          <table class="session-table">
            <thead><tr>
              <th>${t("session_end")}</th><th>${t("duration")}</th><th>${t("darts")}</th>
              <th>${t("average")}</th><th>${t("highest_short")}</th>
            </tr></thead>
            <tbody></tbody>
          </table>
        </div>`;
    }

    _footerHtml(t) {
      return `
        <div class="footer-row">
          <span class="muted session-state"></span>
          <div class="footer-actions">
            <button class="action" data-action="session" hidden></button>
            <button class="action" data-action="new_session">${t("new_session")}</button>
          </div>
        </div>`;
    }

    _build() {
      const c = this._config;
      const t = (key) => escapeHtml(this._t(key));
      this.shadowRoot.innerHTML = `
        <style>${TRAINING_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="training">
              <header>
                <div class="title"></div>
                <div class="muted since"></div>
              </header>
              <div class="daily" hidden>
                <span class="streak" hidden><span aria-hidden="true">🔥</span> <span class="streak-text"></span></span>
                <div class="goal" hidden>
                  <div class="goal-bar" hidden><span></span></div>
                  <span class="goal-text"></span>
                </div>
              </div>
              <div class="hero">
                <div>
                  <div class="average">–</div>
                  <div class="average-label">${t("average_long")}</div>
                </div>
                <div class="totals">
                  <div class="total"><div class="value" data-total="darts">–</div><div class="name">${t("darts")}</div></div>
                  <div class="total"><div class="value" data-total="visits">–</div><div class="name">${t("visits")}</div></div>
                </div>
              </div>
              <div class="empty-hint" hidden>${t("no_darts")}</div>
              ${this._bodyHtml(t)}
              ${c.show_bests ? `<div class="bests" hidden><div class="section-label">${t("personal_bests")}</div><dl></dl></div>` : ""}
              ${
                c.show_history
                  ? `<div class="history"><div class="section-label">${t("history")}</div><div class="history-chart"></div></div>`
                  : ""
              }
              ${c.show_sessions ? this._sessionsHtml(t) : ""}
              ${c.show_reset ? this._footerHtml(t) : ""}
            </div>
          </div>
        </ha-card>`;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        since: root.querySelector(".since"),
        daily: root.querySelector(".daily"),
        streak: root.querySelector(".streak"),
        streakText: root.querySelector(".streak-text"),
        goal: root.querySelector(".goal"),
        goalBar: root.querySelector(".goal-bar"),
        goalFill: root.querySelector(".goal-bar span"),
        goalText: root.querySelector(".goal-text"),
        average: root.querySelector(".average"),
        totals: Object.fromEntries([...root.querySelectorAll("[data-total]")].map((el) => [el.dataset.total, el])),
        empty: root.querySelector(".empty-hint"),
        heat: root.querySelector(".heat-layer"),
        legendMax: root.querySelector(".legend-max"),
        tiles: Object.fromEntries(
          [...root.querySelectorAll("[data-tile]")].map((el) => [el.dataset.tile, el.querySelector(".value")])
        ),
        bests: root.querySelector(".bests"),
        bestList: root.querySelector(".bests dl"),
        top: root.querySelector(".top"),
        history: root.querySelector(".history-chart"),
        newSession: root.querySelector('[data-action="new_session"]'),
        session: root.querySelector('[data-action="session"]'),
        sessionState: root.querySelector(".session-state"),
        sessions: root.querySelector(".sessions"),
        sessionRows: root.querySelector(".session-table tbody"),
      };
      this._el.newSession?.addEventListener("click", () => {
        if (this.preview) return;
        if (this._confirmed("new_session")) this._press(this._ids.newSession);
        this._confirmChanged();
      });
      this._el.session?.addEventListener("click", () => {
        if (this.preview || !this._ids.session) return;
        const running = this._state("session")?.state === "on";
        // Starting is harmless; ending needs a second tap like a new session.
        if (!running || this._confirmed("end_session")) {
          this._call("switch", running ? "turn_off" : "turn_on", { entity_id: this._ids.session });
        }
        this._confirmChanged();
      });
      const tiles = root.querySelector(".tiles");
      tiles?.addEventListener("click", () => this._moreInfo(this._ids.darts));
      this._onKeys(tiles, () => this._moreInfo(this._ids.darts));
      this._historyFor = null;
    }

    _confirmChanged() {
      const button = this._el?.newSession;
      if (button) {
        const confirming = this._confirm === "new_session";
        button.textContent = this._t(confirming ? "confirm" : "new_session");
        button.classList.toggle("confirm", confirming);
        button.disabled = !this._ids.newSession;
      }
      const toggle = this._el?.session;
      if (toggle) {
        const running = this._state("session")?.state === "on";
        const confirming = running && this._confirm === "end_session";
        toggle.hidden = !this._ids.session;
        toggle.textContent = this._t(confirming ? "confirm" : running ? "end_session" : "start_session");
        toggle.classList.toggle("primary", !running);
        toggle.classList.toggle("confirm", confirming);
      }
    }

    _updateSessions() {
      const el = this._el;
      const session = this._state("session");
      if (el.sessionState) {
        const changed = Date.parse(session?.last_changed);
        el.sessionState.textContent = !session
          ? ""
          : session.state === "on"
            ? this._t("session_running")
            : Number.isFinite(changed)
              ? `${this._t("session_ended")} ${formatDateTime(this._hass, changed)}`
              : this._t("no_session");
      }
      if (!el.sessions) return;
      const sessions = pastSessions(this._state("lastSession")?.attributes?.sessions);
      const duration = (minutes) =>
        minutes === null
          ? "–"
          : minutes < 1
            ? this._t("under_a_minute")
            : fill(this._t("unit_minutes"), { value: this._format(minutes) });
      el.sessions.hidden = !sessions.length;
      this._setHtml(
        el.sessionRows,
        sessions
          .map((item) =>
            [
              formatDateTime(this._hass, item.ended),
              duration(item.minutes),
              this._format(item.darts),
              this._format(item.average, 1),
              this._format(item.best),
            ]
              .map((cell) => `<td>${escapeHtml(cell)}</td>`)
              .join("")
          )
          .map((row) => `<tr>${row}</tr>`)
          .join("")
      );
    }

    // The streak and today's darts towards the daily goal.
    _updateDaily() {
      const el = this._el;
      const streak = this._number("streak");
      const today = this._number("today");
      el.daily.hidden = !(streak > 0) && today === null;
      el.streak.hidden = !(streak > 0);
      el.streakText.textContent = `${this._format(streak)} ${this._t(streak === 1 ? "streak_day" : "streak_days")}`;
      el.goal.hidden = today === null;
      const attributes = this._state("today")?.attributes || {};
      const goal = Number(attributes.goal) || 0;
      el.goalBar.hidden = !goal;
      el.goalFill.style.width = goal ? `${Math.min(100, (today / goal) * 100)}%` : "0";
      el.goal.classList.toggle("reached", attributes.goal_reached === true);
      el.goalText.textContent = `${
        goal ? `${this._format(today)} / ${this._format(goal)}` : this._format(today)
      } ${this._t("darts_today")}`;
    }

    _updateBests() {
      if (!this._el.bests) return;
      const records = bestsView(this._state("bests"), this._state("streak"));
      this._el.bests.hidden = !records.length;
      this._setHtml(this._el.bestList, bestsHtml(records, this._ui()));
    }

    _update() {
      const c = this._config;
      const el = this._el;
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      el.title.textContent = c.title || `${this._t("training")} · ${this._deviceName()}`;
      el.since.textContent = this._since();
      this._updateDaily();

      const darts = this._number("darts");
      const points = this._number("points");
      const average = this._ids.average
        ? this._number("average")
        : darts > 0 && points !== null
          ? (points / darts) * 3
          : null;
      el.average.textContent = this._format(average, 1);
      el.totals.darts.textContent = this._format(darts);
      el.totals.visits.textContent = this._format(this._number("visits"));
      el.empty.hidden = darts > 0;
      const idle = this._state("session")?.state === "off";
      el.empty.textContent = this._t(idle ? "no_session_hint" : "no_darts");

      const tiles = el.tiles;
      if (tiles.highest) {
        for (const key of ["highest", "scores_100", "scores_140", "max", "doubles", "bulls", "misses"]) {
          tiles[key].textContent = this._format(this._number(key));
        }
        tiles.max.parentElement.classList.toggle("hot", this._number("max") > 0);
        const triples = this._number("triples");
        tiles.triple_rate.textContent = darts > 0 && triples !== null ? this._percent((triples / darts) * 100, 1) : "–";
      }

      const hits = this._state("darts")?.attributes?.hits;
      this._updateHeat(hits);
      this._updateTop(hits, darts);
      this._updateBests();
      this._updateHistory();
      this._updateSessions();
      this._confirmChanged();
    }

    _updateHeat(hits) {
      if (!this._el.heat) return;
      const levels = heatLevels(hits, this._config.mode);
      const max = Math.max(0, ...levels.values());
      const counts = new Map(validHits(hits));
      const total = [...counts.values()].reduce((sum, count) => sum + count, 0);
      const describe = (bed) => {
        // Tooltips name the scoring bed; singles cover both single areas.
        const key = bed === "Bull" ? "BULL" : bed.replace(/^S[IO]/, "S");
        const numbers = this._config.mode === "numbers";
        const count = numbers ? levels.get(bed) : counts.get(key) || 0;
        const name = numbers ? (bed === "Bull" || bed === "25" ? "Bull" : bed.replace(/^\D+/, "")) : hitLabel(this._hass, key);
        const share = total ? ` · ${this._percent((count / total) * 100, 1)}` : "";
        return `${name}: ${count} ${this._t("hits")}${share}`;
      };
      const markup = [...levels.entries()]
        .map(([bed, count]) => {
          const path = bedPath(bed);
          if (!path || !max) return "";
          const ratio = heatRatio(count, max);
          return (
            `<path class="heat-bed" d="${path}" fill="${heatColor(ratio)}" fill-opacity="${fmt(0.6 + 0.35 * ratio)}">` +
            `<title>${escapeHtml(describe(bed))}</title></path>`
          );
        })
        .join("");
      this._setHtml(this._el.heat, markup);
      if (this._el.legendMax) this._el.legendMax.textContent = max ? this._format(max) : "–";
    }

    _updateTop(hits, darts) {
      if (!this._el.top) return;
      const top = topHits(hits, 5);
      const most = top[0]?.[1] || 0;
      this._setHtml(
        this._el.top,
        top.length
          ? top
              .map(([key, count]) => {
                const width = most ? count / most : 0;
                const share = darts > 0 ? ` · ${this._percent((count / darts) * 100, 0)}` : "";
                return (
                  `<div class="top-row"><span class="key">${escapeHtml(hitLabel(this._hass, key))}</span>` +
                  `<div class="bar"><div class="fill" style="width:${fmt(width * 100)}%;background:${heatColor(heatRatio(count, most))}"></div></div>` +
                  `<span class="count">${escapeHtml(`${this._format(count)}×${share}`)}</span></div>`
                );
              })
              .join("")
          : `<div class="empty-hint">–</div>`
      );
    }

    _sessionStart() {
      const started = Date.parse(this._state("started")?.state);
      return Number.isFinite(started) ? started : 0;
    }

    _updateHistory() {
      if (!this._el.history) return;
      const since = this._sessionStart();
      const key = `${this._ids.events}|${since}`;
      if (this._historyFor !== key) {
        // A new session or board starts an empty history.
        this._historyFor = key;
        this._visits = [];
        this._seen = new Set();
        this._loadHistory(since, key);
      }
      const event = this._state("events");
      if (event?.attributes?.event_type === "visit_completed") {
        this._addVisits(visitsFromHistory([event], since));
      }
      this._drawHistory();
    }

    async _loadHistory(since, key) {
      const id = this._ids.events;
      if (!id || typeof this._hass.callWS !== "function") return;
      // The recorder keeps ten days by default; older visits are not needed.
      const start = Math.max(since, Date.now() - 7 * 86400000);
      try {
        const result = await this._hass.callWS({
          type: "history/history_during_period",
          start_time: new Date(start).toISOString(),
          entity_ids: [id],
          minimal_response: false,
          no_attributes: false,
          significant_changes_only: false,
        });
        if (this._historyFor !== key) return;
        this._addVisits(visitsFromHistory(result?.[id], since));
        this._drawHistory();
      } catch (error) {
        // Without the recorder, visits of the open dashboard still appear.
      }
    }

    _historySize() {
      return Math.min(60, Math.max(5, Number(this._config.history_size) || 20));
    }

    _addVisits(visits) {
      for (const visit of visits) {
        if (this._seen.has(visit.time)) continue;
        this._seen.add(visit.time);
        this._visits.push(visit);
      }
      this._visits.sort((a, b) => a.time - b.time);
      const size = this._historySize();
      if (this._visits.length > size) this._visits = this._visits.slice(-size);
    }

    _drawHistory() {
      const chart = this._el.history;
      if (!chart) return;
      const visits = this._visits;
      if (!visits.length) {
        chart.removeAttribute("role");
        chart.removeAttribute("aria-label");
        this._setHtml(chart, `<div class="empty-hint">${escapeHtml(this._t("history_empty"))}</div>`);
        return;
      }
      const size = this._historySize();
      const labels = size <= 30;
      const share = (score) => fmt(Math.min(180, Math.max(0, score)) / 180);
      const bars = visits.map((visit) => {
        const tip = `${visit.segments.join(" · ")}${visit.segments.length ? " = " : ""}${visit.score}`;
        return (
          `<div class="visit-bar" title="${escapeHtml(tip)}">` +
          (labels ? `<span class="label">${visit.score}</span>` : "") +
          `<div class="fill" style="--height:${share(visit.score)};background:${VISIT_COLORS[visitBucket(visit.score)]}"></div></div>`
        );
      });
      // Empty slots keep the bar width steady while the session fills the chart.
      for (let index = visits.length; index < size; index += 1) {
        bars.push(`<div class="visit-bar empty"><div class="fill"></div></div>`);
      }
      const average = this._number("average");
      const line =
        average !== null
          ? `<div class="average-line" style="--height:${share(average)}" title="${escapeHtml(
              `${this._t("average_long")}: ${this._format(average, 1)}`
            )}"></div>`
          : "";
      chart.setAttribute("role", "img");
      chart.setAttribute(
        "aria-label",
        `${this._t("history")}: ${visits.map((visit) => visit.score).join(", ")}`
      );
      this._setHtml(chart, line + bars.join(""));
    }
  }

  // Status card -----------------------------------------------------------------

  class AutodartsStatusCard extends CardBase {
    static keys = STATUS_KEYS;

    static defaults = STATUS_DEFAULTS;

    static form = "status";

    getCardSize() {
      return 7;
    }

    _css() {
      return STATUS_CSS;
    }

    _watched() {
      const cameras = Object.values(CAMERA_KEYS).flatMap((key) => this._index[key] || []);
      return [...Object.values(this._ids), ...cameras];
    }

    _build() {
      const c = this._config;
      const t = (key) => escapeHtml(this._t(key));
      const connections = `
        <div class="info-tile">
          <span class="section-label">${t("connections")}</span>
          <div class="chips"></div>
        </div>`;
      const system = `
        <div class="info-tile system-tile" hidden>
          <span class="section-label">${t("system")}</span>
          <div class="metrics"></div>
          <button class="system-info muted" hidden></button>
        </div>`;
      const cameras = `
        <div class="cameras-section" hidden>
          <div class="section-label">${t("cameras")}</div>
          <div class="camera-grid"></div>
        </div>`;
      const controls = `
        <div class="controls">
          <button data-action="calibrate">${t("calibrate")}</button>
          <button data-action="reset">${t("reset")}</button>
          <button data-action="restart">${t("restart")}</button>
        </div>`;
      this.shadowRoot.innerHTML = `
        <style>${STATUS_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="status-card">
              <header>
                <div class="title"></div>
                <div class="pill" role="status"></div>
              </header>
              <div class="detection">
                <div>
                  <div class="name">${t("detection")}</div>
                  <div class="state"></div>
                </div>
                <button class="toggle" role="switch" aria-checked="false" aria-label="${t("detection")}"></button>
              </div>
              <div class="info">
                <div class="info-tile board-tile">
                  <span class="section-label">${t("board")}</span>
                  <span class="value version">–</span>
                  <button class="badge update-badge"></button>
                </div>
                ${c.show_connection ? connections : ""}
                ${c.show_system ? system : ""}
              </div>
              ${c.show_cameras ? cameras : ""}
              ${c.show_controls ? controls : ""}
            </div>
          </div>
        </ha-card>`;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        pill: root.querySelector(".pill"),
        detectionState: root.querySelector(".detection .state"),
        toggle: root.querySelector(".toggle"),
        version: root.querySelector(".version"),
        update: root.querySelector(".update-badge"),
        chips: root.querySelector(".chips"),
        system: root.querySelector(".system-tile"),
        metrics: root.querySelector(".metrics"),
        systemInfo: root.querySelector(".system-info"),
        camerasSection: root.querySelector(".cameras-section"),
        cameras: root.querySelector(".camera-grid"),
        controls: root.querySelector(".controls"),
      };
      this._el.toggle.addEventListener("click", () => this._toggleDetection());
      this._el.update.addEventListener("click", () => this._moreInfo(this._ids.update));
      for (const list of [this._el.chips, this._el.metrics]) {
        list?.addEventListener("click", (event) => this._moreInfo(event.target.closest("[data-entity]")?.dataset.entity));
      }
      this._el.systemInfo?.addEventListener("click", () => this._moreInfo(this._ids.hostOs));
      this._el.cameras?.addEventListener("click", (event) => {
        const target = event.target.closest("[data-entity], [data-calibrate]");
        if (!target) return;
        if (target.dataset.entity) {
          this._moreInfo(target.dataset.entity);
          return;
        }
        if (this.preview) return;
        const action = `camera:${target.dataset.calibrate}`;
        if (this._confirmed(action)) this._press(target.dataset.calibrate);
        this._confirmChanged();
      });
      this._el.controls?.addEventListener("click", (event) => {
        const action = event.target.closest("button")?.dataset.action;
        if (!action || this.preview) return;
        if (this._confirmed(action)) this._press(this._ids[action]);
        this._confirmChanged();
      });
    }

    _confirmChanged() {
      if (!this._el) return;
      const [status] = this._status();
      this._updateControls(status);
      this._updateCameras(status);
    }

    _update() {
      const c = this._config;
      const el = this._el;
      const t = (key) => this._t(key);
      el.title.textContent = c.title || this._deviceName();
      const [status, statusText] = this._status();
      this.style.setProperty("--ad-status", STATUS_COLORS[status]);
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      el.pill.textContent = t(statusText);

      const running = detectionRunning((name) => this._state(name), status);
      el.toggle.setAttribute("aria-checked", String(running));
      el.toggle.disabled = status === "offline" || !(this._ids.detection || this._ids[running ? "stop" : "start"]);
      el.detectionState.textContent = t(statusText);

      const device = this._hass.devices?.[this._deviceId];
      el.version.textContent = device?.sw_version ? `${t("version")} ${device.sw_version}` : "–";
      const update = this._state("update");
      el.update.hidden = update?.state !== "on" && update?.state !== "off";
      el.update.classList.toggle("ok", update?.state === "off");
      el.update.disabled = update?.state !== "on";
      el.update.textContent =
        update?.state === "on" ? `${t("update_available")} ${update.attributes?.latest_version ?? ""}`.trim() : t("up_to_date");

      this._updateChips();
      this._updateSystem();
      this._updateCameras(status);
      this._updateControls(status);
    }

    _updateChips() {
      if (!this._el.chips) return;
      const chip = (name, text) => {
        const id = this._ids[name];
        if (!id) return "";
        const cls = this._hass.states[id]?.state === "on" ? "on" : "off";
        return `<button class="chip ${cls}" data-entity="${escapeHtml(id)}" data-focus="${escapeHtml(id)}">${escapeHtml(text)}</button>`;
      };
      this._setHtml(
        this._el.chips,
        [
          chip("connected", this._t("board")),
          chip("realtime", this._t("realtime")),
          this._ids.cloudLink ? chip("cloudLink", this._t("cloud")) : chip("upstream", this._t("cloud")),
        ].join("")
      );
    }

    _updateSystem() {
      if (!this._el.system) return;
      const metric = (name, text, value) =>
        value === null
          ? ""
          : `<button class="metric" data-entity="${escapeHtml(this._ids[name])}" data-focus="${escapeHtml(name)}">` +
            `<span class="value">${escapeHtml(value)}</span><span class="name">${escapeHtml(text)}</span></button>`;
      // Percentages read as Home Assistant writes them; other units keep their symbol.
      const measured = (name, digits, unit) => {
        const number = this._number(name);
        if (number === null) return null;
        if (unit === "%") return this._percent(number, digits);
        return `${this._format(number, digits)}${unit ? ` ${unit}` : ""}`;
      };
      const markup = [
        metric("cpu", this._t("cpu"), measured("cpu", 0, "%")),
        metric("memory", this._t("memory"), measured("memory", 0, this._state("memory")?.attributes?.unit_of_measurement)),
        metric("fps", this._t("detection_fps"), measured("fps", 1, "fps")),
        metric("corrected", this._t("corrected"), measured("corrected", 1, "%")),
      ].join("");
      const text = (name) => (usable(this._state(name)) ? String(this._state(name).state) : "");
      const vision = text("vision");
      const info = [
        text("hostOs"),
        shortProcessor(text("processor")),
        vision ? `${this._t("vision_short")} ${vision}` : "",
      ].filter(Boolean);
      if (this._el.systemInfo) {
        this._el.systemInfo.hidden = !info.length;
        this._el.systemInfo.textContent = info.join(" · ");
      }
      this._el.system.hidden = !markup && !info.length;
      this._setHtml(this._el.metrics, markup);
    }

    _updateCameras(status) {
      if (!this._el.cameras) return;
      const cameras = cameraEntities(this._hass, this._index);
      this._el.camerasSection.hidden = !cameras.length;
      const markup = cameras
        .map((camera) => {
          const problem = this._hass.states[camera.problem]?.state === "on";
          const fpsState = camera.fps ? this._hass.states[camera.fps] : undefined;
          const fps = usable(fpsState) ? `${this._format(Number(fpsState.state), 1)} fps` : "";
          const target = camera.image || camera.problem || camera.fps;
          const confirming = camera.calibrate && this._confirm === `camera:${camera.calibrate}`;
          const calibrate = camera.calibrate
            ? `<button class="action${confirming ? " confirm" : ""}" data-calibrate="${escapeHtml(camera.calibrate)}"` +
              ` data-focus="${escapeHtml(`calibrate:${camera.calibrate}`)}"${status === "offline" ? " disabled" : ""}>` +
              `${escapeHtml(this._t(confirming ? "confirm" : "calibrate"))}</button>`
            : "";
          return (
            `<div class="camera${problem ? " problem" : ""}">` +
            `<div class="camera-head"><button class="camera-name" data-entity="${escapeHtml(target || "")}"` +
            ` data-focus="${escapeHtml(`camera:${camera.number}`)}">` +
            `${escapeHtml(`${this._t("camera")} ${camera.number}`)}</button><span class="dot" title="${escapeHtml(
              this._t(problem ? "camera_failure" : "camera_ok")
            )}"></span></div>` +
            `<div class="fps">${escapeHtml(problem ? this._t("camera_failure") : fps || this._t("camera_ok"))}</div>` +
            `${calibrate}</div>`
          );
        })
        .join("");
      this._setHtml(this._el.cameras, markup);
    }

    _updateControls(status) {
      const controls = this._el.controls;
      if (!controls) return;
      for (const action of ["calibrate", "reset", "restart"]) {
        const button = controls.querySelector(`[data-action="${action}"]`);
        const confirming = this._confirm === action;
        button.textContent = this._t(confirming ? "confirm" : action);
        button.classList.toggle("confirm", confirming);
        button.hidden = !this._ids[action];
        button.disabled = status === "offline";
      }
    }
  }

  // Scoreboard card -------------------------------------------------------------

  class AutodartsScoreboardCard extends CardBase {
    static keys = SCOREBOARD_KEYS;

    static defaults = SCOREBOARD_DEFAULTS;

    static form = "scoreboard";

    getCardSize() {
      return 8;
    }

    getGridOptions() {
      return { columns: "full", min_columns: 6 };
    }

    _css() {
      return SCOREBOARD_CSS;
    }

    _build() {
      const c = this._config;
      const t = (key) => escapeHtml(this._t(key));
      // The label stays; the pressed state and the speaker tell whether the caller is on.
      const caller =
        `<button class="caller-toggle" aria-pressed="false" title="${t("caller_hint")}">` +
        `<span class="caller-icon" aria-hidden="true">🔇</span><span>${t("caller")}</span></button>`;
      this.shadowRoot.innerHTML = `
        <style>${SCOREBOARD_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="scoreboard${c.full_height ? " full" : ""}">
              <header>
                <div class="heading">
                  <div class="title"></div>
                  <div class="muted meta"></div>
                </div>
                <div class="header-actions">
                  ${c.caller ? caller : ""}
                  ${c.show_status ? `<div class="pill" role="status"></div>` : ""}
                </div>
              </header>
              <div class="banner" role="status" hidden></div>
              <div class="main"></div>
              ${c.show_visit ? `<div class="visit"></div>` : ""}
            </div>
          </div>
        </ha-card>
      `;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        meta: root.querySelector(".meta"),
        pill: root.querySelector(".pill"),
        banner: root.querySelector(".banner"),
        main: root.querySelector(".main"),
        visit: root.querySelector(".visit"),
        caller: root.querySelector(".caller-toggle"),
        callerIcon: root.querySelector(".caller-icon"),
      };
      this._callerState = null;
      this._el.caller?.addEventListener("click", () => this._toggleCaller());
    }

    // The tap that unlocks the sound; a second tap mutes the caller again.
    _toggleCaller() {
      if (this.preview) return;
      callerAudio.unlocked = !callerAudio.unlocked;
      if (callerAudio.unlocked) {
        const Context = window.AudioContext || window.webkitAudioContext;
        if (!callerAudio.context && Context) callerAudio.context = new Context();
        callerAudio.context?.resume?.();
        // Speaking inside the tap keeps browsers from blocking later calls.
        this._speak(this._t("caller_on"));
      } else {
        window.speechSynthesis?.cancel();
      }
      this._showCaller();
    }

    _showCaller() {
      const button = this._el.caller;
      if (!button) return;
      button.setAttribute("aria-pressed", String(callerAudio.unlocked));
      this._el.callerIcon.textContent = callerAudio.unlocked ? "🔊" : "🔇";
    }

    _speak(text) {
      const speech = window.speechSynthesis;
      if (!text || !speech || typeof SpeechSynthesisUtterance === "undefined") return;
      const utterance = new SpeechSynthesisUtterance(text);
      // The words are English or German, so the voice must be too.
      utterance.lang = voiceLanguage(this._hass);
      speech.speak(utterance);
    }

    _announce(visit, view) {
      const current = callerState(visit, view, this._callerState);
      const previous = this._callerState;
      this._callerState = current;
      if (!this._config.caller || !callerAudio.unlocked || this.preview) return;
      for (const call of callerCalls(previous, current, this._config)) {
        if (call.kind === "fanfare") playFanfare();
        else this._speak(callerText(call, (key) => this._t(key)));
      }
    }

    _update() {
      const c = this._config;
      const el = this._el;
      const t = (key) => this._t(key);
      this._showCaller();
      const [status, statusText] = this._status();
      this.style.setProperty("--ad-status", STATUS_COLORS[status]);
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      if (el.pill) el.pill.textContent = t(statusText);

      const visit = this._state("visit");
      const view = gameView((name) => this._state(name));
      const board = scoreboardHtml(view, {
        ...this._ui(),
        name: this._deviceName(),
        stats: {
          visit: usable(visit) ? visit.state : null,
          darts: this._number("darts"),
          average: this._number("average"),
          highest: this._number("highest"),
          max: this._number("max"),
          streak: this._number("streak"),
          today: this._number("today"),
          goal: Number(this._state("today")?.attributes?.goal) || 0,
        },
      });
      this._announce(visit, view);
      el.title.textContent = board.title;
      el.meta.textContent = board.meta;
      el.banner.hidden = !board.banner;
      el.banner.textContent = board.banner;
      this._setHtml(el.main, board.main);
      if (!el.visit) return;
      // Between games the big number already is the visit score.
      el.visit.classList.toggle("plain", view.mode === "idle");
      const darts = visitThrows(visit).slice(-3);
      const slots = [0, 1, 2].map((index) => {
        const dart = darts[index];
        return dart
          ? `<div class="dart"><span class="segment">${escapeHtml(label(this._hass, dart))}</span>` +
              `<span class="points">${dart.number * dart.multiplier}</span></div>`
          : `<div class="dart empty"><span class="segment">–</span><span class="points"></span></div>`;
      });
      const sum =
        view.mode === "idle"
          ? ""
          : `<div class="sum"><span class="muted">${escapeHtml(t("visit_short"))}</span>` +
            `<span class="value">${escapeHtml(usable(visit) ? visit.state : "–")}</span></div>`;
      this._setHtml(el.visit, slots.join("") + sum);
    }
  }

  // Players card ----------------------------------------------------------------

  class AutodartsPlayersCard extends CardBase {
    static keys = PLAYERS_KEYS;

    static defaults = PLAYERS_DEFAULTS;

    static form = "players";

    getCardSize() {
      return 6;
    }

    _css() {
      return PLAYERS_CSS;
    }

    _build() {
      const c = this._config;
      const t = (key) => escapeHtml(this._t(key));
      const section = (name, title) =>
        `<div class="${name}-section" hidden><div class="section-label">${t(title)}</div><div class="${name}"></div></div>`;
      this.shadowRoot.innerHTML = `
        <style>${PLAYERS_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="players-card">
              <header>
                <div class="title"></div>
                <div class="muted count"></div>
              </header>
              <div class="message empty" hidden>${t("no_profiles")}</div>
              <div class="profiles"></div>
              ${c.show_head_to_head ? section("h2h", "head_to_head") : ""}
              ${c.show_matches ? section("matches", "recent_matches") : ""}
            </div>
          </div>
        </ha-card>
      `;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        count: root.querySelector(".count"),
        empty: root.querySelector(".empty"),
        profiles: root.querySelector(".profiles"),
        h2hSection: root.querySelector(".h2h-section"),
        h2h: root.querySelector(".h2h"),
        matchesSection: root.querySelector(".matches-section"),
        matches: root.querySelector(".matches"),
      };
    }

    _update() {
      const c = this._config;
      const el = this._el;
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      el.title.textContent = c.title || this._t("players_title");
      const view = playersView(this._state("profiles"), this._state("lastMatch"));
      el.count.textContent = view.players.length ? String(view.players.length) : "";
      el.empty.hidden = view.players.length > 0;
      const html = playersHtml(view, this._ui());
      this._setHtml(el.profiles, html.players);
      if (el.h2hSection) {
        el.h2hSection.hidden = !view.headToHead.length;
        this._setHtml(el.h2h, html.headToHead);
      }
      if (el.matchesSection) {
        el.matchesSection.hidden = !view.matches.length;
        this._setHtml(el.matches, html.matches);
      }
    }
  }

  // Doubles card ----------------------------------------------------------------

  class AutodartsDoublesCard extends CardBase {
    static keys = DOUBLES_KEYS;

    static defaults = DOUBLES_DEFAULTS;

    static form = "doubles";

    getCardSize() {
      return 6;
    }

    _css() {
      return DOUBLES_CSS;
    }

    _build() {
      const t = (key) => escapeHtml(this._t(key));
      this.shadowRoot.innerHTML = `
        <style>${DOUBLES_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="doubles-card">
              <header>
                <div class="title"></div>
                <div class="muted meta"></div>
              </header>
              <div class="message empty" hidden></div>
              <div class="doubles-body">
                <div class="doubles-board">
                  <svg viewBox="-230 -230 460 460" role="img">
                    <g class="face">${boardSvg("muted")}</g>
                    <g class="ring"></g>
                    <g class="numbers">${numbersSvg("muted")}</g>
                  </svg>
                </div>
                <div>
                  <div class="double-list"></div>
                  <p class="muted">${t("doubles_routes")}</p>
                </div>
              </div>
            </div>
          </div>
        </ha-card>
      `;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        meta: root.querySelector(".meta"),
        empty: root.querySelector(".empty"),
        body: root.querySelector(".doubles-body"),
        ring: root.querySelector(".ring"),
        list: root.querySelector(".double-list"),
        svg: root.querySelector("svg"),
      };
    }

    _update() {
      const c = this._config;
      const el = this._el;
      const t = (key) => this._t(key);
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      const view = doublesView(this._state("doubles"), this._state("profiles"), c.player);
      el.title.textContent = c.title || [t("doubles_title"), view.player].filter(Boolean).join(" · ");
      el.meta.textContent = view.attempts
        ? `${this._format(view.attempts)} ${t("doubles_darts")}` +
          (view.rate === null ? "" : ` · ${this._percent(view.rate, 1)}`)
        : "";
      el.empty.hidden = view.doubles.length > 0;
      // A name without a profile is most likely mistyped, which the card says.
      el.empty.textContent = view.known ? t("doubles_empty") : fill(t("doubles_unknown_player"), { player: view.player });
      el.body.hidden = view.doubles.length === 0;
      el.svg.setAttribute("aria-label", t("doubles_title"));
      const html = doublesHtml(view, this._ui());
      this._setHtml(el.ring, html.ring);
      this._setHtml(el.list, html.list);
    }
  }

  // Dashboard strategy -----------------------------------------------------------

  // The editor of the dashboard strategy: the board and the title.
  class AutodartsStrategyEditor extends Base {
    setConfig(config) {
      this._config = { ...config };
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    connectedCallback() {
      if (customElements.get("ha-form")) this._render();
      else customElements.whenDefined("ha-form").then(() => this._render());
    }

    _render() {
      if (!this._hass || !this._config || !customElements.get("ha-form")) return;
      if (!this._form) {
        const form = document.createElement("ha-form");
        form.schema = STRATEGY_FORM;
        form.computeLabel = (field) => translate(this._hass, field.name);
        form.computeHelper = (field) =>
          field.name === "device_id" ? translate(this._hass, "strategy_device_helper") : undefined;
        form.addEventListener("value-changed", (event) => {
          event.stopPropagation();
          const config = { ...event.detail.value };
          for (const key of ["device_id", "title"]) if (!config[key]) delete config[key];
          this._config = config;
          this.dispatchEvent(new CustomEvent("config-changed", { bubbles: true, composed: true, detail: { config } }));
        });
        this.appendChild(form);
        this._form = form;
      }
      this._form.hass = this._hass;
      this._form.data = this._config;
    }
  }

  class AutodartsDashboardStrategy extends Base {
    static async generate(config, hass) {
      return dashboardStrategy(hass, config);
    }

    static async getConfigElement() {
      await loadForm();
      return document.createElement(STRATEGY_EDITOR_TYPE);
    }
  }

  return {
    [STRATEGY_ELEMENT]: AutodartsDashboardStrategy,
    [STRATEGY_EDITOR_TYPE]: AutodartsStrategyEditor,
    [CARD_TYPE]: AutodartsCard,
    [TRAINING_TYPE]: AutodartsTrainingCard,
    [STATUS_TYPE]: AutodartsStatusCard,
    [SCOREBOARD_TYPE]: AutodartsScoreboardCard,
    [PLAYERS_TYPE]: AutodartsPlayersCard,
    [DOUBLES_TYPE]: AutodartsDoublesCard,
  };
}

// Registration ------------------------------------------------------------------

// Card picker entries with their documentation in both languages.
const CARDS = [
  { type: CARD_TYPE, key: "live", docs: ["cards.md#live-card", "de/karten.md#live-karte"] },
  { type: TRAINING_TYPE, key: "training", docs: ["cards.md#training-card", "de/karten.md#trainingskarte"] },
  { type: STATUS_TYPE, key: "status", docs: ["cards.md#board-status-card", "de/karten.md#board-status"] },
  { type: SCOREBOARD_TYPE, key: "scoreboard", docs: ["cards.md#scoreboard-card", "de/karten.md#anzeigetafel"] },
  { type: PLAYERS_TYPE, key: "players", docs: ["cards.md#players-card", "de/karten.md#spielerkarte"] },
  { type: DOUBLES_TYPE, key: "doubles", docs: ["cards.md#doubles-card", "de/karten.md#doubles-karte"] },
];
const STRATEGY_DOCS = ["cards.md#automatic-dashboard", "de/karten.md#automatisches-dashboard"];

const documentation = ([en, de]) => `${REPOSITORY}/${pageLanguage() === "de" ? de : en}`;

// Home Assistant reads the entries when it opens its card picker, so the
// getters answer in the language of that moment.
const pickerEntry = ({ type, key, docs }) => ({
  type,
  preview: true,
  get name() {
    return pageText(`picker_${key}`);
  },
  get description() {
    return pageText(`picker_${key}_description`);
  },
  get documentationURL() {
    return documentation(docs);
  },
});

function register() {
  const registry = window.customElements;
  for (const [type, element] of Object.entries(createElements(window.HTMLElement))) {
    if (!registry.get(type)) registry.define(type, element);
  }
  window.customCards = window.customCards || [];
  for (const card of CARDS) {
    if (!window.customCards.some((known) => known.type === card.type)) window.customCards.push(pickerEntry(card));
  }
  // Offered in the "Add dashboard" dialog of Home Assistant.
  window.customStrategies = window.customStrategies || [];
  if (!window.customStrategies.some((known) => known.type === STRATEGY_TYPE)) {
    window.customStrategies.push({
      type: STRATEGY_TYPE,
      strategyType: "dashboard",
      name: "Autodarts",
      get description() {
        return pageText("picker_strategy_description");
      },
      get documentationURL() {
        return documentation(STRATEGY_DOCS);
      },
    });
  }
}

// Home Assistant loads this module in parallel with its own app, which then swaps in
// a scoped custom element registry. Elements defined before that swap stay invisible
// to dashboards, so the cards wait for the app element; other hosts get them after a timeout.
async function frontendReady(timeout = 30000) {
  const registry = window.customElements;
  if (registry.get("home-assistant")) return;
  let timer;
  const expired = new Promise((resolve) => {
    timer = setTimeout(resolve, timeout);
  });
  await Promise.race([registry.whenDefined?.("home-assistant") ?? expired, expired]);
  clearTimeout(timer);
}

if (globalThis.window?.customElements) frontendReady().then(register);

export {
  aimBeds,
  bedPath,
  beds,
  bestsHtml,
  bestsView,
  boardStatus,
  boardSvg,
  bullOffView,
  callerCalls,
  callerState,
  callerText,
  cameraEntities,
  cardForm,
  createElements,
  cricketBeds,
  cricketTable,
  cricketView,
  cssColor,
  dartKey,
  dashboardStrategy,
  detectionRunning,
  doubleColor,
  doublesHtml,
  doublesView,
  drillBeds,
  drillView,
  entityIndex,
  escapeHtml,
  formatDateTime,
  formatNumber,
  formatPercent,
  frontendReady,
  gameView,
  heatColor,
  heatLevels,
  heatRatio,
  hitBeds,
  kind,
  label,
  livePanel,
  NORM,
  NUMBERS,
  numbersSvg,
  parseSegment,
  partyBeds,
  partyView,
  pastSessions,
  playersHtml,
  playersView,
  practiceView,
  profileNames,
  R,
  recentVisits,
  register,
  scoreboardHtml,
  sectorAt,
  shortProcessor,
  targetBeds,
  topHits,
  visitBucket,
  visitCount,
  visitsFromHistory,
  voiceLanguage,
};
