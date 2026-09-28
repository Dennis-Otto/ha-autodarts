"""Hit rates per double, checkout routes over the strongest doubles, and how
often every double was hit at all."""

from custom_components.autodarts.checkout import checkout
from custom_components.autodarts.doubles import (
    MIN_ATTEMPTS,
    DoubleHits,
    DoubleStats,
    aimed_at,
)
from custom_components.autodarts.practice import PracticeGame

from .local_helpers import dart, throw


def test_the_double_that_finishes_a_score():
    assert aimed_at(32) == "D16" and aimed_at(40) == "D20" and aimed_at(2) == "D1"
    assert aimed_at(50) == "BULL"
    assert aimed_at(41) is None and aimed_at(42) is None and aimed_at(0) is None


def test_hit_rates_the_favourite_and_the_preferred_order():
    stats = DoubleStats()
    stats.record([("D16", True)] * 6 + [("D16", False)] * 4)
    stats.record([("D20", True)] * 3 + [("D20", False)] * 9)
    stats.record([("D8", True)] * 2)
    stats.record([("S20", True)])
    assert stats.rate("D16") == 60.0 and stats.rate("D1") is None
    # D8 has too few darts to count yet, and D20 hits less often than the
    # doubles together (11 of 24).
    assert stats.preferred() == ("D16",)
    snapshot = stats.snapshot()
    assert (snapshot["attempts"], snapshot["hits"], snapshot["favourite"]) == (
        24,
        11,
        "D16",
    )
    assert [item["double"] for item in snapshot["doubles"]] == ["D8", "D16", "D20"]
    restored = DoubleStats()
    restored.restore(stats.stored())
    assert restored.stored() == stats.stored()
    restored.restore({"D16": [1, 2], "D3": [4], "X": [1, 1], "BULL": [3, 1]})
    assert restored.stored() == {"BULL": [3, 1]}
    assert DoubleStats().snapshot()["rate"] is None


def test_a_double_is_preferred_only_when_it_is_a_strong_one():
    stats = DoubleStats()
    # Ten misses at D1, and five of nine at D20: D1 has the attempts, but it
    # is never hit, so the usual routes stay.
    stats.record([("D1", False)] * 10 + [("D20", True)] * 5 + [("D20", False)] * 4)
    assert stats.preferred() == () and stats.snapshot()["favourite"] is None
    assert checkout(62, 3, True, stats.preferred()) == checkout(62) == ("T10", "D16")
    # Once D20 has its attempts, it leads; D1 never does.
    stats.record([("D20", False)])
    assert stats.preferred() == ("D20",)
    # A double hit exactly as often as all doubles together is strong enough.
    even = DoubleStats()
    even.record([("D16", True)] * 3 + [("D16", False)] * 7)
    assert even.preferred() == ("D16",)


def test_preferred_doubles_rank_first_among_equal_routes():
    assert checkout(70) == ("T18", "D8")
    assert checkout(70, 3, True, ("D20",)) == ("T10", "D20")
    # Fewer darts still come first.
    assert checkout(40, 3, True, ("D8",)) == ("D20",)


def test_x01_drills_and_bobs_record_darts_at_doubles():
    practice = PracticeGame()
    practice.set_name(0, "Alex")
    practice.play(501)
    practice.players[0].remaining = 32
    throw(practice, "S16", "D8")
    assert practice.doubles.stored() == {"D16": [1, 0], "D8": [1, 1]}
    alex = practice.profiles.snapshot()["players"][0]
    assert alex["doubles"]["attempts"] == 2 and alex["doubles"]["hits"] == 1

    practice.play("doubles")
    throw(practice, "D1", "S2", "D2")
    assert practice.doubles.counts["D1"] == [1, 1]
    assert practice.doubles.counts["D2"] == [2, 1]
    practice.play("bobs_27")
    throw(practice, "D1", "S1", "MISS")
    assert practice.doubles.counts["D1"] == [4, 2]
    # Around the Clock aims at numbers, not doubles.
    practice.play("around_the_clock")
    throw(practice, "D1")
    assert practice.doubles.counts["D1"] == [4, 2]


