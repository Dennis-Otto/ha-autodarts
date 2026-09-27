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
 * - autodarts-leaderboard-card: records across all players, for all time, the
 *   last four weeks or this week.
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
const LEADERBOARD_TYPE = "autodarts-leaderboard-card";
const STRATEGY_TYPE = "autodarts";
const STRATEGY_ELEMENT = `ll-strategy-dashboard-${STRATEGY_TYPE}`;
const STRATEGY_EDITOR_TYPE = "autodarts-strategy-editor";
const REPOSITORY = "https://github.com/Dennis-Otto/ha-autodarts/blob/main/docs";
// Files of the action autodarts.export, downloaded with the user's login.
const EXPORT_DOWNLOADS = "/api/autodarts/export/";

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
    practice_starts: "Start scores (handicap)",
    practice_game_row: "Game",
    // How the names of practice entities read; the dashboard shows them without the section.
    practice_entity: "Practice {name}",
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
    drill_checkout_121: "121 checkout",
    drill_catch_40: "Catch 40",
    drill_jdc_challenge: "JDC Challenge",
    drill_singles: "Singles training",
    drill_part: "Part",
    drill_best: "Best",
    drill_target: "Target",
    cricket: "Cricket",
    cricket_cut_throat: "Cut-Throat Cricket",
    cricket_tactics: "Tactics",
    cut_throat_hint: "Fewest points win",
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
    party_golf: "Golf",
    party_baseball: "Baseball",
    party_count_up: "Count-Up",
    golf_hole: "Hole",
    baseball_inning: "Inning",
    playoff: "Play-off",
    golf_hint: "The last dart counts – pull your darts to stop",
    total: "Total",
    team: "Team",
    score_winners: "win the match!",
    start_score: "Start score",
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
    export: "Show export button",
    export_format: "Export format",
    export_format_csv: "CSV (a ZIP file with one table each)",
    export_format_json: "JSON",
    export_button: "Export",
    exporting: "Exporting …",
    export_failed: "Export failed",
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
    say_run: "One run",
    say_runs: "{runs} runs",
    say_leg: "Game shot, and the leg!",
    say_match: "Game shot, and the match, {name}!",
    // New game screen of the scoreboard
    lobby_open: "New game",
    lobby_title: "New game",
    lobby_label: "Choose the game, the players and the format",
    lobby_group_x01: "X01",
    lobby_group_cricket: "Cricket",
    lobby_group_party: "Party games",
    lobby_group_training: "Training games",
    lobby_group_more: "More games",
    lobby_players: "Players",
    lobby_guest: "Guest",
    lobby_add: "Add",
    lobby_name: "Name",
    lobby_new_player: "Name of another player",
    lobby_home: "at home",
    lobby_move_up: "Move {name} up",
    lobby_move_down: "Move {name} down",
    lobby_remove: "Remove {name}",
    lobby_format: "Format",
    lobby_legs: "Legs per set",
    lobby_sets: "Sets to win",
    lobby_decrease: "Fewer: {name}",
    lobby_increase: "More: {name}",
    lobby_options: "Options",
    lobby_one_player: "Training games are for one player: {name} plays.",
    lobby_nobody: "Nobody chosen: one player throws without a name.",
    lobby_start: "Start {game}",
    lobby_close: "Close",
    lobby_end: "End game",
    lobby_start_lower: "Lower start score: {name}",
    lobby_start_raise: "Higher start score: {name}",
    teams: "Teams (1 + 3 against 2 + 4)",
    double_out: "Double out",
    double_in: "Double in",
    bull_off_distance: "Bull-off by distance",
    // Idle mode of the scoreboard
    idle_panel_leaderboard: "Leaderboard",
    idle_panel_records: "Personal bests",
    idle_panel_today: "Today",
    idle_panel_last_match: "Last match",
    idle_panel_clock: "Clock",
    idle_legs: "Legs {won}/{played}",
    idle_goal: "of {goal} darts",
    idle_back: "Tap to return",
    // Tournaments
    tournament: "Tournament",
    tournament_entity: "Tournament {name}",
    tournament_round_robin: "Round robin",
    tournament_knockout: "Knockout",
    tournament_round: "Round {round}",
    tournament_stage_quarter_final: "Quarter-final",
    tournament_stage_semi_final: "Semi-final",
    tournament_stage_third_place: "Third-place match",
    tournament_stage_final: "Final",
    tournament_match: "Match {match} of {matches}",
    tournament_progress: "{played} of {total} matches played",
    tournament_next: "Next up",
    tournament_vs: "vs",
    tournament_countdown: "starts in {time}",
    tournament_after_takeout: "starts when the board is clear",
    tournament_on_request: "starts with Next tournament match",
    tournament_start_now: "Start now",
    tournament_winner: "{name} wins the tournament!",
    tournament_bye: "Bye",
    tournament_open: "Still open",
    tournament_player: "Player",
    tournament_played: "P",
    tournament_played_long: "Matches played",
    tournament_won: "W",
    tournament_won_long: "Matches won",
    tournament_lost: "L",
    tournament_lost_long: "Matches lost",
    tournament_legs: "Legs",
    tournament_legs_long: "Legs won and lost",
    tournament_difference: "+/−",
    tournament_difference_long: "Leg difference",
    tournament_points: "Pts",
    tournament_points_long: "Points: two for a win",
    tournament_start: "Start tournament",
    tournament_stop: "Stop tournament",
    tournament_needs_players: "A tournament needs three to eight players.",
    tournament_mode: "Match or tournament",
    tournament_mode_match: "Match",
    tournament_mode_tournament: "Tournament",
    third_place: "Third-place match",
    random_draw: "Random draw",
    idle_panel_tournament: "Tournament",
    say_tournament_next: "Next match: {first} against {second}",
    say_tournament_won: "{name} wins the tournament!",
    // Scoreboard editor
    lobby: "New game screen",
    lobby_games: "Games offered",
    lobby_games_helper: "Empty offers every game of the board.",
    lobby_section: "New game screen",
    lobby_section_helper: "Tap New game to choose the game, the players and the format; it also opens a few seconds after a game ends.",
    idle: "Idle mode",
    idle_after: "Idle after",
    idle_interval: "Next panel after",
    idle_panels: "Panels",
    idle_panels_helper: "Empty shows every panel.",
    idle_section: "Idle mode",
    idle_section_helper: "When no game runs and nobody throws or taps, the scoreboard shows these panels in turn.",
    // Bull targets, the bull-off and the result of a match
    bull_target: "Bull (25/50)",
    bull_off_rethrow: "Tie – throw again",
    bull_off_leads: "leads",
    score_winner_by: "wins the match {result}!",
    score_winners_by: "win the match {result}!",
    // Match summary
    summary: "Match summary",
    summary_marks: "Marks",
    summary_best_leg: "Best leg",
    summary_checkout: "Checkout rate",
    summary_at_double: "Darts at a double",
    show_summary: "Show the match summary",
    summary_seconds: "Match summary (seconds)",
    summary_seconds_helper: "How long the summary stays after a match; 0 keeps it until the next game starts.",
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
    // Progress: badges, trends, grouping, dart positions and the leaderboard
    badges: "Badges",
    badge_count: "{count} badges",
    badge_count_one: "1 badge",
    badge_locked: "Locked",
    badge_earned: "Earned {date}",
    badge_progress: "{value} of {goal}",
    badge_best: "Best so far: {value}",
    tier_1: "Bronze",
    tier_2: "Silver",
    tier_3: "Gold",
    tier_4: "Platinum",
    achievement_maximum: "180",
    achievement_maximum_goal: "180s in X01: {value}",
    achievement_ton_plus: "Ton-plus visits",
    achievement_ton_plus_goal: "X01 visits of 100 or more: {value}",
    achievement_ton_forty: "Ton-forty visits",
    achievement_ton_forty_goal: "X01 visits of 140 or more: {value}",
    achievement_high_finish: "High finish",
    achievement_high_finish_goal: "A checkout of {value} or more",
    achievement_short_leg: "Short leg",
    achievement_short_leg_goal: "A 501 leg in {value} darts or fewer",
    achievement_nine_darter: "Nine-darter",
    achievement_nine_darter_goal: "A 501 leg in nine darts",
    achievement_legs_won: "Legs won",
    achievement_legs_won_goal: "Legs won: {value}",
    achievement_matches_won: "Matches won",
    achievement_matches_won_goal: "Matches won: {value}",
    achievement_hat_trick: "Hat trick",
    achievement_hat_trick_goal: "Three bulls in one visit",
    achievement_all_doubles: "Every double",
    achievement_all_doubles_goal: "Every double from D1 to D20 and the bullseye",
    achievement_cricket_nine: "Nine marks",
    achievement_cricket_nine_goal: "Three trebles in one Cricket visit",
    achievement_shanghai: "Shanghai",
    achievement_shanghai_goal: "Win Shanghai with a single, double and treble",
    achievement_around_the_clock: "Around the Clock",
    achievement_around_the_clock_goal: "Around the Clock in {value} darts or fewer",
    achievement_bobs_27: "Bob's 27",
    achievement_bobs_27_goal: "Bob's 27 with {value} points or more",
    achievement_streak: "Streak",
    achievement_streak_goal: "Days in a row: {value}",
    achievement_darts_thrown: "Darts thrown",
    achievement_darts_thrown_goal: "Darts thrown: {value}",
    show_badges: "Show badges",
    show_locked: "Show locked badges",
    show_trends: "Show trends",
    show_spread: "Show grouping",
    trend_weeks: "Weeks in the trends",
    trends: "Trends",
    trends_range: "last {weeks} weeks",
    doubles_rate_short: "Doubles",
    trend_up: "rising",
    trend_down: "falling",
    trend_steady: "steady",
    spread: "Grouping",
    spread_group: "grouping {r50}",
    spread_group80: "80 % within {r80}",
    spread_left: "{distance} left of center",
    spread_right: "{distance} right of center",
    spread_high: "{distance} high",
    spread_low: "{distance} low",
    spread_centered: "centered",
    spread_tighter: "{value} tighter",
    spread_wider: "{value} wider",
    spread_hint: "Half of the darts land within the grouping around their mean point, 80 % within the second radius.",
    unit_mm: "{value} mm",
    mode_positions: "Positions",
    heatmap_source: "Whose darts",
    heatmap_session: "Session",
    show_heatmap_controls: "Show the heatmap switches",
    heatmap_player_helper:
      "Optional. The heatmap starts with this player's darts instead of the session's; the switches above the board change it.",
    positions_label: "Dartboard with the positions of the darts",
    positions_empty: "No dart positions yet.",
    legend_few: "few",
    legend_many: "many",
    leaderboard: "Leaderboard",
    period: "Period",
    period_all: "All time",
    period_month: "Last 4 weeks",
    period_week: "This week",
    show_period: "Show the period switch",
    limit: "Places per record",
    record_average: "Best average",
    record_checkout: "Highest checkout",
    record_maximums: "Most 180s",
    record_best_501: "Fewest darts, 501",
    record_mpr: "Best Cricket MPR",
    record_streak: "Longest streak",
    record_achievements: "Most badges",
    record_darts: "Most darts",
    leaderboard_empty: "No records yet. Name the players of a practice game, and their legs make the leaderboard.",
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
    picker_leaderboard: "Autodarts leaderboard",
    picker_leaderboard_description:
      "Records across all players: best average, highest checkout, most 180s, fewest darts and more, for all time, the last four weeks or this week.",
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
    practice_starts: "Startpunkte (Handicap)",
    practice_game_row: "Spiel",
    practice_entity: "Übungsspiel {name}",
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
    drill_checkout_121: "121-Checkout",
    drill_catch_40: "Catch 40",
    drill_jdc_challenge: "JDC Challenge",
    drill_singles: "Singles-Training",
    drill_part: "Teil",
    drill_best: "Bestes",
    drill_target: "Ziel",
    cricket: "Cricket",
    cricket_cut_throat: "Cut-Throat Cricket",
    cricket_tactics: "Tactics",
    cut_throat_hint: "Die wenigsten Punkte gewinnen",
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
    party_golf: "Golf",
    party_baseball: "Baseball",
    party_count_up: "Count-Up",
    golf_hole: "Loch",
    baseball_inning: "Inning",
    playoff: "Stechen",
    golf_hint: "Der letzte Dart zählt – zieh deine Darts, um aufzuhören",
    total: "Gesamt",
    team: "Team",
    score_winners: "gewinnen das Match!",
    start_score: "Startpunkte",
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
    export: "Export-Button anzeigen",
    export_format: "Exportformat",
    export_format_csv: "CSV (eine ZIP-Datei mit je einer Tabelle)",
    export_format_json: "JSON",
    export_button: "Exportieren",
    exporting: "Exportiere …",
    export_failed: "Export fehlgeschlagen",
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
    say_run: "Ein Run",
    say_runs: "{runs} Runs",
    say_leg: "Game shot, und das Leg!",
    say_match: "Game shot, und das Match, {name}!",
    lobby_open: "Neues Spiel",
    lobby_title: "Neues Spiel",
    lobby_label: "Wähle das Spiel, die Spieler und das Format",
    lobby_group_x01: "X01",
    lobby_group_cricket: "Cricket",
    lobby_group_party: "Partyspiele",
    lobby_group_training: "Trainingsspiele",
    lobby_group_more: "Weitere Spiele",
    lobby_players: "Spieler",
    lobby_guest: "Gast",
    lobby_add: "Hinzufügen",
    lobby_name: "Name",
    lobby_new_player: "Name eines weiteren Spielers",
    lobby_home: "zu Hause",
    lobby_move_up: "{name} nach oben",
    lobby_move_down: "{name} nach unten",
    lobby_remove: "{name} entfernen",
    lobby_format: "Format",
    lobby_legs: "Legs pro Satz",
    lobby_sets: "Sätze zum Sieg",
    lobby_decrease: "Weniger: {name}",
    lobby_increase: "Mehr: {name}",
    lobby_options: "Optionen",
    lobby_one_player: "Trainingsspiele sind für einen Spieler: {name} spielt.",
    lobby_nobody: "Niemand gewählt: Ein Spieler wirft ohne Namen.",
    lobby_start: "{game} starten",
    lobby_close: "Schließen",
    lobby_end: "Spiel beenden",
    lobby_start_lower: "Weniger Startpunkte: {name}",
    lobby_start_raise: "Mehr Startpunkte: {name}",
    teams: "Teams (1 + 3 gegen 2 + 4)",
    double_out: "Double-Out",
    double_in: "Double-In",
    bull_off_distance: "Ausbullen nach Abstand",
    idle_panel_leaderboard: "Bestenliste",
    idle_panel_records: "Bestleistungen",
    idle_panel_today: "Heute",
    idle_panel_last_match: "Letztes Match",
    idle_panel_clock: "Uhr",
    idle_legs: "Legs {won}/{played}",
    idle_goal: "von {goal} Darts",
    idle_back: "Tippen, um zurückzukehren",
    tournament: "Turnier",
    tournament_entity: "Turnier {name}",
    tournament_round_robin: "Jeder gegen jeden",
    tournament_knockout: "K.-o.-System",
    tournament_round: "Runde {round}",
    tournament_stage_quarter_final: "Viertelfinale",
    tournament_stage_semi_final: "Halbfinale",
    tournament_stage_third_place: "Spiel um Platz 3",
    tournament_stage_final: "Finale",
    tournament_match: "Match {match} von {matches}",
    tournament_progress: "{played} von {total} Matches gespielt",
    tournament_next: "Als Nächstes",
    tournament_vs: "gegen",
    tournament_countdown: "beginnt in {time}",
    tournament_after_takeout: "beginnt, sobald das Board frei ist",
    tournament_on_request: "beginnt mit Nächstes Turniermatch",
    tournament_start_now: "Jetzt starten",
    tournament_winner: "{name} gewinnt das Turnier!",
    tournament_bye: "Freilos",
    tournament_open: "Noch offen",
    tournament_player: "Spieler",
    tournament_played: "Sp.",
    tournament_played_long: "Gespielte Matches",
    tournament_won: "S",
    tournament_won_long: "Gewonnene Matches",
    tournament_lost: "N",
    tournament_lost_long: "Verlorene Matches",
    tournament_legs: "Legs",
    tournament_legs_long: "Gewonnene und verlorene Legs",
    tournament_difference: "+/−",
    tournament_difference_long: "Leg-Differenz",
    tournament_points: "Pkt.",
    tournament_points_long: "Punkte: zwei für einen Sieg",
    tournament_start: "Turnier starten",
    tournament_stop: "Turnier beenden",
    tournament_needs_players: "Ein Turnier braucht drei bis acht Spieler.",
    tournament_mode: "Match oder Turnier",
    tournament_mode_match: "Match",
    tournament_mode_tournament: "Turnier",
    third_place: "Spiel um Platz 3",
    random_draw: "Zufällige Auslosung",
    idle_panel_tournament: "Turnier",
    say_tournament_next: "Nächstes Match: {first} gegen {second}",
    say_tournament_won: "{name} gewinnt das Turnier!",
    lobby: "Spielauswahl",
    lobby_games: "Angebotene Spiele",
    lobby_games_helper: "Leer bietet jedes Spiel des Boards an.",
    lobby_section: "Spielauswahl",
    lobby_section_helper: "Tippe auf Neues Spiel, um Spiel, Spieler und Format zu wählen; die Auswahl öffnet sich auch einige Sekunden nach dem Ende eines Spiels.",
    idle: "Ruhemodus",
    idle_after: "Ruhemodus nach",
    idle_interval: "Nächste Tafel nach",
    idle_panels: "Tafeln",
    idle_panels_helper: "Leer zeigt jede Tafel.",
    idle_section: "Ruhemodus",
    idle_section_helper: "Läuft kein Spiel und wirft oder tippt niemand, zeigt die Anzeigetafel diese Tafeln im Wechsel.",
    bull_target: "Bull (25/50)",
    bull_off_rethrow: "Gleichstand – noch einmal werfen",
    bull_off_leads: "führt",
    score_winner_by: "gewinnt das Match {result}!",
    score_winners_by: "gewinnen das Match {result}!",
    summary: "Match-Zusammenfassung",
    summary_marks: "Marks",
    summary_best_leg: "Bestes Leg",
    summary_checkout: "Checkout-Quote",
    summary_at_double: "Darts aufs Double",
    show_summary: "Match-Zusammenfassung anzeigen",
    summary_seconds: "Match-Zusammenfassung (Sekunden)",
    summary_seconds_helper: "Wie lange die Zusammenfassung nach einem Match bleibt; 0 zeigt sie bis zum nächsten Spiel.",
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
    // Fortschritt: Abzeichen, Trends, Streuung, Dart-Positionen und die Bestenliste
    badges: "Abzeichen",
    badge_count: "{count} Abzeichen",
    badge_count_one: "1 Abzeichen",
    badge_locked: "Gesperrt",
    badge_earned: "Erreicht {date}",
    badge_progress: "{value} von {goal}",
    badge_best: "Bestwert bisher: {value}",
    tier_1: "Bronze",
    tier_2: "Silber",
    tier_3: "Gold",
    tier_4: "Platin",
    achievement_maximum: "180",
    achievement_maximum_goal: "180er in X01: {value}",
    achievement_ton_plus: "100+-Aufnahmen",
    achievement_ton_plus_goal: "X01-Aufnahmen mit 100 oder mehr: {value}",
    achievement_ton_forty: "140+-Aufnahmen",
    achievement_ton_forty_goal: "X01-Aufnahmen mit 140 oder mehr: {value}",
    achievement_high_finish: "High Finish",
    achievement_high_finish_goal: "Ein Checkout von {value} oder mehr",
    achievement_short_leg: "Kurzes Leg",
    achievement_short_leg_goal: "Ein 501-Leg mit höchstens {value} Darts",
    achievement_nine_darter: "Neun-Darter",
    achievement_nine_darter_goal: "Ein 501-Leg mit neun Darts",
    achievement_legs_won: "Gewonnene Legs",
    achievement_legs_won_goal: "Gewonnene Legs: {value}",
    achievement_matches_won: "Gewonnene Matches",
    achievement_matches_won_goal: "Gewonnene Matches: {value}",
    achievement_hat_trick: "Hattrick",
    achievement_hat_trick_goal: "Drei Bulls in einer Aufnahme",
    achievement_all_doubles: "Alle Doubles",
    achievement_all_doubles_goal: "Jedes Double von D1 bis D20 und das Bullseye",
    achievement_cricket_nine: "Neun Marks",
    achievement_cricket_nine_goal: "Drei Triples in einer Cricket-Aufnahme",
    achievement_shanghai: "Shanghai",
    achievement_shanghai_goal: "Shanghai mit Single, Double und Triple gewinnen",
    achievement_around_the_clock: "Around the Clock",
    achievement_around_the_clock_goal: "Around the Clock mit höchstens {value} Darts",
    achievement_bobs_27: "Bob's 27",
    achievement_bobs_27_goal: "Bob's 27 mit mindestens {value} Punkten",
    achievement_streak: "Serie",
    achievement_streak_goal: "Tage in Folge: {value}",
    achievement_darts_thrown: "Geworfene Darts",
    achievement_darts_thrown_goal: "Geworfene Darts: {value}",
    show_badges: "Abzeichen anzeigen",
    show_locked: "Gesperrte Abzeichen anzeigen",
    show_trends: "Trends anzeigen",
    show_spread: "Streuung anzeigen",
    trend_weeks: "Wochen in den Trends",
    trends: "Trends",
    trends_range: "letzte {weeks} Wochen",
    doubles_rate_short: "Doubles",
    trend_up: "steigend",
    trend_down: "fallend",
    trend_steady: "gleichbleibend",
    spread: "Streuung",
    spread_group: "Streuung {r50}",
    spread_group80: "80 % innerhalb {r80}",
    spread_left: "{distance} links der Mitte",
    spread_right: "{distance} rechts der Mitte",
    spread_high: "{distance} zu hoch",
    spread_low: "{distance} zu tief",
    spread_centered: "mittig",
    spread_tighter: "{value} enger",
    spread_wider: "{value} weiter",
    spread_hint: "Die Hälfte der Darts landet innerhalb der Streuung um ihren Mittelpunkt, 80 % innerhalb des zweiten Radius.",
    unit_mm: "{value} mm",
    mode_positions: "Positionen",
    heatmap_source: "Wessen Darts",
    heatmap_session: "Session",
    show_heatmap_controls: "Umschalter der Heatmap anzeigen",
    heatmap_player_helper:
      "Optional. Die Heatmap zeigt zuerst die Darts dieses Spielers statt der Session; die Umschalter über der Scheibe wechseln das.",
    positions_label: "Dartscheibe mit den Positionen der Darts",
    positions_empty: "Noch keine Dart-Positionen.",
    legend_few: "wenige",
    legend_many: "viele",
    leaderboard: "Bestenliste",
    period: "Zeitraum",
    period_all: "Gesamt",
    period_month: "Letzte 4 Wochen",
    period_week: "Diese Woche",
    show_period: "Umschalter des Zeitraums anzeigen",
    limit: "Plätze je Rekord",
    record_average: "Bester Average",
    record_checkout: "Höchster Checkout",
    record_maximums: "Meiste 180er",
    record_best_501: "Wenigste Darts, 501",
    record_mpr: "Beste Cricket-MPR",
    record_streak: "Längste Serie",
    record_achievements: "Meiste Abzeichen",
    record_darts: "Meiste Darts",
    leaderboard_empty: "Noch keine Rekorde. Gib den Spielern eines Übungsspiels Namen, dann kommen ihre Legs in die Bestenliste.",
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
    picker_leaderboard: "Autodarts Bestenliste",
    picker_leaderboard_description:
      "Rekorde aller Spieler: bester Average, höchster Checkout, meiste 180er, wenigste Darts und mehr, gesamt, in den letzten vier Wochen oder in dieser Woche.",
    picker_strategy_description:
      "Live-, Anzeigetafel-, Trainings-, Spieler- und Board-Ansicht für jedes Autodarts-Board, automatisch erstellt.",
  },
  es: {
    visit: "Tirada actual",
    points: "puntos",
    dart: "Dardo",
    of: "de",
    miss: "Fallo",
    session: "Sesión de entrenamiento",
    since: "desde",
    darts: "Dardos",
    average: "Media 3 d.",
    triples: "Triples",
    bulls: "Bulls",
    max: "180",
    board: "Board Manager",
    realtime: "Tiempo real",
    cameras: "Cámaras",
    camera_problem: "Revisar cámaras",
    start: "Iniciar detección",
    stop: "Detener detección",
    reset: "Restablecer detección",
    calibrate: "Calibrar",
    confirm: "¿Confirmar?",
    status_offline: "Diana inaccesible",
    status_calibrating: "Calibrando",
    status_problem: "Revisar cámaras",
    status_starting: "Iniciando detección",
    status_stopping: "Deteniendo detección",
    status_stopped: "Detección detenida",
    status_takeout: "Retirando dardos",
    status_hand: "Mano en la diana",
    status_full: "Retira tus dardos",
    status_ready: "Todo listo – ¡lanza!",
    no_board: "No se ha encontrado ninguna diana Autodarts. Selecciona un dispositivo en la configuración de la tarjeta.",
    board_label: "Diana con la tirada actual",
    device_id: "Diana",
    device_helper: "Opcional. Sin selección, la tarjeta usa la primera diana Autodarts.",
    title: "Título",
    layout: "Disposición",
    layout_auto: "Automática",
    layout_horizontal: "Diana a la derecha",
    layout_vertical: "Diana debajo",
    layout_board: "Solo la diana",
    board_style: "Estilo de la diana",
    style_classic: "Clásico",
    style_autodarts: "Autodarts",
    style_muted: "Discreto",
    highlight: "Resaltado",
    highlight_visit: "Todos los dardos de la tirada",
    highlight_last: "Solo el último dardo",
    highlight_none: "Desactivado",
    blink: "Parpadeo de segmentos acertados",
    show_markers: "Mostrar posiciones de los dardos",
    show_numbers: "Mostrar números",
    show_stats: "Mostrar estadísticas de entrenamiento",
    show_connection: "Mostrar estado de la conexión",
    show_controls: "Mostrar controles",
    show_recent: "Mostrar últimas tiradas",
    show_practice: "Mostrar partida",
    accent_color: "Color de acento",
    highlight_color: "Color de resaltado",
    color_helper: "Un color del tema de la lista o cualquier color CSS, como #00e5ff. Si lo dejas vacío, se usa el color primario del tema.",
    highlight_color_helper: "Un color del tema de la lista o cualquier color CSS, como #00e5ff. Si lo dejas vacío, se usa dorado (#ffd60a).",
    default_hint: "Predeterminado: {value}",
    invalid_option: "La opción {name} no admite {value}.",
    recent: "Últimas tiradas",
    practice: "Partida",
    leg_darts: "dardos",
    checkout: "Cierre",
    bust: "Bust – te pasas, no cuenta",
    game_shot: "¡Game shot!",
    no_checkout: "Sin cierre posible",
    score_player: "Jugador",
    score_turn: "lanza",
    score_winner: "gana el partido",
    score_legs: "Legs",
    score_sets: "Sets",
    practice_names: "Nombres de los jugadores",
    practice_starts: "Puntuaciones iniciales (hándicap)",
    practice_game_row: "Juego",
    practice_entity: "{name} de la partida",
    practice_legs_per_day: "Legs jugados por día",
    practice_trend: "First 9, porcentaje de cierre y de dobles",
    streak_day: "día seguido",
    streak_days: "días seguidos",
    darts_today: "dardos hoy",
    goals_and_bests: "Objetivos y récords personales",
    drill_around_the_clock: "Around the Clock",
    drill_doubles: "Entrenamiento de dobles",
    drill_checkout: "Entrenamiento de cierres",
    drill_bobs_27: "Bob's 27",
    drill_hits: "aciertos",
    drill_round: "Ronda",
    drill_points: "puntos",
    drill_visit: "Tirada",
    drill_checked: "cerrados",
    drill_done: "Completado en {darts} dardos",
    drill_bobs_done: "Completado con {points} puntos",
    drill_bobs_lost: "Por debajo de cero – con el siguiente dardo vuelves a empezar",
    drill_checkout_121: "121 checkout",
    drill_catch_40: "Catch 40",
    drill_jdc_challenge: "JDC Challenge",
    drill_singles: "Entrenamiento de simples",
    drill_part: "Parte",
    drill_best: "Mejor",
    drill_target: "Objetivo",
    cricket: "Cricket",
    cricket_cut_throat: "Cut-Throat Cricket",
    cricket_tactics: "Tactics",
    cut_throat_hint: "Gana quien tenga menos puntos",
    cricket_mpr: "MPR",
    cricket_points: "Puntos",
    mark_0: "Sin marcas",
    mark_1: "1 marca",
    mark_2: "2 marcas",
    mark_3: "Cerrado",
    bull_off: "Bull-off",
    bull_off_hint: "Empieza quien quede más cerca del bull",
    party_shanghai: "Shanghai",
    party_halve_it: "Halve-It",
    party_killer: "Killer",
    party_golf: "Golf",
    party_baseball: "Baseball",
    party_count_up: "Count-Up",
    golf_hole: "Hoyo",
    baseball_inning: "Entrada",
    playoff: "Desempate",
    golf_hint: "Cuenta el último dardo – retira tus dardos para plantarte",
    total: "Total",
    team: "Equipo",
    score_winners: "ganan el partido",
    start_score: "Puntuación inicial",
    any_double: "Cualquier doble",
    any_treble: "Cualquier triple",
    killer_choose: "Lanza para conseguir tu número",
    killer_hunt: "Killer – acierta los dobles de los demás",
    needs_players: "Killer necesita al menos dos jugadores",
    double_in_needed: "Empieza con un doble",
    out: "eliminado",
    view_scoreboard: "Marcador",
    view_players: "Jugadores",
    players_title: "Jugadores",
    no_profiles: "Aún no hay perfiles de jugador. Pon nombre a los jugadores de una partida y cada leg contará para ellos.",
    profile_legs: "Legs",
    profile_matches: "Partidos",
    first_9: "First 9",
    checkout_short: "Cierre",
    highest_checkout: "Cierre más alto",
    best_leg: "Mejor leg de {game}",
    best_mpr: "Mejor MPR",
    head_to_head: "Cara a cara",
    recent_matches: "Últimos partidos",
    show_head_to_head: "Mostrar cara a cara",
    show_matches: "Mostrar últimos partidos",
    export: "Mostrar botón de exportación",
    export_format: "Formato de exportación",
    export_format_csv: "CSV (un archivo ZIP con un archivo por tabla)",
    export_format_json: "JSON",
    export_button: "Exportar",
    exporting: "Exportando…",
    export_failed: "Error al exportar",
    doubles_title: "Dobles",
    doubles_darts: "dardos a doble",
    doubles_empty: "Lanza a dobles en X01, en el entrenamiento de dobles o en Bob's 27 para ver tu porcentaje de aciertos en cada doble.",
    doubles_unknown_player:
      "Aún no hay dobles de {player}. Comprueba el nombre en la configuración de la tarjeta o lanza a dobles en una partida como {player}.",
    doubles_routes: "Las rutas de cierre personales usan dobles con al menos 10 dardos.",
    player: "Jugador",
    player_helper: "Opcional. Elige o escribe el nombre de un jugador para ver sus dobles; si lo dejas vacío, se muestran los de todos.",
    full_height: "Ocupar toda la pantalla",
    show_visit: "Mostrar la tirada actual",
    show_status: "Mostrar el estado de la diana",
    legs_per_set: "legs por set",
    sets_to_win: "sets para ganar",
    visit_short: "Tirada",
    caller: "Locutor",
    caller_on: "Locutor activado",
    caller_hint: "Toca para activar o desactivar el locutor",
    caller_options: "Opciones del locutor",
    caller_options_helper: "El locutor hace estos anuncios mientras está activado.",
    call_scores: "Anunciar cada tirada",
    call_checkouts: "Anunciar lo que le queda a cada jugador",
    call_results: "Anunciar game shots y busts",
    call_sounds: "Tocar una fanfarria con cada 180",
    say_require: "{name}, te quedan {remaining}",
    say_require_alone: "Te quedan {remaining}",
    say_bust: "Sin puntos",
    say_no_score: "Sin puntos",
    say_mark: "Una marca",
    say_marks: "{marks} marcas",
    say_run: "Una carrera",
    say_runs: "{runs} carreras",
    say_leg: "¡Game shot, y el leg!",
    say_match: "¡Game shot, y el partido, {name}!",
    lobby_open: "Nueva partida",
    lobby_title: "Nueva partida",
    lobby_label: "Elige el juego, los jugadores y el formato",
    lobby_group_x01: "X01",
    lobby_group_cricket: "Cricket",
    lobby_group_party: "Juegos de fiesta",
    lobby_group_training: "Juegos de entrenamiento",
    lobby_group_more: "Más juegos",
    lobby_players: "Jugadores",
    lobby_guest: "Invitado",
    lobby_add: "Añadir",
    lobby_name: "Nombre",
    lobby_new_player: "Nombre de otro jugador",
    lobby_home: "en casa",
    lobby_move_up: "Mover a {name} hacia arriba",
    lobby_move_down: "Mover a {name} hacia abajo",
    lobby_remove: "Quitar a {name}",
    lobby_format: "Formato",
    lobby_legs: "Legs por set",
    lobby_sets: "Sets para ganar",
    lobby_decrease: "Menos: {name}",
    lobby_increase: "Más: {name}",
    lobby_options: "Opciones",
    lobby_one_player: "Los juegos de entrenamiento son para un jugador: juega {name}.",
    lobby_nobody: "No has elegido a nadie: lanza un jugador sin nombre.",
    lobby_start: "Empezar {game}",
    lobby_close: "Cerrar",
    lobby_end: "Terminar partida",
    lobby_start_lower: "Bajar puntuación inicial: {name}",
    lobby_start_raise: "Subir puntuación inicial: {name}",
    teams: "Equipos (1 + 3 contra 2 + 4)",
    double_out: "Double out",
    double_in: "Double in",
    bull_off_distance: "Bull-off por distancia",
    idle_panel_leaderboard: "Clasificación",
    idle_panel_records: "Récords personales",
    idle_panel_today: "Hoy",
    idle_panel_last_match: "Último partido",
    idle_panel_clock: "Reloj",
    idle_legs: "Legs {won}/{played}",
    idle_goal: "de {goal} dardos",
    idle_back: "Toca para volver",
    lobby: "Pantalla de nueva partida",
    lobby_games: "Juegos disponibles",
    lobby_games_helper: "Si lo dejas vacío, se ofrecen todos los juegos de la diana.",
    lobby_section: "Pantalla de nueva partida",
    lobby_section_helper: "Toca Nueva partida para elegir el juego, los jugadores y el formato; la pantalla también se abre unos segundos después de terminar una partida.",
    idle: "Modo de espera",
    idle_after: "Modo de espera tras",
    idle_interval: "Siguiente panel tras",
    idle_panels: "Paneles",
    idle_panels_helper: "Si lo dejas vacío, se muestran todos los paneles.",
    idle_section: "Modo de espera",
    idle_section_helper: "Cuando no hay ninguna partida en curso y nadie lanza ni toca la pantalla, el marcador muestra estos paneles por turnos.",
    training: "Entrenamiento",
    average_long: "Media de 3 dardos",
    visits: "Tiradas",
    highest: "Tirada más alta",
    scores_100: "100+",
    scores_140: "140+",
    doubles: "Dobles",
    misses: "Fallos",
    triple_rate: "% de triples",
    heatmap: "Mapa de aciertos",
    heatmap_label: "Diana coloreada según la frecuencia con la que se ha acertado cada segmento",
    top: "Más acertados",
    history: "Tiradas recientes",
    history_empty: "Aquí aparecen las tiradas completadas.",
    no_darts: "Aún no hay dardos en esta sesión. ¡Empieza a lanzar!",
    new_session: "Nueva sesión",
    hits: "aciertos",
    mode: "Mapa de calor",
    mode_beds: "Segmentos",
    mode_numbers: "Números",
    show_heatmap: "Mostrar mapa de calor",
    show_top: "Mostrar segmentos más acertados",
    show_history: "Mostrar tiradas recientes",
    show_reset: "Mostrar controles de la sesión",
    show_bests: "Mostrar récords personales",
    history_size: "Tiradas en el historial",
    start_session: "Empezar sesión",
    end_session: "Terminar sesión",
    session_running: "Sesión en curso",
    session_ended: "Sesión terminada",
    no_session: "Ninguna sesión en curso",
    no_session_hint: "Empieza una sesión para contar tus dardos.",
    past_sessions: "Sesiones anteriores",
    session_end: "Fin",
    duration: "Duración",
    highest_short: "Más alta",
    show_sessions: "Mostrar sesiones anteriores",
    statistics_label: "Estadísticas de entrenamiento, ver detalles",
    personal_bests: "Récords personales",
    best_session_average: "Mejor media de sesión",
    best_cricket_mpr: "Mejor MPR en Cricket",
    best_streak: "Racha más larga",
    unit_darts: "{value} dardos",
    unit_points: "{value} puntos",
    unit_day: "{value} día",
    unit_days: "{value} días",
    unit_minutes: "{value} min",
    under_a_minute: "<1 min",
    detection: "Detección",
    connections: "Conexiones",
    cloud: "Nube",
    version: "Versión",
    update_available: "Actualizar a",
    up_to_date: "Actualizado",
    system: "PC de la diana",
    cpu: "CPU",
    memory: "Memoria",
    detection_fps: "Detección",
    corrected: "Corregidos",
    camera: "Cámara",
    camera_ok: "OK",
    camera_failure: "Problema",
    restart: "Reiniciar",
    show_cameras: "Mostrar cámaras",
    show_system: "Mostrar PC de la diana",
    vision_short: "Detección",
    view_live: "En directo",
    view_training: "Entrenamiento",
    view_board: "Diana",
    darts_per_day: "Dardos por día",
    average_trend: "Media de 3 dardos, últimos 7 días",
    board_settings: "Configuración de la diana",
    training_settings: "Configuración del entrenamiento",
    strategy_device_helper: "Opcional. Sin selección, el panel de control muestra todas las dianas Autodarts.",
    strategy_no_board: "No se ha encontrado ninguna diana Autodarts. Configura la integración Autodarts y vuelve a cargar este panel de control.",
    strategy_board_missing:
      "La diana de este panel de control ya no existe. Edita el panel de control y elige otra diana, o quita la diana seleccionada para mostrar todas las dianas.",
    picker_live: "Autodarts",
    picker_live_description:
      "La tirada actual en una diana en directo con los segmentos acertados, las posiciones de los dardos, la partida, las estadísticas de entrenamiento y los controles.",
    picker_training: "Entrenamiento Autodarts",
    picker_training_description:
      "La sesión de entrenamiento con un mapa de calor de aciertos, la media de 3 dardos, estadísticas, récords personales y las últimas tiradas.",
    picker_status: "Estado de la diana Autodarts",
    picker_status_description: "Detección, conexiones, cámaras, PC de la diana y controles de mantenimiento de una diana Autodarts.",
    picker_scoreboard: "Marcador Autodarts",
    picker_scoreboard_description:
      "Un marcador grande para una tableta o un televisor junto a la diana: X01, Cricket, juegos de fiesta y de entrenamiento, la tirada y un locutor.",
    picker_players: "Jugadores Autodarts",
    picker_players_description:
      "Estadísticas y récords personales de cada jugador con nombre, enfrentamientos cara a cara y últimos partidos.",
    picker_doubles: "Dobles Autodarts",
    picker_doubles_description:
      "El porcentaje de aciertos de cada doble de la diana, para todos o para un jugador, con el doble favorito.",
    picker_strategy_description:
      "Vistas en directo, de marcador, de entrenamiento, de jugadores y de la diana, creadas automáticamente para cada diana Autodarts.",
  },
  fr: {
    visit: "Volée en cours",
    points: "points",
    dart: "Fléchette",
    of: "sur",
    miss: "Raté",
    session: "Session d'entraînement",
    since: "depuis",
    darts: "Fléchettes",
    average: "Moy. 3 fl.",
    triples: "Triples",
    bulls: "Bulls",
    max: "180",
    board: "Board Manager",
    realtime: "Temps réel",
    cameras: "Caméras",
    camera_problem: "Vérifier les caméras",
    start: "Démarrer la détection",
    stop: "Arrêter la détection",
    reset: "Réinitialiser la détection",
    calibrate: "Calibrer",
    confirm: "Confirmer\u00a0?",
    status_offline: "Cible injoignable",
    status_calibrating: "Calibrage en cours",
    status_problem: "Vérifier les caméras",
    status_starting: "Démarrage de la détection",
    status_stopping: "Arrêt de la détection",
    status_stopped: "Détection arrêtée",
    status_takeout: "Retrait des fléchettes",
    status_hand: "Main devant la cible",
    status_full: "Retirez vos fléchettes",
    status_ready: "Prêt – lancez\u00a0!",
    no_board: "Aucune cible Autodarts trouvée. Sélectionnez un appareil dans les paramètres de la carte.",
    board_label: "Cible avec la volée en cours",
    device_id: "Cible",
    device_helper: "Facultatif. Sans sélection, la carte utilise la première cible Autodarts.",
    title: "Titre",
    layout: "Disposition",
    layout_auto: "Automatique",
    layout_horizontal: "Cible à droite",
    layout_vertical: "Cible en dessous",
    layout_board: "Cible seule",
    board_style: "Style de la cible",
    style_classic: "Classique",
    style_autodarts: "Autodarts",
    style_muted: "Sobre",
    highlight: "Mise en évidence",
    highlight_visit: "Toutes les fléchettes de la volée",
    highlight_last: "Dernière fléchette seulement",
    highlight_none: "Désactivée",
    blink: "Faire clignoter les zones touchées",
    show_markers: "Afficher la position des fléchettes",
    show_numbers: "Afficher les numéros",
    show_stats: "Afficher les statistiques d'entraînement",
    show_connection: "Afficher l'état de la connexion",
    show_controls: "Afficher les commandes",
    show_recent: "Afficher les dernières volées",
    show_practice: "Afficher la partie",
    accent_color: "Couleur d'accentuation",
    highlight_color: "Couleur de mise en évidence",
    color_helper: "Une couleur du thème dans la liste, ou n'importe quelle couleur CSS comme #00e5ff. Si vide, la couleur principale du thème est utilisée.",
    highlight_color_helper: "Une couleur du thème dans la liste, ou n'importe quelle couleur CSS comme #00e5ff. Si vide, la couleur or (#ffd60a) est utilisée.",
    default_hint: "Par défaut\u00a0: {value}",
    invalid_option: "L'option {name} n'accepte pas la valeur {value}.",
    recent: "Dernières volées",
    practice: "Partie",
    leg_darts: "fléchettes",
    checkout: "Finish",
    bust: "Bust – score inchangé",
    game_shot: "Game shot\u00a0!",
    no_checkout: "Aucun finish possible",
    score_player: "Joueur",
    score_turn: "lance",
    score_winner: "remporte le match\u00a0!",
    score_legs: "Manches",
    score_sets: "Sets",
    practice_names: "Noms des joueurs",
    practice_starts: "Scores de départ (handicap)",
    practice_game_row: "Jeu",
    practice_entity: "{name} de la partie",
    practice_legs_per_day: "Manches jouées par jour",
    practice_trend: "First 9, taux de finish et de doubles",
    streak_day: "jour d'affilée",
    streak_days: "jours d'affilée",
    darts_today: "fléchettes aujourd'hui",
    goals_and_bests: "Objectifs et records personnels",
    drill_around_the_clock: "Around the Clock",
    drill_doubles: "Entraînement aux doubles",
    drill_checkout: "Entraînement au finish",
    drill_bobs_27: "Bob's 27",
    drill_hits: "touches",
    drill_round: "Tour",
    drill_points: "points",
    drill_visit: "Volée",
    drill_checked: "réussis",
    drill_done: "Terminé en {darts} fléchettes",
    drill_bobs_done: "Terminé avec {points} points",
    drill_bobs_lost: "Sous zéro – la prochaine fléchette relance le jeu",
    drill_checkout_121: "121 checkout",
    drill_catch_40: "Catch 40",
    drill_jdc_challenge: "JDC Challenge",
    drill_singles: "Entraînement aux simples",
    drill_part: "Étape",
    drill_best: "Record",
    drill_target: "Zone visée",
    cricket: "Cricket",
    cricket_cut_throat: "Cut-Throat Cricket",
    cricket_tactics: "Tactics",
    cut_throat_hint: "Le moins de points gagne",
    cricket_mpr: "MPR",
    cricket_points: "Points",
    mark_0: "Aucune marque",
    mark_1: "1 marque",
    mark_2: "2 marques",
    mark_3: "Fermé",
    bull_off: "Bull-off",
    bull_off_hint: "Le plus proche du bull commence",
    party_shanghai: "Shanghai",
    party_halve_it: "Halve-It",
    party_killer: "Killer",
    party_golf: "Golf",
    party_baseball: "Baseball",
    party_count_up: "Count-Up",
    golf_hole: "Trou",
    baseball_inning: "Inning",
    playoff: "Barrage",
    golf_hint: "La dernière fléchette compte – retirez vos fléchettes pour vous arrêter",
    total: "Total",
    team: "Équipe",
    score_winners: "remportent le match\u00a0!",
    start_score: "Score de départ",
    any_double: "N'importe quel double",
    any_treble: "N'importe quel triple",
    killer_choose: "Lancez pour obtenir votre numéro",
    killer_hunt: "Killer – touchez les doubles des autres",
    needs_players: "Il faut au moins deux joueurs pour Killer",
    double_in_needed: "Commencez par un double",
    out: "éliminé",
    view_scoreboard: "Tableau des scores",
    view_players: "Joueurs",
    players_title: "Joueurs",
    no_profiles: "Aucun profil de joueur pour l'instant. Donnez un nom aux joueurs d'une partie, et chaque manche comptera pour eux.",
    profile_legs: "Manches",
    profile_matches: "Matchs",
    first_9: "First 9",
    checkout_short: "Finish",
    highest_checkout: "Meilleur finish",
    best_leg: "Meilleur {game}",
    best_mpr: "Meilleur MPR",
    head_to_head: "Face-à-face",
    recent_matches: "Derniers matchs",
    show_head_to_head: "Afficher les face-à-face",
    show_matches: "Afficher les derniers matchs",
    export: "Afficher le bouton d'export",
    export_format: "Format d'export",
    export_format_csv: "CSV (un fichier ZIP, un fichier par tableau)",
    export_format_json: "JSON",
    export_button: "Exporter",
    exporting: "Export en cours…",
    export_failed: "Échec de l'export",
    doubles_title: "Doubles",
    doubles_darts: "fléchettes sur double",
    doubles_empty: "Lancez sur les doubles en X01, à l'entraînement aux doubles ou au Bob's 27 pour voir ici votre taux de réussite sur chaque double.",
    doubles_unknown_player:
      "Aucun double de {player} pour l'instant. Vérifiez le nom dans les paramètres de la carte, ou lancez sur les doubles dans une partie en tant que {player}.",
    doubles_routes: "Les combinaisons de finish personnelles utilisent les doubles visés par au moins 10 fléchettes.",
    player: "Joueur",
    player_helper: "Facultatif. Choisissez ou saisissez le nom d'un joueur pour afficher ses doubles\u00a0; si vide, ceux de tous les joueurs sont affichés.",
    full_height: "Remplir l'écran",
    show_visit: "Afficher la volée en cours",
    show_status: "Afficher l'état de la cible",
    legs_per_set: "manches par set",
    sets_to_win: "sets pour gagner",
    visit_short: "Volée",
    caller: "Annonceur",
    caller_on: "Annonceur activé",
    caller_hint: "Touchez pour activer ou désactiver l'annonceur",
    caller_options: "Options de l'annonceur",
    caller_options_helper: "L'annonceur fait ces annonces tant qu'il est activé.",
    call_scores: "Annoncer chaque volée",
    call_checkouts: "Annoncer les points restants",
    call_results: "Annoncer les game shots et les busts",
    call_sounds: "Jouer une fanfare pour un 180",
    say_require: "{name}, il vous reste {remaining}",
    say_require_alone: "Il vous reste {remaining}",
    say_bust: "Aucun point",
    say_no_score: "Aucun point",
    say_mark: "Une marque",
    say_marks: "{marks} marques",
    say_run: "Un point",
    say_runs: "{runs} points",
    say_leg: "Game shot, et la manche\u00a0!",
    say_match: "Game shot, et le match, {name}\u00a0!",
    lobby_open: "Nouvelle partie",
    lobby_title: "Nouvelle partie",
    lobby_label: "Choisissez le jeu, les joueurs et le format",
    lobby_group_x01: "X01",
    lobby_group_cricket: "Cricket",
    lobby_group_party: "Jeux de soirée",
    lobby_group_training: "Jeux d'entraînement",
    lobby_group_more: "Autres jeux",
    lobby_players: "Joueurs",
    lobby_guest: "Invité",
    lobby_add: "Ajouter",
    lobby_name: "Nom",
    lobby_new_player: "Nom d'un autre joueur",
    lobby_home: "à la maison",
    lobby_move_up: "Déplacer {name} vers le haut",
    lobby_move_down: "Déplacer {name} vers le bas",
    lobby_remove: "Retirer {name}",
    lobby_format: "Format",
    lobby_legs: "Manches par set",
    lobby_sets: "Sets pour gagner",
    lobby_decrease: "Moins\u00a0: {name}",
    lobby_increase: "Plus\u00a0: {name}",
    lobby_options: "Options",
    lobby_one_player: "Les jeux d'entraînement se jouent seul\u00a0: c'est {name} qui joue.",
    lobby_nobody: "Aucun joueur choisi\u00a0: un joueur lance sans nom.",
    lobby_start: "Démarrer {game}",
    lobby_close: "Fermer",
    lobby_end: "Terminer la partie",
    lobby_start_lower: "Baisser le score de départ\u00a0: {name}",
    lobby_start_raise: "Augmenter le score de départ\u00a0: {name}",
    teams: "Équipes (1 + 3 contre 2 + 4)",
    double_out: "Double out",
    double_in: "Double in",
    bull_off_distance: "Bull-off à la distance",
    idle_panel_leaderboard: "Classement",
    idle_panel_records: "Records personnels",
    idle_panel_today: "Aujourd'hui",
    idle_panel_last_match: "Dernier match",
    idle_panel_clock: "Horloge",
    idle_legs: "Manches {won}/{played}",
    idle_goal: "sur {goal} fléchettes",
    idle_back: "Touchez pour revenir",
    lobby: "Écran Nouvelle partie",
    lobby_games: "Jeux proposés",
    lobby_games_helper: "Si vide, tous les jeux de la cible sont proposés.",
    lobby_section: "Écran Nouvelle partie",
    lobby_section_helper: "Touchez Nouvelle partie pour choisir le jeu, les joueurs et le format\u00a0; l'écran s'ouvre aussi quelques secondes après la fin d'une partie.",
    idle: "Mode veille",
    idle_after: "Mode veille après",
    idle_interval: "Panneau suivant après",
    idle_panels: "Panneaux",
    idle_panels_helper: "Si vide, tous les panneaux sont affichés.",
    idle_section: "Mode veille",
    idle_section_helper: "Quand aucune partie n'est en cours et que personne ne lance ni ne touche l'écran, le tableau des scores affiche ces panneaux à tour de rôle.",
    training: "Entraînement",
    average_long: "Moyenne 3 fléchettes",
    visits: "Volées",
    highest: "Meilleure volée",
    scores_100: "100+",
    scores_140: "140+",
    doubles: "Doubles",
    misses: "Ratés",
    triple_rate: "Taux de triples",
    heatmap: "Carte des touches",
    heatmap_label: "Cible colorée selon la fréquence à laquelle chaque zone a été touchée",
    top: "Zones les plus touchées",
    history: "Dernières volées",
    history_empty: "Les volées terminées apparaissent ici.",
    no_darts: "Aucune fléchette dans cette session pour l'instant. À vous de jouer\u00a0!",
    new_session: "Nouvelle session",
    hits: "touches",
    mode: "Carte de chaleur",
    mode_beds: "Zones",
    mode_numbers: "Numéros",
    show_heatmap: "Afficher la carte de chaleur",
    show_top: "Afficher les zones les plus touchées",
    show_history: "Afficher les dernières volées",
    show_reset: "Afficher les commandes de session",
    show_bests: "Afficher les records personnels",
    history_size: "Volées dans l'historique",
    start_session: "Démarrer la session",
    end_session: "Terminer la session",
    session_running: "Session en cours",
    session_ended: "Session terminée",
    no_session: "Aucune session en cours",
    no_session_hint: "Démarrez une session pour compter vos fléchettes.",
    past_sessions: "Sessions précédentes",
    session_end: "Fin",
    duration: "Durée",
    highest_short: "Meilleure",
    show_sessions: "Afficher les sessions précédentes",
    statistics_label: "Statistiques d'entraînement, ouvrir les détails",
    personal_bests: "Records personnels",
    best_session_average: "Meilleure moyenne de session",
    best_cricket_mpr: "Meilleur MPR au Cricket",
    best_streak: "Plus longue série",
    unit_darts: "{value} fléchettes",
    unit_points: "{value} points",
    unit_day: "{value} jour",
    unit_days: "{value} jours",
    unit_minutes: "{value} min",
    under_a_minute: "<1 min",
    detection: "Détection",
    connections: "Connexions",
    cloud: "Cloud",
    version: "Version",
    update_available: "Mise à jour vers",
    up_to_date: "À jour",
    system: "PC de la cible",
    cpu: "CPU",
    memory: "Mémoire",
    detection_fps: "Détection",
    corrected: "Corrigées",
    camera: "Caméra",
    camera_ok: "OK",
    camera_failure: "Problème",
    restart: "Redémarrer",
    show_cameras: "Afficher les caméras",
    show_system: "Afficher le PC de la cible",
    vision_short: "Détection",
    view_live: "En direct",
    view_training: "Entraînement",
    view_board: "Cible",
    darts_per_day: "Fléchettes par jour",
    average_trend: "Moyenne 3 fléchettes, 7 derniers jours",
    board_settings: "Paramètres de la cible",
    training_settings: "Paramètres d'entraînement",
    strategy_device_helper: "Facultatif. Sans sélection, le tableau de bord affiche toutes les cibles Autodarts.",
    strategy_no_board: "Aucune cible Autodarts trouvée. Configurez l'intégration Autodarts, puis rechargez ce tableau de bord.",
    strategy_board_missing:
      "La cible de ce tableau de bord n'existe plus. Modifiez le tableau de bord et choisissez une autre cible, ou effacez la sélection pour afficher toutes les cibles.",
    picker_live: "Autodarts",
    picker_live_description:
      "La volée en cours sur une cible en direct, avec les zones touchées, la position des fléchettes, la partie, les statistiques d'entraînement et les commandes.",
    picker_training: "Entraînement Autodarts",
    picker_training_description:
      "La session d'entraînement avec la carte de chaleur des touches, la moyenne 3 fléchettes, les statistiques, les records personnels et les dernières volées.",
    picker_status: "État de la cible Autodarts",
    picker_status_description: "Détection, connexions, caméras, PC de la cible et commandes de maintenance d'une cible Autodarts.",
    picker_scoreboard: "Tableau des scores Autodarts",
    picker_scoreboard_description:
      "Un grand tableau des scores pour une tablette ou une télévision près de la cible\u00a0: X01, Cricket, jeux de soirée et d'entraînement, la volée et un annonceur.",
    picker_players: "Joueurs Autodarts",
    picker_players_description:
      "Statistiques et records personnels de chaque joueur nommé, face-à-face et derniers matchs.",
    picker_doubles: "Doubles Autodarts",
    picker_doubles_description:
      "Le taux de réussite sur chaque double de la cible, pour tous les joueurs ou un seul, avec le double préféré.",
    picker_strategy_description:
      "Vues En direct, Tableau des scores, Entraînement, Joueurs et Cible pour chaque cible Autodarts, créées automatiquement.",
  },
  nl: {
    visit: "Huidige beurt",
    points: "punten",
    dart: "Dart",
    of: "van",
    miss: "Mis",
    session: "Trainingssessie",
    since: "sinds",
    darts: "Darts",
    average: "3-dart-gem.",
    triples: "Triples",
    bulls: "Bulls",
    max: "180's",
    board: "Board Manager",
    realtime: "Realtime",
    cameras: "Camera's",
    camera_problem: "Controleer camera's",
    start: "Detectie starten",
    stop: "Detectie stoppen",
    reset: "Detectie resetten",
    calibrate: "Kalibreren",
    confirm: "Bevestigen?",
    status_offline: "Bord onbereikbaar",
    status_calibrating: "Bezig met kalibreren",
    status_problem: "Controleer camera's",
    status_starting: "Detectie wordt gestart",
    status_stopping: "Detectie wordt gestopt",
    status_stopped: "Detectie gestopt",
    status_takeout: "Darts worden verwijderd",
    status_hand: "Hand bij het bord",
    status_full: "Haal je darts eruit",
    status_ready: "Klaar – gooi!",
    no_board: "Geen Autodarts-bord gevonden. Selecteer een apparaat in de kaartinstellingen.",
    board_label: "Dartbord met de huidige beurt",
    device_id: "Bord",
    device_helper: "Optioneel. Zonder selectie gebruikt de kaart het eerste Autodarts-bord.",
    title: "Titel",
    layout: "Indeling",
    layout_auto: "Automatisch",
    layout_horizontal: "Bord rechts",
    layout_vertical: "Bord onderaan",
    layout_board: "Alleen bord",
    board_style: "Bordstijl",
    style_classic: "Klassiek",
    style_autodarts: "Autodarts",
    style_muted: "Gedempt",
    highlight: "Markering",
    highlight_visit: "Alle darts van de beurt",
    highlight_last: "Alleen laatste dart",
    highlight_none: "Uit",
    blink: "Geraakte vakken laten knipperen",
    show_markers: "Dartposities tonen",
    show_numbers: "Getallen tonen",
    show_stats: "Trainingsstatistieken tonen",
    show_connection: "Verbindingsstatus tonen",
    show_controls: "Bediening tonen",
    show_recent: "Laatste beurten tonen",
    show_practice: "Oefenspel tonen",
    accent_color: "Accentkleur",
    highlight_color: "Markeringskleur",
    color_helper: "Een themakleur uit de lijst, of een CSS-kleur zoals #00e5ff. Laat leeg voor de primaire kleur van het thema.",
    highlight_color_helper: "Een themakleur uit de lijst, of een CSS-kleur zoals #00e5ff. Laat leeg voor goud (#ffd60a).",
    default_hint: "Standaard: {value}",
    invalid_option: "De optie {name} accepteert {value} niet.",
    recent: "Laatste beurten",
    practice: "Oefenspel",
    leg_darts: "darts",
    checkout: "Uitgooi",
    bust: "Bust – de score blijft staan",
    game_shot: "Game shot!",
    no_checkout: "Geen uitgooi mogelijk",
    score_player: "Speler",
    score_turn: "aan de beurt",
    score_winner: "wint de wedstrijd!",
    score_legs: "Legs",
    score_sets: "Sets",
    practice_names: "Spelersnamen",
    practice_starts: "Startscores (handicap)",
    practice_game_row: "Spel",
    practice_entity: "Oefenspel {name}",
    practice_legs_per_day: "Oefenlegs per dag",
    practice_trend: "First 9, uitgooi- en dubbelpercentage",
    streak_day: "dag op rij",
    streak_days: "dagen op rij",
    darts_today: "darts vandaag",
    goals_and_bests: "Doelen en persoonlijke records",
    drill_around_the_clock: "Around the Clock",
    drill_doubles: "Dubbeltraining",
    drill_checkout: "Uitgooitraining",
    drill_bobs_27: "Bob's 27",
    drill_hits: "treffers",
    drill_round: "Ronde",
    drill_points: "punten",
    drill_visit: "Beurt",
    drill_checked: "uitgegooid",
    drill_done: "Klaar in {darts} darts",
    drill_bobs_done: "Klaar met {points} punten",
    drill_bobs_lost: "Onder nul – met de volgende dart begin je opnieuw",
    drill_checkout_121: "121 checkout",
    drill_catch_40: "Catch 40",
    drill_jdc_challenge: "JDC Challenge",
    drill_singles: "Singletraining",
    drill_part: "Deel",
    drill_best: "Beste",
    drill_target: "Doel",
    cricket: "Cricket",
    cricket_cut_throat: "Cut-Throat Cricket",
    cricket_tactics: "Tactics",
    cut_throat_hint: "Laagste score wint",
    cricket_mpr: "MPR",
    cricket_points: "Punten",
    mark_0: "Geen marks",
    mark_1: "1 mark",
    mark_2: "2 marks",
    mark_3: "Gesloten",
    bull_off: "Bullen",
    bull_off_hint: "Wie het dichtst bij de bull gooit, begint",
    party_shanghai: "Shanghai",
    party_halve_it: "Halve-It",
    party_killer: "Killer",
    party_golf: "Golf",
    party_baseball: "Baseball",
    party_count_up: "Count-Up",
    golf_hole: "Hole",
    baseball_inning: "Inning",
    playoff: "Barrage",
    golf_hint: "De laatste dart telt – haal je darts eruit om te stoppen",
    total: "Totaal",
    team: "Team",
    score_winners: "winnen de wedstrijd!",
    start_score: "Startscore",
    any_double: "Willekeurige dubbel",
    any_treble: "Willekeurige triple",
    killer_choose: "Gooi voor je nummer",
    killer_hunt: "Killer – raak de dubbels van de anderen",
    needs_players: "Killer heeft minstens twee spelers nodig",
    double_in_needed: "Begin met een dubbel",
    out: "eruit",
    view_scoreboard: "Scorebord",
    view_players: "Spelers",
    players_title: "Spelers",
    no_profiles: "Nog geen spelersprofielen. Geef de spelers van een oefenspel een naam, dan telt elke leg voor hen mee.",
    profile_legs: "Legs",
    profile_matches: "Wedstrijden",
    first_9: "First 9",
    checkout_short: "Uitgooi",
    highest_checkout: "Hoogste uitgooi",
    best_leg: "Beste {game}",
    best_mpr: "Beste MPR",
    head_to_head: "Onderlinge duels",
    recent_matches: "Recente wedstrijden",
    show_head_to_head: "Onderlinge duels tonen",
    show_matches: "Recente wedstrijden tonen",
    export: "Exportknop tonen",
    export_format: "Exportformaat",
    export_format_csv: "CSV (ZIP-bestand met één tabel per bestand)",
    export_format_json: "JSON",
    export_button: "Exporteren",
    exporting: "Exporteren …",
    export_failed: "Exporteren mislukt",
    doubles_title: "Dubbels",
    doubles_darts: "darts op een dubbel",
    doubles_empty: "Gooi op dubbels in X01, de dubbeltraining of Bob's 27 om je trefferpercentage op elke dubbel te zien.",
    doubles_unknown_player:
      "Nog geen dubbels van {player}. Controleer de naam in de kaartinstellingen, of gooi in een oefenspel als {player} op dubbels.",
    doubles_routes: "Persoonlijke uitgooiroutes gebruiken dubbels waarop minstens 10 darts zijn gegooid.",
    player: "Speler",
    player_helper: "Optioneel. Kies of typ een spelersnaam voor de dubbels van die speler; laat leeg om die van iedereen te tonen.",
    full_height: "Scherm vullen",
    show_visit: "Huidige beurt tonen",
    show_status: "Bordstatus tonen",
    legs_per_set: "legs per set",
    sets_to_win: "sets om te winnen",
    visit_short: "Beurt",
    caller: "Caller",
    caller_on: "Caller aan",
    caller_hint: "Tik om de caller aan of uit te zetten",
    caller_options: "Calleropties",
    caller_options_helper: "Dit roept de caller om zolang hij aanstaat.",
    call_scores: "Elke beurt omroepen",
    call_checkouts: "Omroepen wat een speler nog nodig heeft",
    call_results: "Game shots en busts omroepen",
    call_sounds: "Fanfare afspelen bij een 180",
    say_require: "{name}, je hebt nog {remaining} nodig",
    say_require_alone: "Je hebt nog {remaining} nodig",
    say_bust: "Geen score",
    say_no_score: "Geen score",
    say_mark: "Eén mark",
    say_marks: "{marks} marks",
    say_run: "Eén run",
    say_runs: "{runs} runs",
    say_leg: "Game shot, en de leg!",
    say_match: "Game shot, en de wedstrijd, {name}!",
    lobby_open: "Nieuw spel",
    lobby_title: "Nieuw spel",
    lobby_label: "Kies het spel, de spelers en het format",
    lobby_group_x01: "X01",
    lobby_group_cricket: "Cricket",
    lobby_group_party: "Partyspellen",
    lobby_group_training: "Trainingsspellen",
    lobby_group_more: "Meer spellen",
    lobby_players: "Spelers",
    lobby_guest: "Gast",
    lobby_add: "Toevoegen",
    lobby_name: "Naam",
    lobby_new_player: "Naam van nog een speler",
    lobby_home: "thuis",
    lobby_move_up: "{name} omhoog",
    lobby_move_down: "{name} omlaag",
    lobby_remove: "{name} verwijderen",
    lobby_format: "Format",
    lobby_legs: "Legs per set",
    lobby_sets: "Sets om te winnen",
    lobby_decrease: "Minder: {name}",
    lobby_increase: "Meer: {name}",
    lobby_options: "Opties",
    lobby_one_player: "Trainingsspellen zijn voor één speler: {name} speelt.",
    lobby_nobody: "Niemand gekozen: één speler gooit zonder naam.",
    lobby_start: "{game} starten",
    lobby_close: "Sluiten",
    lobby_end: "Spel beëindigen",
    lobby_start_lower: "Lagere startscore: {name}",
    lobby_start_raise: "Hogere startscore: {name}",
    teams: "Teams (1 + 3 tegen 2 + 4)",
    double_out: "Double out",
    double_in: "Double in",
    bull_off_distance: "Bullen op afstand",
    idle_panel_leaderboard: "Ranglijst",
    idle_panel_records: "Persoonlijke records",
    idle_panel_today: "Vandaag",
    idle_panel_last_match: "Laatste wedstrijd",
    idle_panel_clock: "Klok",
    idle_legs: "Legs {won}/{played}",
    idle_goal: "van {goal} darts",
    idle_back: "Tik om terug te gaan",
    lobby: "Scherm Nieuw spel",
    lobby_games: "Aangeboden spellen",
    lobby_games_helper: "Laat leeg om alle spellen van het bord aan te bieden.",
    lobby_section: "Scherm Nieuw spel",
    lobby_section_helper: "Tik op Nieuw spel om het spel, de spelers en het format te kiezen; het scherm opent ook een paar seconden nadat een spel is afgelopen.",
    idle: "Ruststand",
    idle_after: "Ruststand na",
    idle_interval: "Volgend paneel na",
    idle_panels: "Panelen",
    idle_panels_helper: "Laat leeg om alle panelen te tonen.",
    idle_section: "Ruststand",
    idle_section_helper: "Als er geen spel loopt en niemand gooit of tikt, toont het scorebord deze panelen afwisselend.",
    training: "Training",
    average_long: "3-dart-gemiddelde",
    visits: "Beurten",
    highest: "Hoogste beurt",
    scores_100: "100+",
    scores_140: "140+",
    doubles: "Dubbels",
    misses: "Missers",
    triple_rate: "Triplepercentage",
    heatmap: "Trefferkaart",
    heatmap_label: "Dartbord, gekleurd naar hoe vaak elk vak is geraakt",
    top: "Meest geraakt",
    history: "Recente beurten",
    history_empty: "Afgeronde beurten verschijnen hier.",
    no_darts: "Nog geen darts in deze sessie. Begin met gooien!",
    new_session: "Nieuwe sessie",
    hits: "treffers",
    mode: "Heatmap",
    mode_beds: "Vakken",
    mode_numbers: "Getallen",
    show_heatmap: "Heatmap tonen",
    show_top: "Meest geraakte vakken tonen",
    show_history: "Recente beurten tonen",
    show_reset: "Sessiebediening tonen",
    show_bests: "Persoonlijke records tonen",
    history_size: "Beurten in de geschiedenis",
    start_session: "Sessie starten",
    end_session: "Sessie beëindigen",
    session_running: "Sessie loopt",
    session_ended: "Sessie beëindigd",
    no_session: "Geen actieve sessie",
    no_session_hint: "Start een sessie om je darts te tellen.",
    past_sessions: "Eerdere sessies",
    session_end: "Einde",
    duration: "Duur",
    highest_short: "Hoogste",
    show_sessions: "Eerdere sessies tonen",
    statistics_label: "Trainingsstatistieken, details openen",
    personal_bests: "Persoonlijke records",
    best_session_average: "Beste sessiegemiddelde",
    best_cricket_mpr: "Beste Cricket-MPR",
    best_streak: "Langste reeks",
    unit_darts: "{value} darts",
    unit_points: "{value} punten",
    unit_day: "{value} dag",
    unit_days: "{value} dagen",
    unit_minutes: "{value} min",
    under_a_minute: "<1 min",
    detection: "Detectie",
    connections: "Verbindingen",
    cloud: "Cloud",
    version: "Versie",
    update_available: "Update naar",
    up_to_date: "Up-to-date",
    system: "Bord-pc",
    cpu: "CPU",
    memory: "Geheugen",
    detection_fps: "Detectie",
    corrected: "Gecorrigeerd",
    camera: "Camera",
    camera_ok: "OK",
    camera_failure: "Probleem",
    restart: "Herstarten",
    show_cameras: "Camera's tonen",
    show_system: "Bord-pc tonen",
    vision_short: "Detectie",
    view_live: "Live",
    view_training: "Training",
    view_board: "Bord",
    darts_per_day: "Darts per dag",
    average_trend: "3-dart-gemiddelde, laatste 7 dagen",
    board_settings: "Bordinstellingen",
    training_settings: "Trainingsinstellingen",
    strategy_device_helper: "Optioneel. Zonder selectie toont het dashboard elk Autodarts-bord.",
    strategy_no_board: "Geen Autodarts-bord gevonden. Stel de Autodarts-integratie in en laad dit dashboard daarna opnieuw.",
    strategy_board_missing:
      "Het bord van dit dashboard bestaat niet meer. Bewerk het dashboard en kies een ander bord, of wis de bordkeuze om alle borden te tonen.",
    picker_live: "Autodarts",
    picker_live_description:
      "De huidige beurt op een live dartbord met geraakte vakken, dartposities, het oefenspel, trainingsstatistieken en bediening.",
    picker_training: "Autodarts-training",
    picker_training_description:
      "De trainingssessie met een heatmap van de treffers, 3-dart-gemiddelde, statistieken, persoonlijke records en recente beurten.",
    picker_status: "Autodarts-bordstatus",
    picker_status_description: "Detectie, verbindingen, camera's, bord-pc en onderhoudsbediening van een Autodarts-bord.",
    picker_scoreboard: "Autodarts-scorebord",
    picker_scoreboard_description:
      "Een groot scorebord voor een tablet of tv bij het bord: X01, Cricket, party- en trainingsspellen, de beurt en een caller.",
    picker_players: "Autodarts-spelers",
    picker_players_description:
      "Statistieken en persoonlijke records van elke speler met een naam, onderlinge duels en recente wedstrijden.",
    picker_doubles: "Autodarts-dubbels",
    picker_doubles_description:
      "Het trefferpercentage van elke dubbel op het bord, voor iedereen of één speler, met de favoriete dubbel.",
    picker_strategy_description:
      "Live-, scorebord-, trainings-, spelers- en bordweergaven voor elk Autodarts-bord, automatisch opgebouwd.",
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
  // The summary of a finished match stays until the next game, or this many seconds.
  show_summary: true,
  summary_seconds: 0,
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
  show_heatmap_controls: true,
};

