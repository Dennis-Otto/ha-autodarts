"""A local session must count observations, not messages or camera jitter."""

import pytest

from custom_components.autodarts.training import COUNTERS, TrainingSession


def board(*hits, **changes):
    return {
        "running": True,
        "connected": True,
        "status": "Throw",
        "event": "Throw",
        "numThrows": len(hits),
        "throws": [
            {"segment": {"name": name, "number": number, "multiplier": multiplier}}
            for name, number, multiplier in hits
        ],
        **changes,
    }


T20 = ("T20", 20, 3)
S20 = ("S20", 20, 1)
BULL = ("Bull", 25, 2)
OUTER_BULL = ("25", 25, 1)
MISS = ("M", 0, 0)


def test_visits_duplicates_coordinates_and_bulls():
    session = TrainingSession()
    assert session.observe(board()) == []
    events = []
    for i in range(1, 4):
        events.extend(session.observe(board(*([T20] * i))))
    assert [event[0] for event in events] == [*["dart_detected"] * 3, "visit_thrown"]
    repeated = board(T20, T20, T20)
    repeated["throws"][0]["coords"] = {"x": 0.1, "y": 0.2}
    assert session.observe(repeated) == []
    assert session.snapshot()["darts"] == 3
    assert session.snapshot()["scores_180"] == 1
    assert session.snapshot()["triples"] == 3
    session.observe(board())
    # A miss next to a number keeps its number: it is still a miss.
    session.observe(board(BULL, OUTER_BULL, ("M7", 7, 0)))
    assert {key: session.snapshot()[key] for key in COUNTERS} == {
        "darts": 6,
        "points": 255,
        "doubles": 0,
        "triples": 3,
        "bulls": 2,
        "misses": 1,
        "visits": 2,
        "scores_100": 0,
        "scores_140": 0,
        "scores_180": 1,
    }


def test_corrections_revise_score_and_180_without_adding_darts():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20, T20))
    events = session.observe(board(T20, S20, T20))
    assert events == [
        ("dart_corrected", {"dart_index": 2, "segment": "S20", "score": 20})
    ]
    assert session.snapshot()["darts"] == 3
    assert session.snapshot()["scores_180"] == 0
    assert session.snapshot()["triples"] == 2
    assert session.snapshot()["points"] == 140
    session.observe(board(T20, T20, T20))
    assert session.snapshot()["scores_180"] == 1
    assert session.snapshot()["points"] == 180


TAKEOUT = {"status": "Takeout in progress", "event": "Takeout started"}


def test_partial_takeout_never_counts_remaining_darts_again():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, S20, BULL))
    session.observe(board(S20, BULL, **TAKEOUT))
    session.observe(board(BULL, **TAKEOUT))
    session.observe(board())
    assert session.snapshot()["darts"] == 3
    assert session.snapshot()["points"] == 130
    session.observe(board(S20))
    assert session.snapshot()["darts"] == 4


def test_darts_still_being_pulled_are_neither_announced_nor_counted():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, S20, BULL))
    session.observe(board(S20, BULL, **TAKEOUT))
    # The same darts again, and one of them read differently, while pulling.
    assert session.observe(board(S20, BULL, **TAKEOUT)) == []
    assert session.observe(board(S1, BULL)) == []
    assert session.snapshot()["darts"] == 3
    assert session.snapshot()["points"] == 130


def test_darts_thrown_before_the_takeout_ends_are_counted():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, S20, BULL))
    session.observe(board(BULL, **TAKEOUT))
    events = session.observe(board(BULL, S20))
    assert events == [
        ("dart_detected", {"dart_index": 2, "segment": "S20", "score": 20})
    ]
    assert session.snapshot()["darts"] == 4
    assert session.snapshot()["points"] == 150


def test_missed_empty_board_between_visits_keeps_counting():
    # A slow poll can miss the empty frame; the next visit must still count.
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20, T20))
    events = session.observe(board(S20))
    events += session.observe(board(S20, BULL))
    events += session.observe(board(S20, BULL, OUTER_BULL))
    assert events[0] == (
        "visit_completed",
        {"score": 180, "darts": 3, "segments": ["T20", "T20", "T20"], "thrown": True},
    )
    assert [event[1]["segment"] for event in events[1:-1]] == ["S20", "Bull", "25"]
    # The next visit is complete with its third dart, before the takeout.
    assert events[-1] == (
        "visit_thrown",
        {"score": 95, "darts": 3, "segments": ["S20", "Bull", "25"]},
    )
    snapshot = session.snapshot()
    assert {key: snapshot[key] for key in ("darts", "bulls", "points")} == {
        "darts": 6,
        "bulls": 2,
        "points": 275,
    }
    assert snapshot["visits"] == 2
    assert snapshot["scores_180"] == 1


