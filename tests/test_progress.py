"""Progress of named players: visits, legs, training games, weeks, streaks and badges."""

from datetime import UTC, datetime, timedelta

from custom_components.autodarts.achievements import ACHIEVEMENTS, CATALOGUE
from custom_components.autodarts.practice import PracticeGame
from custom_components.autodarts.profiles import Profile, Profiles
from custom_components.autodarts.progress import (
    COUNTERS,
    TREND_WEEKS,
    WEEK_FIELDS,
    PlayerProgress,
    Progress,
)

from .test_positions import around
from .test_practice import dart

# A Wednesday; its week starts on Monday, 21 September.
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=UTC)


def play(game: PracticeGame, progress: Progress, *names: str, positions=None, now=NOW):
    """Throw a visit, pull the darts and collect the progress; its events."""
    visit = [dart(name) for name in names]
    for count in range(1, len(visit) + 1):
        game.track(visit[:count], positions[:count] if positions else None)
    pending = progress.before(game)
    progress.session_visit(pending.booking)
    game.finish_visit()
    events = progress.after(pending, game, now)
    game.track([])
    return events


def practice(game_kind, *names: str, **options) -> PracticeGame:
    game = PracticeGame()
    for index, name in enumerate(names):
        game.set_name(index, name)
    for option, value in options.items():
        setattr(game, option, value)
    if len(names) > 1:
        game.set_players(len(names))
    game.play(game_kind)
    return game


def unlocked(events) -> list[tuple[str, int]]:
    return [(details["achievement"], details["tier"]) for _, details in events]


def week(progress: Progress, name: str, field: str, ago: int = 0):
    trend = progress.summary(name, NOW.date())["trend"]
    return trend[field][TREND_WEEKS - 1 - ago]


def test_a_180_counts_for_the_player_at_the_board():
    game, progress = practice(501, "Alex"), Progress()
    events = play(game, progress, "T20", "T20", "T20")
    assert events == [
        (
            "achievement_unlocked",
            {
                "player": 1,
                "name": "Alex",
                "achievement": "maximum",
                "tier": 1,
                "tiers": 3,
                "threshold": 1,
            },
        )
    ]
    player = progress.players["alex"]
    assert {key: player.counters[key] for key in ("darts", "maximums", "tons")} == {
        "darts": 3,
        "maximums": 1,
        "tons": 1,
    }
    assert player.counters["ton_forties"] == 1
    summary = progress.summary("ALEX", NOW.date())
    assert summary["darts_thrown"] == 3 and summary["maximums"] == 1
    assert summary["hits"] == {"T20": 3}
    assert (summary["streak"], summary["best_streak"]) == (1, 1)
    trend = summary["trend"]
    assert len(trend["weeks"]) == TREND_WEEKS
    assert trend["weeks"][-1] == "2026-09-21"
    assert trend["weeks"][0] == "2026-07-06"
    assert (trend["darts"][-1], trend["maximums"][-1]) == (3, 1)
    # Bests of a week without a leg are none.
    assert trend["highest_checkout"][-1] is None and trend["best_mpr"][-1] is None
    assert progress.latest == {
        "name": "Alex",
        "achievement": "maximum",
        "tier": 1,
        "date": NOW.isoformat(),
    }
    # The same tier again unlocks nothing.
    assert play(game, progress, "T20", "T20", "T20") == []


def test_unnamed_players_have_no_progress():
    game, progress = practice(501), Progress()
    assert play(game, progress, "T20", "T20", "T20") == []
    assert progress.players == {}
    assert progress.summary("Alex", NOW.date()) == {}
    # The session still logs where darts landed; these had no position.
    assert len(progress.session) == 0