// Hits per bed, per number, or where the darts landed.
const HEAT_MODES = ["beds", "numbers", "positions"];

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
  // The export writes a file with player names; the button appears on request.
  export: false,
  export_format: "csv",
  show_badges: true,
  show_locked: true,
  show_trends: true,
  show_spread: true,
  trend_weeks: 12,
};

const LEADERBOARD_DEFAULTS = {
  period: "all",
  show_period: true,
  limit: 3,
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
  // The new game screen; without a list of games it offers every game of the board.
  lobby: true,
  // Panels in turn when no game runs and nobody threw or tapped for a while.
  idle: true,
  idle_after: 180,
  idle_interval: 10,
  show_summary: true,
  summary_seconds: 0,
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
  profiles: "sensor.player_profiles",
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
  achievements: "sensor.achievements",
};

const LEADERBOARD_KEYS = {
  profiles: "sensor.player_profiles",
  achievements: "sensor.achievements",
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
  // The new game screen reads the game, the format and the rules as they are set.
  game: "select.practice_game",
  players: "number.practice_players",
  legs: "number.practice_legs",
  sets: "number.practice_sets",
  doubleOut: "switch.practice_double_out",
  doubleIn: "switch.practice_double_in",
  bullOff: "switch.practice_bull_off",
  bullOffDistance: "switch.practice_bull_off_distance",
  teams: "switch.practice_teams",
  // Profiles with their pictures, records and the last match for the idle panels.
  profiles: "sensor.player_profiles",
  lastMatch: "sensor.last_match",
  bests: "sensor.personal_best",
  // The tournament, its settings for the new game screen and its buttons.
  tournament: "sensor.tournament",
  tournamentGame: "select.tournament_game",
  tournamentFormat: "select.tournament_format",
  tournamentThird: "switch.tournament_third_place",
  tournamentDraw: "switch.tournament_random_draw",
  tournamentNext: "button.tournament_next_match",
  tournamentStop: "button.tournament_stop",
};