def test_transient_shorter_frame_does_not_split_a_visit():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20))
    assert session.observe(board(T20)) == []
    session.observe(board(T20, T20))
    session.observe(board(T20, T20, T20))
    session.observe(board())
    assert session.snapshot()["darts"] == 3
    assert session.snapshot()["scores_180"] == 1
    assert session.snapshot()["points"] == 180


def test_withdrawn_detection_no_longer_counts():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, S20, MISS))
    session.observe(board(T20, S20))
    session.observe(board())
    assert session.snapshot()["darts"] == 2
    assert session.snapshot()["points"] == 80


def test_reset_ignores_darts_already_on_the_board():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20))
    session.new_session()
    assert all(session.snapshot()[key] == 0 for key in COUNTERS)
    assert session.observe(board(T20, T20)) == []
    session.observe(board(T20, T20, T20))
    assert session.snapshot()["darts"] == 1
    assert session.snapshot()["scores_180"] == 0
    session.observe(board())
    session.observe(board(T20, T20, T20))
    assert session.snapshot()["darts"] == 4
    assert session.snapshot()["scores_180"] == 1


def test_reload_restores_totals_and_does_not_replay_current_visit():
    old = TrainingSession()
    old.observe(board())
    old.observe(board(T20, T20, T20))
    restored = TrainingSession()
    restored.restore(old.snapshot())
    assert restored.observe(board(T20, T20, T20)) == []
    assert restored.snapshot() == old.snapshot()
    restored.observe(board())
    restored.observe(board(BULL))
    assert restored.snapshot()["darts"] == 4
    assert restored.snapshot()["bulls"] == 1


@pytest.mark.parametrize("status", ["Starting", "Calibrating", "Stopped", "Error"])
def test_inactive_states_do_not_create_training_darts(status):
    session = TrainingSession()
    session.observe(board())
    assert session.observe(board(T20, status=status)) == []
    assert session.snapshot()["darts"] == 0


@pytest.mark.parametrize(
    "invalid",
    [
        {"numThrows": 1, "throws": []},
        {"numThrows": "1"},
        {"numThrows": 1, "throws": [None]},
        {"numThrows": 1, "throws": [{"segment": {"number": "20", "multiplier": 3}}]},
        {"numThrows": 1, "throws": [{"segment": "T20"}]},
        {"numThrows": 1, "throws": [{"segment": {"number": 21, "multiplier": 1}}]},
        {"numThrows": 1, "throws": [{"segment": {"number": 20, "multiplier": 4}}]},
        # The bull has no treble, and only a miss has no number.
        {"numThrows": 1, "throws": [{"segment": {"number": 25, "multiplier": 3}}]},
        {"numThrows": 1, "throws": [{"segment": {"number": 0, "multiplier": 1}}]},
    ],
)
def test_incomplete_or_malformed_snapshot_does_not_reset_visit(invalid):
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20))
    assert session.observe(board(**invalid)) == []
    session.observe(board(T20, S20))
    assert session.snapshot()["darts"] == 2


def test_malformed_storage_is_sanitized():
    session = TrainingSession()
    session.restore({"darts": "bad", "points": -3, "bulls": True, "started": "bad"})
    assert all(session.snapshot()[key] == 0 for key in COUNTERS)


D16 = ("D16", 16, 2)
S1 = ("S1", 1, 1)


def test_analytics_buckets_hits_and_highest_visit():
    session = TrainingSession()
    session.observe(board())
    for visit in ((T20, T20, S20), (T20, S20, S20), (D16, S1, MISS), (T20, T20, T20)):
        for count in range(1, len(visit) + 1):
            session.observe(board(*visit[:count]))
        session.observe(board())
    snapshot = session.snapshot()
    assert snapshot["visits"] == 4
    assert snapshot["scores_100"] == 1  # 100
    assert snapshot["scores_140"] == 1  # 140
    assert snapshot["scores_180"] == 1
    assert snapshot["highest_visit"] == 180
    assert snapshot["doubles"] == 1
    assert snapshot["misses"] == 1
    assert snapshot["hits"] == {"D16": 1, "MISS": 1, "S1": 1, "S20": 3, "T20": 6}


