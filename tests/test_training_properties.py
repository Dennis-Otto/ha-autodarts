"""Property-based tests: any sequence of board states keeps the session consistent."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from custom_components.autodarts.training import (
    COUNTERS,
    TrainingSession,
    hit_key,
    segments,
)

SEGMENTS = [
    ("T20", 20, 3),
    ("S20", 20, 1),
    ("D16", 16, 2),
    ("T19", 19, 3),
    ("S5", 5, 1),
    ("S1", 1, 1),
    ("Bull", 25, 2),
    ("25", 25, 1),
    ("M", 0, 0),
]
STATUSES = ["Throw", "Throw", "Throw", "Takeout in progress", "Stopped", "Calibrating"]
EVENTS = ["Throw detected", "Takeout started", "Takeout finished", ""]
VALUES = {"MISS": 0, "25": 25, "BULL": 50}


def value(key: str) -> int:
    if key in VALUES:
        return VALUES[key]
    return {"S": 1, "D": 2, "T": 3}[key[0]] * int(key[1:])


board_state = st.builds(
    lambda darts, status, event, running: {
        "running": running,
        "status": status,
        "event": event,
        "numThrows": len(darts),
        "throws": [
            {"segment": {"name": name, "number": number, "multiplier": multiplier}}
            for name, number, multiplier in darts
        ],
    },
    st.lists(st.sampled_from(SEGMENTS), max_size=3),
    st.sampled_from(STATUSES),
    st.sampled_from(EVENTS),
    # Detection runs most of the time.
    st.sampled_from([True, True, True, False]),
)
# Realistic play: darts are mostly added one at a time, with occasional jumps.
histories = st.lists(board_state, min_size=1, max_size=40)
PROPERTIES = settings(
    max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)


def check_consistent(snapshot: dict) -> None:
    for key in COUNTERS:
        assert type(snapshot[key]) is int and snapshot[key] >= 0, key
    hits = snapshot["hits"]
    assert all(type(count) is int and count > 0 for count in hits.values())
    assert sum(hits.values()) == snapshot["darts"]
    assert sum(value(key) * count for key, count in hits.items()) == snapshot["points"]
    assert snapshot["triples"] == sum(c for k, c in hits.items() if k.startswith("T"))
    assert snapshot["doubles"] == sum(c for k, c in hits.items() if k.startswith("D"))
    assert snapshot["bulls"] == hits.get("25", 0) + hits.get("BULL", 0)
    assert snapshot["misses"] == hits.get("MISS", 0)
    buckets = snapshot["scores_100"] + snapshot["scores_140"] + snapshot["scores_180"]
    assert buckets <= snapshot["visits"]
    # A visit never holds more than three darts when the board reports at most three.
    assert snapshot["highest_visit"] <= 180
    assert snapshot["darts"] <= 3 * snapshot["visits"]


@PROPERTIES
@given(histories)
def test_any_history_keeps_the_session_consistent(history):
    session = TrainingSession()
    for state in history:
        for kind, attributes in session.observe(state):
            assert kind in {
                "dart_detected",
                "dart_corrected",
                "visit_thrown",
                "visit_completed",
            }
            if kind in ("visit_thrown", "visit_completed"):
                assert 1 <= attributes["darts"] <= 3
                assert 0 <= attributes["score"] <= 180
            else:
                assert 1 <= attributes["dart_index"] <= state["numThrows"]
        check_consistent(session.snapshot())


@PROPERTIES
@given(histories)
def test_every_visit_is_announced_once_as_early_as_possible(history):
    """A full visit is thrown once, before it completes; nothing is announced twice."""
    session = TrainingSession()
    thrown = False
    for state in history:
        for kind, attributes in session.observe(state):
            if kind == "visit_thrown":
                assert not thrown
                assert attributes["darts"] == 3
                thrown = True
            elif kind == "visit_completed":
                assert attributes["thrown"] is thrown
                # A visit that was not thrown never had three announced darts.
                assert thrown or attributes["darts"] < 3
                thrown = False


@PROPERTIES
@given(histories)
def test_restarting_home_assistant_keeps_every_total(history):
    session = TrainingSession()
    for state in history:
        session.observe(state)
    saved = session.snapshot()
    restored = TrainingSession()
    restored.restore(saved)
    assert restored.snapshot() == saved


@PROPERTIES
@given(histories)
def test_repeated_messages_never_count_twice(history):
    once, twice = TrainingSession(), TrainingSession()
    for state in history:
        once.observe(state)
        twice.observe(state)
        twice.observe(state)
    assert {k: v for k, v in once.snapshot().items() if k != "started"} == {
        k: v for k, v in twice.snapshot().items() if k != "started"
    }


@given(st.lists(st.sampled_from(SEGMENTS), max_size=3))
def test_hit_keys_match_their_value(darts):
    state = {
        "numThrows": len(darts),
        "throws": [
            {"segment": {"name": name, "number": number, "multiplier": multiplier}}
            for name, number, multiplier in darts
        ],
    }
    for dart in segments(state) or []:
        assert value(hit_key(dart)) == dart["number"] * dart["multiplier"]


@PROPERTIES
@given(histories)
def test_sessions_only_decide_what_counts(history):
    """Dart and visit events are the same with or without a running session."""
    running, paused = TrainingSession(), TrainingSession()
    paused.auto_start = False
    paused.end("manual")
    frozen = paused.snapshot()
    for state in history:
        assert running.observe(state) == paused.observe(state)
        check_consistent(running.snapshot())
    assert paused.snapshot() == frozen


@PROPERTIES
@given(histories, st.integers(min_value=0, max_value=40))
def test_restarting_keeps_sessions_history_and_settings(history, cut):
    session = TrainingSession()
    for index, state in enumerate(history):
        session.observe(state)
        if index == cut:
            session.new_session()
    restored = TrainingSession()
    restored.restore(session.stored())
    assert restored.stored() == session.stored()
    for summary in session.history:
        assert 0 < summary["darts"] <= 3 * summary["visits"]
        assert summary["average"] == round(summary["points"] / summary["darts"] * 3, 2)
        assert summary["duration_minutes"] >= 0