// Per-camera entities carry their camera number as an attribute.
const CAMERA_KEYS = {
  problem: "binary_sensor.individual_camera_problem",
  fps: "sensor.camera_fps",
  calibrate: "button.calibrate_camera",
  image: "camera.board_camera",
};

// The card speaks Home Assistant's language, also in a regional variant such as "es-419"
// or "de-CH"; a language without card texts reads English.
const LANGUAGES = Object.keys(TEXT);
function language(hass) {
  const own = String(hass?.locale?.language || hass?.language || "en").toLowerCase();
  return LANGUAGES.find((lang) => own === lang || own.startsWith(`${lang}-`)) ?? "en";
}

// Every language has every key; an unknown key reads as itself.
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
function amPm(locale, language) {
  const format = locale.time_format ?? "language";
  const key = `${format}|${language}`;
  if (!clocks.has(key)) {
    let twelve = format === "12";
    if (format === "language" || format === "system") {
      // Only "system" follows the browser; never fall back to it for the language.
      const lang = format === "language" ? language || "en" : undefined;
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
  const language = locale.language || hass?.language;
  const twelve = amPm(locale, language);
  const server = hass?.config?.time_zone;
  return formatter("date", language, {
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
  ["checkout_121", "drill_checkout_121", "count"],
  ["catch_40", "drill_catch_40", "points"],
  ["jdc_challenge", "drill_jdc_challenge", "points"],
  ["singles", "drill_singles", "points"],
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

// The two teams of a team match: the team number and its players.
function teamsView(teams) {
  return (Array.isArray(teams) ? teams : [])
    .filter((team) => team && Number.isInteger(team.team) && Array.isArray(team.players))
    .map((team) => ({ team: team.team, players: team.players.filter(Number.isInteger) }));
}

const teamOf = (score) => (Number.isInteger(score.team) ? score.team : null);

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
      start: finite(score.start),
      team: teamOf(score),
      legs: finite(score.legs) ?? 0,
      sets: finite(score.sets) ?? 0,
      average: finite(score.average),
    }));
  return {
    game: finite(attributes.game),
    remaining,
    teams: teamsView(attributes.teams),
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

const DRILLS = [
  "around_the_clock",
  "doubles",
  "checkout",
  "bobs_27",
  "checkout_121",
  "catch_40",
  "jdc_challenge",
  "singles",
];
// Training games that check out a score, with a route to show.
const CHECKOUT_DRILLS = ["checkout", "checkout_121", "catch_40"];

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
    part: finite(attributes.part),
    best: finite(attributes.best),
    thrown: gameVisit(attributes),
    completed: Array.isArray(attributes.results) ? attributes.results[0]?.completed === true : false,
  };
}

// Beds to aim at in a training game: the route of a checkout, every bed of a
// number and the whole bull for 25, or the double of the doubles.
function drillBeds(drill) {
  if (!drill || drill.finished) return [];
  if (CHECKOUT_DRILLS.includes(drill.kind)) return hitBeds(drill.route[0] ?? "");
  const target = drill.target ?? "";
  return /^\d+$/.test(target) ? targetBeds(target) : hitBeds(target);
}

const CRICKET_NUMBERS = [20, 19, 18, 17, 16, 15, 25];
const CRICKET_GAMES = ["cricket", "cut_throat", "tactics"];
// No mark, one, two, and a closed number, as on a Cricket chalkboard.
const CRICKET_MARKS = ["", "/", "X", "Ⓧ"];

// The Cricket leg of the remaining-score sensor, which has no state then.
function cricketView(state) {
  const attributes = state?.attributes || {};
  if (!state || state.state === "unavailable" || !CRICKET_GAMES.includes(attributes.game)) return null;
  // Tactics adds the numbers 14 to 10.
  const numbers =
    Array.isArray(attributes.numbers) && attributes.numbers.length && attributes.numbers.every(Number.isInteger)
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
      team: teamOf(score),
      legs: finite(score.legs) ?? 0,
      sets: finite(score.sets) ?? 0,
      mpr: finite(score.mpr),
    }));
  return {
    kind: attributes.game,
    numbers,
    teams: teamsView(attributes.teams),
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

// Beds to aim at in Cricket: the treble of the next open number, or the whole
// bull, whose beds both mark.
function cricketBeds(cricket) {
  if (!cricket || cricket.won || cricket.winner !== null || !cricket.target) return [];
  return cricket.target === "BULL" ? targetBeds("25") : hitBeds(cricket.target);
}

const PARTY_GAMES = ["shanghai", "halve_it", "killer", "golf", "baseball", "count_up"];
// Party games with a scorecard of every round.
const SCORECARD_GAMES = ["golf", "baseball"];
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
      scorecard: Array.isArray(score.scorecard) ? score.scorecard.filter(Number.isInteger) : [],
    }));
  return {
    kind: attributes.game,
    round: finite(attributes.round),
    rounds: finite(attributes.rounds),
    // The players of extra rounds after a tie.
    playoff: Array.isArray(attributes.playoff) ? attributes.playoff.filter(Number.isInteger) : null,
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

// The bull-off before a match, while it runs: the bed and distance of every
// dart so far, and whether a tie throws again.
function bullOffView(state) {
  const bullOff = state?.attributes?.bull_off;
  if (!state || state.state === "unavailable" || !bullOff || typeof bullOff !== "object") return null;
  return {
    player: Number.isInteger(bullOff.player) ? bullOff.player : 1,
    name: named(bullOff.name),
    rethrow: bullOff.rethrow === true,
    byDistance: bullOff.by_distance === true,
    throws: (Array.isArray(bullOff.throws) ? bullOff.throws : [])
      .filter((item) => item && Number.isInteger(item.player))
      .map((item) => ({
        player: item.player,
        name: named(item.name),
        hit: named(item.hit),
        distance: finite(item.distance),
      })),
  };
}

// The bullseye beats the outer bull, which beats every other bed.
const BULL_RANKS = { BULL: 2, 25: 1 };

// The players whose dart no other beats so far, as the integration decides:
// the better bull bed first; outside the bull, or by distance if the players
// want, the closer dart. Darts the board did not measure stay tied.
function bullOffLeaders(bullOff) {
  const thrown = bullOff.throws.filter((item) => item.hit);
  const rank = (item) => BULL_RANKS[item.hit] ?? 0;
  const best = Math.max(0, ...thrown.map(rank));
  const leaders = thrown.filter((item) => rank(item) === best);
  const measured = leaders.every((item) => item.distance !== null);
  if (leaders.length < 2 || (best && !bullOff.byDistance) || !measured) return leaders.map((item) => item.player);
  const nearest = Math.min(...leaders.map((item) => item.distance));
  return leaders.filter((item) => item.distance === nearest).map((item) => item.player);
}

// Beds of a target: a number, any double (with the bull) or treble, or the
// whole bull, which games name 25.
function targetBeds(target) {
  if (!target) return [];
  if (target === "BULL" || target === "25") return [...hitBeds("BULL"), ...hitBeds("25")];
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

// How a target reads: "Any double" for D, "Bull (25/50)" for the bull where
// both beds count, "Bull" for the bullseye, D7 for D7.
function targetText(ui, target) {
  if (target === "D") return ui.t("any_double");
  if (target === "T") return ui.t("any_treble");
  if (target === "25") return ui.t("bull_target");
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
  if (mode === "bulloff") return targetBeds("25");
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

// The players of a team as they are called: Alex & Kim.
const teamName = (ui, team, scores) =>
  team.players
    .map((player) => playerName(ui, scores.find((score) => score.player === player) ?? { player, name: null }, true))
    .join(" & ");

// A won match as darts players tell it, the winner first: 3 : 2 in legs, or
// in sets when the match has them; a team counts once. A match of one leg
// has no result to tell.
function matchResult(game) {
  const winner = game.scores.find((score) => score.player === game.winner);
  if (!winner || game.scores.length < 2 || (game.legsToWin < 2 && game.setsToWin < 2)) return "";
  const count = (score) => (game.setsToWin > 1 ? score.sets : score.legs);
  const teams = game.teams ?? [];
  const others = teams.length
    ? teams
        .filter((team) => !team.players.includes(winner.player))
        .map((team) => game.scores.find((score) => score.player === team.players[0]))
        .filter(Boolean)
    : game.scores.filter((score) => score !== winner);
  return [winner, ...others].map(count).join(" : ");
}

// Who won the match, and how: "Alex wins the match 3 : 2!", or both players
// of a team; without a result "Alex wins the match!".
function winnerText(game, ui) {
  const result = matchResult(game);
  const team = game.teams?.find((item) => item.players.includes(game.winner));
  if (team) {
    const said = result ? fill(ui.t("score_winners_by"), { result }) : ui.t("score_winners");
    return `${teamName(ui, team, game.scores)} ${said}`;
  }
  const score = game.scores.find((item) => item.player === game.winner) ?? { player: game.winner, name: null };
  const said = result ? fill(ui.t("score_winner_by"), { result }) : ui.t("score_winner");
  return `${playerName(ui, score, true)} ${said}`;
}

// The Cricket game as players call it: Cricket, Cut-Throat Cricket, Tactics.
const cricketTitle = (t, kind) => t(kind === "cricket" ? "cricket" : `cricket_${kind}`);

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

// Start scores are worth showing when players start from different scores.
const handicap = (practice) => practice.scores.some((score) => score.start !== null && score.start !== practice.game);

// A player of the scoreboard and of the live card's match list.
function x01Players(practice, ui) {
  const { t, format } = ui;
  const scores = practice.scores.length
    ? practice.scores
    : [{ player: 1, name: practice.name, remaining: practice.remaining, legs: 0, sets: 0, average: null }];
  const match = scores.length > 1;
  const starts = handicap(practice);
  return scores.map((score) => {
    const active = practice.winner === null && score.player === practice.player;
    return {
      name: playerName(ui, score, match),
      badge: starts && score.start ? String(score.start) : "",
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

// The two teams of a team match: the score, the partners with the one at the
// board, and legs and sets.
function x01Teams(practice, ui) {
  const { t, format } = ui;
  const starts = handicap(practice);
  return practice.teams
    .map((team) => ({ team, members: practice.scores.filter((score) => team.players.includes(score.player)) }))
    .filter(({ members }) => members.length)
    .map(({ team, members }) => {
      const up = practice.winner === null && team.players.includes(practice.player);
      const [first] = members;
      return {
        name: teamName(ui, team, practice.scores),
        badge: starts && first.start ? String(first.start) : "",
        value: String(first.remaining),
        state: team.players.includes(practice.winner) ? "winner" : up ? "active" : "",
        note: up ? x01Note(practice, ui) : "",
        members: members.map((score) => ({
          name: playerName(ui, score, true),
          up: up && score.player === practice.player,
          detail: score.average === null ? "" : `Ø ${format(score.average, 1)}`,
        })),
        details: matchScore(practice, first, t),
      };
    });
}

// Every player, or in a team match the two teams.
function x01Tiles(practice, ui) {
  const teams = x01Teams(practice, ui);
  return teams.length ? teams : x01Players(practice, ui);
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
    // Out in Killer, or out of the extra rounds after a tie.
    const out = (killer && score.lives === 0) || Boolean(party.playoff && !party.playoff.includes(score.player));
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
        killer && out ? t("out") : "",
      ],
    };
  });
}

// Every dart of the bull-off with its bed and, where measured, its distance;
// once two darts are in, the one that leads.
function bullOffPlayers(bullOff, ui) {
  const match = bullOff.throws.length > 1;
  const leaders = bullOffLeaders(bullOff);
  const thrown = bullOff.throws.filter((item) => item.hit).length;
  const leader = thrown > 1 && leaders.length === 1 ? leaders[0] : null;
  return bullOff.throws.map((item) => ({
    name: playerName(ui, item, match),
    value: item.hit ? ui.label(item.hit) : "–",
    state: item.player === bullOff.player ? "active" : item.player === leader ? "winner" : "",
    note: "",
    details: [
      item.distance === null ? "" : `${ui.format(item.distance, 1)} mm`,
      item.player === leader ? ui.t("bull_off_leads") : "",
    ],
  }));
}

// A start score of the player's own, beside the name.
const badge = (player) => (player.badge ? ` <span class="badge">${escapeHtml(player.badge)}</span>` : "");

// The partners of a team, the one at the board in bold.
const membersHtml = (members) =>
  members
    .map((member) => {
      const text = escapeHtml([member.name, member.detail].filter(Boolean).join(" "));
      return member.up ? `<b>${text}</b>` : `<span>${text}</span>`;
    })
    .join(" · ");

// Players as large tiles on the scoreboard, with the picture of a linked person.
function playerTiles(players, ui = {}) {
  const tiles = players.map(
    (player) =>
      `<div class="player${player.state ? ` ${player.state}` : ""}"><div class="name">` +
      `${avatarHtml(ui.avatar?.(player.name))}${escapeHtml(player.name)}${badge(player)}</div>` +
      `<div class="big${player.lives ? " lives" : ""}">${escapeHtml(player.value)}</div>` +
      `<div class="route">${player.note}</div>` +
      (player.members ? `<div class="members">${membersHtml(player.members)}</div>` : "") +
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
        `<span class="who">${escapeHtml(player.name)}${badge(player)}</span>` +
        `<span class="muted">${escapeHtml(player.details.filter(Boolean).join(" · "))}</span>` +
        `<span class="rest${player.lives ? " lives" : ""}">${escapeHtml(player.value)}</span></div>`
    )
    .join("");

// The columns of the chalkboard: every player, or every team with its
// partners, the one at the board in bold.
function cricketColumns(cricket, ui) {
  const mpr = (score) => (score.mpr === null ? "–" : ui.format(score.mpr, 2));
  const playing = cricket.winner === null;
  const teams = cricket.teams
    .map((team) => ({ team, members: cricket.scores.filter((score) => team.players.includes(score.player)) }))
    .filter(({ members }) => members.length)
    .map(({ team, members }) => ({
      ...members[0],
      head: members
        .map((score) => {
          const name = escapeHtml(playerName(ui, score, true));
          return playing && score.player === cricket.player ? `<b>${name}</b>` : name;
        })
        .join(" &#38; "),
      mpr: members.map(mpr).join(" · "),
      active: playing && team.players.includes(cricket.player),
      winner: team.players.includes(cricket.winner),
    }));
  if (teams.length) return teams;
  const match = cricket.scores.length > 1;
  return cricket.scores.map((score) => ({
    ...score,
    head: `${avatarHtml(ui.avatar?.(playerName(ui, score, match)))}${escapeHtml(playerName(ui, score, match))}`,
    mpr: mpr(score),
    active: playing && cricket.player === score.player,
    winner: cricket.winner === score.player,
  }));
}

// The Cricket chalkboard: marks, points, marks per round, legs and sets. The
// scoreboard shows the next number in its corner; the live card has it beside.
function cricketTable(cricket, ui, { aim = true } = {}) {
  const { t } = ui;
  const columns = cricketColumns(cricket, ui);
  const match = columns.length > 1;
  const kind = (column) => (column.winner ? "winner" : match && column.active ? "active" : "");
  const row = (style, heading, content) =>
    `<tr class="${style}"><th>${escapeHtml(heading)}</th>${columns
      .map((column) => `<td class="${kind(column)}">${content(column)}</td>`)
      .join("")}</tr>`;
  const marks = (count) =>
    `<span role="img" aria-label="${escapeHtml(t(`mark_${count}`))}">${CRICKET_MARKS[count]}</span>`;
  const rows = cricket.numbers.map((number, slot) => {
    const bed = number === 25 ? "BULL" : `T${number}`;
    const style = columns.every((column) => column.marks[slot] >= 3)
      ? "closed"
      : bed === cricket.target
        ? "target"
        : "";
    return row(style, number === 25 ? "Bull" : String(number), (column) => marks(column.marks[slot]));
  });
  const text = (value) => (column) => escapeHtml(value(column));
  if (match) rows.push(row("total", t("cricket_points"), text((column) => String(column.points))));
  rows.push(row("detail", t("cricket_mpr"), text((column) => column.mpr)));
  if (match && cricket.legsToWin > 1) rows.push(row("detail", t("score_legs"), text((column) => String(column.legs))));
  if (match && cricket.setsToWin > 1) rows.push(row("detail", t("score_sets"), text((column) => String(column.sets))));
  const head = columns.map((column) => `<th class="${kind(column)}">${column.head}</th>`).join("");
  const next = aim && cricket.target && !cricket.won && cricket.winner === null ? bedChips(ui, [cricket.target]) : "";
  const shot = aim && cricket.won && cricket.winner === null ? note(t("game_shot"), "won") : "";
  const corner = shot || next;
  // Tactics has twelve numbers; they fit the screen in smaller type.
  const size = cricket.numbers.length > CRICKET_NUMBERS.length ? " many" : "";
  // The next number sits above the numbers, so the chalkboard fits a landscape screen.
  return (
    `<table class="cricket${size}">${
      corner || columns.some((column) => column.head) ? `<thead><tr><th class="aim">${corner}</th>${head}</tr></thead>` : ""
    }<tbody>${rows.join("")}</tbody></table>`
  );
}

// Golf and Baseball: the score of every hole or inning per player, and the total.
function scorecardTable(party, ui) {
  const current = party.winner === null ? party.round : null;
  const played = Math.max(party.rounds ?? 0, current ?? 0, ...party.scores.map((score) => score.scorecard.length));
  const rounds = Array.from({ length: played }, (_, index) => index + 1);
  // Extra rounds go on from 1 after 20.
  const number = (round) => ((round - 1) % 20) + 1;
  const now = (round) => (round === current ? ` class="now"` : "");
  const match = party.scores.length > 1;
  const rows = party.scores.map((score) => {
    const up = current !== null && score.player === party.player;
    // The visit at the board counts for the round being played.
    const booked = score.scorecard.reduce((sum, value) => sum + value, 0);
    const live = up && party.visit.length ? score.points - booked : null;
    const cells = rounds
      .map((round) => `<td${now(round)}>${score.scorecard[round - 1] ?? (round === current && live !== null ? live : "")}</td>`)
      .join("");
    const style = party.winner === score.player ? "winner" : up && match ? "active" : "";
    return (
      `<tr${style ? ` class="${style}"` : ""}><th>${escapeHtml(playerName(ui, score, match))}</th>${cells}` +
      `<td class="total">${score.points}</td></tr>`
    );
  });
  const head = rounds.map((round) => `<th${now(round)}>${number(round)}</th>`).join("");
  return (
    `<table class="scorecard"><thead><tr><th></th>${head}<th class="total">${escapeHtml(ui.t("total"))}</th></tr></thead>` +
    `<tbody>${rows.join("")}</tbody></table>`
  );
}

// The round of a party game: Hole 3/9, Inning 5/9, Round 2/7, or an extra round.
function partyRound(party, t) {
  if (!party.rounds || party.round === null) return "";
  const name = t({ golf: "golf_hole", baseball: "baseball_inning" }[party.kind] ?? "drill_round");
  if (party.playoff) return `${t("playoff")} · ${name} ${party.target ?? party.round}`;
  return `${name} ${party.round}/${party.rounds}`;
}

// A training game: the target, what happened and the facts about the game.
// A fact reads "12 darts", or with its name first "Round 3 / 21".
function drillParts(drill, ui) {
  const { t, percent } = ui;
  const fact = (value, name = "", lead = false) => ({ value, name, lead });
  const big = drill.finished ? "✓" : targetText(ui, drill.target ?? "–");
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
  const scored = drill.finished ? note(fill(t("drill_bobs_done"), { points: drill.score }), "won") : "";
  if (drill.kind === "catch_40" && drill.finished) {
    return { big, note: scored, facts: [fact(String(drill.score ?? 0), t("drill_points"))] };
  }
  if (CHECKOUT_DRILLS.includes(drill.kind)) {
    const visit = fact(`${drill.visit ?? 1} / ${drill.visits ?? 3}`, t("drill_visit"), true);
    const facts =
      drill.kind === "catch_40"
        ? [
            fact(`${drill.progress + 1} / ${drill.targets}`, t("drill_round"), true),
            visit,
            fact(String(drill.score ?? 0), t("drill_points")),
          ]
        : [
            visit,
            fact(`${drill.successes} / ${drill.attempts}`, t("drill_checked")),
            ...(drill.rate === null ? [] : [fact(percent(drill.rate))]),
            ...(drill.best === null ? [] : [fact(String(drill.best), t("drill_best"), true)]),
          ];
    return {
      big: String(drill.remaining ?? drill.target ?? "–"),
      note: drill.won ? note(t("game_shot"), "won") : drill.bust ? note(t("bust"), "bust") : bedChips(ui, drill.route),
      facts,
    };
  }
  if (drill.kind === "jdc_challenge" || drill.kind === "singles") {
    const step =
      drill.kind === "jdc_challenge"
        ? fact(`${drill.part ?? 1} / 3`, t("drill_part"), true)
        : fact(`${Math.min(drill.progress + 1, drill.targets)} / ${drill.targets}`, t("drill_round"), true);
    return {
      big,
      note: scored,
      facts: [
        step,
        fact(String(drill.score ?? 0), t("drill_points")),
        ...(drill.best === null ? [] : [fact(String(drill.best), t("drill_best"), true)]),
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
  // "Bull (25/50)" fits the screen in smaller type than a number.
  const long = parts.big.length > 4 ? " long" : "";
  return (
    `<div class="single"><div class="big${long}">${escapeHtml(parts.big)}</div><div class="route">${parts.note}</div>` +
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

// Match summary ----------------------------------------------------------------

// The summary of the finished match on the board, as the practice sensor keeps
// it; the next game, which clears the winner, ends it.
function summaryView(state) {
  const attributes = state?.attributes || {};
  const summary = attributes.summary;
  if (!state || state.state === "unavailable" || !summary || typeof summary !== "object") return null;
  if (!Number.isInteger(attributes.winner) || summary.winner !== attributes.winner || summary.game !== attributes.game) {
    return null;
  }
  const raw = (Array.isArray(summary.players) ? summary.players : []).filter(
    (item) => item && Number.isInteger(item.player)
  );
  if (raw.length < 2) return null;
  // X01 has averages, the Cricket games marks per round; party games neither.
  const kind = "average" in raw[0] ? "x01" : "mpr" in raw[0] ? "cricket" : "party";
  return {
    ended: String(summary.ended ?? ""),
    kind,
    winner: summary.winner,
    legsToWin: finite(summary.legs_to_win) ?? 1,
    setsToWin: finite(summary.sets_to_win) ?? 1,
    doubleOut: summary.double_out !== false,
    players: raw.map((item) => ({
      player: item.player,
      name: named(item.name),
      legs: finite(item.legs) ?? 0,
      sets: finite(item.sets) ?? 0,
      darts: finite(item.darts),
      average: finite(item.average),
      first9: finite(item.first_9_average),
      checkouts: finite(item.checkouts) ?? 0,
      atDouble: finite(item.darts_at_double) ?? 0,
      checkoutRate: finite(item.checkout_rate),
      highestCheckout: finite(item.highest_checkout),
      scores100: finite(item.scores_100),
      scores140: finite(item.scores_140),
      scores180: finite(item.scores_180),
      bestLeg: finite(item.best_leg),
      mpr: finite(item.mpr),
      marks: finite(item.marks),
    })),
  };
}

// The rows of the summary: the result, then the numbers of the game.
function summaryRows(summary, ui) {
  const { t, format, percent } = ui;
  const value = (number, digits = 0) => (number === null ? "–" : format(number, digits));
  const darts = (number) => (number === null ? "–" : fill(t("unit_darts"), { value: format(number, 0) }));
  const checkout = (player) =>
    player.checkoutRate === null
      ? "–"
      : `${percent(player.checkoutRate, 1)} (${player.checkouts}/${player.atDouble})`;
  const doubles = summary.doubleOut;
  const rows = {
    x01: [
      [t("average"), (player) => value(player.average, 1)],
      [t("first_9"), (player) => value(player.first9, 1)],
      ...(doubles ? [[t("summary_checkout"), checkout]] : []),
      [t("highest_checkout"), (player) => value(player.highestCheckout)],
      [t("max"), (player) => value(player.scores180)],
      [t("scores_140"), (player) => value(player.scores140)],
      [t("scores_100"), (player) => value(player.scores100)],
      [t("summary_best_leg"), (player) => darts(player.bestLeg)],
      ...(doubles ? [[t("summary_at_double"), (player) => value(player.atDouble)]] : []),
    ],
    cricket: [
      [t("cricket_mpr"), (player) => value(player.mpr, 2)],
      [t("summary_marks"), (player) => value(player.marks)],
      [t("summary_best_leg"), (player) => darts(player.bestLeg)],
    ],
    party: [],
  }[summary.kind];
  const sets = summary.setsToWin > 1;
  const legs = [t("score_legs"), (player) => String(player.legs)];
  return [
    ...(sets ? [[t("score_sets"), (player) => String(player.sets)], legs] : [legs]),
    ...rows,
    [t("darts"), (player) => value(player.darts)],
  ];
}

// The summary as a table: a column per player with the picture of a linked
// person, the winner's highlighted, and the result in the first row.
function summaryTable(summary, ui) {
  const column = (player) => (player.player === summary.winner ? "winner" : "");
  const head = summary.players
    .map((player) => {
      const name = playerName(ui, player, true);
      return `<th class="${column(player)}">${avatarHtml(ui.avatar?.(name))}${escapeHtml(name)}</th>`;
    })
    .join("");
  const rows = summaryRows(summary, ui)
    .map(
      ([name, cell], index) =>
        `<tr${index ? "" : ` class="result"`}><th>${escapeHtml(name)}</th>${summary.players
          .map((player) => `<td class="${column(player)}">${escapeHtml(cell(player))}</td>`)
          .join("")}</tr>`
    )
    .join("");
  return (
    `<table class="summary"><thead><tr><th class="caption">${escapeHtml(ui.t("summary"))}</th>${head}</tr></thead>` +
    `<tbody>${rows}</tbody></table>`
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
    return { title: t(`drill_${view.drill.kind}`), meta: "", banner: "", bannerKind: "", main: drillBoard(view.drill, ui) };
  }
  if (view.mode === "idle") {
    return { title: ui.name, meta: t("training"), banner: "", bannerKind: "", main: idleBoard(ui.stats, ui) };
  }
  if (view.mode === "bulloff") {
    // A tie throws again, which the banner tells in the colour of a warning.
    const { rethrow } = view.bullOff;
    return {
      title: t("bull_off"),
      meta: t("bull_off_hint"),
      banner: rethrow ? t("bull_off_rethrow") : "",
      bannerKind: rethrow ? "rethrow" : "",
      main: playerTiles(bullOffPlayers(view.bullOff, ui), ui),
    };
  }
  const game = { cricket: view.cricket, party: view.party }[view.mode] ?? view.practice;
  const round = view.mode === "party" ? partyRound(game, t) : "";
  // Cut-Throat turns the points round, and Golf's players stop by pulling their darts.
  const hint = { cut_throat: "cut_throat_hint", golf: "golf_hint" }[game.kind];
  const scorecard = view.mode === "party" && SCORECARD_GAMES.includes(game.kind);
  // The summary of a won match takes the place of the players.
  const main = view.summary
    ? () => summaryTable(view.summary, ui)
    : {
        cricket: () => cricketTable(game, ui),
        party: () => playerTiles(partyPlayers(game, ui), ui) + (scorecard ? scorecardTable(game, ui) : ""),
        x01: () => playerTiles(x01Tiles(game, ui), ui),
      }[view.mode];
  return {
    title: { cricket: cricketTitle(t, game.kind), party: t(`party_${game.kind}`) }[view.mode] ??
      `${t("practice")} ${game.game ?? ""}`.trim(),
    meta: [round, hint ? t(hint) : "", ...matchFormat(game, t)].filter(Boolean).join(" · "),
    banner: game.winner !== null ? winnerText(game, ui) : "",
    bannerKind: "",
    main: main(),
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
      // Both players of the winning team, in a team match.
      winners: Array.isArray(match.winners) ? match.winners.filter(Number.isInteger) : [finite(match.winner)],
      legsToWin: finite(match.legs_to_win) ?? 1,
      setsToWin: finite(match.sets_to_win) ?? 1,
      players: match.players.filter((player) => player && typeof player === "object"),
    }));
  return { players, headToHead, matches };
}

// What a player won in a match of the history: sets when the match had sets,
// otherwise legs. Up to version 1.5, winning the match took the winner's legs
// of the deciding set away again; a match won in legs had all it needed.
function historyScore(match, player, index) {
  if (match.setsToWin > 1) return finite(player.sets) ?? 0;
  const legs = finite(player.legs) ?? 0;
  return match.winners.includes(index + 1) ? Math.max(legs, match.legsToWin) : legs;
}

// A game as players call it: 501, Cricket, Killer, Bob's 27. Games the card does
// not know yet read as Home Assistant names the option, if it is asked.
function gameName(t, game, fallback) {
  if (Number.isInteger(game)) return String(game);
  if (CRICKET_GAMES.includes(game)) return cricketTitle(t, game);
  if (PARTY_GAMES.includes(game)) return t(`party_${game}`);
  if (DRILLS.includes(game)) return t(`drill_${game}`);
  return (fallback && fallback(game)) || String(game ?? "");
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
        `<div class="profile"><div class="profile-name">${avatarHtml(ui.avatar?.(player.name))}` +
        `<span>${escapeHtml(player.name)}</span></div>` +
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
          const shown = `${player.name || `${t("score_player")} ${index + 1}`} ${historyScore(match, player, index)}`;
          const tag = match.winners.includes(index + 1) ? "b" : "span";
          return `<${tag}>${escapeHtml(shown)}</${tag}>`;
        })
        .join(" · ");
      // Results count legs; a match of sets says so.
      const game = [gameName(t, match.game), match.setsToWin > 1 ? t("score_sets") : ""].filter(Boolean).join(" · ");
      return (
        `<div class="match"><span class="muted">${escapeHtml(date(match.ended))}</span>` +
        `<span class="game">${escapeHtml(game)}</span><span>${players}</span></div>`
      );
    })
    .join("");
  return { players, headToHead, matches };
}

// People ---------------------------------------------------------------------

// Pictures that Home Assistant serves itself or that come from the web; no other schemes.
function pictureUrl(value) {
  return typeof value === "string" && /^(\/(?!\/)|https?:\/\/)/i.test(value) ? value : null;
}

const avatarHtml = (picture) =>
  picture ? `<img class="avatar" src="${escapeHtml(picture)}" alt="" draggable="false">` : "";

// Names are the same player regardless of upper and lower case, as in the integration.
const nameKey = (name) => String(name ?? "").trim().toLowerCase();

// The person each player is linked to, with the picture and whether they are home.
function personLinks(hass, profiles) {
  const links = new Map();
  const players = Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : [];
  for (const player of players) {
    if (!named(player?.name) || !named(player.person)) continue;
    const state = hass?.states?.[player.person];
    links.set(nameKey(player.name), {
      person: player.person,
      picture: pictureUrl(state?.attributes?.entity_picture),
      home: state?.state === "home",
    });
  }
  return links;
}

// The new game screen ------------------------------------------------------------

const LOBBY_GROUPS = ["x01", "cricket", "party", "training", "more"];
// Limits of the start_game action.
const LOBBY_LIMITS = { players: 4, name: 20, legs: 11, sets: 7 };
// Every game of the practice select this card knows, for the editor before a board is seen.
const KNOWN_GAMES = ["101", "301", "501", "701", "901", "1001", ...CRICKET_GAMES, ...PARTY_GAMES, ...DRILLS];
// A game that ended opens the new game screen after this pause, so the result shows first.
const LOBBY_DELAY = 8000;
const LOBBY_OPTIONS = ["double_out", "double_in", "bull_off", "bull_off_distance", "teams"];
// Teams are two pairs of players; start scores of their own go in steps of 100.
const TEAM_SIZE = 4;
const START_STEP = 100;
const START_LIMITS = [101, 1001];

function gameGroup(game) {
  if (/^\d+$/.test(game)) return "x01";
  if (game.startsWith("cricket") || CRICKET_GAMES.includes(game)) return "cricket";
  if (PARTY_GAMES.includes(game)) return "party";
  return DRILLS.includes(game) ? "training" : "more";
}

// What a game asks of the players, and whether the X01 rules apply.
function gameRules(game) {
  const group = gameGroup(game);
  const drill = group === "training";
  return {
    x01: group === "x01",
    drill,
    // Four players of X01 or a Cricket game may play as two teams.
    teams: group === "x01" || group === "cricket",
    minPlayers: game === "killer" ? 2 : 1,
    maxPlayers: drill ? 1 : LOBBY_LIMITS.players,
  };
}

// The games of the practice select by group, as far as the card offers them.
function lobbyGames(options, offered) {
  const wanted = Array.isArray(offered) && offered.length ? new Set(offered.map(String)) : null;
  const games = (Array.isArray(options) ? options : [])
    .map(String)
    .filter((game) => game !== "off" && (!wanted || wanted.has(game)));
  return LOBBY_GROUPS.map((group) => ({ group, games: games.filter((game) => gameGroup(game) === group) })).filter(
    (item) => item.games.length
  );
}

const within = (value, max, fallback) =>
  Number.isInteger(value) ? Math.min(Math.max(value, 1), max) : fallback;

// The choice the new game screen starts from: the game, the players and the
// rules as the board has them now. A name twice becomes a guest.
function lobbyChoice(board, games) {
  const game = games.includes(board.game) ? board.game : games.includes("501") ? "501" : games[0];
  const count = within(board.players, LOBBY_LIMITS.players, 1);
  const players = [];
  for (let index = 0; index < count; index += 1) {
    const name = String(board.names[index] ?? "").trim();
    players.push(players.some((other) => name && nameKey(other) === nameKey(name)) ? "" : name);
  }
  // Players without any name need not be chosen: the game starts with one of them.
  const chosen = players.some(Boolean) ? players : [];
  const starts = Array.isArray(board.starts) ? board.starts : [];
  const start = (index) => (Number.isInteger(starts[index]) ? starts[index] : 0);
  return {
    game,
    players: chosen,
    // The start score of every player, 0 for the game's; set ones go back with the start.
    starts: chosen.map((_, index) => start(index)),
    handicap: starts.some((value) => Number.isInteger(value) && value > 0),
    teams: board.teams === true,
    legs: within(board.legs, LOBBY_LIMITS.legs, 1),
    sets: within(board.sets, LOBBY_LIMITS.sets, 1),
    double_out: board.double_out !== false,
    double_in: board.double_in === true,
    bull_off: board.bull_off === true,
    bull_off_distance: board.bull_off_distance === true,
    // A tournament instead of a match, with the settings of the next tournament.
    tournament: false,
    format: TOURNAMENT_FORMATS.includes(board.format) ? board.format : "round_robin",
    third_place: board.third_place === true,
    random_draw: board.random_draw === true,
    draft: "",
  };
}

// How many players a choice takes: up to four in a match, eight in a tournament.
const playerLimit = (choice) => (choice.tournament ? TOURNAMENT_LIMITS.players : LOBBY_LIMITS.players);

// The choice after a tap: a game, a player added, moved or removed, the format or a rule.
function lobbyChange(choice, action, value) {
  const next = { ...choice, players: [...choice.players], starts: [...(choice.starts ?? [])] };
  const index = Number(value);
  const room = next.players.length < playerLimit(next);
  if (action === "game") {
    next.game = String(value);
  } else if (action === "mode") {
    // Tournament players need a name; a tournament of guests has no table.
    next.tournament = value === "tournament";
    // The start scores stay with their players.
    const kept = next.players
      .map((name, index) => [name, next.starts[index] ?? 0])
      .filter(([name]) => name || !next.tournament)
      .slice(0, playerLimit(next));
    next.players = kept.map(([name]) => name);
    next.starts = kept.map(([, start]) => start);
  } else if (action === "format" && TOURNAMENT_FORMATS.includes(value)) {
    next.format = value;
  } else if (action === "add") {
    const name = String(value ?? "").trim().slice(0, LOBBY_LIMITS.name);
    if (room && name && !next.players.some((player) => nameKey(player) === nameKey(name))) {
      next.players.push(name);
      next.starts.push(0);
      next.draft = "";
    }
  } else if (action === "guest" && room && !next.tournament) {
    next.players.push("");
    next.starts.push(0);
  } else if (action === "remove") {
    next.players.splice(index, 1);
    next.starts.splice(index, 1);
  } else if (action === "up" || action === "down") {
    const other = action === "up" ? index - 1 : index + 1;
    if (other >= 0 && other < next.players.length) {
      [next.players[index], next.players[other]] = [next.players[other], next.players[index]];
      [next.starts[index], next.starts[other]] = [next.starts[other] ?? 0, next.starts[index] ?? 0];
    }
  } else if ((action === "lower" || action === "raise") && gameGroup(next.game) === "x01" && index in next.players) {
    // A start score of the player's own in steps of 100; the game's start is 0.
    const game = Number(next.game);
    const shown = (next.starts[index] || game) + (action === "raise" ? START_STEP : -START_STEP);
    const start = Math.min(Math.max(shown, START_LIMITS[0]), START_LIMITS[1]);
    next.starts[index] = start === game ? 0 : start;
  } else if (action === "legs" || action === "sets") {
    next[action] = within(next[action] + index, LOBBY_LIMITS[action], next[action]);
  } else if (action === "toggle" && [...LOBBY_OPTIONS, "third_place", "random_draw"].includes(value)) {
    next[value] = !next[value];
  }
  return next;
}

// Names to add: players at home first, then everybody else with a profile or a name field.
function lobbySuggestions(profiles, names, links, chosen) {
  const taken = new Set(chosen.map(nameKey));
  const people = new Map();
  const listed = (Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : []).map(
    (player) => player?.name
  );
  for (const name of [...listed, ...names]) {
    const key = nameKey(name);
    if (!named(name) || !key || taken.has(key) || people.has(key)) continue;
    const link = links.get(key);
    people.set(key, { name: name.trim(), picture: link?.picture ?? null, home: link?.home === true });
  }
  const all = [...people.values()];
  return [...all.filter((person) => person.home), ...all.filter((person) => !person.home)];
}

// The start_game action for a choice; rules the game or the board does not have stay out.
function startGameData(choice, { entry = null, distance = false } = {}) {
  const rules = gameRules(choice.game);
  const players = choice.players.slice(0, rules.maxPlayers);
  const data = { game: choice.game, players: players.length ? players : [""] };
  if (entry) data.config_entry_id = entry;
  if (!rules.drill && players.length > 1) {
    Object.assign(data, { legs: choice.legs, sets: choice.sets, bull_off: choice.bull_off });
    if (distance && choice.bull_off) data.bull_off_distance = choice.bull_off_distance;
  }
  if (rules.x01) Object.assign(data, { double_out: choice.double_out, double_in: choice.double_in });
  // Start scores go with the start once any is set, so the game's start comes back, too.
  const starts = players.map((_, index) => choice.starts?.[index] ?? 0);
  if (rules.x01 && (choice.handicap || starts.some(Boolean))) data.start_scores = starts;
  if (rules.teams && players.length === TEAM_SIZE) data.teams = choice.teams === true;
  return data;
}

// The new game screen: the games by group, the players, the format, the rules and the start.
function lobbyHtml(choice, ui) {
  const { t } = ui;
  const rules = gameRules(choice.game);
  const text = (key, values) => escapeHtml(values ? fill(t(key), values) : t(key));
  const button = (action, value, content, extra = "") =>
    `<button type="button" data-lobby="${action}"${value === undefined ? "" : ` data-value="${escapeHtml(value)}"`}` +
    `${extra}>${content}</button>`;
  const block = (label, content, kind) =>
    `<div class="lobby-block ${kind}"><div class="section-label">${text(label)}</div>${content}</div>`;
  // A tournament plays X01 and Cricket, as far as the board offers them.
  const offered = choice.tournament ? ui.tournamentGames : ui.games;
  const modes = ui.tournamentGames.length
    ? `<div class="lobby-mode" role="group" aria-label="${text("tournament_mode")}">${["match", "tournament"]
        .map((mode) =>
          button(
            "mode",
            mode,
            text(`tournament_mode_${mode}`),
            ` class="mode" aria-pressed="${choice.tournament === (mode === "tournament")}"`
          )
        )
        .join("")}</div>`
    : "";
  const games = offered
    .map(
      ({ group, games: list }) =>
        `<div class="lobby-group ${group}"><div class="section-label">${text(`lobby_group_${group}`)}</div>` +
        `<div class="game-grid">${list
          .map((game) =>
            button("game", game, escapeHtml(ui.name(game)), ` class="game" aria-pressed="${game === choice.game}"`)
          )
          .join("")}</div></div>`
    )
    .join("");
  const shown = (name, index) => name || `${t("score_player")} ${index + 1}`;
  const last = choice.players.length - 1;
  // In X01, every player can start from a score of their own.
  const startHtml = (index, who) => {
    if (!rules.x01) return "";
    const start = choice.starts?.[index] || Number(choice.game);
    return (
      `<span class="lobby-start${choice.starts?.[index] ? " own" : ""}">` +
      button("lower", index, "−", ` aria-label="${text("lobby_start_lower", who)}"${start <= START_LIMITS[0] ? " disabled" : ""}`) +
      `<b>${start}</b>` +
      button("raise", index, "+", ` aria-label="${text("lobby_start_raise", who)}"${start >= START_LIMITS[1] ? " disabled" : ""}`) +
      `</span>`
    );
  };
  const seats = choice.tournament ? TOURNAMENT_LIMITS.players : rules.maxPlayers;
  const players = choice.players
    .map((name, index) => {
      const who = { name: shown(name, index) };
      return (
        `<li class="lobby-player${index >= seats ? " resting" : ""}">${avatarHtml(ui.avatar(name))}` +
        `<span class="who">${escapeHtml(who.name)}</span>${startHtml(index, who)}` +
        button("up", index, "▲", ` aria-label="${text("lobby_move_up", who)}"${index === 0 ? " disabled" : ""}`) +
        button("down", index, "▼", ` aria-label="${text("lobby_move_down", who)}"${index === last ? " disabled" : ""}`) +
        button("remove", index, "✕", ` aria-label="${text("lobby_remove", who)}"`) +
        `</li>`
      );
    })
    .join("");
  const full = choice.players.length >= playerLimit(choice) ? " disabled" : "";
  const suggestions =
    ui.suggestions
      .map((person) =>
        button(
          "add",
          person.name,
          `${avatarHtml(person.picture)}<span>${escapeHtml(person.name)}</span>` +
            (person.home ? `<span class="home" title="${text("lobby_home")}" aria-label="${text("lobby_home")}">⌂</span>` : ""),
          ` class="suggestion${person.home ? " home" : ""}"${full}`
        )
      )
      .join("") +
    (choice.tournament ? "" : button("guest", undefined, `+ ${text("lobby_guest")}`, ` class="suggestion guest"${full}`));
  const entry =
    `<div class="name-entry"><input class="lobby-name" type="text" maxlength="${LOBBY_LIMITS.name}" autocomplete="off"` +
    ` enterkeyhint="done" data-focus="lobby-name" placeholder="${text("lobby_name")}"` +
    ` aria-label="${text("lobby_new_player")}" value="${escapeHtml(choice.draft)}"${full}>` +
    `${button("add-name", undefined, text("lobby_add"), full)}</div>`;
  const match = choice.tournament || (!rules.drill && choice.players.length > 1);
  const stepper = (key, label) => {
    const name = { name: t(label) };
    return (
      `<div class="stepper"><span class="stepper-label">${text(label)}</span><span class="stepper-controls">` +
      button(key, -1, "−", ` aria-label="${text("lobby_decrease", name)}"${choice[key] <= 1 ? " disabled" : ""}`) +
      `<b class="stepper-value">${choice[key]}</b>` +
      button(key, 1, "+", ` aria-label="${text("lobby_increase", name)}"${choice[key] >= LOBBY_LIMITS[key] ? " disabled" : ""}`) +
      `</span></div>`
    );
  };
  const options = [
    ...(rules.x01 ? ["double_out", "double_in"] : []),
    ...(match ? ["bull_off"] : []),
    ...(match && ui.distance && choice.bull_off ? ["bull_off_distance"] : []),
    ...(!choice.tournament && rules.teams && ui.teams && choice.players.length === TEAM_SIZE ? ["teams"] : []),
    ...(choice.tournament && choice.format === "knockout" && choice.players.length >= THIRD_PLACE_PLAYERS
      ? ["third_place"]
      : []),
    ...(choice.tournament ? ["random_draw"] : []),
  ];
  const formats = choice.tournament
    ? `<div class="formats">${TOURNAMENT_FORMATS.map((format) =>
        button("format", format, text(`tournament_${format}`), ` class="option" aria-pressed="${choice.format === format}"`)
      ).join("")}</div>`
    : "";
  // Nobody chosen is one player without a name.
  const blocked = choice.tournament
    ? choice.players.length < TOURNAMENT_LIMITS.min
    : Math.max(choice.players.length, 1) < rules.minPlayers;
  const hint = blocked
    ? t(choice.tournament ? "tournament_needs_players" : "needs_players")
    : !choice.tournament && rules.drill && choice.players.length > 1
      ? fill(t("lobby_one_player"), { name: shown(choice.players[0], 0) })
      : "";
  const actions =
    `<div class="lobby-actions"><span class="lobby-hint" role="status">${escapeHtml(hint)}</span>` +
    (ui.running || ui.tournamentRunning
      ? button(
          "end",
          undefined,
          text(ui.confirmEnd ? "confirm" : ui.tournamentRunning ? "tournament_stop" : "lobby_end"),
          ' class="secondary"'
        )
      : "") +
    button("close", undefined, text("lobby_close"), ' class="secondary"') +
    button(
      "start",
      undefined,
      choice.tournament ? text("tournament_start") : text("lobby_start", { game: ui.name(choice.game) }),
      ` class="start"${blocked ? " disabled" : ""}`
    ) +
    `</div>`;
  return (
    `<section class="lobby" aria-label="${text("lobby_label")}"><div class="lobby-games">${modes}${games}</div>` +
    `<div class="lobby-setup">${block(
      "lobby_players",
      (players ? `<ol class="lobby-players">${players}</ol>` : `<p class="lobby-nobody muted">${text("lobby_nobody")}</p>`) +
        `<div class="suggestions">${suggestions}</div>${entry}`,
      "players-block"
    )}` +
    (match
      ? block(
          "lobby_format",
          `${formats}<div class="steppers">${stepper("legs", "lobby_legs")}${stepper("sets", "lobby_sets")}</div>`,
          "format"
        )
      : "") +
    (options.length
      ? block(
          "lobby_options",
          options
            .map((option) =>
              button("toggle", option, text(option), ` class="option" aria-pressed="${choice[option]}"`)
            )
            .join(""),
          "options"
        )
      : "") +
    `${actions}</div></section>`
  );
}

// Idle mode ----------------------------------------------------------------------

// The tournament first: while one is on, it matters most.
const IDLE_PANELS = ["tournament", "leaderboard", "records", "today", "last_match", "clock"];

// Whether a game is on: none without a game, over once a match or a training game is decided.
function gameState(view) {
  if (view.mode === "idle") return "none";
  if (view.mode === "drill") return view.drill.finished ? "over" : "running";
  if (view.mode === "bulloff") return "running";
  const game = view.practice ?? view.cricket ?? view.party;
  return game.winner === null ? "running" : "over";
}

// The best players by 3-dart average, then by legs won.
function leaderboardHtml(data, ui) {
  const ranked = data.players
    .filter((player) => player.legsPlayed > 0)
    .sort(
      (a, b) => (b.average ?? -1) - (a.average ?? -1) || b.legsWon - a.legsWon || a.name.localeCompare(b.name)
    )
    .slice(0, 5);
  if (!ranked.length) return "";
  return `<ol class="ranking">${ranked
    .map(
      (player, index) =>
        `<li><span class="rank">${index + 1}</span>${avatarHtml(ui.avatar(player.name))}` +
        `<span class="who">${escapeHtml(player.name)}</span>` +
        `<span class="score">${player.average === null ? "–" : `Ø ${escapeHtml(ui.format(player.average, 1))}`}</span>` +
        `<span class="muted">${escapeHtml(
          fill(ui.t("idle_legs"), { won: player.legsWon, played: player.legsPlayed })
        )}</span></li>`
    )
    .join("")}</ol>`;
}

function recordsHtml(data, ui) {
  return data.records.length ? `<dl class="records">${bestsHtml(data.records, ui)}</dl>` : "";
}

// Today's darts towards the daily goal, and the session.
function todayHtml(data, ui) {
  const { t, format } = ui;
  const { stats } = data;
  if (stats.today === null) return "";
  const goal = stats.goal > 0;
  const share = goal ? Math.min(100, Math.round((stats.today * 100) / stats.goal)) : 0;
  const facts = [
    { value: format(stats.average, 1), name: t("average") },
    { value: format(stats.highest, 0), name: t("highest") },
    { value: format(stats.max, 0), name: t("max") },
    ...(stats.streak > 0
      ? [{ value: format(stats.streak, 0), name: t(stats.streak === 1 ? "streak_day" : "streak_days") }]
      : []),
  ];
  return (
    `<div class="single"><div class="big">${escapeHtml(format(stats.today, 0))}</div>` +
    `<div class="label">${escapeHtml(goal ? fill(t("idle_goal"), { goal: format(stats.goal, 0) }) : t("darts_today"))}</div>` +
    (goal ? `<div class="goal${share >= 100 ? " reached" : ""}"><i style="width:${share}%"></i></div>` : "") +
    `<div class="facts">${factsHtml(facts)}</div></div>`
  );
}

// The last match of several players: the game, when, and everybody's result.
function lastMatchHtml(data, ui) {
  const { t, format } = ui;
  const match = data.match;
  if (!match) return "";
  const rows = match.players
    .map((player, index) => {
      const name = named(player.name) ?? `${t("score_player")} ${index + 1}`;
      const winner = index + 1 === match.winner;
      const numbers = [
        // Legs, or sets in a match of sets, as in the players card.
        String(historyScore(match, player, index)),
        finite(player.average) === null ? "" : `Ø ${format(player.average, 1)}`,
        finite(player.mpr) === null ? "" : `${t("cricket_mpr")} ${format(player.mpr, 2)}`,
      ];
      return (
        `<li class="${winner ? "winner" : ""}">${avatarHtml(ui.avatar(name))}<span class="who">${escapeHtml(name)}</span>` +
        `<span class="score">${escapeHtml(numbers[0])}</span>` +
        `<span class="muted">${escapeHtml(numbers.slice(1).filter(Boolean).join(" · "))}</span>` +
        `${winner ? '<span class="trophy" aria-hidden="true">🏆</span>' : ""}</li>`
      );
    })
    .join("");
  return (
    `<div class="match-head">${escapeHtml(`${gameName(t, match.game)} · ${ui.date(match.ended)}`)}</div>` +
    `<ol class="ranking result">${rows}</ol>`
  );
}

function clockHtml(data, ui) {
  const shown = ui.clock(data.now);
  return (
    `<div class="single clock"><div class="big">${escapeHtml(shown.time)}</div>` +
    `<div class="facts"><span>${escapeHtml(shown.day)}</span></div></div>`
  );
}

const IDLE_RENDER = {
  tournament: tournamentPanelHtml,
  leaderboard: leaderboardHtml,
  records: recordsHtml,
  today: todayHtml,
  last_match: lastMatchHtml,
  clock: clockHtml,
};

// The panels with something to show, in the order of the card's list.
function idlePanels(wanted, data, ui) {
  const list = Array.isArray(wanted) && wanted.length ? [...new Set(wanted)] : IDLE_PANELS;
  return list
    .filter((panel) => IDLE_PANELS.includes(panel))
    .map((panel) => ({ panel, html: IDLE_RENDER[panel](data, ui) }))
    .filter((panel) => panel.html);
}

// The time and the day as a clock shows them, in the server's or the browser's time zone.
function formatClock(hass, moment) {
  const locale = hass?.locale || {};
  const language = locale.language || hass?.language;
  const twelve = amPm(locale, language);
  const server = hass?.config?.time_zone;
  const zone = server && locale.time_zone !== "local" ? { timeZone: server } : {};
  return {
    time: formatter("date", language, {
      hour: twelve ? "numeric" : "2-digit",
      minute: "2-digit",
      hourCycle: twelve ? "h12" : "h23",
      ...zone,
    }).format(moment),
    day: formatter("date", language, { weekday: "long", day: "numeric", month: "long", ...zone }).format(moment),
  };
}

// Tournaments ----------------------------------------------------------------------

const TOURNAMENT_STATUS = ["playing", "waiting", "finished"];
// Players of the start_tournament action.
const TOURNAMENT_LIMITS = { min: 3, players: 8 };
const TOURNAMENT_FORMATS = ["round_robin", "knockout"];
// A knockout has a match for third place from four players.
const THIRD_PLACE_PLAYERS = 4;

// A match of the tournament sensor: its players, the winner and the result.
function tournamentMatch(item) {
  if (!item || typeof item !== "object") return null;
  const pair = (list, read) => [0, 1].map((index) => read(Array.isArray(list) ? list[index] : undefined));
  return {
    match: finite(item.match),
    round: finite(item.round) ?? 1,
    stage: named(item.stage) ?? "",
    players: pair(item.players, named),
    winner: named(item.winner),
    bye: item.bye === true,
    legs: pair(item.legs, (value) => finite(value) ?? 0),
    sets: pair(item.sets, (value) => finite(value) ?? 0),
    ended: named(item.ended),
  };
}

// The tournament being played or just finished, from its sensor; null without one.
function tournamentView(state) {
  const attributes = state?.attributes ?? {};
  if (!usable(state) || !TOURNAMENT_STATUS.includes(attributes.status)) return null;
  const list = (value) => (Array.isArray(value) ? value : []);
  const game = Number.isInteger(attributes.game) ? attributes.game : named(attributes.game);
  const nextAt = Date.parse(attributes.next_at);
  return {
    stage: state.state,
    status: attributes.status,
    format: attributes.format === "knockout" ? "knockout" : "round_robin",
    game,
    // Cricket ranks by marks per round, X01 by the 3-dart average.
    mpr: typeof game === "string",
    setsToWin: finite(attributes.sets_to_win) ?? 1,
    played: finite(attributes.matches_played) ?? 0,
    total: finite(attributes.matches_total) ?? 0,
    current: tournamentMatch(attributes.current),
    next: tournamentMatch(attributes.next),
    last: tournamentMatch(attributes.last_result),
    nextAt: Number.isFinite(nextAt) ? nextAt : null,
    pause: finite(attributes.pause) ?? 0,
    summary: finite(attributes.summary) ?? 8,
    winner: named(attributes.winner),
    started: named(attributes.started),
    standings: list(attributes.standings)
      .filter((row) => named(row?.name))
      .map((row) => ({
        position: finite(row.position) ?? 0,
        name: row.name,
        played: finite(row.played) ?? 0,
        won: finite(row.won) ?? 0,
        lost: finite(row.lost) ?? 0,
        legsFor: finite(row.legs_for) ?? 0,
        legsAgainst: finite(row.legs_against) ?? 0,
        difference: finite(row.leg_difference) ?? 0,
        points: finite(row.points) ?? 0,
        average: finite(row.average ?? row.mpr),
      })),
    bracket: list(attributes.bracket)
      .filter((round) => named(round?.stage))
      .map((round) => ({ stage: round.stage, matches: list(round.matches).map(tournamentMatch).filter(Boolean) })),
  };
}

// "Round 2", or a knockout stage such as "Semi-final".
function stageName(t, stage) {
  const round = /^round_(\d+)$/.exec(stage);
  return round ? fill(t("tournament_round"), { round: round[1] }) : t(`tournament_stage_${stage}`);
}

// The tournament round of a match, for the scoreboard's match view.
function tournamentLabel(view, match, t) {
  return [
    t("tournament"),
    stageName(t, match.stage),
    fill(t("tournament_match"), { match: match.match, matches: view.total }),
  ].join(" · ");
}

// Whether the practice game plays this match: the same two players, in order.
const playsMatch = (names, match) =>
  Boolean(match) && names.length === 2 && match.players.every((name, index) => name === names[index]);

const signed = (value) => (value > 0 ? `+${value}` : value < 0 ? `−${-value}` : "0");

// The round robin table, with the players of the next match marked.
function tournamentTable(view, ui) {
  const { t, format } = ui;
  const column = (key) =>
    `<th scope="col"><abbr title="${escapeHtml(t(`${key}_long`))}">${escapeHtml(t(key))}</abbr></th>`;
  const statistic = view.mpr
    ? `<th scope="col">${escapeHtml(t("cricket_mpr"))}</th>`
    : `<th scope="col"><abbr title="${escapeHtml(t("average_long"))}">Ø</abbr></th>`;
  const next = new Set((view.status === "waiting" ? view.next : view.current)?.players ?? []);
  const rows = view.standings.map((row) => {
    const kind = row.name === view.winner ? "champion" : next.has(row.name) ? "next" : "";
    return (
      `<tr${kind ? ` class="${kind}"` : ""}><td class="rank">${row.position}</td>` +
      `<th scope="row" class="who"><span class="player-name">${avatarHtml(ui.avatar(row.name))}` +
      `<span>${escapeHtml(row.name)}</span></span></th>` +
      `<td>${row.played}</td><td>${row.won}</td><td>${row.lost}</td>` +
      `<td>${row.legsFor}:${row.legsAgainst}</td><td>${signed(row.difference)}</td>` +
      `<td>${row.average === null ? "–" : escapeHtml(format(row.average, view.mpr ? 2 : 1))}</td>` +
      `<td class="points">${row.points}</td></tr>`
    );
  });
  return (
    `<table class="standings"><thead><tr><th scope="col" class="rank">#</th>` +
    `<th scope="col" class="who">${escapeHtml(t("tournament_player"))}</th>` +
    ["tournament_played", "tournament_won", "tournament_lost", "tournament_legs", "tournament_difference"]
      .map(column)
      .join("") +
    `${statistic}${column("tournament_points")}</tr></thead><tbody>${rows.join("")}</tbody></table>`
  );
}

// Every place of the bracket with its player and whether the match decided it,
// so that a place filled since the last look can be animated.
function bracketSlots(view) {
  const slots = new Map();
  for (const round of view?.bracket ?? []) {
    round.matches.forEach((match, index) => {
      const decided = match.winner !== null && !match.bye;
      match.players.forEach((name, side) => {
        slots.set(`${round.stage}-${index}-${side}`, `${name}|${decided && name === match.winner}`);
      });
    });
  }
  return slots;
}

// The places that got a player or a result since the last bracket; none at first sight.
function freshSlots(before, after) {
  const fresh = new Set();
  if (!before) return fresh;
  for (const [key, value] of after) {
    if (before.get(key) !== value && !value.startsWith("null|")) fresh.add(key);
  }
  return fresh;
}

// The knockout bracket: a column per round; the match for third place below the final.
function tournamentBracket(view, ui, fresh = new Set()) {
  const { t } = ui;
  const live = (view.status === "waiting" ? view.next : view.current)?.match ?? null;
  const box = (match, stage, index) => {
    const decided = match.winner !== null && !match.bye;
    const slots = match.players.map((name, side) => {
      const key = `${stage}-${index}-${side}`;
      const classes = [
        "slot",
        name === null ? "open" : "",
        decided && name === match.winner ? "won" : "",
        decided && name !== match.winner ? "lost" : "",
        fresh.has(key) ? "fresh" : "",
      ].filter(Boolean);
      const shown = name ?? t(match.bye ? "tournament_bye" : "tournament_open");
      const score = decided ? String(view.setsToWin > 1 ? match.sets[side] : match.legs[side]) : "";
      return (
        `<div class="${classes.join(" ")}">${avatarHtml(name && ui.avatar(name))}` +
        `<span class="who">${escapeHtml(shown)}</span><span class="score">${score}</span></div>`
      );
    });
    const kind = [
      "duel",
      match.bye ? "bye" : "",
      match.match !== null && match.match === live ? "live" : "",
      stage === "final" && view.winner ? "crowned" : "",
    ].filter(Boolean);
    return `<div class="${kind.join(" ")}">${slots.join("")}</div>`;
  };
  const third = view.bracket.find((round) => round.stage === "third_place");
  const columns = view.bracket
    .filter((round) => round !== third)
    .map(
      (round) =>
        `<div class="round ${round.stage}"><div class="section-label">${escapeHtml(stageName(t, round.stage))}</div>` +
        `<div class="duels">${round.matches.map((match, index) => box(match, round.stage, index)).join("")}` +
        (third && round.stage === "final"
          ? `<div class="section-label third">${escapeHtml(stageName(t, third.stage))}</div>` +
            third.matches.map((match, index) => box(match, third.stage, index)).join("")
          : "") +
        `</div></div>`
    );
  return `<div class="bracket">${columns.join("")}</div>`;
}

// Who plays next, while the tournament waits; the countdown is filled in every second.
function tournamentNextUp(view, ui) {
  const { t } = ui;
  const match = view.status === "waiting" ? view.next : null;
  if (!match) return "";
  const [first, second] = match.players.map((name) => name ?? t("tournament_open"));
  return (
    `<div class="next-up"><span class="section-label">${escapeHtml(
      `${t("tournament_next")} · ${stageName(t, match.stage)}`
    )}</span>` +
    `<span class="pairing">${avatarHtml(ui.avatar(first))}<b>${escapeHtml(first)}</b>` +
    `<span class="vs">${escapeHtml(t("tournament_vs"))}</span><b>${escapeHtml(second)}</b>${avatarHtml(
      ui.avatar(second)
    )}</span>` +
    `<span class="countdown" role="timer"></span>` +
    (ui.startNow
      ? `<button type="button" class="start-next" data-tournament="next">${escapeHtml(t("tournament_start_now"))}</button>`
      : "") +
    `</div>`
  );
}

// When the next match starts: in a few seconds, after the takeout, or when asked.
function tournamentCountdown(view, now, t) {
  if (view.status !== "waiting") return "";
  if (!view.pause || view.nextAt === null) return t("tournament_on_request");
  const seconds = Math.min(Math.max(Math.ceil((view.nextAt - now) / 1000), 0), view.pause);
  if (!seconds) return t("tournament_after_takeout");
  // A long pause counts down in minutes and seconds.
  const time =
    seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} min`;
  return fill(t("tournament_countdown"), { time });
}

// The tournament between its matches: who plays next, and the table or the bracket.
function tournamentHtml(view, ui) {
  const { t } = ui;
  const body = view.format === "knockout" ? tournamentBracket(view, ui, ui.fresh) : tournamentTable(view, ui);
  return {
    title: t("tournament"),
    meta: [
      t(`tournament_${view.format}`),
      gameName(t, view.game),
      view.status === "finished" ? "" : fill(t("tournament_progress"), { played: view.played, total: view.total }),
    ]
      .filter(Boolean)
      .join(" · "),
    banner: view.winner ? fill(t("tournament_winner"), { name: view.winner }) : "",
    main: `<div class="tournament ${view.format}">${tournamentNextUp(view, ui)}${body}</div>`,
  };
}

// The idle panel of a tournament: its table or bracket.
function tournamentPanelHtml(data, ui) {
  const view = data.tournament;
  if (!view) return "";
  return view.format === "knockout" ? tournamentBracket(view, ui) : tournamentTable(view, ui);
}

// What the caller follows of a tournament.
function tournamentCallState(view) {
  return view
    ? {
        started: view.started,
        status: view.status,
        match: view.current?.match ?? null,
        players: view.current?.players ?? [],
        winner: view.winner,
      }
    : null;
}

// The calls of a tournament: every match as it starts, and the champion. Nothing
// at first sight: undefined is a card that has not seen the tournament sensor yet.
function tournamentCalls(previous, current, options) {
  if (previous === undefined || !current || options.call_results === false) return [];
  const same = previous?.started === current.started;
  if (current.status === "finished") {
    return same && previous.status !== "finished" ? [{ kind: "tournament_won", name: current.winner }] : [];
  }
  if (current.status !== "playing" || (same && current.match === previous.match)) return [];
  const [first, second] = current.players;
  return [{ kind: "tournament_next", first, second }];
}

// The start_tournament action for the choice of the new game screen.
function tournamentStartData(choice, { entry = null, distance = false } = {}) {
  const named = choice.players.map((name, index) => [name, choice.starts?.[index] ?? 0]).filter(([name]) => name);
  const players = named.map(([name]) => name);
  const starts = named.map(([, start]) => start);
  const data = {
    players,
    format: choice.format,
    game: choice.game,
    legs: choice.legs,
    sets: choice.sets,
    bull_off: choice.bull_off,
    random_draw: choice.random_draw,
  };
  if (entry) data.config_entry_id = entry;
  if (distance && choice.bull_off) data.bull_off_distance = choice.bull_off_distance;
  if (gameGroup(choice.game) === "x01") Object.assign(data, { double_out: choice.double_out, double_in: choice.double_in });
  // A handicap goes with the start, and so does the game's start score when it is back.
  if (gameGroup(choice.game) === "x01" && (choice.handicap || starts.some(Boolean))) data.start_scores = starts;
  if (choice.format === "knockout") data.third_place = choice.third_place && players.length >= THIRD_PLACE_PLAYERS;
  return data;
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

// Progress -------------------------------------------------------------------

// The icon of every achievement; the colour of a badge tells its tier.
const ACHIEVEMENT_ICONS = {
  maximum: "mdi:crown",
  ton_plus: "mdi:arrow-up-bold-circle-outline",
  ton_forty: "mdi:rocket-launch",
  high_finish: "mdi:flag-checkered",
  short_leg: "mdi:run-fast",
  nine_darter: "mdi:star-shooting",
  legs_won: "mdi:trophy-variant-outline",
  matches_won: "mdi:trophy",
  hat_trick: "mdi:bullseye",
  all_doubles: "mdi:circle-double",
  cricket_nine: "mdi:pound",
  shanghai: "mdi:dice-multiple",
  around_the_clock: "mdi:clock-time-twelve-outline",
  bobs_27: "mdi:target",
  streak: "mdi:fire",
  darts_thrown: "mdi:arrow-projectile-multiple",
};
// Bronze, silver, gold and platinum; an achievement of a single tier is gold.
const TIER_COLORS = ["#c07a3c", "#a9b6c4", GOLD, "#5fd0e8"];

function tierColor(tier, tiers) {
  if (!tier) return null;
  return TIER_COLORS[tiers === 1 ? 2 : Math.min(tier, TIER_COLORS.length) - 1];
}

// Every player's badges from the achievements sensor: the tier reached, when,
// and how far the value has come towards the next tier.
function badgesView(achievements) {
  const attributes = achievements?.attributes || {};
  const catalogue = (Array.isArray(attributes.catalogue) ? attributes.catalogue : []).filter(
    (item) =>
      item && typeof item.id === "string" && Array.isArray(item.tiers) && item.tiers.length && item.tiers.every(Number.isFinite)
  );
  const players = (Array.isArray(attributes.players) ? attributes.players : [])
    .filter((player) => player && named(player.name))
    .map((player) => {
      const earned = player.badges && typeof player.badges === "object" ? player.badges : {};
      const progress = player.progress && typeof player.progress === "object" ? player.progress : {};
      const badges = catalogue.map((item) => {
        const tiers = item.tiers.length;
        const reached = Number(earned[item.id]?.tier);
        const tier = Number.isInteger(reached) ? Math.min(Math.max(reached, 0), tiers) : 0;
        const dates = (Array.isArray(earned[item.id]?.dates) ? earned[item.id].dates : []).filter(
          (date) => typeof date === "string"
        );
        const value = finite(progress[item.id]);
        const goal = item.tiers[Math.min(tier, tiers - 1)];
        // A count shows how far it has come; fewest darts and yes-or-no badges do not.
        const measurable = item.lower !== true && goal > 1 && tier < tiers && value !== null;
        return {
          id: item.id,
          tier,
          tiers,
          goal,
          lower: item.lower === true,
          value,
          share: measurable ? Math.min(1, Math.max(0, value / goal)) : null,
          date: dates.at(-1) ?? null,
          dates,
        };
      });
      return { name: player.name, unlocked: badges.reduce((sum, badge) => sum + badge.tier, 0), badges };
    });
  return { players };
}

function badgesHtml(player, ui, locked = true) {
  const { t, format, date } = ui;
  return player.badges
    .filter((badge) => locked || badge.tier)
    .map((badge) => {
      const tier = badge.tier && badge.tiers > 1 ? t(`tier_${Math.min(badge.tier, 4)}`) : "";
      const title = `${t(`achievement_${badge.id}`)}${tier ? ` · ${tier}` : ""}`;
      const goal = fill(t(`achievement_${badge.id}_goal`), { value: format(badge.goal) });
      let status = t("badge_locked");
      if (badge.share !== null) status = fill(t("badge_progress"), { value: format(badge.value), goal: format(badge.goal) });
      else if (badge.lower && badge.value !== null && badge.tier < badge.tiers) status = fill(t("badge_best"), { value: format(badge.value) });
      else if (badge.tier) status = fill(t("badge_earned"), { date: date(badge.date) });
      const bar = badge.share === null ? "" : `<span class="badge-bar"><i style="width:${fmt(badge.share * 100)}%"></i></span>`;
      const color = tierColor(badge.tier, badge.tiers);
      return (
        `<div class="badge${badge.tier ? "" : " locked"}" data-badge="${escapeHtml(badge.id)}"` +
        `${color ? ` style="--tier:${color}"` : ""}>` +
        `<span class="badge-icon"><ha-icon icon="${ACHIEVEMENT_ICONS[badge.id] ?? "mdi:medal-outline"}"></ha-icon></span>` +
        `<span class="badge-text"><b>${escapeHtml(title)}</b><span>${escapeHtml(goal)}</span>` +
        `<span class="muted">${escapeHtml(status)}</span>${bar}</span></div>`
      );
    })
    .join("");
}

// The weekly sums of a player's trend that its figures come from.
const TREND_SUMS = [
  "darts",
  "x01_darts",
  "x01_points",
  "first9_points",
  "first9_darts",
  "at_double",
  "checkouts",
  "double_attempts",
  "double_hits",
  "maximums",
];
const ratioOf = (part, whole, factor) => (whole > 0 ? (part * factor) / whole : null);
const TREND_METRICS = [
  { key: "average", label: "average", digits: 1, of: (sums) => ratioOf(sums.x01_points, sums.x01_darts, 3) },
  { key: "first_9", label: "first_9", digits: 1, of: (sums) => ratioOf(sums.first9_points, sums.first9_darts, 3) },
  {
    key: "checkout_rate",
    label: "checkout_short",
    digits: 1,
    percent: true,
    of: (sums) => ratioOf(sums.checkouts, sums.at_double, 100),
  },
  {
    key: "doubles_rate",
    label: "doubles_rate_short",
    digits: 1,
    percent: true,
    of: (sums) => ratioOf(sums.double_hits, sums.double_attempts, 100),
  },
  { key: "darts", label: "darts", digits: 0, of: (sums) => (sums.darts > 0 ? sums.darts : null) },
];

// The last weeks of a trend, oldest first, each with its sums.
function trendWeeks(trend, size) {
  const weeks = Array.isArray(trend?.weeks) ? trend.weeks.filter((week) => typeof week === "string") : [];
  const count = Math.min(Math.max(1, Math.round(size) || 1), weeks.length);
  const first = weeks.length - count;
  return weeks.slice(first).map((week, index) => {
    const sums = { week };
    for (const name of TREND_SUMS) sums[name] = finite(trend[name]?.[first + index]) ?? 0;
    for (const name of ["highest_checkout", "best_501", "best_mpr"]) sums[name] = finite(trend[name]?.[first + index]);
    return sums;
  });
}

// Sums of several weeks; bests keep the best week.
function addWeeks(weeks) {
  const total = Object.fromEntries(TREND_SUMS.map((name) => [name, 0]));
  const best = (values, pick) => (values.length ? pick(...values) : null);
  for (const week of weeks) for (const name of TREND_SUMS) total[name] += week[name];
  const known = (name) => weeks.map((week) => week[name]).filter((value) => value !== null && value > 0);
  total.highest_checkout = best(known("highest_checkout"), Math.max);
  total.best_501 = best(known("best_501"), Math.min);
  total.best_mpr = best(known("best_mpr"), Math.max);
  return total;
}

// Every figure of a player's trend: its value over the weeks, the value of each
// week for the sparkline, and whether the newer half of the weeks is better.
function trendView(trend, size = 12) {
  const weeks = trendWeeks(trend, size);
  const half = Math.floor(weeks.length / 2);
  return TREND_METRICS.map((metric) => {
    const before = metric.of(addWeeks(weeks.slice(0, half)));
    const after = metric.of(addWeeks(weeks.slice(half)));
    let direction = "steady";
    if (before !== null && after !== null) {
      const change = after - before;
      if (Math.abs(change) >= Math.max(0.5, Math.abs(before) * 0.02)) direction = change > 0 ? "up" : "down";
    }
    return {
      key: metric.key,
      label: metric.label,
      digits: metric.digits,
      percent: metric.percent === true,
      values: weeks.map((week) => metric.of(week)),
      value: metric.of(addWeeks(weeks)),
      direction,
    };
  });
}

// A small line of the weekly values; weeks without a value interrupt it.
function sparkline(values) {
  const known = values.filter((value) => value !== null);
  if (!known.length) return "";
  const low = Math.min(...known);
  const high = Math.max(...known);
  const x = (index) => fmt(values.length > 1 ? (index * 100) / (values.length - 1) : 50);
  const y = (value) => fmt(high === low ? 12 : 21 - ((value - low) / (high - low)) * 18);
  const runs = [[]];
  values.forEach((value, index) => {
    if (value === null) runs.push([]);
    else runs.at(-1).push(`${x(index)},${y(value)}`);
  });
  const lines = runs
    .filter((points) => points.length)
    .map((points) =>
      points.length > 1 ? `<polyline points="${points.join(" ")}"/>` : `<polyline class="dot" points="${points[0]} ${points[0]}"/>`
    )
    .join("");
  const last = values.findLastIndex((value) => value !== null);
  const end = `${x(last)},${y(values[last])}`;
  return (
    `<svg class="spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">` +
    `${lines}<polyline class="dot last" points="${end} ${end}"/></svg>`
  );
}

const TREND_ARROWS = { up: "↗", down: "↘", steady: "→" };

function trendsHtml(players, ui) {
  const { t, format, percent } = ui;
  return players
    .map((player) => {
      const metrics = player.metrics
        .map((metric) => {
          const shown =
            metric.value === null ? "–" : metric.percent ? percent(metric.value, metric.digits) : format(metric.value, metric.digits);
          const trend = t(`trend_${metric.direction}`);
          return (
            `<div class="trend" data-metric="${metric.key}"><span class="trend-label">${escapeHtml(t(metric.label))}</span>` +
            `<span class="trend-value">${escapeHtml(shown)} <span class="arrow ${metric.direction}" title="${escapeHtml(
              trend
            )}" aria-label="${escapeHtml(trend)}">${TREND_ARROWS[metric.direction]}</span></span>` +
            `${sparkline(metric.values)}</div>`
          );
        })
        .join("");
      return `<div class="trend-player"><div class="trend-name">${escapeHtml(player.name)}</div><div class="trends">${metrics}</div></div>`;
    })
    .join("");
}