def test_completed_visits_are_announced_once():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20))
    session.observe(board(T20, S20))
    assert session.observe(board(T20, **TAKEOUT)) == [
        (
            "visit_completed",
            {"score": 80, "darts": 2, "segments": ["T20", "S20"], "thrown": False},
        )
    ]
    assert session.observe(board()) == []
    session.observe(board(BULL))
    # Stopping the detection also ends the visit.
    assert session.observe(board(BULL, status="Stopped", running=False)) == [
        (
            "visit_completed",
            {"score": 50, "darts": 1, "segments": ["Bull"], "thrown": False},
        )
    ]


def test_the_third_dart_announces_the_visit_once():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20))
    assert session.observe(board(T20, T20, S20)) == [
        ("dart_detected", {"dart_index": 3, "segment": "S20", "score": 20}),
        (
            "visit_thrown",
            {"score": 140, "darts": 3, "segments": ["T20", "T20", "S20"]},
        ),
    ]
    # Neither a correction nor a withdrawn and detected dart announce it again.
    assert session.observe(board(T20, T20, T20)) == [
        ("dart_corrected", {"dart_index": 3, "segment": "T20", "score": 60})
    ]
    assert session.observe(board(T20, T20)) == []
    assert [kind for kind, _ in session.observe(board(T20, T20, T20))] == [
        "dart_detected"
    ]
    # The takeout completes it with the final score, marked as already thrown.
    assert session.observe(board(T20, **TAKEOUT)) == [
        (
            "visit_completed",
            {"score": 180, "darts": 3, "segments": ["T20"] * 3, "thrown": True},
        )
    ]
    # The next visit is announced again.
    session.observe(board())
    session.observe(board(BULL, BULL))
    assert session.observe(board(BULL, BULL, BULL))[-1] == (
        "visit_thrown",
        {"score": 150, "darts": 3, "segments": ["Bull"] * 3},
    )


def test_a_visit_without_three_announced_darts_is_not_thrown():
    session = TrainingSession()
    # A dart already in the board when Home Assistant starts is not announced.
    session.observe(board(T20))
    events = session.observe(board(T20, T20)) + session.observe(board(T20, T20, T20))
    assert [kind for kind, _ in events] == ["dart_detected", "dart_detected"]
    assert session.observe(board()) == [
        (
            "visit_completed",
            {"score": 120, "darts": 2, "segments": ["T20", "T20"], "thrown": False},
        )
    ]
    # A detection withdrawn after the third dart leaves a thrown visit.
    session.observe(board(T20, T20, S20))
    session.observe(board(T20, T20))
    assert session.observe(board()) == [
        (
            "visit_completed",
            {"score": 120, "darts": 2, "segments": ["T20", "T20"], "thrown": True},
        )
    ]


def test_a_dart_without_a_name_is_named_by_its_bed():
    session = TrainingSession()
    session.observe(board())
    unnamed = board(T20, MISS)
    for dart in unnamed["throws"]:
        del dart["segment"]["name"]
    assert session.observe(unnamed) == [
        ("dart_detected", {"dart_index": 1, "segment": "T20", "score": 60}),
        ("dart_detected", {"dart_index": 2, "segment": "MISS", "score": 0}),
    ]


def test_average_inputs_and_restore_of_analytics():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, D16))
    session.observe(board())
    restored = TrainingSession()
    restored.restore(session.snapshot())
    assert restored.snapshot() == session.snapshot()
    restored.restore(
        {**session.snapshot(), "highest_visit": -1, "hits": {"T20": "x", "S1": 2}}
    )
    assert restored.snapshot()["highest_visit"] == 0
    assert restored.snapshot()["hits"] == {"S1": 2}
    restored.restore({"darts": 3})
    assert restored.snapshot()["hits"] == {}
    restored.new_session()
    assert restored.snapshot()["highest_visit"] == 0
    assert restored.snapshot()["hits"] == {}


def ended_session(auto_start=False):
    session = TrainingSession()
    session.auto_start = auto_start
    session.observe(board())
    session.observe(board(T20))
    session.observe(board())
    kind, summary = session.end("manual")
    assert kind == "session_ended"
    assert summary["darts"] == 1 and summary["reason"] == "manual"
    return session