def test_a_nine_darter_unlocks_the_finishing_achievements():
    game, progress = practice(501, "Alex"), Progress()
    assert unlocked(play(game, progress, "T20", "T20", "T20")) == [("maximum", 1)]
    assert play(game, progress, "T20", "T20", "T20") == []
    events = play(game, progress, "T20", "T19", "D12")
    assert unlocked(events) == [
        ("high_finish", 1),
        ("short_leg", 3),
        ("nine_darter", 1),
        ("legs_won", 1),
    ]
    assert events[1][1]["threshold"] == 12
    player = progress.players["alex"]
    assert (player.counters["tons"], player.counters["ton_forties"]) == (3, 3)
    # The week collects the leg from the growth of the profile.
    assert week(progress, "Alex", "x01_darts") == 9
    assert week(progress, "Alex", "x01_points") == 501
    assert week(progress, "Alex", "first9_points") == 501
    assert week(progress, "Alex", "first9_darts") == 9
    assert (week(progress, "Alex", "legs"), week(progress, "Alex", "legs_won")) == (
        1,
        1,
    )
    assert (
        week(progress, "Alex", "at_double"),
        week(progress, "Alex", "checkouts"),
    ) == (
        1,
        1,
    )
    assert week(progress, "Alex", "double_attempts") == 1
    assert week(progress, "Alex", "double_hits") == 1
    assert week(progress, "Alex", "highest_checkout") == 141
    assert week(progress, "Alex", "best_501") == 9
    assert week(progress, "Alex", "darts") == 9
    # Without positions from the board, no dart is logged.
    assert len(player.log) == 0
    assert play(game, progress, "S1") == []


def test_positions_and_aims_make_the_grouping():
    game, progress = practice(1001, "Alex"), Progress()
    scatter = [
        around("T20", dx, -3) for dx in (-9, -6, -3, 0, 3, 6, 9, -6, -6, -6, 0, 0)
    ]
    for start in range(0, 12, 3):
        play(
            game,
            progress,
            "T20",
            "T20",
            "T20",
            positions=[(x, y) for x, y, _ in scatter[start : start + 3]],
        )
    [group] = progress.summary("Alex", NOW.date())["spread"]
    assert group["target"] == "T20" and group["darts"] == 12
    assert (group["offset_x"], group["offset_y"]) == (-1.5, -3.0)
    positions = progress.positions("alex")
    assert positions["player"] == "Alex" and positions["known"] is True
    assert len(positions["positions"]) == 12 and positions["spread"] == [group]
    # The darts of the session were logged as well.
    session = progress.positions()
    assert session["player"] is None and len(session["positions"]) == 12
    progress.session_started()
    assert progress.positions("  ")["positions"] == []
    assert progress.positions("Kim") == {
        "player": "Kim",
        "known": False,
        "positions": [],
        "spread": [],
    }


def test_cricket_nine_marks_and_a_hat_trick():
    game, progress = practice("cricket", "Alex"), Progress()
    assert unlocked(play(game, progress, "T20", "T19", "T18")) == [("cricket_nine", 1)]
    assert unlocked(play(game, progress, "25", "BULL", "25")) == [("hat_trick", 1)]
    # Trebles of numbers that are no Cricket numbers are no nine marks.
    game.play(501)
    assert play(game, progress, "T14", "T13", "T12") == []
    game.play("cricket")
    assert play(game, progress, "T20", "T19", "T14") == []
    assert progress.players["alex"].counters["cricket_nines"] == 1
    # Tactics plays 10 to 20.
    game.play("tactics")
    play(game, progress, "T14", "T13", "T12")
    assert progress.players["alex"].counters["cricket_nines"] == 2


def test_a_won_cricket_leg_sets_the_best_mpr_of_the_week():
    game, progress = practice("cricket", "Alex"), Progress()
    for visit in (("T20", "T19", "T18"), ("T17", "T16", "T15"), ("BULL", "25")):
        play(game, progress, *visit)
    # 21 marks with 8 darts.
    assert week(progress, "Alex", "best_mpr") == 7.88
    assert week(progress, "Alex", "cricket_darts") == 8
    assert week(progress, "Alex", "cricket_marks") == 21
    assert week(progress, "Alex", "highest_checkout") is None


def test_a_shanghai():
    game, progress = practice("shanghai", "Alex"), Progress()
    assert unlocked(play(game, progress, "S1", "D1", "T1")) == [
        ("legs_won", 1),
        ("shanghai", 1),
    ]