// The groupings of a player or the session, at most `limit` beds.
function spreadView(groups, limit = 3) {
  return (Array.isArray(groups) ? groups : [])
    .filter(
      (group) =>
        group &&
        typeof group.target === "string" &&
        ["darts", "offset_x", "offset_y", "r50", "r80"].every((key) => Number.isFinite(group[key]))
    )
    .slice(0, limit)
    .map((group) => ({ ...group, change: finite(group.change) }));
}

// "6 mm left of center, 2 mm high", in board directions as the player sees them.
function offsetText(ui, group) {
  const { t, format } = ui;
  const mm = (value) => fill(t("unit_mm"), { value: format(Math.abs(value)) });
  const parts = [];
  if (Math.abs(group.offset_x) >= 1) {
    parts.push(fill(t(group.offset_x < 0 ? "spread_left" : "spread_right"), { distance: mm(group.offset_x) }));
  }
  if (Math.abs(group.offset_y) >= 1) {
    parts.push(fill(t(group.offset_y < 0 ? "spread_low" : "spread_high"), { distance: mm(group.offset_y) }));
  }
  return parts.join(", ") || t("spread_centered");
}

function spreadHtml(groups, ui) {
  const { t, format, label } = ui;
  const mm = (value) => fill(t("unit_mm"), { value: format(Math.abs(value)) });
  return groups
    .map((group) => {
      const text = [
        fill(t("spread_group"), { r50: mm(group.r50) }),
        fill(t("spread_group80"), { r80: mm(group.r80) }),
        offsetText(ui, group),
      ].join(" · ");
      const changed = group.change !== null && Math.abs(group.change) >= 1;
      const change = changed
        ? `<span class="group-change ${group.change < 0 ? "better" : "worse"}">${escapeHtml(
            fill(t(group.change < 0 ? "spread_tighter" : "spread_wider"), { value: mm(group.change) })
          )}</span>`
        : "";
      return (
        `<div class="group" data-target="${escapeHtml(group.target)}"><span class="group-target">${escapeHtml(
          label(group.target)
        )}</span><span class="group-text">${escapeHtml(text)}</span>${change}</div>`
      );
    })
    .join("");
}

