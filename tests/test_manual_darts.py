"""Corrections, darts entered by hand and the bot's darts on top of the board's."""

from custom_components.autodarts.manual import ManualDarts, parse_bed
from custom_components.autodarts.training import TrainingSession, segments

from .local_helpers import MISS, S20, T20, board

S1 = ("S1", 1, 1)
D16 = ("D16", 16, 2)


def names(state: dict) -> list[str]:
    return [dart["name"] for dart in segments(state)]


def with_coords(*hits, **changes) -> dict:
    """A board whose darts have positions: the first at (0.1, 0.2) and so on."""
    state = board(*hits, **changes)
    for index, throw in enumerate(state["throws"], 1):
        throw["coords"] = {"x": index / 10, "y": index / 5}
    return state


def test_beds_by_name():
    assert parse_bed(" t20 ") == {"number": 20, "multiplier": 3, "name": "T20"}
    assert parse_bed("bull") == {"number": 25, "multiplier": 2, "name": "BULL"}
    assert parse_bed("25") == {"number": 25, "multiplier": 1, "name": "25"}
    assert parse_bed("Miss") == {"number": 0, "multiplier": 0, "name": "MISS"}
    assert parse_bed("s5")["name"] == "S5"
    # Other names of the bulls.
    for alias in ("S25", "sb", "OB"):
        assert parse_bed(alias) == parse_bed("25")
    for alias in ("D25", "db", "50", " Bull "):
        assert parse_bed(alias) == parse_bed("BULL")
    for wrong in ("T21", "S0", "T25", "D50", "X", "", 20, None):
        assert parse_bed(wrong) is None


def test_the_board_alone_stays_as_it_is():
    manual = ManualDarts()
    state = with_coords(T20, S20)
    assert manual.apply(state) == state
    assert manual.sources == [("board", 0), ("board", 1)]
    assert not manual.pending and manual.board_darts(state) == 2
    # A state the training rejects is not touched either.
    broken = {**board(T20), "numThrows": 3}
    assert manual.apply(broken) is broken
    assert manual.board_darts(broken) == 0


def test_darts_entered_by_hand_keep_their_place_among_the_boards():
    manual = ManualDarts()
    manual.apply(board(T20))
    manual.add(parse_bed("S5"), None, "manual")
    assert manual.pending
    effective = manual.apply(with_coords(T20, S20))
    assert names(effective) == ["T20", "S5", "S20"]
    assert effective["numThrows"] == 3
    assert effective["throws"][1] == {
        "segment": {"name": "S5", "number": 5, "multiplier": 1},
        "manual": True,
    }
    assert segments(effective)[1] == {
        "number": 5,
        "multiplier": 1,
        "name": "S5",
        "manual": True,
    }
    assert manual.sources == [("board", 0), ("extra", 0), ("board", 1)]
    # The bot's darts come with their positions.
    manual.add(parse_bed("T19"), (0.1, -0.5), "bot")
    throw = manual.apply(board(T20, S20))["throws"][-1]
    assert throw["bot"] is True and throw["coords"] == {"x": 0.1, "y": -0.5}
    assert manual.bot_darts() == 1


def test_a_correction_holds_while_the_board_keeps_its_reading():
    manual = ManualDarts()
    manual.apply(with_coords(T20, S20))
    manual.correct(1, parse_bed("T20"))
    effective = manual.apply(with_coords(T20, S20))
    assert names(effective) == ["T20", "T20"]
    # Where the board misread the bed, it misread the spot: the dart has no position.
    assert effective["throws"][1] == {
        "segment": {"name": "T20", "number": 20, "multiplier": 3},
        "corrected": True,
    }
    assert effective["throws"][0]["coords"] == {"x": 0.1, "y": 0.2}
    # A third dart does not disturb it.
    assert names(manual.apply(with_coords(T20, S20, S1))) == ["T20", "T20", "S1"]
    # Once the board corrects the dart itself, its reading counts again.
    assert names(manual.apply(with_coords(T20, D16, S1))) == ["T20", "D16", "S1"]
    assert not manual.fixes


def test_correcting_back_to_the_boards_reading_drops_the_correction():
    manual = ManualDarts()
    manual.apply(board(T20, S20))
    manual.correct(1, parse_bed("T20"))
    manual.correct(1, parse_bed("S20"))
    assert not manual.fixes
    assert manual.apply(board(T20, S20)) == board(T20, S20)


def test_darts_entered_by_hand_can_be_corrected_too():
    manual = ManualDarts()
    manual.apply(board())
    manual.add(parse_bed("S5"), None, "manual")
    manual.apply(board())
    manual.correct(0, parse_bed("S5"))
    assert manual.extras[0].dart == {
        "number": 5,
        "multiplier": 1,
        "name": "S5",
        "manual": True,
    }
    manual.correct(0, parse_bed("T5"))
    assert manual.extras[0].dart == {
        "number": 5,
        "multiplier": 3,
        "name": "T5",
        "manual": True,
        "corrected": True,
    }
    # A replayed dart of the board is corrected like any other, and leaves the
    # board's position behind.
    manual.replay([{"number": 20, "multiplier": 1, "name": "S20"}], [(0.02, 0.8)])
    manual.correct(0, parse_bed("T20"))
    assert manual.extras[0].dart["corrected"] is True
    assert "manual" not in manual.extras[0].dart
    assert manual.extras[0].position is None


