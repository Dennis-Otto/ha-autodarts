"""Training sessions with darts entered by hand, the bot's darts and undone visits."""

from custom_components.autodarts.training import (
    COUNTERS,
    TrainingSession,
    dart_flags,
    segments,
)

from .local_helpers import S20, T20, board

KEYS = (*COUNTERS, "highest_visit", "hits", "manual_darts")


def flagged(*hits, **flags) -> dict:
    """A running board whose darts carry the flags, like the visit Home
    Assistant knows."""
    state = board(*hits)
    for throw in state["throws"]:
        throw.update(flags)
    return state


def visit(session: TrainingSession, *states: dict) -> list:
    events = []
    for state in (board(), *states, board()):
        events += session.observe(state)
    return events


def totals(session: TrainingSession) -> dict:
    snapshot = session.snapshot()
    return {key: snapshot[key] for key in KEYS}


def test_the_flags_of_darts_and_visits():
    assert segments(flagged(T20, manual=True, bot=False)) == [
        {"number": 20, "multiplier": 3, "name": "T20", "manual": True}
    ]
    assert dart_flags([{"corrected": True}, {}]) == {"manual": True}
    assert dart_flags([{"bot": True}]) == {"bot": True}
    assert dart_flags([{}]) == {}


def test_darts_entered_by_hand_count_and_say_so():
    session = TrainingSession()
    events = visit(session, flagged(T20, manual=True), board(T20, S20))
    # The board's darts of the same visit are its own again.
    kinds = [(kind, attributes.get("manual")) for kind, attributes in events]
    assert kinds[:2] == [("dart_detected", True), ("dart_corrected", None)]
    completed = dict(events)["visit_completed"]
    assert completed["score"] == 80 and "manual" not in completed
    session = TrainingSession()
    events = visit(session, flagged(T20, manual=True), flagged(T20, S20, manual=True))
    assert dict(events)["visit_completed"]["manual"] is True
    snapshot = session.snapshot()
    assert snapshot["darts"] == 2 and snapshot["manual_darts"] == 2
    assert session.recent_visits[0]["manual"] is True
    # Finished sessions keep the count, and so do restarts.
    ended = session.end("manual")
    assert ended is not None and ended[1]["manual_darts"] == 2
    restored = TrainingSession()
    restored.restore(session.stored())
    assert restored.history[0]["manual_darts"] == 2
    assert restored.recent_visits[0]["manual"] is True
    restored.restore({**session.stored(), "manual_darts": 5, "active": True})
    assert restored.snapshot()["manual_darts"] == 5


def test_the_bots_darts_are_announced_but_count_nowhere():
    session = TrainingSession()
    events = visit(session, flagged(T20, T20, T20, bot=True))
    assert [kind for kind, _ in events] == [
        *["dart_detected"] * 3,
        "visit_thrown",
        "visit_completed",
    ]
    assert all(attributes["bot"] is True for _, attributes in events)
    snapshot = session.snapshot()
    assert snapshot["darts"] == 0 and snapshot["scores_180"] == 0
    assert snapshot["hits"] == {} and session.recent_visits == []
    # Nothing to undo either.
    assert session.undo_visit() is None


def test_the_last_visit_comes_back_and_leaves_the_session():
    session = TrainingSession()
    visit(session, board(T20), board(T20, T20))
    visit(session, board(S20), flagged(S20, T20, manual=True), board(S20, T20, T20))
    assert session.snapshot()["darts"] == 5
    darts = session.undo_visit()
    assert darts is not None
    assert [dart["name"] for dart in darts] == ["S20", "T20", "T20"]
    assert "manual" not in darts[1]
    # The visit is the current one again, counted as before it was booked.
    assert session.visit() == darts and session.visit_slots() == [0, 1, 2]
    reference = TrainingSession()
    visit(reference, board(T20), board(T20, T20))
    reference.observe(board(S20, T20, T20))
    assert totals(session) == totals(reference)
    assert [len(item["segments"]) for item in session.recent_visits] == [2]
    # Only once.
    assert session.undo_visit() is None
    # Booked again, it counts once.
    assert session.observe(board())[0][0] == "visit_completed"
    assert session.snapshot()["darts"] == 5


def test_undoing_takes_back_the_highest_visit_and_the_hits():
    session = TrainingSession()
    visit(session, board(S20))
    visit(session, board(T20, T20, T20))
    assert session.snapshot()["highest_visit"] == 180
    session.undo_visit()
    # Corrected, the visit no longer is a 180.
    session.observe(board(S20, S20, S20))
    snapshot = session.snapshot()
    assert snapshot["highest_visit"] == 60 and snapshot["scores_180"] == 0
    assert snapshot["hits"] == {"S20": 4}


def test_undo_needs_an_empty_board_and_the_same_session():
    session = TrainingSession()
    visit(session, board(T20))
    session.observe(board(S20))
    assert session.undo_visit() is None
    session.observe(board())
    session.new_session()
    assert session.undo_visit() is None
    visit(session, board(T20))
    session.end("manual")
    assert session.undo_visit() is None