// Trends and groupings of every named player from the profiles sensor.
function progressView(profiles, weeks = 12) {
  return (Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : [])
    .filter((player) => player && named(player.name))
    .map((player) => ({
      name: player.name,
      metrics: trendView(player.trend, weeks),
      groups: spreadView(player.spread),
      active: trendWeeks(player.trend, weeks).some((week) => week.darts > 0 || week.x01_darts > 0),
    }));
}

// A smoothed density of dart positions on a grid over the board, in millimetres.
const DENSITY_CELL = 8;
const DENSITY_SIGMA = 8;
// The newest darts are also drawn as dots, up to this many.
const POSITION_DOTS = 300;

const validPositions = (positions) =>
  (Array.isArray(positions) ? positions : []).filter(
    (position) => Array.isArray(position) && Number.isFinite(position[0]) && Number.isFinite(position[1])
  );

function positionsDensity(positions) {
  const cells = new Map();
  const reach = Math.ceil((3 * DENSITY_SIGMA) / DENSITY_CELL);
  for (const [nx, ny] of validPositions(positions)) {
    const x = nx * NORM;
    const y = -ny * NORM;
    const column = Math.round(x / DENSITY_CELL);
    const row = Math.round(y / DENSITY_CELL);
    for (let i = column - reach; i <= column + reach; i += 1) {
      for (let j = row - reach; j <= row + reach; j += 1) {
        const dx = i * DENSITY_CELL - x;
        const dy = j * DENSITY_CELL - y;
        const weight = Math.exp(-(dx * dx + dy * dy) / (2 * DENSITY_SIGMA * DENSITY_SIGMA));
        if (weight < 0.01) continue;
        const key = `${i},${j}`;
        cells.set(key, (cells.get(key) || 0) + weight);
      }
    }
  }
  return cells;
}

