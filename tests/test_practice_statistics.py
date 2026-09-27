"""Practice statistics: first-9 average, checkout rate, doubles rate and legs."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.practice import STATS_LEGS, PracticeGame

from .local_helpers import match, playing, throw


def test_a_nine_darter_counts_its_first_nine_and_one_dart_at_a_double():
    game = playing(501)
    throw(game, "T20", "T20", "T20")
    throw(game, "T20", "T20", "T20")
    throw(game, "T20", "T19", "D12")
    assert game.statistics() == {
        "first_9_average": 167.0,
        "checkout_rate": 100.0,
        "doubles_rate": 100.0,
        "legs_played": 1,
        "legs_counted": 1,
        "darts_at_double": 1,
    }


def test_the_first_nine_average_leaves_later_darts_out():
    game = playing(301)
    throw(game, "T20", "T20", "T20")
    throw(game, "S1", "S1", "S1")
    throw(game, "S1", "S1", "S1")
    throw(game, "T20", "S15", "D20")
    statistics = game.statistics()
    assert statistics["first_9_average"] == 62.0
    assert statistics["legs_played"] == 1
    assert statistics["darts_at_double"] == 1


def test_busts_score_nothing_and_every_dart_on_a_finish_counts_at_a_double():
    game = playing(301, 40)
    # 40 and 20 are both finishes; 20 - 20 without a double busts.
    throw(game, "S20", "S20")
    throw(game, "D20")
    statistics = game.statistics()
    assert statistics["checkout_rate"] == 33.3
    assert statistics["darts_at_double"] == 3
    # The restored leg started at 40: only the last dart scored.
    assert statistics["first_9_average"] == 40.0


def test_without_double_out_there_is_no_checkout_rate():
    game = playing(301, 20, double_out=False)
    throw(game, "S20")
    statistics = game.statistics()
    assert statistics["checkout_rate"] is None and statistics["doubles_rate"] is None
    assert statistics["legs_played"] == 1


def test_the_doubles_rate_adds_the_double_drills():
    game = playing(301, 40)
    throw(game, "S20", "S20")
    throw(game, "D20")
    game.drills["doubles"].results = [
        {
            "drill": "doubles",
            "darts": 30,
            "hits": 21,
            "ended": "2026-09-26T12:00:00+00:00",
        }
    ]
    game.drills["bobs_27"].results = [
        {
            "drill": "bobs_27",
            "darts": 3,
            "hits": "x",
            "ended": "2026-09-26T12:00:00+00:00",
        }
    ]
    assert game.statistics()["doubles_rate"] == 66.7


def test_matches_count_every_player_and_the_statistics_survive_a_restart():
    game = match(2)
    throw(game, "T20", "T20", "T20")
    throw(game, "S20", "S20", "S20")
    game.players[0].remaining = 40
    throw(game, "D20")
    statistics = game.statistics()
    # Alex 180 + 40 in four darts, Sam 60 in three darts.
    assert statistics["first_9_average"] == round(280 * 3 / 7, 2)
    assert statistics["legs_played"] == 1
    assert all(player.first9_darts == 0 for player in game.players)
    restored = PracticeGame()
    restored.restore(game.stored())
    assert restored.statistics() == statistics
    restored.restore({"leg_stats": [{"first9_points": -1}], "legs_total": "x"})
    assert restored.statistics()["legs_played"] == 0


def test_only_the_last_ten_legs_count():
    game = playing(301, 40)
    for _ in range(STATS_LEGS + 3):
        game.players[0].remaining = 40
        throw(game, "D20")
    statistics = game.statistics()
    assert statistics["legs_played"] == STATS_LEGS + 3
    assert statistics["legs_counted"] == STATS_LEGS


@given(
    st.lists(
        st.lists(
            st.sampled_from(["T20", "S20", "D20", "D10", "S5", "BULL", "MISS"]),
            min_size=1,
            max_size=3,
        ),
        max_size=60,
    )
)
def test_rates_stay_percentages(visits):
    game = playing(301)
    for visit in visits:
        throw(game, *visit)
        statistics = game.statistics()
        for key in ("checkout_rate", "doubles_rate"):
            assert statistics[key] is None or 0 <= statistics[key] <= 100
        assert all(player.first9_darts <= 9 for player in game.players)