def test_the_bull_off_aims_at_the_bull():
    game = practice(501, "Alex", "Sam", bull_off=True)
    progress = Progress()
    game.new_match()
    play(game, progress, "S20", "T20", positions=[(0.1, 0.1), (0.0, 0.6)])
    alex = progress.players["alex"]
    assert alex.counters["darts"] == 1 and alex.hits == {"S20": 1}
    assert list(alex.log.darts) == [(0.1, 0.1, "BULL")]
    # The session logs both darts; only the first had an aim.
    assert [aim for _, _, aim in progress.session.darts] == ["BULL", None]


def test_the_opponents_legs_count_in_their_week():
    game, progress = practice(301, "Alex", "Sam"), Progress()
    game.players[0].remaining = 40
    play(game, progress, "D20")
    assert week(progress, "Sam", "legs") == 1 and week(progress, "Sam", "legs_won") == 0
    assert week(progress, "Alex", "legs_won") == 1
    # Sam threw no dart: no streak, no darts.
    assert progress.summary("Sam", NOW.date())["streak"] == 0


def test_legs_without_double_out_set_no_checkout():
    game, progress = practice(101, "Alex", double_out=False), Progress()
    game.players[0].remaining = 20
    play(game, progress, "S20")
    assert week(progress, "Alex", "highest_checkout") is None
    assert week(progress, "Alex", "best_501") is None
    assert week(progress, "Alex", "legs_won") == 1


def test_around_the_clock_and_the_doubles_training_count_for_player_1():
    game, progress = practice("around_the_clock", "Alex"), Progress()
    targets = [*(f"S{number}" for number in range(1, 21)), "25"]
    events = []
    for start in range(0, 21, 3):
        events += play(game, progress, *targets[start : start + 3])
    assert unlocked(events) == [("around_the_clock", 3)]
    assert events[0][1]["threshold"] == 21
    assert progress.players["alex"].counters["around_the_clock"] == 21
    # A slower game keeps the best one; nothing is aimed at in Around the Clock.
    game.play("around_the_clock")
    for start in range(0, 21, 3):
        play(game, progress, "MISS", *targets[start : start + 3])
    assert progress.players["alex"].counters["around_the_clock"] == 21
    assert {aim for _, _, aim in progress.players["alex"].log.darts} <= {None}

    game.play("doubles")
    play(game, progress, "S1", "D1", "D2", positions=[(0.0, 0.9)] * 3)
    aims = [aim for _, _, aim in list(progress.players["alex"].log.darts)[-3:]]
    assert aims == ["D1", "D1", "D2"]


def test_bobs_27_above_the_thresholds():
    game, progress = practice("bobs_27", "Alex"), Progress()
    events = []
    for number in range(1, 21):
        second = f"D{number}" if number == 20 else "MISS"
        events += play(game, progress, f"D{number}", second, "MISS")
    events += play(game, progress, "BULL", "MISS", "MISS")
    # Every double and the bull were hit on the way.
    assert unlocked(events) == [("all_doubles", 1), ("bobs_27", 3)]
    assert progress.players["alex"].counters["bobs_27"] == 537
    # A lost game sets no best.
    game.play("bobs_27")
    for _ in range(5):
        play(game, progress, "MISS", "MISS", "MISS")
    assert game.drills["bobs_27"].results[0]["completed"] is False
    assert progress.players["alex"].counters["bobs_27"] == 537


def test_a_checkout_training_finish_is_a_high_finish():
    game, progress = practice("checkout", "Alex"), Progress()
    drill = game.drills["checkout"]
    drill.target = drill.start = 121
    positions = [(0.0, 0.6), (0.0, 0.0), (0.0, -0.97)]
    events = play(game, progress, "T20", "25", "D18", positions=positions)
    assert unlocked(events) == [("high_finish", 1)]
    aims = [aim for _, _, aim in progress.players["alex"].log.darts]
    # The outer bull is no bed to aim at for the grouping.
    assert aims == ["T20", None, "D18"]
    drill.target = drill.start = 40
    play(game, progress, "S20", "S1")
    assert progress.players["alex"].counters["high_finish"] == 121