// The density in the heatmap colours, softened by a blur, and the newest darts as dots.
function positionsHtml(positions) {
  const valid = validPositions(positions);
  const cells = positionsDensity(valid);
  let max = 0;
  for (const value of cells.values()) max = Math.max(max, value);
  const half = DENSITY_CELL / 2;
  const density = [...cells.entries()]
    .filter(([, value]) => value >= max * 0.04)
    .map(([key, value]) => {
      const [column, row] = key.split(",").map(Number);
      const ratio = value / max;
      return (
        `<rect x="${fmt(column * DENSITY_CELL - half)}" y="${fmt(row * DENSITY_CELL - half)}" ` +
        `width="${DENSITY_CELL}" height="${DENSITY_CELL}" fill="${heatColor(ratio)}" fill-opacity="${fmt(0.3 + 0.6 * ratio)}"/>`
      );
    })
    .join("");
  const dots = valid
    .slice(-POSITION_DOTS)
    .map(([x, y]) => `<circle class="position" cx="${fmt(x * NORM)}" cy="${fmt(-y * NORM)}" r="2.2"/>`)
    .join("");
  return `<g class="density" filter="url(#ad-density)">${density}</g><g class="positions">${dots}</g>`;
}

// Leaderboard ------------------------------------------------------------------

// Records across all players: all time from the profiles, a period from the weeks.
const LEADERBOARD_RECORDS = [
  { key: "average", digits: 1 },
  { key: "checkout", digits: 0 },
  { key: "maximums", digits: 0 },
  { key: "best_501", digits: 0, lower: true, unit: "unit_darts" },
  { key: "mpr", digits: 2 },
  { key: "streak", digits: 0, unit: "unit_days", always: true },
  { key: "achievements", digits: 0 },
  { key: "darts", digits: 0 },
];
const PERIOD_WEEKS = { week: 1, month: 4 };
const PERIODS = ["all", "month", "week"];

function leaderboardRecords(profiles, achievements, period = "all") {
  const weeks = PERIOD_WEEKS[period] ?? null;
  const badges = new Map(badgesView(achievements).players.map((player) => [player.name.toLowerCase(), player]));
  const players = (Array.isArray(profiles?.attributes?.players) ? profiles.attributes.players : []).filter(
    (player) => player && named(player.name)
  );
  const rows = players.map((player) => {
    const earned = badges.get(player.name.toLowerCase());
    if (!weeks) {
      return {
        name: player.name,
        average: finite(player.average),
        checkout: finite(player.highest_checkout),
        maximums: finite(player.maximums),
        best_501: finite(player.fewest_darts?.["501"]),
        mpr: finite(player.best_mpr),
        streak: finite(player.best_streak),
        achievements: earned?.unlocked ?? null,
        darts: finite(player.darts_thrown),
      };
    }
    const range = trendWeeks(player.trend, weeks);
    const sums = addWeeks(range);
    const since = range[0]?.week ?? "9999";
    return {
      name: player.name,
      average: ratioOf(sums.x01_points, sums.x01_darts, 3),
      checkout: sums.highest_checkout,
      maximums: sums.maximums,
      best_501: sums.best_501,
      mpr: sums.best_mpr,
      streak: null,
      // Every tier unlocked since the first day of the period.
      achievements: (earned?.badges ?? []).reduce(
        (count, badge) => count + badge.dates.filter((date) => date.slice(0, 10) >= since).length,
        0
      ),
      darts: sums.darts,
    };
  });
  const records = LEADERBOARD_RECORDS.filter((record) => !weeks || !record.always)
    .map((record) => {
      const better = (a, b) => (record.lower ? a[record.key] - b[record.key] : b[record.key] - a[record.key]);
      const ranked = rows
        .filter((row) => row[record.key] !== null && row[record.key] > 0)
        .sort((a, b) => better(a, b) || a.name.localeCompare(b.name));
      // Equal values share their place.
      const places = ranked.map((row) => ({
        name: row.name,
        value: row[record.key],
        place: 1 + ranked.filter((other) => better(other, row) < 0).length,
      }));
      return { ...record, places };
    })
    .filter((record) => record.places.length);
  return { period: weeks ? period : "all", records };
}

function leaderboardRecordsHtml(view, ui, limit = 3) {
  const { t, format } = ui;
  const shown = (record, value) => {
    const number = format(value, record.digits);
    if (!record.unit) return number;
    return fill(t(record.unit === "unit_days" && value === 1 ? "unit_day" : record.unit), { value: number });
  };
  return view.records
    .map((record) => {
      const [leader, ...rest] = record.places.slice(0, Math.max(1, limit));
      const others = rest
        .map(
          (place) =>
            `<li><span class="place">${place.place}.</span><span class="who">${escapeHtml(place.name)}</span>` +
            `<span class="value">${escapeHtml(shown(record, place.value))}</span></li>`
        )
        .join("");
      return (
        `<div class="record" data-record="${record.key}"><div class="record-name">${escapeHtml(t(`record_${record.key}`))}</div>` +
        `<div class="record-leader"><span class="who">${escapeHtml(leader.name)}</span>` +
        `<span class="value">${escapeHtml(shown(record, leader.value))}</span></div>` +
        `${others ? `<ol class="record-places">${others}</ol>` : ""}</div>`
      );
    })
    .join("");
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
  // Killer counts lives, and in Golf the last dart counts, whenever the darts are pulled.
  const { party } = view;
  if (view.mode !== "party" || party.won || ["killer", "golf"].includes(party.kind)) return null;
  if (party.kind === "count_up") return { kind: "score", score: points(keys) };
  if (party.kind === "baseball") {
    const inning = [Number(party.target)];
    return { kind: "runs", runs: keys.reduce((sum, key) => sum + cricketMarks(key, inning), 0) };
  }
  const aim = new Set(targetBeds(party.target));
  return { kind: "score", score: points(keys.filter((key) => hitBeds(key).some((bed) => aim.has(bed)))) };
}

// What the caller listens to: the darts a game counted, or the visit on the board between games.
function callerState(visit, view, previous = null) {
  const current = view ?? { mode: "idle" };
  const game = current.practice ?? current.cricket ?? current.party ?? null;
  const winner = game?.scores?.find((score) => score.player === game.winner);
  // Darts after a bust or a game shot are not among the darts of the game.
  const idle = current.mode === "idle" ? visitThrows(visit).map(dartKey) : [];
  const keys = game ? game.visit : (current.drill?.thrown ?? idle);
  // A checkout training has a remaining score, too.
  const remaining = current.practice?.remaining ?? current.drill?.remaining ?? null;
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
    route: current.practice?.route ?? current.drill?.route ?? [],
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
    ["x01", "drill"].includes(current.mode) &&
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
  if (call.kind === "runs") {
    if (call.runs === 0) return t("say_no_score");
    return call.runs === 1 ? t("say_run") : fill(t("say_runs"), { runs: call.runs });
  }
  if (call.kind === "bust") return t("say_bust");
  if (call.kind === "leg") return t("say_leg");
  if (call.kind === "match") {
    // Without a name the call ends with the match, before the punctuation of the language.
    const words = call.name ? t("say_match") : t("say_match").replace(/,\s*\{name\}/, "");
    return fill(words, { name: call.name });
  }
  if (call.kind === "tournament_next") return fill(t("say_tournament_next"), { first: call.first, second: call.second });
  if (call.kind === "tournament_won") return fill(t("say_tournament_won"), { name: call.name });
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
  "switch.practice_teams",
  "switch.practice_personal_routes",
  "select.practice_golf_holes",
  "number.practice_count_up_rounds",
  "button.practice_new_leg",
  "button.practice_new_match",
];

// The settings of the next tournament and its buttons; the sensor gets a tile.
const TOURNAMENT_KEYS = [
  "select.tournament_format",
  "select.tournament_game",
  "text.tournament_players",
  "number.tournament_pause",
  "switch.tournament_third_place",
  "switch.tournament_random_draw",
  "button.tournament_start",
  "button.tournament_next_match",
  "button.tournament_stop",
];