def test_darts_without_a_session_are_announced_but_not_counted():
    session = ended_session()
    before = session.snapshot()
    assert [kind for kind, _ in session.observe(board(T20, S20))] == [
        "dart_detected",
        "dart_detected",
    ]
    assert session.observe(board()) == [
        (
            "visit_completed",
            {"score": 80, "darts": 2, "segments": ["T20", "S20"], "thrown": False},
        )
    ]
    assert session.snapshot() == before
    assert session.recent_visits[0]["score"] == 80
    assert session.start() == (
        "session_started",
        {"started": session.started, "reason": "manual"},
    )
    assert session.start() is None
    assert all(session.snapshot()[key] == 0 for key in COUNTERS)


def test_the_first_dart_starts_a_session_automatically():
    session = ended_session(auto_start=True)
    events = session.observe(board(BULL))
    assert [kind for kind, _ in events] == ["session_started", "dart_detected"]
    assert events[0][1]["reason"] == "first_dart"
    assert session.active and session.snapshot()["darts"] == 1
    assert session.snapshot()["bulls"] == 1


def test_a_session_ignores_darts_already_on_the_board_but_announces_the_visit():
    session = ended_session()
    session.observe(board(T20, T20))
    session.start()
    session.observe(board(T20, T20, T20))
    assert session.snapshot()["darts"] == 1
    assert session.observe(board()) == [
        (
            "visit_completed",
            {"score": 180, "darts": 3, "segments": ["T20"] * 3, "thrown": True},
        )
    ]
    assert session.snapshot()["scores_180"] == 0


def test_darts_on_the_board_stay_with_the_ended_session():
    session = TrainingSession()
    session.observe(board())
    session.observe(board(T20, T20))
    _, summary = session.end("manual")
    assert summary["darts"] == 2 and summary["points"] == 120
    assert summary["visits"] == 1 and summary["highest_visit"] == 120
    session.observe(board())
    assert session.snapshot()["darts"] == 2
    assert session.new_session() == [
        ("session_started", {"started": session.started, "reason": "new_session"})
    ]
    assert session.end("manual")[1]["darts"] == 0
    assert len(session.history) == 1
    assert session.end("manual") is None


def test_new_session_ends_the_running_one_and_history_keeps_twenty():
    session = TrainingSession()
    session.observe(board())
    for _ in range(25):
        session.observe(board(T20, S20, S1))
        session.observe(board())
        kinds = [kind for kind, _ in session.new_session()]
        assert kinds == ["session_ended", "session_started"]
    assert len(session.history) == 20
    summary = session.history[0]
    assert summary["darts"] == 3 and summary["points"] == 81
    assert summary["average"] == 81.0
    assert summary["duration_minutes"] >= 0
    assert session.recent_visits[0]["segments"] == ["T20", "S20", "S1"]
    assert len(session.recent_visits) == 10


def test_version_1_storage_keeps_counting_and_everything_round_trips():
    session = TrainingSession()
    session.restore({"darts": 3, "points": 60, "started": "2026-09-01T10:00:00+00:00"})
    assert session.active and session.auto_start and session.idle_minutes == 0
    session.observe(board())
    session.observe(board(T20, S20))
    session.observe(board())
    session.end("manual")
    session.auto_start, session.idle_minutes = False, 15
    restored = TrainingSession()
    restored.restore(session.stored())
    assert restored.stored() == session.stored()
    assert not restored.active and restored.ended == session.ended


def test_malformed_session_storage_is_sanitized():
    session = TrainingSession()
    valid = {
        "started": "2026-09-01T10:00:00+00:00",
        "ended": "2026-09-01T10:30:00+00:00",
        "darts": 3,
        "points": 60,
    }
    session.restore(
        {
            "active": "yes",
            "auto_start": 1,
            "idle_minutes": 999,
            "ended": "2026-09-01T10:30:00+00:00",
            "last_activity": "yesterday",
            "history": [valid, {"started": "bad", "ended": "bad"}, "junk"],
            "recent_visits": [
                {"time": "2026-09-01T10:10:00+00:00", "score": 60, "segments": ["T20"]},
                {"time": "2026-09-01T10:11:00+00:00", "segments": [1]},
                {"time": "bad", "segments": []},
                None,
            ],
        }
    )
    assert session.active and session.auto_start and session.idle_minutes == 0
    assert session.ended is None and session.last_activity is None
    assert len(session.history) == 1
    assert session.history[0]["average"] == 60.0
    assert session.history[0]["duration_minutes"] == 30.0
    assert session.recent_visits == [
        {
            "time": "2026-09-01T10:10:00+00:00",
            "score": 60,
            "darts": 0,
            "segments": ["T20"],
        }
    ]