def test_personal_routes_follow_the_strongest_doubles_of_the_player():
    practice = PracticeGame()
    practice.set_name(0, "Alex")
    practice.play(501)
    practice.players[0].remaining = 70
    assert practice.snapshot()["checkout"] == "T18 D8"
    practice.personal_routes = True
    # Without enough darts at a double, the usual route stays.
    assert practice.snapshot()["checkout"] == "T18 D8"
    practice.profiles.doubles("Alex", [("D20", True)] * MIN_ATTEMPTS)
    assert practice.snapshot()["checkout"] == "T10 D20"
    # Nobody's profile knows the doubles: everybody's darts decide.
    practice.set_name(0, "")
    assert practice.snapshot()["checkout"] == "T18 D8"
    practice.doubles.record([("D20", True)] * MIN_ATTEMPTS)
    assert practice.snapshot()["checkout"] == "T10 D20"
    restored = PracticeGame()
    restored.restore(practice.stored())
    assert (
        restored.personal_routes
        and restored.doubles.stored() == practice.doubles.stored()
    )


def test_finished_drills_and_darts_after_the_last_double_count_nothing():
    practice = PracticeGame()
    practice.play("checkout")
    drill = practice.drills["checkout"]
    drill.target = drill.start = 40
    # Darts at a double in the checkout training count, up to the finish.
    throw(practice, "S20", "D10", "D5")
    assert practice.doubles.counts == {"D20": [1, 0], "D10": [1, 1]}
    doubles = practice.drills["doubles"]
    doubles.index = 20
    doubles.track([dart("BULL"), dart("D1")])
    assert doubles.double_attempts() == [("BULL", True)]
    doubles.finished = True
    assert doubles.double_attempts() == []
    bobs = practice.drills["bobs_27"]
    bobs.track([dart("D1")])
    bobs.finished = True
    assert bobs.double_attempts() == []


def test_every_double_hit_counts_whatever_the_dart_was_aimed_at():
    practice = PracticeGame()
    # Training without a game.
    throw(practice, "D20", "T20", "BULL")
    assert practice.double_hits.snapshot() == {"D20": 1, "BULL": 1}
    # X01 without double out: no attempts, but the hits count.
    practice.play(301)
    practice.double_out = False
    throw(practice, "D16", "S16", "D16")
    assert practice.doubles.stored() == {}
    # Cricket aims at the numbers; its doubles are hits as well.
    practice.play("cricket")
    throw(practice, "D20", "D19", "MISS")
    assert practice.double_hits.snapshot() == {
        "D16": 2,
        "D19": 1,
        "D20": 2,
        "BULL": 1,
    }
    # A dart before the leg began counts for no visit, and for no hit.
    practice.play(501)
    practice.track([dart("D5")])
    practice.play(501)
    throw(practice, "D6")
    assert "D5" not in practice.double_hits.snapshot()


def test_the_bots_doubles_count_for_nobody():
    practice = PracticeGame()
    practice.set_name(0, "Alex")
    practice.set_bot(60)
    practice.play(501)
    throw(practice, "S1", "S1", "S1")
    assert practice.bot_up
    throw(practice, "D20", "D20", "D20")
    assert practice.double_hits.snapshot() == {}
    # A dart the board marks as the bot's counts for nobody either.
    hits = DoubleHits()
    hits.record([{**dart("D3"), "bot": True}, dart("D4"), dart("S4"), dart("MISS")])
    assert hits.snapshot() == {"D4": 1}


def test_double_hits_are_stored_restored_and_rewound():
    practice = PracticeGame()
    throw(practice, "D8", "D8")
    saved = practice.stored()
    assert saved["double_hits"] == {"D8": 2}
    other = PracticeGame()
    other.restore(saved)
    assert other.double_hits.snapshot() == {"D8": 2}
    # Only whole counts of real doubles come back.
    other.double_hits.restore(
        {"D21": 3, "D5": 0, "D6": -1, "D7": "2", "D9": 1.5, "BULL": 2, "S8": 4}
    )
    assert other.double_hits.snapshot() == {"BULL": 2}
    other.double_hits.restore(None)
    assert other.double_hits.snapshot() == {}
    # An undone visit takes its hits back.
    practice.play(501)
    checkpoint = practice.checkpoint()
    throw(practice, "D10")
    assert practice.double_hits.snapshot() == {"D8": 2, "D10": 1}
    practice.rewind(checkpoint, [], [])
    assert practice.double_hits.snapshot() == {"D8": 2}
    # The summary of a decided match books its visit on a copy, not twice.
    practice.players[0].remaining = 40
    throw(practice, "D20")
    assert practice.double_hits.snapshot() == {"D8": 2, "D20": 1}