// A name pattern such as "Practice {name}" or "{name} de la partie" that finds the {name}.
function namePattern(text) {
  const escape = (part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const [before, after = ""] = text.split("{name}");
  return new RegExp(`^${escape(before)}(.+)${escape(after)}$`, "i");
}

// An entity's name without its board and without the section it sits in, so
// "Autodarts Board Practice players" reads "Players" under "Practice", and
// "Joueurs de la partie" reads "Joueurs" under "Partie".
function rowName(hass, entityId, board, section) {
  let name = hass?.states?.[entityId]?.attributes?.friendly_name;
  if (typeof name !== "string") return null;
  if (board && name.toLowerCase().startsWith(`${board.toLowerCase()} `)) name = name.slice(board.length + 1);
  // The section's name pattern, such as namePattern("Practice {name}").
  name = (section?.exec(name)?.[1] ?? name).trim();
  return name ? name[0].toUpperCase() + name.slice(1) : null;
}

// What the views of one board share: its entities, their rows and the view names.
function boardContext(hass, t, deviceId, number, count) {
  const index = entityIndex(hass, deviceId);
  const id = (key) => index[key]?.[0];
  const device = hass.devices?.[deviceId];
  const name = device?.name_by_user || device?.name || "Autodarts";
  // Rows and graphs name their entities briefly, the board is the view's. A section such as
  // "practice" leaves out what the names of its entities share, after "practice_entity".
  const patterns = {};
  const row = (entity, section) => {
    const pattern = section && (patterns[section] ??= namePattern(t(`${section}_entity`)));
    const text = rowName(hass, entity, name, pattern);
    if (!text) return entity;
    // The game select is the practice section itself.
    return { entity, name: section && text.toLowerCase() === t(section).toLowerCase() ? t("practice_game_row") : text };
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
  const practice = board.rows(PRACTICE_KEYS, "practice");
  const names = (board.index["text.practice_player"] ?? []).map((entity) => board.row(entity, "practice"));
  const starts = (board.index["number.practice_start"] ?? []).map((entity) => board.row(entity, "practice"));
  const controls = [
    { type: "heading", heading: t("practice") },
    { type: "entities", entities: practice },
    ...(names.length ? [{ type: "entities", title: t("practice_names"), entities: names }] : []),
    ...(starts.length ? [{ type: "entities", title: t("practice_starts"), entities: starts }] : []),
  ];
  const tournament = board.rows(TOURNAMENT_KEYS, "tournament");
  const stage = board.id("sensor.tournament");
  const tournamentCards = [
    { type: "heading", heading: t("tournament") },
    ...(stage ? [tile(stage)] : []),
    { type: "entities", entities: tournament },
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
      ...(tournament.length ? [{ type: "grid", column_span: 2, cards: tournamentCards }] : []),
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
    sections: [
      { type: "grid", column_span: 2, cards: [board.card(PLAYERS_TYPE, FULL)] },
      { type: "grid", column_span: 2, cards: [board.card(LEADERBOARD_TYPE, FULL)] },
    ],
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
// Named players to pick from; any other name can be typed in.
const playerField = (helper) => ({
  name: "player",
  ...(helper ? { helper } : {}),
  selector: {
    select: {
      mode: "dropdown",
      custom_value: true,
      options: profileNames(pageHass).map((name) => ({ value: name, label: name })),
    },
  },
});

const FORM_HELPERS = {
  device_id: "device_helper",
  player: "player_helper",
  accent_color: "color_helper",
  highlight_color: "highlight_color_helper",
  caller_options: "caller_options_helper",
  lobby_section: "lobby_section_helper",
  lobby_games: "lobby_games_helper",
  idle_section: "idle_section_helper",
  idle_panels: "idle_panels_helper",
  summary_seconds: "summary_seconds_helper",
};

// The games to offer in the editor: those of a board's practice select, or every game the card knows.
function gameOptions(hass) {
  const select = Object.values(hass?.entities || {}).find(
    (entity) => entity.platform === "autodarts" && entity.translation_key === "practice_game"
  );
  const options = hass?.states?.[select?.entity_id]?.attributes?.options;
  return (Array.isArray(options) ? options.map(String) : KNOWN_GAMES)
    .filter((game) => game !== "off")
    .map((game) => ({ value: game, label: gameName(pageText, /^\d+$/.test(game) ? Number(game) : game) }));
}

// Seconds in a box with their unit.
const secondsField = (name, min, max, defaults = SCOREBOARD_DEFAULTS) => ({
  name,
  selector: { number: { min, max, step: 1, mode: "box", unit_of_measurement: "s" } },
  default: defaults[name],
});

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
      if (field.helper) return pageText(field.helper);
      if (FORM_HELPERS[field.name]) return pageText(FORM_HELPERS[field.name]);
      const standard = options.get(field.name)?.find((option) => option.value === defaults[field.name]);
      return standard ? fill(pageText("default_hint"), { value: standard.label }) : undefined;
    },
    assertConfig: (config) => {
      for (const field of fields) {
        const value = config?.[field.name];
        if (value === undefined || value === null || value === "") continue;
        // YAML reads 501 as a number; the option is the text "501".
        const allowed = (item) =>
          options.get(field.name).some((option) => option.value === (typeof item === "number" ? String(item) : item));
        const valid = options.has(field.name)
          ? field.selector.select.multiple
            ? Array.isArray(value) && value.every(allowed)
            : allowed(value)
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
        "show_summary",
      ],
      DEFAULTS
    ),
    // Seconds the summary of a finished match stays; 0 until the next game starts.
    secondsField("summary_seconds", 0, 600, DEFAULTS),
    { type: "grid", name: "", schema: [accentField, colorField("highlight_color")] },
  ],
  training: () => [
    deviceField,
    titleField,
    {
      type: "grid",
      name: "",
      schema: [dropdown("mode", "mode", HEAT_MODES), dropdown("board_style", "style", ["muted", "classic", "autodarts"])],
    },
    playerField("heatmap_player_helper"),
    {
      name: "history_size",
      selector: { number: { min: 5, max: 60, step: 1, mode: "slider" } },
      default: TRAINING_DEFAULTS.history_size,
    },
    toggles(
      [
        "show_heatmap",
        "show_heatmap_controls",
        "show_stats",
        "show_bests",
        "show_top",
        "show_history",
        "show_sessions",
        "show_reset",
      ],
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
    toggles(["full_height", "show_visit", "show_status", "caller", "show_summary"], SCOREBOARD_DEFAULTS),
    secondsField("summary_seconds", 0, 600),
    // The calls matter only with the caller on, so they wait in a closed section.
    {
      type: "expandable",
      name: "caller_options",
      flatten: true,
      schema: [toggles(["call_scores", "call_checkouts", "call_results", "call_sounds"], SCOREBOARD_DEFAULTS)],
    },
    {
      type: "expandable",
      name: "lobby_section",
      flatten: true,
      schema: [
        toggles(["lobby"], SCOREBOARD_DEFAULTS),
        { name: "lobby_games", selector: { select: { multiple: true, mode: "dropdown", options: gameOptions(pageHass) } } },
      ],
    },
    {
      type: "expandable",
      name: "idle_section",
      flatten: true,
      schema: [
        toggles(["idle"], SCOREBOARD_DEFAULTS),
        { type: "grid", name: "", schema: [secondsField("idle_after", 10, 3600), secondsField("idle_interval", 3, 120)] },
        {
          name: "idle_panels",
          selector: {
            select: {
              multiple: true,
              mode: "list",
              options: IDLE_PANELS.map((panel) => ({ value: panel, label: pageText(`idle_panel_${panel}`) })),
            },
          },
        },
      ],
    },
    accentField,
  ],
  players: () => [
    deviceField,
    titleField,
    toggles(
      ["show_head_to_head", "show_matches", "show_badges", "show_locked", "show_trends", "show_spread", "export"],
      PLAYERS_DEFAULTS
    ),
    {
      name: "trend_weeks",
      selector: { number: { min: 4, max: 12, step: 1, mode: "slider" } },
      default: PLAYERS_DEFAULTS.trend_weeks,
    },
    dropdown("export_format", "export_format", ["csv", "json"]),
    accentField,
  ],
  leaderboard: () => [
    deviceField,
    titleField,
    {
      type: "grid",
      name: "",
      schema: [
        dropdown("period", "period", PERIODS),
        { name: "limit", selector: { number: { min: 1, max: 5, step: 1, mode: "box" } }, default: LEADERBOARD_DEFAULTS.limit },
      ],
    },
    toggles(["show_period"], LEADERBOARD_DEFAULTS),
    accentField,
  ],
  doubles: () => [deviceField, titleField, playerField(), accentField],
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
  .note.rethrow { color: var(--ad-warn-text); }
  .message { padding: 18px; color: var(--secondary-text-color); }
  /* The picture of the person a player is linked to. */
  .avatar {
    display: inline-block; flex-shrink: 0; width: 1.25em; height: 1.25em; margin-right: .35em;
    border-radius: 50%; object-fit: cover; vertical-align: -.2em;
    background: color-mix(in srgb, var(--primary-text-color) 10%, transparent);
  }
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
  .player-score .badge {
    margin-left: .3em; padding: 0 .35em; border-radius: 6px; font-size: 11px; font-weight: 600;
    color: var(--secondary-text-color); border: 1px solid var(--divider-color, rgba(127,127,127,.4));
  }
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
  .summary { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; font-variant-numeric: tabular-nums; }
  .summary th, .summary td { padding: 2px 6px; text-align: center; }
  .summary tr > :first-child { width: 36%; text-align: left; }
  .summary thead th { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .summary thead th.caption { font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ad-accent); }
  .summary tbody th { font-weight: 400; color: var(--secondary-text-color); }
  .summary td { font-weight: 700; color: var(--primary-text-color); }
  .summary tr.result td { font-size: 17px; font-weight: 800; color: var(--ad-accent); }
  .summary .winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 20%, transparent); }
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

// Buttons that switch the view of a card: the heatmap mode, whose darts, the period.
const SEGMENTED_CSS = `
  .segmented {
    display: inline-flex; flex-wrap: wrap; gap: 2px; padding: 3px; border-radius: 999px;
    background: color-mix(in srgb, var(--primary-text-color) 6%, transparent);
  }
  .segmented button {
    font: inherit; font-size: 12px; font-weight: 600; padding: 4px 10px; border: 0; border-radius: 999px;
    cursor: pointer; color: var(--secondary-text-color); background: none; white-space: nowrap;
  }
  .segmented button[aria-pressed="true"] { color: var(--text-primary-color, #fff); background: var(--ad-accent); }
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
  .heat-head { width: 100%; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }
  .heat-controls { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
  .position { fill: #fff; fill-opacity: .85; stroke: rgba(0,0,0,.55); stroke-width: .6; }
  .heat .groups { width: 100%; display: grid; gap: 2px; }
  .group { display: grid; grid-template-columns: 3.4em minmax(0, 1fr) auto; gap: 10px; align-items: baseline; font-size: 13px; }
  .group-target {
    padding: 1px 0; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 800;
    color: var(--ad-accent); border: 1px solid var(--ad-accent);
  }
  .group-change { font-size: 12px; font-weight: 700; white-space: nowrap; }
  .group-change.better { color: var(--ad-ok-text); }
  .group-change.worse { color: var(--ad-error-text); }
  ${SEGMENTED_CSS}
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
  .banner.rethrow { color: var(--ad-warn-text); background: color-mix(in srgb, ${STATUS_COLORS.takeout} 18%, transparent); }
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
  .badge {
    display: inline-block; margin-left: .3em; padding: 0 .4em; border-radius: 8px; vertical-align: middle;
    font-size: .55em; font-weight: 700; color: var(--secondary-text-color);
    border: 1px solid var(--divider-color, rgba(127,127,127,.4));
  }
  .members { font-size: clamp(13px, 2.1cqi, 28px); color: var(--secondary-text-color); text-align: center; }
  .members b { color: var(--ad-accent); }
  .cricket.many tbody th, .cricket.many tbody td { padding-top: .05em; padding-bottom: .05em; line-height: 1.05; }
  .cricket.many td { font-size: clamp(14px, min(3.2cqi, 2.7vh), 42px); }
  .cricket.many tbody th { font-size: clamp(13px, min(2.4cqi, 2.4vh), 32px); }
  .cricket.many tr.total td { font-size: clamp(20px, min(4.2cqi, 3.8vh), 56px); }
  .scorecard { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  .scorecard th, .scorecard td { padding: .15em .2em; text-align: center; font-size: clamp(11px, 1.8cqi, 26px); }
  .scorecard thead th { color: var(--secondary-text-color); font-weight: 600; }
  .scorecard tbody th {
    text-align: left; max-width: 8em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--primary-text-color);
  }
  .scorecard .now { background: color-mix(in srgb, var(--ad-accent) 14%, transparent); }
  .scorecard .total { font-weight: 800; color: var(--primary-text-color); }
  .scorecard tr.active th { color: var(--ad-accent); }
  .scorecard tr.winner > * { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
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
  .single .big.long { font-size: clamp(48px, min(11cqi, 20vh), 150px); letter-spacing: -0.02em; }
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
  .summary { width: 100%; border-collapse: collapse; table-layout: fixed; font-variant-numeric: tabular-nums; }
  .summary th, .summary td { padding: .12em .4em; line-height: 1.2; text-align: center; }
  .summary tr > :first-child { width: 26%; text-align: left; }
  .summary thead th {
    font-size: clamp(14px, min(2.6cqi, 3.4vh), 34px); font-weight: 700; color: var(--primary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .summary thead th.caption {
    font-size: clamp(11px, min(1.5cqi, 2vh), 18px); letter-spacing: .12em; text-transform: uppercase; color: var(--ad-accent);
  }
  .summary tbody th { font-size: clamp(12px, min(1.8cqi, 2.5vh), 24px); font-weight: 600; color: var(--secondary-text-color); }
  /* Sized by width and height, so every row fits a landscape screen. */
  .summary td { font-size: clamp(16px, min(2.8cqi, 2.9vh), 38px); font-weight: 800; color: var(--primary-text-color); }
  .summary tr.result td { font-size: clamp(24px, min(5cqi, 5vh), 72px); line-height: 1.1; color: var(--ad-accent); }
  .summary tbody tr + tr > * { border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
  .summary .winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
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
  /* The new game screen: large targets for a finger, readable from the oche. */
  .lobby-toggle, .lobby-cta, .lobby button { font: inherit; cursor: pointer; touch-action: manipulation; }
  .lobby-toggle {
    display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 0 14px; border-radius: 999px;
    font-size: clamp(12px, 1.5cqi, 18px); font-weight: 700; color: var(--ad-accent);
    border: 1px solid var(--ad-accent); background: none;
  }
  .lobby-cta {
    align-self: center; min-height: 56px; padding: 0 clamp(24px, 4cqi, 56px); border: none; border-radius: 999px;
    font-size: clamp(16px, 2.4cqi, 28px); font-weight: 800; color: var(--text-primary-color, #fff); background: var(--ad-accent);
  }
  .choosing .main { justify-content: flex-start; }
  .lobby {
    display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: clamp(14px, 2.4cqi, 32px); align-items: start;
  }
  /* A portrait tablet or a phone stacks the games above the players. */
  @container (max-width: 880px) { .lobby { grid-template-columns: minmax(0, 1fr); } }
  .lobby-games, .lobby-setup {
    display: grid; grid-template-columns: minmax(0, 1fr); gap: clamp(12px, 1.8cqi, 22px); align-content: start;
  }
  .lobby .section-label { margin-bottom: 8px; font-size: clamp(11px, 1.4cqi, 15px); }
  .game-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(clamp(112px, 15cqi, 180px), 1fr)); gap: 8px; }
  .lobby button {
    min-height: 48px; padding: 0 14px; border-radius: 14px; font-weight: 700; color: var(--primary-text-color);
    border: 2px solid var(--divider-color, rgba(127,127,127,.3));
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .lobby button:disabled { opacity: .4; cursor: default; }
  /* Training games have longer names. */
  .lobby-group.training .game-grid, .lobby-group.more .game-grid {
    grid-template-columns: repeat(auto-fill, minmax(clamp(150px, 20cqi, 240px), 1fr));
  }
  .lobby .game {
    min-height: clamp(52px, 7cqi, 76px); padding: 4px 8px; font-size: clamp(15px, 2.1cqi, 26px); line-height: 1.1;
    hyphens: auto; overflow-wrap: break-word;
  }
  .lobby [aria-pressed="true"] { color: var(--text-primary-color, #fff); background: var(--ad-accent); border-color: var(--ad-accent); }
  .lobby-players { list-style: none; margin: 0 0 10px; padding: 0; display: grid; gap: 6px; }
  .lobby-player {
    display: flex; align-items: center; gap: 6px; padding: 4px 4px 4px 12px; border-radius: 16px;
    font-size: clamp(16px, 2cqi, 24px); font-weight: 700; background: color-mix(in srgb, var(--ad-accent) 12%, transparent);
  }
  .lobby-player.resting { opacity: .45; }
  .lobby-player .who { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lobby-player button { min-width: 48px; padding: 0; }
  .lobby-start { display: inline-flex; align-items: center; gap: 4px; font-variant-numeric: tabular-nums; }
  .lobby-start b { min-width: 3.2ch; text-align: center; font-size: .85em; color: var(--secondary-text-color); }
  .lobby-start.own b { color: var(--ad-accent); }
  .lobby-player .lobby-start button { min-width: 40px; }
  .suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .lobby .suggestion { display: inline-flex; align-items: center; border-radius: 999px; }
  .suggestion .home { margin-left: 6px; color: var(--ad-ok-text); }
  .lobby .suggestion.guest { border-style: dashed; }
  .name-entry { display: flex; gap: 8px; }
  .lobby-name {
    flex: 1; min-width: 0; min-height: 48px; box-sizing: border-box; padding: 0 14px; border-radius: 14px;
    font: inherit; font-size: 16px; color: var(--primary-text-color); background: none;
    border: 2px solid var(--divider-color, rgba(127,127,127,.3));
  }
  .steppers { display: flex; flex-wrap: wrap; gap: 8px 24px; }
  .stepper { display: grid; gap: 4px; }
  .stepper-label { font-size: clamp(13px, 1.6cqi, 18px); font-weight: 600; color: var(--secondary-text-color); }
  .stepper-controls { display: flex; align-items: center; gap: 10px; }
  .lobby .stepper button { min-width: 52px; font-size: 22px; }
  .stepper-value { min-width: 2ch; text-align: center; font-size: clamp(20px, 2.6cqi, 32px); font-variant-numeric: tabular-nums; }
  .lobby-nobody { margin: 0 0 10px; font-size: clamp(12px, 1.5cqi, 16px); }
  .options { display: flex; flex-wrap: wrap; gap: 8px; }
  .options .section-label { flex-basis: 100%; margin-bottom: 0; }
  /* The start stays in reach at the bottom of the screen while the page scrolls. */
  .lobby-actions {
    position: sticky; bottom: 0; z-index: 1; display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end;
    gap: 10px; padding: 8px 0; background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
  }
  .lobby-hint { flex: 1 1 100%; font-weight: 700; color: var(--ad-warn-text); }
  .lobby-hint:empty { display: none; }
  .lobby .secondary { background: none; }
  .lobby .start {
    min-height: 60px; padding: 0 clamp(20px, 3cqi, 40px); font-size: clamp(17px, 2.3cqi, 26px); font-weight: 800;
    color: var(--text-primary-color, #fff); background: var(--ad-accent); border-color: var(--ad-accent);
  }
  /* Idle mode: panels in turn, faded in unless the device asks for less motion. */
  .idle-panel { display: flex; flex-direction: column; gap: clamp(8px, 1.6cqi, 20px); animation: ad-fade .6s ease both; }
  @keyframes ad-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .idle-panel { animation: none; } }
  .idle-back { text-align: center; font-size: clamp(11px, 1.4cqi, 15px); }
  .ranking {
    list-style: none; margin: 0 auto; padding: 0; width: min(100%, 960px); display: grid; gap: clamp(6px, 1.2cqi, 14px);
  }
  .ranking li {
    display: flex; align-items: center; gap: clamp(8px, 1.6cqi, 20px); padding: clamp(8px, 1.4cqi, 16px) clamp(12px, 2cqi, 24px);
    border-radius: 16px; font-size: clamp(16px, 2.8cqi, 36px); background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .ranking li.winner { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
  .ranking .rank { min-width: 1.2em; font-weight: 800; color: var(--ad-accent); }
  .ranking .who { flex: 1; min-width: 0; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ranking .score { font-weight: 800; font-variant-numeric: tabular-nums; }
  .ranking .muted { font-size: .55em; }
  .match-head { text-align: center; font-size: clamp(14px, 2.2cqi, 28px); font-weight: 700; color: var(--secondary-text-color); }
  .records {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(clamp(160px, 24cqi, 300px), 1fr));
    gap: clamp(8px, 1.4cqi, 16px); width: min(100%, 1100px); margin: 0 auto;
  }
  .records div { padding: clamp(10px, 1.6cqi, 18px); border-radius: 16px; background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
  .records dt { font-size: clamp(12px, 1.6cqi, 18px); color: var(--secondary-text-color); }
  .records dd { margin: 4px 0 0; font-size: clamp(20px, 3.4cqi, 44px); font-weight: 800; font-variant-numeric: tabular-nums; }
  .goal {
    width: min(80%, 640px); height: 12px; border-radius: 999px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
  }
  .goal i { display: block; height: 100%; border-radius: inherit; background: var(--ad-accent); }
  .goal.reached i { background: ${STATUS_COLORS.ready}; }
  /* Tournaments: who plays next, the round robin table and the knockout bracket. */
  .tournament { display: flex; flex-direction: column; gap: clamp(10px, 1.8cqi, 24px); width: 100%; }
  .next-up {
    display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 6px clamp(10px, 2cqi, 24px);
    padding: clamp(10px, 1.6cqi, 20px); border-radius: 18px; text-align: center;
    background: color-mix(in srgb, var(--ad-accent) 12%, transparent);
  }
  .next-up .section-label { flex-basis: 100%; font-size: clamp(11px, 1.4cqi, 15px); }
  .pairing {
    display: inline-flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: .35em;
    font-size: clamp(20px, 3.6cqi, 48px); font-weight: 800; color: var(--primary-text-color);
  }
  .pairing .vs { font-size: .5em; font-weight: 600; color: var(--secondary-text-color); }
  .countdown { font-size: clamp(13px, 1.8cqi, 22px); font-weight: 600; color: var(--secondary-text-color); }
  .start-next {
    min-height: 44px; padding: 0 18px; border-radius: 999px; cursor: pointer; touch-action: manipulation;
    font: inherit; font-size: clamp(13px, 1.7cqi, 20px); font-weight: 700;
    color: var(--text-primary-color, #fff); background: var(--ad-accent); border: none;
  }
  .standings {
    width: min(100%, 1100px); margin: 0 auto; border-collapse: collapse; font-variant-numeric: tabular-nums;
    font-size: clamp(14px, 2.2cqi, 30px); color: var(--primary-text-color);
  }
  .standings th, .standings td { padding: .3em .45em; text-align: center; }
  .standings thead th {
    font-size: .55em; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--secondary-text-color);
  }
  .standings abbr { text-decoration: none; }
  /* The name takes the room the numbers leave, and a long one ends in an ellipsis. */
  .standings .who { width: 40%; max-width: 0; text-align: left; font-weight: 700; }
  .standings .player-name { display: flex; align-items: center; min-width: 0; }
  .standings .player-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .standings tbody tr { border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
  .standings .rank { width: 2em; font-weight: 800; color: var(--ad-accent); }
  .standings .points { font-weight: 800; }
  .standings tr.next { background: color-mix(in srgb, var(--ad-accent) 10%, transparent); }
  .standings tr.champion { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
  .standings tr.champion .player-name span::after { content: " 🏆"; }
  .bracket { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: clamp(10px, 2.4cqi, 36px); }
  .bracket .round { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
  .bracket .duels { flex: 1; display: flex; flex-direction: column; justify-content: space-around; gap: 10px; }
  .bracket .section-label { font-size: clamp(11px, 1.4cqi, 15px); }
  .bracket .section-label.third { margin-top: 6px; }
  .duel {
    position: relative; border-radius: 14px; overflow: hidden; background: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    border: 2px solid var(--divider-color, rgba(127,127,127,.3));
  }
  .duel.live { border-color: var(--ad-accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ad-accent) 25%, transparent); }
  .duel.bye { border-style: dashed; opacity: .7; }
  .slot {
    display: flex; align-items: center; gap: .3em; min-height: 1.7em; padding: .25em .6em;
    font-size: clamp(13px, 2cqi, 26px); color: var(--primary-text-color);
  }
  .slot + .slot { border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
  .slot .who { flex: 1; min-width: 0; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .slot.open .who { font-weight: 500; font-style: italic; color: var(--secondary-text-color); }
  .slot .score { font-weight: 800; font-variant-numeric: tabular-nums; }
  .slot.won { background: color-mix(in srgb, ${STATUS_COLORS.ready} 16%, transparent); }
  .slot.lost { opacity: .5; }
  .duel.crowned .slot.won .who::after { content: " 🏆"; }
  /* A player who goes on slides into the next round, outlined for a moment. */
  .slot.fresh { animation: ad-advance 1.6s ease-out backwards; }
  @keyframes ad-advance {
    from { opacity: 0; transform: translateX(-1.5em); box-shadow: inset 0 0 0 3px var(--ad-accent); }
    35% { opacity: 1; transform: none; box-shadow: inset 0 0 0 3px var(--ad-accent); }
    to { box-shadow: inset 0 0 0 3px transparent; }
  }
  @media (prefers-reduced-motion: reduce) { .slot.fresh { animation: none; } }
  /* A phone shows the rounds one below the other. */
  @container (max-width: 560px) { .bracket { grid-auto-flow: row; } }
  .lobby-mode { display: flex; gap: 8px; }
  .lobby .mode { flex: 1; font-size: clamp(15px, 2cqi, 22px); }
  .formats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
`;

const PLAYERS_CSS = `${BASE_CSS}
  .players-card { display: flex; flex-direction: column; gap: 16px; padding: 18px; box-sizing: border-box; }
  .profiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
  .profile {
    display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 14px; min-width: 0;
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .profile-name {
    display: flex; align-items: center; min-width: 0; font-size: 17px; font-weight: 800; color: var(--primary-text-color);
  }
  .profile-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .profile-name .avatar { width: 1.6em; height: 1.6em; margin-right: .45em; }
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
  .players-card header .export { margin-left: auto; min-height: 32px; font-size: 13px; }
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

// Badges, trends and groupings of the players card.
const PROGRESS_CSS = `
  .section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
  .badge-player + .badge-player { margin-top: 12px; }
  .badge-owner { display: flex; align-items: baseline; gap: 8px; margin: 8px 0 6px; }
  .badge-owner b { font-size: 15px; color: var(--primary-text-color); }
  .badge-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
  .badge {
    display: grid; grid-template-columns: 38px minmax(0, 1fr); gap: 10px; align-items: center; min-width: 0;
    padding: 8px 10px; border-radius: 12px; background: color-mix(in srgb, var(--tier) 13%, transparent);
  }
  /* A medal: the tier's colour with a metallic sheen. */
  .badge-icon {
    width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; --mdc-icon-size: 22px;
    color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.3);
    background: radial-gradient(circle at 32% 28%, color-mix(in srgb, var(--tier) 35%, #fff), var(--tier) 55%,
      color-mix(in srgb, var(--tier) 70%, #000));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--tier) 45%, transparent), 0 1px 3px rgba(0,0,0,.25);
  }
  .badge-text { display: flex; flex-direction: column; gap: 1px; min-width: 0; font-size: 12px; line-height: 1.3; }
  .badge-text b { font-size: 13px; color: var(--primary-text-color); }
  .badge-text > span { color: var(--secondary-text-color); }
  .badge.locked {
    background: none; border: 1px dashed color-mix(in srgb, var(--primary-text-color) 22%, transparent);
    padding: 7px 9px;
  }
  .badge.locked .badge-icon {
    color: var(--disabled-text-color, #9e9e9e); box-shadow: none; text-shadow: none;
    background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
  }
  .badge.locked .badge-text b { color: var(--secondary-text-color); }
  .badge-bar {
    display: block; height: 4px; margin-top: 3px; border-radius: 999px; overflow: hidden;
    background: color-mix(in srgb, var(--primary-text-color) 10%, transparent);
  }
  .badge-bar i { display: block; height: 100%; border-radius: inherit; background: var(--ad-accent); }
  .trend-player, .group-player { padding: 8px 0; border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
  :is(.trend-player, .group-player):first-child { border-top: 0; }
  .trend-name { font-weight: 700; margin-bottom: 6px; color: var(--primary-text-color); }
  .trends { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
  .trend {
    display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 6px; align-items: center;
    padding: 8px 10px; border-radius: 12px; background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .trend-label { font-size: 11px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .trend-value { font-size: 14px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .trend .spark { grid-column: 1 / -1; height: 24px; }
  .spark polyline {
    fill: none; stroke: var(--ad-accent); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round;
    vector-effect: non-scaling-stroke;
  }
  .spark .dot { stroke-width: 5; }
  .arrow.up { color: var(--ad-ok-text); }
  .arrow.down { color: var(--ad-error-text); }
  .arrow.steady { color: var(--secondary-text-color); }
  .groups { display: grid; gap: 2px; }
  .group { display: grid; grid-template-columns: 3.4em minmax(0, 1fr) auto; gap: 10px; align-items: baseline; font-size: 13px; }
  .group-target {
    padding: 1px 0; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 800;
    color: var(--ad-accent); border: 1px solid var(--ad-accent);
  }
  .group-text { color: var(--primary-text-color); }
  .group-change { font-size: 12px; font-weight: 700; white-space: nowrap; }
  .group-change.better { color: var(--ad-ok-text); }
  .group-change.worse { color: var(--ad-error-text); }
`;

const LEADERBOARD_CSS = `${BASE_CSS}${SEGMENTED_CSS}
  .leaderboard { display: flex; flex-direction: column; gap: 14px; padding: 18px; box-sizing: border-box; }
  .leaderboard header { flex-wrap: wrap; }
  .records { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
  .record {
    display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 14px; min-width: 0;
    background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
  }
  .record-name { font-size: 12px; font-weight: 700; letter-spacing: .02em; color: var(--ad-accent); }
  .record-leader { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; min-width: 0; }
  .record-leader .who {
    font-size: 17px; font-weight: 800; color: var(--primary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .record-leader .who::before { content: "👑 "; font-size: 14px; }
  .record-leader .value { font-size: 20px; font-weight: 800; color: var(--ad-gold-text); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .record-places { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; font-size: 13px; }
  .record-places li { display: grid; grid-template-columns: 1.8em minmax(0, 1fr) auto; gap: 6px; color: var(--secondary-text-color); }
  .record-places .who { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .record-places .value { font-variant-numeric: tabular-nums; }
`;

// Live card panel --------------------------------------------------------------

// The practice panel of the live card: the game, the line under it, the big
// number, what to aim at next and, in a match, a row for every player.
function livePanel(view, ui) {
  if (view.summary) return summaryPanel(view, ui);
  const { t, format } = ui;
  const turn = (game) =>
    game.winner === null ? `${playerName(ui, { player: game.player, name: game.name }, true)} ${t("score_turn")}` : "";
  const winner = (game) => note(winnerText(game, ui), "won");
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
      route: bullOff.rethrow ? note(t("bull_off_rethrow"), "rethrow") : note(t("bull_off_hint")),
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
      title: cricketTitle(t, cricket.kind),
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
      meta: [partyRound(party, t), match ? turn(party) : ""].filter(Boolean).join(" · "),
      big: killer ? (party.phase === "choose" ? "?" : String(current?.number ?? "–")) : String(party.points),
      route: party.winner !== null ? winner(party) : partyNote(party, ui),
      rows: match ? playerRows(partyPlayers(party, ui)) : "",
    };
  }
  const { practice } = view;
  const players = x01Tiles(practice, ui);
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

// A won match with its summary: the result in large type, the summary below.
function summaryPanel(view, ui) {
  const panel = livePanel({ ...view, summary: null }, ui);
  const game = view.cricket ?? view.party ?? view.practice;
  return { ...panel, big: matchResult(game) || panel.big, routeTitle: "", rows: summaryTable(view.summary, ui) };
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
      clearTimeout(this._summaryTimer);
    }

    // A summary whose time ran out while the card was away is gone when it returns.
    connectedCallback() {
      if (this._built && this._summarySeen) this._update();
    }

    // The summary of the finished match, while it shows: until the next game
    // starts or, with summary_seconds, that long after the card first showed it.
    _matchSummary(view) {
      const c = this._config;
      clearTimeout(this._summaryTimer);
      // Party games keep their final scores on screen; they have no numbers to sum up.
      const shown = ["x01", "cricket"].includes(view.mode) && c.show_summary !== false;
      const summary = shown ? summaryView(this._state("practice")) : null;
      const seconds = Number(c.summary_seconds) || 0;
      if (!summary || seconds <= 0) return summary;
      if (this._summarySeen?.ended !== summary.ended) this._summarySeen = { ended: summary.ended, at: Date.now() };
      const left = this._summarySeen.at + seconds * 1000 - Date.now();
      if (left <= 0) return null;
      this._summaryTimer = setTimeout(() => this._update(), left);
      return summary;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }

    _css() {
      return BASE_CSS;
    }

    // Cards that show the pictures of the persons linked to the players.
    static avatars = false;

    // Entity ids whose state changes redraw the card.
    _watched() {
      return [...Object.values(this._ids), ...(this.constructor.avatars ? this._personIds() : [])];
    }

    // The persons linked to the player profiles.
    _personIds() {
      const players = this._state("profiles")?.attributes?.players;
      return (Array.isArray(players) ? players : []).map((player) => named(player?.person)).filter(Boolean);
    }

    // The state of a watched entity as far as the card cares about it: of a
    // person only the picture and whether they are home, not every move.
    _relevant(id, state) {
      if (!state || !id.startsWith("person.")) return state;
      return `${state.state}|${state.attributes?.entity_picture ?? ""}`;
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

    // Texts, numbers, beds and the pictures of players as the shared renderers read them.
    _ui() {
      const links = personLinks(this._hass, this._state("profiles"));
      return {
        t: (key) => this._t(key),
        format: (value, digits) => this._format(value, digits),
        percent: (value, digits) => this._percent(value, digits),
        label: (key) => hitLabel(this._hass, key),
        date: (value) => formatDateTime(this._hass, value),
        avatar: (name) => links.get(nameKey(name))?.picture ?? null,
        links,
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
      const panel = livePanel({ ...view, summary: this._matchSummary(view) }, this._ui());
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
      // The heatmap mode and whose darts it shows, as switched in the card.
      this._mode = null;
      this._source = null;
      this._positions = null;
      this._positionsFor = null;
    }

    // A new configuration shows its own mode and player again.
    setConfig(config) {
      this._mode = null;
      this._source = null;
      super.setConfig(config);
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
      const modes = HEAT_MODES.map(
        (mode) => `<button type="button" data-mode="${mode}" aria-pressed="false">${t(`mode_${mode}`)}</button>`
      ).join("");
      const controls = c.show_heatmap_controls
        ? `<div class="heat-controls">
            <div class="segmented modes" role="group" aria-label="${t("mode")}">${modes}</div>
            <div class="segmented sources" role="group" aria-label="${t("heatmap_source")}" hidden></div>
          </div>`
        : "";
      return `
        <div class="heat">
          <div class="heat-head"><div class="section-label">${t("heatmap")}</div>${controls}</div>
          <div class="heat-frame">
            <svg viewBox="-230 -230 460 460" role="img" aria-label="${t("heatmap_label")}">
              <defs><filter id="ad-density" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="4"/>
              </filter></defs>
              <g class="face">${boardSvg(c.board_style)}</g>
              <g class="heat-layer"></g>
              <g class="numbers">${numbersSvg(c.board_style)}</g>
            </svg>
          </div>
          <div class="legend">
            <span class="muted legend-min">1</span>
            <div class="legend-bar" style="background: linear-gradient(90deg, ${legend})"></div>
            <span class="muted legend-max">–</span>
          </div>
          <div class="groups" hidden></div>
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
        heatSvg: root.querySelector(".heat-frame svg"),
        legendMin: root.querySelector(".legend-min"),
        legendMax: root.querySelector(".legend-max"),
        modes: root.querySelector(".modes"),
        sources: root.querySelector(".sources"),
        groups: root.querySelector(".heat .groups"),
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
      this._el.modes?.addEventListener("click", (event) => {
        const button = event.target.closest?.("button[data-mode]");
        if (!button) return;
        this._mode = button.dataset.mode;
        this._update();
      });
      this._el.sources?.addEventListener("click", (event) => {
        const button = event.target.closest?.("button[data-source]");
        if (!button) return;
        this._source = button.dataset.source;
        this._update();
      });
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

      this._updateHeatmap(darts);
      this._updateBests();
      this._updateHistory();
      this._updateSessions();
      this._confirmChanged();
    }

    // The heatmap mode chosen in the card, otherwise the configured one.
    _heatMode() {
      const mode = this._mode ?? this._config.mode;
      return HEAT_MODES.includes(mode) ? mode : "beds";
    }

    // Whose darts the heatmap shows: a player's name, or empty for the session.
    _heatSource() {
      return this._source ?? String(this._config.player ?? "").trim();
    }

    _profile(name) {
      const players = this._state("profiles")?.attributes?.players;
      const wanted = name.toLowerCase();
      return (Array.isArray(players) ? players : []).find(
        (player) => typeof player?.name === "string" && player.name.toLowerCase() === wanted
      );
    }

    // The session or a player: hits for the beds and numbers, positions from the board.
    _updateHeatmap(darts) {
      const source = this._heatSource();
      const profile = source ? this._profile(source) : null;
      const hits = source ? profile?.hits : this._state("darts")?.attributes?.hits;
      this._updateHeatControls(source);
      if (this._heatMode() === "positions") this._loadPositions(source);
      this._updateHeat(hits);
      this._updateTop(hits, source ? (finite(profile?.darts_thrown) ?? 0) : darts);
    }

    _updateHeatControls(source) {
      const el = this._el;
      if (el.heatSvg) {
        el.heatSvg.setAttribute("aria-label", this._t(this._heatMode() === "positions" ? "positions_label" : "heatmap_label"));
      }
      if (!el.modes) return;
      for (const button of el.modes.querySelectorAll("button")) {
        button.setAttribute("aria-pressed", String(button.dataset.mode === this._heatMode()));
      }
      const players = this._state("profiles")?.attributes?.players;
      const names = (Array.isArray(players) ? players : [])
        .filter((player) => named(player?.name) && (finite(player.darts_thrown) ?? 0) > 0)
        .map((player) => player.name)
        .sort((a, b) => a.localeCompare(b));
      if (source && !names.some((name) => name.toLowerCase() === source.toLowerCase())) names.push(source);
      el.sources.hidden = !names.length;
      this._setHtml(
        el.sources,
        ["", ...names]
          .map(
            (name) =>
              `<button type="button" data-source="${escapeHtml(name)}" aria-pressed="${
                name.toLowerCase() === source.toLowerCase()
              }">${escapeHtml(name || this._t("heatmap_session"))}</button>`
          )
          .join("")
      );
    }

    // New positions come with every booked visit of the session or the player.
    _positionsKey(source) {
      const count = source ? finite(this._profile(source)?.darts_thrown) : this._number("visits");
      return `${this._deviceId}|${source}|${count ?? ""}`;
    }

    async _loadPositions(source) {
      const key = this._positionsKey(source);
      if (this._positionsFor === key || typeof this._hass.callWS !== "function") return;
      this._positionsFor = key;
      let result = null;
      try {
        result = await this._hass.callWS({
          type: "autodarts/positions",
          device_id: this._deviceId,
          ...(source ? { player: source } : {}),
        });
      } catch (error) {
        // A board that is being removed has no positions to show.
      }
      if (this._positionsFor !== key) return;
      this._positions = { source, positions: validPositions(result?.positions), spread: spreadView(result?.spread) };
      this._drawPositions();
    }

    _drawPositions() {
      const el = this._el;
      const shown = this._positions?.source === this._heatSource() ? this._positions : null;
      const positions = shown?.positions ?? [];
      this._setHtml(el.heat, positionsHtml(positions));
      el.legendMin.textContent = this._t("legend_few");
      el.legendMax.textContent = positions.length ? this._t("legend_many") : "–";
      // Groupings need darts at a bed the game knows; without positions, the card says so.
      el.groups.hidden = !shown || (positions.length > 0 && !shown.spread.length);
      this._setHtml(
        el.groups,
        shown && !positions.length
          ? `<div class="empty-hint">${escapeHtml(this._t("positions_empty"))}</div>`
          : spreadHtml(shown?.spread ?? [], this._ui())
      );
    }

    _updateHeat(hits) {
      if (!this._el.heat) return;
      if (this._heatMode() === "positions") {
        this._drawPositions();
        return;
      }
      this._el.groups.hidden = true;
      this._el.legendMin.textContent = "1";
      const levels = heatLevels(hits, this._heatMode());
      const max = Math.max(0, ...levels.values());
      const counts = new Map(validHits(hits));
      const total = [...counts.values()].reduce((sum, count) => sum + count, 0);
      const describe = (bed) => {
        // Tooltips name the scoring bed; singles cover both single areas.
        const key = bed === "Bull" ? "BULL" : bed.replace(/^S[IO]/, "S");
        const numbers = this._heatMode() === "numbers";
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

    static avatars = true;

    getCardSize() {
      return 8;
    }

    getGridOptions() {
      return { columns: "full", min_columns: 6 };
    }

    _css() {
      return SCOREBOARD_CSS;
    }

    // Back on the screen counts as a look at it: the idle time starts again.
    connectedCallback() {
      if (!this._el) return;
      this._activity = Date.now();
      this._update();
    }

    disconnectedCallback() {
      super.disconnectedCallback();
      clearTimeout(this._lobbyTimer);
      clearTimeout(this._idleTimer);
      clearTimeout(this._tournamentTimer);
      clearInterval(this._tournamentTick);
      this._tournamentTick = null;
      this._idleOff();
    }

    // The four player name fields, in their order.
    _nameIds() {
      return [...(this._index?.["text.practice_player"] ?? [])].sort((a, b) =>
        a.localeCompare(b, "en", { numeric: true })
      );
    }

    // The start scores of the players, in the same order as the names.
    _startIds() {
      return [...(this._index?.["number.practice_start"] ?? [])].sort((a, b) =>
        a.localeCompare(b, "en", { numeric: true })
      );
    }

    _watched() {
      return [...super._watched(), ...this._nameIds(), ...this._startIds()];
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
                  <button type="button" class="lobby-toggle" hidden><span aria-hidden="true">＋</span><span>${t(
                    "lobby_open"
                  )}</span></button>
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
        board: root.querySelector(".scoreboard"),
        title: root.querySelector(".title"),
        meta: root.querySelector(".meta"),
        pill: root.querySelector(".pill"),
        banner: root.querySelector(".banner"),
        main: root.querySelector(".main"),
        visit: root.querySelector(".visit"),
        caller: root.querySelector(".caller-toggle"),
        callerIcon: root.querySelector(".caller-icon"),
        lobby: root.querySelector(".lobby-toggle"),
      };
      this._callerState = null;
      this._followed = null;
      this._el.caller?.addEventListener("click", () => this._toggleCaller());
      this._el.lobby.addEventListener("click", () => this._lobbyAction("open"));
      this._el.main.addEventListener("click", (event) => {
        const target = event.target.closest("[data-lobby]");
        if (target && !target.disabled) this._lobbyAction(target.dataset.lobby, target.dataset.value);
        if (event.target.closest("[data-tournament]") && !this.preview) this._press(this._ids.tournamentNext);
      });
      this._el.main.addEventListener("input", (event) => {
        if (this._lobby && event.target.classList.contains("lobby-name")) this._lobby.draft = event.target.value;
      });
      this._el.main.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || !event.target.classList.contains("lobby-name")) return;
        event.preventDefault();
        this._lobbyAction("add-name");
      });
      // Every tap and key at the screen ends idle mode and starts the idle time again.
      for (const kind of ["click", "keydown"]) this._el.board.addEventListener(kind, () => this._touch());
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

    _announce(visit, view, tournament) {
      const current = callerState(visit, view, this._callerState);
      const previous = this._callerState;
      this._callerState = current;
      const followed = tournamentCallState(tournament);
      const before = this._tournamentCall;
      this._tournamentCall = followed;
      if (!this._config.caller || !callerAudio.unlocked || this.preview) return;
      for (const call of [
        ...callerCalls(previous, current, this._config),
        ...tournamentCalls(before, followed, this._config),
      ]) {
        if (call.kind === "fanfare") playFanfare();
        else this._speak(callerText(call, (key) => this._t(key)));
      }
    }

    // New game screen -----------------------------------------------------------

    // The games the screen offers: none without the practice game or with the screen off.
    _lobbyGames() {
      if (this._config.lobby === false) return [];
      return lobbyGames(this._state("game")?.attributes?.options, this._config.lobby_games);
    }

    // The game, the players and the rules as the board has them now.
    _board() {
      const on = (name) => this._state(name)?.state === "on";
      return {
        game: this._state("game")?.state,
        players: this._number("players"),
        names: this._nameIds().map((id) => {
          const state = this._hass.states[id];
          return usable(state) ? String(state.state) : "";
        }),
        legs: this._number("legs"),
        sets: this._number("sets"),
        double_out: !this._state("doubleOut") || on("doubleOut"),
        double_in: on("doubleIn"),
        bull_off: on("bullOff"),
        bull_off_distance: on("bullOffDistance"),
        teams: on("teams"),
        starts: this._startIds().map((id) => {
          const start = Number(this._hass.states[id]?.state);
          return Number.isInteger(start) ? start : 0;
        }),
        format: this._state("tournamentFormat")?.state,
        third_place: on("tournamentThird"),
        random_draw: on("tournamentDraw"),
      };
    }

    // The tournament games the screen offers, of the games it offers at all.
    _tournamentGames() {
      const offered = new Set(this._lobbyGames().flatMap((group) => group.games));
      const games = this._state("tournamentGame")?.attributes?.options;
      return lobbyGames((Array.isArray(games) ? games : []).filter((game) => offered.has(String(game))));
    }

    // A game by the name players know; newer games by the name Home Assistant gives them.
    _gameName(game) {
      const select = this._state("game");
      return gameName(
        (key) => this._t(key),
        /^\d+$/.test(game) ? Number(game) : game,
        (option) => (this._hass.formatEntityState ? this._hass.formatEntityState(select, option) : null)
      );
    }

    _lobbyAction(action, value) {
      if (this.preview) return;
      if (action === "open") {
        this._openLobby(false);
        return;
      }
      const choice = this._lobby;
      if (!choice) return;
      if (action === "close") {
        this._lobby = null;
      } else if (action === "start") {
        this._startGame(choice);
      } else if (action === "end") {
        // Ending the game needs a second tap; the screen stays for the next game.
        // A tournament ends with its game.
        if (this._confirmed("end")) {
          if (this._tournamentRunning()) this._press(this._ids.tournamentStop);
          this._call("select", "select_option", { entity_id: this._ids.game, option: "off" });
        }
      } else if (action === "mode") {
        const next = lobbyChange(choice, action, value);
        const games = (next.tournament ? this._tournamentGames() : this._lobbyGames()).flatMap((group) => group.games);
        if (!games.includes(next.game)) next.game = games.includes("501") ? "501" : games[0];
        this._lobby = next;
      } else if (action === "add-name") {
        this._lobby = lobbyChange(choice, "add", this._el.main.querySelector(".lobby-name").value);
      } else {
        this._lobby = lobbyChange(choice, action, value);
      }
      this._update();
    }

    // Opened by a tap, or by itself a few seconds after a game ended.
    _openLobby(auto) {
      clearTimeout(this._lobbyTimer);
      const games = this._lobbyGames().flatMap((group) => group.games);
      // Between the matches of a tournament, its table or bracket shows instead.
      if (this.preview || !games.length || this._lobby || (auto && this._tournamentOwned)) return;
      this._lobby = { ...lobbyChoice(this._board(), games), auto };
      // The screen that opens by itself also waits the idle time before idle mode takes over.
      this._activity = Date.now();
      this._idleOff();
      this._update();
    }

    // The start button stays disabled while the game lacks players.
    _startGame(choice) {
      const device = this._hass.devices?.[this._deviceId];
      const entry = device?.primary_config_entry ?? device?.config_entries?.[0] ?? null;
      const options = { entry, distance: Boolean(this._ids.bullOffDistance) };
      if (choice.tournament) this._call("autodarts", "start_tournament", tournamentStartData(choice, options));
      else this._call("autodarts", "start_game", startGameData(choice, options));
      this._lobby = null;
    }

    // Tournament ------------------------------------------------------------------

    _tournamentRunning() {
      return ["playing", "waiting"].includes(tournamentView(this._state("tournament"))?.status);
    }

    // The tournament and what the screen shows of it: the round in the match view,
    // or, between its matches, the table or the bracket once the result has shown.
    _tournamentState(view) {
      const tournament = tournamentView(this._state("tournament"));
      this._tournamentOwned = false;
      clearTimeout(this._tournamentTimer);
      if (!tournament) return { tournament, shown: false, label: "" };
      const game = view.practice ?? view.cricket ?? view.party ?? null;
      const names = game ? game.scores.map((score) => score.name) : [];
      const over = gameState(view) !== "running";
      // A new match after the final: the tournament is over for this screen.
      if (tournament.status === "finished" && !over) this._tournamentDismissed = tournament.started;
      // When the screen saw the result of the last match; long ago at first sight.
      const result = tournament.last ? `${tournament.started}|${tournament.last.match}` : null;
      if (this._tournamentResult?.key !== result) {
        this._tournamentResult = { key: result, at: this._tournamentResult ? Date.now() : 0 };
      }
      const playing = tournament.status === "playing" && playsMatch(names, tournament.current);
      const between =
        over &&
        (tournament.status === "waiting" ||
          (tournament.status === "finished" && this._tournamentDismissed !== tournament.started));
      this._tournamentOwned = playing || between;
      // The summary time of the tournament, after which its pause begins.
      const summary = tournament.summary * 1000;
      const wait = this._tournamentResult.at + summary - Date.now();
      if (between && wait > 0) this._tournamentTimer = setTimeout(() => this._update(), wait);
      // The match view names the round, also with the result of the match.
      const labelled = playing ? tournament.current : between && wait > 0 ? tournament.last : null;
      // The bracket animates the places filled since it last changed.
      const slots = bracketSlots(tournament);
      const signature = JSON.stringify([...slots]);
      if (this._bracket?.signature !== signature) {
        this._bracket = { signature, slots, fresh: freshSlots(this._bracket?.slots, slots) };
      }
      return {
        tournament,
        shown: between && wait <= 0,
        label: labelled ? tournamentLabel(tournament, labelled, (key) => this._t(key)) : "",
      };
    }

    _confirmChanged() {
      if (this._el && this.isConnected) this._update();
    }

    // Idle mode -----------------------------------------------------------------

    // What happened since the last update: darts, and a game that started or ended.
    _follow(visit, view, summary = null) {
      const state = gameState(view);
      const darts = visitThrows(visit);
      const signature = `${darts.map(dartKey).join(" ")}|${view.mode}|${state}`;
      const previous = this._followed;
      this._followed = { signature, state, darts: darts.length };
      if (!previous || signature !== previous.signature) {
        this._activity = Date.now();
        this._idleOff();
      }
      // Players who throw after a game do not need the screen that opened by itself.
      if (previous && darts.length > previous.darts && this._lobby?.auto) this._lobby = null;
      // The summary of a match comes first: the screen opens by itself only after it.
      const summaryEnded = Boolean(this._summaryShown && !summary);
      this._summaryShown = Boolean(summary);
      if (state === "running" || summary) {
        clearTimeout(this._lobbyTimer);
      } else if ((previous?.state === "running" || summaryEnded) && !this.preview && this.isConnected) {
        clearTimeout(this._lobbyTimer);
        this._lobbyTimer = setTimeout(() => this._openLobby(true), LOBBY_DELAY);
      }
      this._scheduleIdle(state);
    }

    _scheduleIdle(state) {
      clearTimeout(this._idleTimer);
      const c = this._config;
      if (this.preview || !c.idle || state === "running" || !this.isConnected) {
        this._idleOff();
        return;
      }
      if (this._idle) return;
      const due = this._activity + Math.max(Number(c.idle_after) || 0, 5) * 1000;
      this._idleTimer = setTimeout(() => this._idleOn(), Math.max(due - Date.now(), 0));
    }

    _idleOn() {
      if (!this._idlePanels().length) return;
      this._idle = { index: 0, since: Date.now() };
      this._lobby = null;
      clearTimeout(this._lobbyTimer);
      this._idleTick = setInterval(() => this._idleStep(), 1000);
      this._update();
    }

    // Every second the clock moves on; after the interval the next panel shows.
    _idleStep() {
      const every = Math.max(Number(this._config.idle_interval) || 0, 3) * 1000;
      if (Date.now() - this._idle.since >= every) {
        this._idle.index += 1;
        this._idle.since = Date.now();
      }
      this._update();
    }

    _idleOff() {
      clearInterval(this._idleTick);
      this._idleTick = null;
      this._idle = null;
    }

    // A tap or a key at the screen.
    _touch() {
      this._activity = Date.now();
      if (this._idle) {
        this._idleOff();
        this._update();
      } else if (this._followed) {
        this._scheduleIdle(this._followed.state);
      }
    }

    // The idle panels with something to show.
    _idlePanels() {
      const profiles = playersView(this._state("profiles"), this._state("lastMatch"));
      const data = {
        tournament: tournamentView(this._state("tournament")),
        players: profiles.players,
        match: profiles.matches[0] ?? null,
        records: bestsView(this._state("bests"), this._state("streak")),
        stats: this._stats(),
        now: new Date(),
      };
      const ui = { ...this._ui(), clock: (moment) => formatClock(this._hass, moment) };
      return idlePanels(this._config.idle_panels, data, ui);
    }

    // The visit and the training session between games.
    _stats() {
      const visit = this._state("visit");
      return {
        visit: usable(visit) ? visit.state : null,
        darts: this._number("darts"),
        average: this._number("average"),
        highest: this._number("highest"),
        max: this._number("max"),
        streak: this._number("streak"),
        today: this._number("today"),
        goal: Number(this._state("today")?.attributes?.goal) || 0,
      };
    }

    // Rendering -----------------------------------------------------------------

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
      const ui = { ...this._ui(), name: this._deviceName(), stats: this._stats() };
      const summary = this._matchSummary(view);
      const board = scoreboardHtml({ ...view, summary }, ui);
      const tournament = this._tournamentState(view);
      this._announce(visit, view, tournament.tournament);
      this._follow(visit, view, summary);
      const games = this._lobbyGames();
      if (!games.length) this._lobby = null;
      const panels = this._idle ? this._idlePanels() : [];
      const panel = panels.length ? panels[this._idle.index % panels.length] : null;
      let { title, meta, banner, main } = board;
      if (this._lobby) {
        const choice = this._lobby;
        title = t("lobby_title");
        meta = "";
        main = lobbyHtml(choice, {
          ...ui,
          games,
          tournamentGames: this._tournamentGames(),
          tournamentRunning: this._tournamentRunning(),
          name: (game) => this._gameName(game),
          suggestions: lobbySuggestions(this._state("profiles"), this._board().names, ui.links, choice.players),
          distance: Boolean(this._ids.bullOffDistance),
          teams: Boolean(this._ids.teams),
          running: ![undefined, "off", "unknown", "unavailable"].includes(this._state("game")?.state),
          confirmEnd: this._confirm === "end",
        });
      } else if (panel) {
        title = ui.name;
        meta = t(`idle_panel_${panel.panel}`);
        banner = "";
        main =
          `<div class="idle-panel" data-panel="${panel.panel}">${panel.html}</div>` +
          `<div class="idle-back muted">${escapeHtml(t("idle_back"))}</div>`;
      } else if (tournament.shown) {
        ({ title, meta, banner, main } = tournamentHtml(tournament.tournament, {
          ...ui,
          fresh: this._bracket.fresh,
          startNow: Boolean(this._ids.tournamentNext) && !this.preview,
        }));
      } else if (tournament.label) {
        meta = [tournament.label, meta].filter(Boolean).join(" · ");
      } else if (view.mode === "idle" && games.length) {
        main += `<button type="button" class="lobby-cta" data-lobby="open">${escapeHtml(t("lobby_open"))}</button>`;
      }
      el.lobby.hidden = !games.length || Boolean(this._lobby);
      el.board.classList.toggle("choosing", Boolean(this._lobby));
      el.board.classList.toggle("idling", Boolean(panel));
      el.title.textContent = title;
      el.meta.textContent = meta;
      el.banner.hidden = !banner;
      el.banner.textContent = banner;
      el.banner.classList.toggle("rethrow", board.bannerKind === "rethrow");
      this._setHtml(el.main, main);
      // The countdown to the next match changes every second, the rest stays.
      const counting = tournament.shown && !this._lobby && !panel && tournament.tournament.status === "waiting";
      const countdown = el.main.querySelector(".countdown");
      if (countdown) countdown.textContent = tournamentCountdown(tournament.tournament, Date.now(), t);
      if (counting !== Boolean(this._tournamentTick)) {
        clearInterval(this._tournamentTick);
        this._tournamentTick = counting ? setInterval(() => this._update(), 1000) : null;
      }
      if (!el.visit) return;
      // The new game screen, the idle panels, the match summary and the tournament need the room of the visit.
      el.visit.hidden = Boolean(this._lobby || panel || summary || tournament.shown);
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

    static avatars = true;

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
        <style>${PLAYERS_CSS}${PROGRESS_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="players-card">
              <header>
                <div class="title"></div>
                <div class="muted count"></div>
                ${c.export ? `<button class="action export">${t("export_button")}</button>` : ""}
              </header>
              <div class="message empty" hidden>${t("no_profiles")}</div>
              <div class="profiles"></div>
              ${c.show_head_to_head ? section("h2h", "head_to_head") : ""}
              ${c.show_matches ? section("matches", "recent_matches") : ""}
              ${this._progressHtml(t)}
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
        export: root.querySelector(".export"),
      };
      this._el.export?.addEventListener("click", () => this._export());
    }

    // The action writes the file; it downloads through Home Assistant with the
    // user's login, also while Home Assistant does not serve the www folder.
    async _export() {
      const button = this._el.export;
      if (this.preview || button.disabled) return;
      button.disabled = true;
      button.textContent = this._t("exporting");
      const device = this._hass.devices?.[this._deviceId];
      const entry = device?.primary_config_entry || device?.config_entries?.[0];
      try {
        const result = await this._hass.callWS({
          type: "call_service",
          domain: "autodarts",
          service: "export",
          service_data: {
            format: this._config.export_format === "json" ? "json" : "csv",
            what: "all",
            ...(entry ? { config_entry_id: entry } : {}),
          },
          return_response: true,
        });
        const download = result?.response?.download;
        if (typeof download !== "string" || !download.startsWith(EXPORT_DOWNLOADS)) {
          throw new Error(result?.response?.path || "");
        }
        const signed = await this._hass.callWS({ type: "auth/sign_path", path: download, expires: 60 });
        const link = document.createElement("a");
        link.href = signed.path;
        link.download = download.slice(EXPORT_DOWNLOADS.length);
        this.shadowRoot.append(link);
        link.click();
        link.remove();
      } catch (error) {
        const detail = error?.message ? `: ${error.message}` : "";
        this.dispatchEvent(
          new CustomEvent("hass-notification", {
            bubbles: true,
            composed: true,
            detail: { message: `${this._t("export_failed")}${detail}` },
          })
        );
      } finally {
        button.disabled = false;
        button.textContent = this._t("export_button");
      }
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
      this._updateProgress();
    }

    // Badges, trends and groupings, each in a section of its own.
    _progressHtml(t) {
      const c = this._config;
      const section = (name, title, extra = "") =>
        `<div class="${name}-section" hidden><div class="section-head"><div class="section-label">${t(title)}</div>` +
        `<span class="muted ${name}-meta"></span></div><div class="${name}-list"></div>${extra}</div>`;
      return [
        c.show_badges ? section("badges", "badges") : "",
        c.show_trends ? section("trends", "trends") : "",
        c.show_spread ? section("groups", "spread", `<p class="muted">${t("spread_hint")}</p>`) : "",
      ].join("");
    }

    _updateProgress() {
      const c = this._config;
      const root = this.shadowRoot;
      const ui = this._ui();
      const badges = root.querySelector(".badges-section");
      if (badges) {
        const players = badgesView(this._state("achievements")).players.filter(
          (player) => c.show_locked || player.unlocked
        );
        badges.hidden = !players.length;
        const count = (player) =>
          player.unlocked === 1 ? this._t("badge_count_one") : fill(this._t("badge_count"), { count: this._format(player.unlocked) });
        this._setHtml(
          badges.querySelector(".badges-list"),
          players
            .map(
              (player) =>
                `<div class="badge-player"><div class="badge-owner"><b>${escapeHtml(player.name)}</b>` +
                `<span class="muted">${escapeHtml(count(player))}</span></div>` +
                `<div class="badge-list">${badgesHtml(player, ui, c.show_locked)}</div></div>`
            )
            .join("")
        );
      }
      const weeks = Math.min(12, Math.max(4, Math.round(Number(c.trend_weeks)) || PLAYERS_DEFAULTS.trend_weeks));
      const progress = progressView(this._state("profiles"), weeks);
      const trends = root.querySelector(".trends-section");
      if (trends) {
        const active = progress.filter((player) => player.active);
        trends.hidden = !active.length;
        trends.querySelector(".trends-meta").textContent = fill(this._t("trends_range"), { weeks });
        this._setHtml(trends.querySelector(".trends-list"), trendsHtml(active, ui));
      }
      const groups = root.querySelector(".groups-section");
      if (groups) {
        const grouped = progress.filter((player) => player.groups.length);
        groups.hidden = !grouped.length;
        this._setHtml(
          groups.querySelector(".groups-list"),
          grouped
            .map(
              (player) =>
                `<div class="group-player"><div class="trend-name">${escapeHtml(player.name)}</div>` +
                `<div class="groups">${spreadHtml(player.groups, ui)}</div></div>`
            )
            .join("")
        );
      }
    }
  }

  // Leaderboard card --------------------------------------------------------------

  class AutodartsLeaderboardCard extends CardBase {
    static keys = LEADERBOARD_KEYS;

    static defaults = LEADERBOARD_DEFAULTS;

    static form = "leaderboard";

    constructor() {
      super();
      // The period switched in the card, until the configuration changes.
      this._chosen = null;
    }

    setConfig(config) {
      this._chosen = null;
      super.setConfig(config);
    }

    getCardSize() {
      return 5;
    }

    _css() {
      return LEADERBOARD_CSS;
    }

    _period() {
      const period = this._chosen ?? this._config.period;
      return PERIODS.includes(period) ? period : "all";
    }

    _build() {
      const t = (key) => escapeHtml(this._t(key));
      const periods = this._config.show_period
        ? `<div class="segmented periods" role="group" aria-label="${t("period")}">${PERIODS.map(
            (period) => `<button type="button" data-period="${period}" aria-pressed="false">${t(`period_${period}`)}</button>`
          ).join("")}</div>`
        : "";
      this.shadowRoot.innerHTML = `
        <style>${LEADERBOARD_CSS}</style>
        <ha-card>
          <div class="root">
            <div class="leaderboard">
              <header><div class="title"></div>${periods}</header>
              <div class="message empty" hidden>${t("leaderboard_empty")}</div>
              <div class="records"></div>
            </div>
          </div>
        </ha-card>
      `;
      const root = this.shadowRoot;
      this._el = {
        title: root.querySelector(".title"),
        empty: root.querySelector(".empty"),
        records: root.querySelector(".records"),
        periods: root.querySelector(".periods"),
      };
      this._el.periods?.addEventListener("click", (event) => {
        const button = event.target.closest?.("button[data-period]");
        if (!button) return;
        this._chosen = button.dataset.period;
        this._update();
      });
    }

    _update() {
      const c = this._config;
      const el = this._el;
      this.style.setProperty("--ad-accent", cssColor(c.accent_color, "var(--primary-color)"));
      el.title.textContent = c.title || this._t("leaderboard");
      const period = this._period();
      for (const button of el.periods?.querySelectorAll("button") ?? []) {
        button.setAttribute("aria-pressed", String(button.dataset.period === period));
      }
      const view = leaderboardRecords(this._state("profiles"), this._state("achievements"), period);
      el.empty.hidden = view.records.length > 0;
      const limit = Math.min(5, Math.max(1, Math.round(Number(c.limit)) || LEADERBOARD_DEFAULTS.limit));
      this._setHtml(el.records, leaderboardRecordsHtml(view, this._ui(), limit));
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
    [LEADERBOARD_TYPE]: AutodartsLeaderboardCard,
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
  { type: LEADERBOARD_TYPE, key: "leaderboard", docs: ["cards.md#leaderboard-card", "de/karten.md#bestenliste"] },
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
  addWeeks,
  aimBeds,
  badgesHtml,
  badgesView,
  bracketSlots,
  freshSlots,
  stageName,
  tournamentCalls,
  tournamentCallState,
  tournamentCountdown,
  tournamentHtml,
  tournamentLabel,
  tournamentStartData,
  tournamentView,
  bedPath,
  beds,
  bestsHtml,
  bestsView,
  boardStatus,
  boardSvg,
  bullOffLeaders,
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
  formatClock,
  formatDateTime,
  formatNumber,
  formatPercent,
  frontendReady,
  gameGroup,
  gameRules,
  gameState,
  gameView,
  heatColor,
  heatLevels,
  heatRatio,
  hitBeds,
  idlePanels,
  kind,
  label,
  language,
  leaderboardRecords,
  leaderboardRecordsHtml,
  livePanel,
  lobbyChange,
  lobbyChoice,
  lobbyGames,
  lobbyHtml,
  lobbySuggestions,
  matchResult,
  NORM,
  NUMBERS,
  numbersSvg,
  offsetText,
  parseSegment,
  partyBeds,
  partyView,
  pastSessions,
  personLinks,
  pictureUrl,
  playersHtml,
  playersView,
  positionsDensity,
  positionsHtml,
  practiceView,
  profileNames,
  progressView,
  R,
  recentVisits,
  register,
  scoreboardHtml,
  sectorAt,
  shortProcessor,
  sparkline,
  spreadHtml,
  spreadView,
  startGameData,
  summaryTable,
  summaryView,
  targetBeds,
  targetText,
  tierColor,
  topHits,
  trendsHtml,
  trendView,
  trendWeeks,
  visitBucket,
  visitCount,
  visitsFromHistory,
  voiceLanguage,
};
