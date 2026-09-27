"""Cricket rules: marks on 20 to 15 and the bull, points on numbers others need.

Two variants play by the same marks: Cut-Throat, where points go to the
players who still have the number open and the lowest score wins, and
Tactics, which adds the numbers 14 to 10.
"""

from __future__ import annotations

from typing import Any, NamedTuple

# The numbers in the order players close them; 25 is the bull.
CRICKET_NUMBERS = (20, 19, 18, 17, 16, 15, 25)
TACTICS_NUMBERS = (20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 25)
# Every Cricket game and its numbers.
CRICKET_GAMES = {
    "cricket": CRICKET_NUMBERS,
    "cut_throat": CRICKET_NUMBERS,
    "tactics": TACTICS_NUMBERS,
}
MARKS_TO_CLOSE = 3


class CricketVisit(NamedTuple):
    """What the darts of a visit change for the player at the board."""

    marks: list[int]
    points: int
    darts: int
    won: bool
    # Marks that closed a number or scored.
    counted: int
    # The points of the others: Cut-Throat gives them the points.
    others: list[int]


def _marks(
    dart: dict[str, Any], numbers: tuple[int, ...] = CRICKET_NUMBERS
) -> tuple[int, int]:
    """Slot of the number and marks of one dart; a double counts two."""
    number, multiplier = dart["number"], dart["multiplier"]
    if number not in numbers or multiplier < 1:
        return -1, 0
    return numbers.index(number), multiplier


def marks_per_round(marks: int, darts: int) -> float | None:
    """Marks per three darts, the usual Cricket statistic."""
    return round(marks * 3 / darts, 2) if darts else None


def play_visit(
    marks: list[int],
    points: int,
    darts: list[dict[str, Any]],
    others_marks: list[list[int]],
    others_points: list[int],
    numbers: tuple[int, ...] = CRICKET_NUMBERS,
    cut_throat: bool = False,
) -> CricketVisit:
    """Marks, points, counted darts, win and marks that counted after the darts.

    Marks beyond three score the number's value only while another player
    still has it open: for the player at the board, or in Cut-Throat for every
    player with the number open. Closing everything wins once no one has more
    points, or in Cut-Throat fewer; playing alone, closing everything wins.
    """
    marks, others = list(marks), list(others_points)
    counted = 0
    for count, dart in enumerate(darts, 1):
        slot, add = _marks(dart, numbers)
        if add:
            closing = min(MARKS_TO_CLOSE - marks[slot], add)
            marks[slot] += closing
            extra = add - closing
            open_for = [
                index
                for index, other in enumerate(others_marks)
                if other[slot] < MARKS_TO_CLOSE
            ]
            if extra and open_for:
                value = extra * numbers[slot]
                if cut_throat:
                    for index in open_for:
                        others[index] += value
                else:
                    points += value
                counted += add
            else:
                counted += closing
        if all(mark >= MARKS_TO_CLOSE for mark in marks) and all(
            points <= other if cut_throat else points >= other for other in others
        ):
            return CricketVisit(marks, points, count, True, counted, others)
    return CricketVisit(marks, points, len(darts), False, counted, others)


def next_target(
    marks: list[int], numbers: tuple[int, ...] = CRICKET_NUMBERS
) -> str | None:
    """The bed to aim at next: the treble of the highest open number, then the bull."""
    for slot, number in enumerate(numbers):
        if marks[slot] < MARKS_TO_CLOSE:
            return "BULL" if number == 25 else f"T{number}"
    return None