def test_a_correction_can_say_where_the_dart_is():
    manual = ManualDarts()
    manual.apply(with_coords(T20, S20))
    manual.correct(1, parse_bed("T20"), (0.03, 0.6))
    effective = manual.apply(with_coords(T20, S20))
    assert effective["throws"][1] == {
        "segment": {"name": "T20", "number": 20, "multiplier": 3},
        "coords": {"x": 0.03, "y": 0.6},
        "corrected": True,
    }
    # The bed the board read: the board's dart where the board saw it.
    manual.correct(1, parse_bed("S20"), (0.02, 0.8))
    assert not manual.fixes
    assert manual.apply(with_coords(T20, S20)) == with_coords(T20, S20)
    # A dart entered by hand gets the spot, in the same bed or another.
    manual.add(parse_bed("S5"), None, "manual")
    manual.apply(with_coords(T20, S20))
    manual.correct(2, parse_bed("S5"), (-0.24, 0.76))
    assert manual.extras[0].position == (-0.24, 0.76)
    assert "corrected" not in manual.extras[0].dart
    manual.correct(2, parse_bed("T5"), (-0.18, 0.57))
    assert manual.extras[0].position == (-0.18, 0.57)
    throw = manual.apply(with_coords(T20, S20))["throws"][2]
    assert throw["coords"] == {"x": -0.18, "y": 0.57} and throw["corrected"] is True


def test_pulling_the_darts_ends_the_visit_with_everything_of_home_assistant():
    manual = ManualDarts()
    manual.apply(board(T20, S20))
    manual.add(parse_bed("S5"), None, "manual")
    manual.correct(0, parse_bed("S20"))
    manual.apply(board(T20, S20))
    assert manual.apply(board()) == board()
    assert not manual.pending
    # A partial takeout ends it, too; the darts still in the board stay hidden.
    manual.apply(board(T20, S20, S1))
    manual.add(parse_bed("S5"), None, "manual")
    manual.apply(board(T20, S20, S1))
    takeout = board(T20, S20, status="Takeout in progress")
    assert names(manual.apply(takeout)) == []
    assert len(manual.hidden) == 2 and not manual.extras
    assert manual.board_darts(takeout) == 0
    # New darts beyond them are the next visit, also when the others are
    # pulled in any order.
    assert names(manual.apply(board(T20, S20, D16))) == ["D16"]
    assert names(manual.apply(board(S20, D16))) == ["D16"]
    assert names(manual.apply(board(D16))) == ["D16"] and not manual.hidden
    # A hidden reading stands for the first of its darts on the board.
    manual.end_visit()
    assert manual.held(board(D16, D16)) == board(D16)
    assert names(manual.apply(board(D16, D16))) == ["D16"]


def test_a_withdrawn_detection_keeps_the_visit_and_a_missed_takeout_ends_it():
    manual = ManualDarts()
    manual.apply(board(T20, S20))
    manual.add(parse_bed("S5"), None, "manual")
    assert names(manual.apply(board(T20))) == ["T20", "S5"]
    # The dart entered after two darts of the board comes last now.
    assert manual.extras[0].after == 2
    # Another reading of the same number of darts is a correction.
    assert names(manual.apply(board(MISS))) == ["M", "S5"]
    # Fewer and other darts without an empty board in between: a missed takeout.
    manual.apply(board(T20, S20))
    assert names(manual.apply(board(MISS))) == ["M"]
    assert not manual.extras and not manual.hidden


def test_a_visit_ended_in_home_assistant_hides_its_darts_until_they_are_pulled():
    manual = ManualDarts()
    manual.apply(board(T20, S20))
    manual.add(parse_bed("S5"), None, "manual")
    manual.end_visit()
    assert not manual.pending
    assert manual.apply(board(T20, S20))["throws"] == []
    assert manual.board_darts(board(T20, S20)) == 0
    assert manual.board_darts(board(T20, S20, S1)) == 1
    assert names(manual.apply(board(T20, S20, S1))) == ["S1"]
    # Pulling them shows the board's darts again.
    manual.apply(board())
    assert names(manual.apply(board(T20))) == ["T20"]


def test_without_detection_the_darts_entered_by_hand_make_the_visit():
    stopped = {**board(T20), "running": False, "status": "Stopped"}
    manual = ManualDarts()
    assert manual.apply(stopped) == stopped
    manual.add(parse_bed("S5"), None, "manual")
    effective = manual.apply(stopped)
    assert effective["running"] is True and effective["status"] == "Throw"
    # The dart in the board belongs to no visit; the one entered follows it.
    assert names(effective) == ["T20", "S5"]
    assert manual.sources == [("hidden", 0), ("extra", 0)]
    assert manual.board_darts(stopped) == 0
    # The detection starts: the visit goes on with the board's new darts.
    assert names(manual.apply(board(T20))) == ["S5"]
    assert names(manual.apply(board())) == ["S5"]
    assert names(manual.apply(board(T20))) == ["S5", "T20"]
    # It stops: the visit ends, as it does on the board.
    assert manual.apply(stopped) == stopped
    assert not manual.extras
    calibrating = {**board(), "status": "Calibrating"}
    assert manual.apply(calibrating) == calibrating


def test_the_training_follows_the_flags_of_the_darts():
    manual = ManualDarts()
    session = TrainingSession()
    session.observe(manual.apply(board()))
    manual.add(parse_bed("T20"), None, "manual")
    events = session.observe(manual.apply(board()))
    assert events == [
        (
            "dart_detected",
            {"dart_index": 1, "segment": "T20", "score": 60, "manual": True},
        )
    ]
    manual.correct(0, parse_bed("S20"))
    events = session.observe(manual.apply(board()))
    assert events == [
        (
            "dart_corrected",
            {
                "dart_index": 1,
                "segment": "S20",
                "score": 20,
                "previous": "T20",
                "manual": True,
            },
        )
    ]
    assert session.snapshot()["manual_darts"] == 1
