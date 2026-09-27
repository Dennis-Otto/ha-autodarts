"""Cut-Throat Cricket and Tactics: the same marks, other points and numbers."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.cricket import (
    CRICKET_NUMBERS,
    TACTICS_NUMBERS,
    next_target,
    play_visit,
)
from custom_components.autodarts.practice import PracticeGame

from .local_helpers import dart, throw

OPEN = [0] * 7
TACTICS_OPEN = [0] * 12


def darts(*names: str) -> list[dict]:
    return [dart(name) for name in names]


def cut_throat(*names, marks=OPEN, points=0, others=None, points_of=None):
    others = others if others is not None else [OPEN, OPEN]
    points_of = points_of if points_of is not None else [0] * len(others)
    return play_visit(marks, points, darts(*names), others, points_of, cut_throat=True)


def test_cut_throat_gives_the_points_to_every_player_with_the_number_open():
    visit = cut_throat("T20", "T20", others=[OPEN, [3, 0, 0, 0, 0, 0, 0]])
    # The second player has closed the 20; only the first one gets 60.
    assert visit.marks[0] == 3 and visit.points == 0
    assert visit.others == [60, 0] and visit.counted == 6 and not visit.won
    # Nobody needs the number any more: extra marks neither score nor count.
    closed = [3, 0, 0, 0, 0, 0, 0]
    visit = cut_throat("T20", "T20", others=[closed, closed])
    assert visit.others == [0, 0] and visit.counted == 3


def test_cut_throat_is_won_by_closing_everything_with_the_fewest_points():
    almost = [3, 3, 3, 3, 3, 3, 2]
    # More points than an opponent: closing the bull does not win yet.
    visit = cut_throat("25", marks=almost, points=40, points_of=[20, 60])
    assert not visit.won
    # Equal to the lowest opponent wins, and later darts do not count.
    visit = cut_throat("25", "T20", marks=almost, points=20, points_of=[20, 60])
    assert visit.won and visit.darts == 1 and visit.others == [20, 60]
    # Alone, closing everything wins.
    visit = play_visit(almost, 0, darts("BULL"), [], [], cut_throat=True)
    assert visit.won and visit.darts == 1


def test_tactics_counts_the_numbers_down_to_ten():
    visit = play_visit(
        TACTICS_OPEN, 0, darts("T10", "T10", "S9"), [TACTICS_OPEN], [0], TACTICS_NUMBERS
    )
    assert visit.marks[10] == 3 and visit.points == 30 and visit.counted == 6
    assert next_target(TACTICS_OPEN, TACTICS_NUMBERS) == "T20"
    almost = [3] * 10 + [0, 3]
    assert next_target(almost, TACTICS_NUMBERS) == "T10"
    # Classic Cricket does not know the 10.
    assert play_visit(OPEN, 0, darts("T10"), [OPEN], [0]).counted == 0


@given(
    st.lists(st.sampled_from(["T20", "D19", "S15", "BULL", "25", "MISS"]), max_size=3)
)
def test_cut_throat_never_scores_for_the_thrower(names):
    visit = cut_throat(*names, others=[OPEN], points_of=[0])
    assert visit.points == 0 and visit.others[0] >= 0
    marks = sum(visit.marks)
    # Every counted mark closed a number or scored for the opponent.
    assert visit.counted >= marks


def game(kind: str, players: int = 2) -> PracticeGame:
    practice = PracticeGame()
    practice.set_players(players)
    practice.play(kind)
    return practice


def test_a_cut_throat_leg_goes_to_the_player_with_the_fewest_points():
    practice = game("cut_throat", 3)
    snapshot = practice.snapshot()
    assert snapshot["game"] == "cut_throat" and snapshot["numbers"] == list(
        CRICKET_NUMBERS
    )
    throw(practice, "T20", "T20")
    scores = practice.snapshot()["scores"]
    assert [score["points"] for score in scores] == [0, 60, 60]
    # While the visit runs, the others' points follow the darts.
    practice.track(darts("T20", "T20"))
    assert [score["points"] for score in practice.snapshot()["scores"]] == [
        0,
        60,
        120,
    ]
    practice.finish_visit()
    practice.track([])
    practice.players[2].marks = [3, 3, 3, 3, 3, 3, 2]
    practice.players[2].points = 0
    # The bullseye closes the bull and gives the others 25 each: the fewest win.
    events = throw(practice, "BULL")
    assert events[0][0] == "leg_won" and events[0][1]["player"] == 3
    assert events[0][1]["game"] == "cut_throat" and events[0][1]["points"] == 0
    assert practice.legs[0]["game"] == "cut_throat"


def test_a_tactics_leg_shows_twelve_numbers_and_survives_a_restart():
    practice = game("tactics")
    practice.track(darts("T10"))
    snapshot = practice.snapshot()
    assert snapshot["numbers"] == list(TACTICS_NUMBERS)
    assert len(snapshot["scores"][0]["marks"]) == 12
    assert snapshot["scores"][0]["marks"][10] == 3 and snapshot["target"] == "T20"
    practice.finish_visit()
    restored = PracticeGame()
    restored.restore(practice.stored())
    assert restored.cricket == "tactics" and restored.stored() == practice.stored()
    assert restored.players[0].marks[10] == 3
    # Marks of another length, from an older store, start the leg again.
    saved = practice.stored()
    saved["players"][0]["marks"] = [3] * 7
    restored.restore(saved)
    assert restored.players[0].marks == [0] * 12