def test_streaks_count_days_in_a_row():
    game, progress = practice(1001, "Alex"), Progress()
    events = []
    for day in range(3):
        events += play(game, progress, "S1", now=NOW + timedelta(days=day))
    assert unlocked(events) == [("streak", 1)]
    player = progress.players["alex"]
    play(game, progress, "S1", now=NOW + timedelta(days=4))
    assert (player.streak, player.best_streak) == (1, 3)
    today = (NOW + timedelta(days=5)).date()
    assert player.current_streak(today) == 1
    assert player.current_streak(today + timedelta(days=1)) == 0


def test_weeks_older_than_the_trend_are_dropped():
    game, progress = practice(1001, "Alex"), Progress()
    play(game, progress, "S1", now=NOW - timedelta(weeks=TREND_WEEKS))
    play(game, progress, "S1", now=NOW - timedelta(weeks=1))
    player = progress.players["alex"]
    assert len(player.weeks) == 2
    play(game, progress, "S1")
    assert sorted(player.weeks) == ["2026-09-14", "2026-09-21"]
    assert week(progress, "Alex", "darts", ago=1) == 1


def test_every_double_counts_from_hits_and_the_doubles_statistics():
    profiles = Profiles()
    profile = Profile(name="Alex")
    profile.doubles = {f"D{number}": [3, 1] for number in range(1, 11)}
    profile.doubles["D11"] = [5, 0]
    profiles.players["alex"] = profile
    progress = Progress()
    player = progress.players.setdefault("alex", PlayerProgress("Alex"))
    player.hits.update({f"D{number}": 1 for number in range(11, 21)})
    assert (
        progress.achievements(profiles)["players"][0]["progress"]["all_doubles"] == 20
    )
    player.hits["BULL"] = 1
    progress.enable(True, profiles, NOW)
    assert player.badges["all_doubles"] == [NOW.isoformat()]


def test_achievements_that_are_off_stay_quiet_and_unlock_later():
    game, progress = practice(501, "Alex"), Progress()
    progress.enable(False, game.profiles, NOW)
    assert play(game, progress, "T20", "T20", "T20") == []
    player = progress.players["alex"]
    assert player.counters["maximums"] == 1 and player.badges == {}
    progress.enable(True, game.profiles, NOW)
    assert player.badges == {"maximum": [NOW.isoformat()]}
    assert progress.latest["achievement"] == "maximum"


def test_older_profiles_unlock_quietly_on_the_first_start():
    profiles = Profiles()
    profile = Profile(
        name="Alex",
        x01_darts=1100,
        cricket_darts=50,
        legs_won=60,
        highest_checkout=170,
        fewest_darts={"501": 11},
    )
    profiles.players["alex"] = profile
    progress = Progress()
    progress.restore(None, profiles, NOW)
    player = progress.players["alex"]
    assert player.counters["darts"] == 1150
    assert {key: len(dates) for key, dates in player.badges.items()} == {
        "high_finish": 3,
        "short_leg": 3,
        "legs_won": 2,
        "darts_thrown": 1,
    }
    assert progress.latest["achievement"] == "darts_thrown"
    # Turned off, the first start unlocks nothing.
    quiet = Progress()
    quiet.enabled = False
    quiet.restore({"enabled": True}, profiles, NOW)
    assert quiet.players["alex"].badges == {}


def test_progress_survives_a_restart():
    game, progress = practice(501, "Alex"), Progress()
    play(game, progress, "T20", "T20", "T20", positions=[(0.0, 0.6)] * 3)
    progress.enable(False, game.profiles, NOW)
    stored = progress.stored()
    restored = Progress()
    restored.restore(stored, Profiles(), NOW)
    assert restored.stored() == stored
    assert restored.enabled is False
    assert restored.latest == progress.latest
    assert len(restored.session) == 3


def test_restore_ignores_broken_progress():
    progress = Progress()
    progress.restore(
        {
            "players": [
                "Alex",
                {"name": " "},
                {
                    "name": "Alex",
                    "hits": {"T20": 3, "S1": 0, "D1": "2", "3": True},
                    "log": [1, 2],
                    "weeks": {
                        "2026-09-21": [1, 2],
                        "2026-09-14": [1, -1],
                        "someday": [1],
                        "2026-09-07": "3",
                    },
                    "counters": {"darts": 5, "maximums": -1, "tons": "2"},
                    "streak": 4,
                    "best_streak": 2,
                    "last_day": "yesterday",
                    "badges": {
                        "maximum": ["a", "b", "c", "d"],
                        "streak": [1],
                        "unknown": ["a"],
                    },
                },
                {"name": "Sam", "hits": [], "weeks": [], "counters": [], "badges": []},
            ],
            "session": "broken",
            "latest": {
                "name": "Alex",
                "achievement": "unknown",
                "tier": 1,
                "date": "x",
            },
        },
        Profiles(),
        NOW,
    )
    alex = progress.players["alex"]
    assert alex.hits == {"T20": 3}
    assert alex.weeks == {"2026-09-21": [1, 2, *[0] * (len(WEEK_FIELDS) - 2)]}
    assert alex.counters == {**dict.fromkeys(COUNTERS, 0), "darts": 5}
    assert (alex.streak, alex.best_streak, alex.last_day) == (4, 4, None)
    assert alex.badges == {"maximum": ["a", "b", "c"]}
    assert progress.players["sam"].weeks == {}
    assert progress.latest is None
    for latest in (
        None,
        {"name": 1, "achievement": "maximum", "tier": 1, "date": "x"},
        {"name": "Alex", "achievement": "maximum", "tier": "1", "date": "x"},
        {"name": "Alex", "achievement": "maximum", "tier": 1, "date": None},
    ):
        progress.restore({"players": [], "latest": latest}, Profiles(), NOW)
        assert progress.latest is None


def test_forgetting_a_player():
    game, progress = practice(501, "Alex", "Sam"), Progress()
    play(game, progress, "T20", "T20", "T20")
    progress.forget("Sam")
    assert progress.latest is not None
    progress.forget(" ALEX")
    assert progress.players == {} and progress.latest is None


def test_the_achievements_of_every_player():
    game, progress = practice(501, "Sam", "alex"), Progress()
    play(game, progress, "T20", "T20", "T20")
    play(game, progress, "S1")
    snapshot = progress.achievements(game.profiles)
    assert snapshot["latest"]["name"] == "Sam"
    assert snapshot["catalogue"][0] == {
        "id": "maximum",
        "tiers": [1, 10, 100],
        "lower": False,
    }
    assert [item["id"] for item in snapshot["catalogue"]] == [
        achievement.key for achievement in CATALOGUE
    ]
    alex, sam = snapshot["players"]
    assert (alex["name"], alex["unlocked"], alex["badges"]) == ("alex", 0, {})
    assert sam["unlocked"] == 1
    assert sam["badges"] == {"maximum": {"tier": 1, "dates": [NOW.isoformat()]}}
    assert set(sam["progress"]) == set(ACHIEVEMENTS)
    assert sam["progress"]["maximum"] == 1 and sam["progress"]["short_leg"] is None
    assert alex["progress"]["darts_thrown"] == 1


def test_tiers_count_up_or_down():
    assert ACHIEVEMENTS["maximum"].tier(None) == 0
    assert ACHIEVEMENTS["maximum"].tier(10) == 2
    assert ACHIEVEMENTS["short_leg"].tier(16) == 1
    assert ACHIEVEMENTS["short_leg"].tier(9) == 3
    assert ACHIEVEMENTS["streak"].tier(30) == 4


def test_legs_and_games_of_unnamed_players_count_for_nobody():
    game, progress = practice(301, "", "Sam"), Progress()
    game.players[0].remaining = 40
    play(game, progress, "D20")
    assert list(progress.players) == ["sam"]
    assert week(progress, "Sam", "legs") == 1

    game, progress = practice("around_the_clock"), Progress()
    targets = [*(f"S{number}" for number in range(1, 21)), "25"]
    for start in range(0, 21, 3):
        play(game, progress, *targets[start : start + 3])
    assert game.drills["around_the_clock"].results and progress.players == {}


def test_a_visit_without_darts_books_nobody():
    game = practice(501, "Alex")
    booking = game.booking()
    assert (booking.visit, booking.player, booking.darts) == ([], None, [])
    # Darts before the leg began belong to nobody either.
    game.track([dart("T20")])
    game.new_leg()
    booking = game.booking()
    assert booking.visit == [dart("T20")] and booking.darts == []
    assert booking.player is None
