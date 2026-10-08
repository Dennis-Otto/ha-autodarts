"""Cricket rules: marks on 20 to 15 and the bull, points on numbers others need.

Three variants play by the same marks: Cut-Throat, where points go to the
players who still have the number open and the lowest score wins, Tactics,
which adds the numbers 14 to 10, and Wild Mouse, also known as Minnesota
Cricket, which adds any double, any triple and three in a bed.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from .scoring import VISIT_DARTS, score
from .training import hit_key

# The numbers in the order players close them; 25 is the bull.
CRICKET_NUMBERS = (20, 19, 18, 17, 16, 15, 25)
TACTICS_NUMBERS = (20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 25)
WILD_MOUSE = "wild_mouse"
# Every Cricket game and its numbers.
CRICKET_GAMES = {
    "cricket": CRICKET_NUMBERS,
    "cut_throat": CRICKET_NUMBERS,
    "tactics": TACTICS_NUMBERS,
    WILD_MOUSE: CRICKET_NUMBERS,
}
MARKS_TO_CLOSE = 3
# Wild Mouse closes three more targets after the numbers: three doubles, three
# triples and three darts of a visit in the same bed, which closes it at once.
DOUBLES, TRIPLES, BED = "doubles", "triples", "bed"
WILD_MOUSE_TARGETS = (DOUBLES, TRIPLES, BED)


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
    # In Cut-Throat, the other player, by their place in the others, whom the
    # points of this visit left with everything closed and the fewest points.
    other_won: int | None = None
    # In Wild Mouse, what every dart counted for: a number, doubles or triples,
    # or None; and whether the visit was three in a bed that counted.
    targets: tuple[str | None, ...] = ()
    bed: bool = False


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
    points, or in Cut-Throat fewer; playing alone, closing everything wins. In
    Cut-Throat, the points a dart gives can also make another player who has
    closed everything the one with the fewest: that player wins at once.
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
        if cut_throat and (winner := _lowest_closed(others_marks, others, points)):
            return CricketVisit(marks, points, count, False, counted, others, winner[0])
    return CricketVisit(marks, points, len(darts), False, counted, others)


def _lowest_closed(
    others_marks: list[list[int]], others: list[int], points: int
) -> list[int]:
    """The others with everything closed and no more points than anybody."""
    fewest = min([points, *others])
    return [
        index
        for index, marks in enumerate(others_marks)
        if others[index] == fewest and all(mark >= MARKS_TO_CLOSE for mark in marks)
    ]


def _bed(number: int) -> str:
    return "BULL" if number == 25 else f"T{number}"


def next_target(
    marks: list[int],
    numbers: tuple[int, ...] = CRICKET_NUMBERS,
    others_marks: list[list[int]] | None = None,
    others_points: list[int] | None = None,
    cut_throat: bool = False,
) -> str | None:
    """The bed to aim at next: the treble of the highest open number, then the bull.

    With everything closed and the points not yet enough to win, the highest
    number another player still has open, to score on it; in Cut-Throat, one
    that a player with the fewest points has open. None when nothing is left.
    """
    for slot, number in enumerate(numbers):
        if marks[slot] < MARKS_TO_CLOSE:
            return _bed(number)
    others = list(others_marks or [])
    if cut_throat and others_points:
        fewest = min(others_points)
        others = [
            other
            for other, points in zip(others, others_points, strict=True)
            if points == fewest
        ]
    for slot, number in enumerate(numbers):
        if any(other[slot] < MARKS_TO_CLOSE for other in others):
            return _bed(number)
    return None


# -- Wild Mouse ------------------------------------------------------------------


def _scores_on(marks: list[int], others_marks: list[list[int]], slot: int) -> bool:
    """A target the player closed scores while another player has it open."""
    return marks[slot] >= MARKS_TO_CLOSE and any(
        other[slot] < MARKS_TO_CLOSE for other in others_marks
    )


def target_key(slot: int, numbers: tuple[int, ...], targets: tuple[str, ...]) -> str:
    """The name of a slot of the marks: its number, or doubles, triples or bed."""
    return str(numbers[slot]) if slot < len(numbers) else targets[slot - len(numbers)]


def _options(
    dart: dict[str, Any], numbers: tuple[int, ...], targets: tuple[str, ...]
) -> list[tuple[int, int]]:
    """The slots a dart can count for, best first, with the marks it brings
    there: its number, which a double or triple marks two or three times, then
    doubles or triples, one mark each. The bull's centre is a double."""
    number, multiplier = dart["number"], dart["multiplier"]
    options = []
    if number in numbers and multiplier:
        options.append((numbers.index(number), multiplier))
    category = {2: DOUBLES, 3: TRIPLES}.get(multiplier)
    if number and category in targets:
        options.append((len(numbers) + targets.index(category), 1))
    return options


def _count_dart(
    marks: list[int],
    others_marks: list[list[int]],
    dart: dict[str, Any],
    numbers: tuple[int, ...],
    targets: tuple[str, ...],
) -> tuple[int | None, int, int]:
    """The slot a dart counts for, its marks that counted and its points.

    The first target it can count for that the player has open takes the dart;
    otherwise the first that scores. The marks change in place.
    """
    options = _options(dart, numbers, targets)
    pick = next(
        (option for option in options if marks[option[0]] < MARKS_TO_CLOSE),
        next(
            (
                option
                for option in options
                if _scores_on(marks, others_marks, option[0])
            ),
            None,
        ),
    )
    if pick is None:
        return None, 0, 0
    slot, add = pick
    # A number scores its value per mark; doubles and triples the dart's score.
    value = numbers[slot] if slot < len(numbers) else score(dart)
    closing = min(MARKS_TO_CLOSE - marks[slot], add)
    marks[slot] += closing
    extra = add - closing
    if extra and _scores_on(marks, others_marks, slot):
        return slot, add, extra * value
    return slot, closing, 0


def _one_bed(darts: list[dict[str, Any]]) -> bool:
    """Whether darts all landed in one bed, the same number and ring; misses
    make no bed."""
    first = darts[0]
    return first["number"] != 0 and all(
        (dart["number"], dart["multiplier"]) == (first["number"], first["multiplier"])
        for dart in darts
    )


def same_bed(darts: list[dict[str, Any]]) -> bool:
    """Three in a bed: the three darts of a visit in one bed."""
    return len(darts) == VISIT_DARTS and _one_bed(darts)


def play_wild_mouse_visit(
    marks: list[int],
    points: int,
    darts: list[dict[str, Any]],
    others_marks: list[list[int]],
    others_points: list[int],
    numbers: tuple[int, ...] = CRICKET_NUMBERS,
    targets: tuple[str, ...] = WILD_MOUSE_TARGETS,
) -> CricketVisit:
    """Marks, points, counted darts and win of a Wild Mouse visit.

    Every dart counts for one target: its number while the player has it open,
    otherwise doubles or triples while those are open, otherwise where it
    scores: the number's value for every mark, the dart's score on doubles and
    triples. Three darts of the visit in the same bed close three in a bed at
    once; once closed, a bed scores its three darts while another player has it
    open. Closing everything wins once no one has more points.
    """
    marks = list(marks)
    counted, count, won, bed, chosen = 0, 0, False, False, []
    for count, dart in enumerate(darts, 1):
        slot, add, scored = _count_dart(marks, others_marks, dart, numbers, targets)
        chosen.append(None if slot is None else target_key(slot, numbers, targets))
        counted += add
        points += scored
        if count == VISIT_DARTS and BED in targets and same_bed(darts):
            slot = len(numbers) + targets.index(BED)
            scores = _scores_on(marks, others_marks, slot)
            bed = scores or marks[slot] < MARKS_TO_CLOSE
            points += sum(score(item) for item in darts) if scores else 0
            marks[slot] = MARKS_TO_CLOSE
            counted += bed
        won = all(mark >= MARKS_TO_CLOSE for mark in marks) and all(
            points >= other for other in others_points
        )
        if won:
            break
    others = list(others_points)
    return CricketVisit(
        marks, points, count, won, counted, others, None, tuple(chosen), bed
    )


def wild_mouse_order(numbers: tuple[int, ...], targets: tuple[str, ...]) -> list[int]:
    """The slots in the order to close them: the numbers, the other targets and
    the bull last, the hardest bed."""
    bull = [numbers.index(25)] if 25 in numbers else []
    return [
        *(slot for slot in range(len(numbers)) if slot not in bull),
        *range(len(numbers), len(numbers) + len(targets)),
        *bull,
    ]


def wild_mouse_bed(
    slot: int,
    numbers: tuple[int, ...],
    targets: tuple[str, ...],
    visit: list[dict[str, Any]],
) -> str | None:
    """The bed to aim at for a slot: the triple of a number or the bull, D or T
    for any double or triple, and for three in a bed the bed of the visit's
    darts, or the big single 20 before the first; None once the visit's darts
    can no longer make a bed."""
    if slot < len(numbers):
        return _bed(numbers[slot])
    target = targets[slot - len(numbers)]
    if target != BED:
        return "D" if target == DOUBLES else "T"
    if not visit:
        return "S20"
    if len(visit) >= VISIT_DARTS or not _one_bed(visit):
        return None
    return hit_key(visit[0])


def wild_mouse_target(
    marks: list[int],
    numbers: tuple[int, ...],
    targets: tuple[str, ...],
    others_marks: list[list[int]],
    visit: list[dict[str, Any]],
) -> tuple[str, str] | None:
    """The row to aim at next and its bed: the next open target in order, and
    with everything closed, or a bed the visit can no longer make, one that
    scores; None when nothing is left."""
    order = wild_mouse_order(numbers, targets)
    for wanted in (
        [slot for slot in order if marks[slot] < MARKS_TO_CLOSE],
        [slot for slot in order if _scores_on(marks, others_marks, slot)],
    ):
        for slot in wanted:
            if bed := wild_mouse_bed(slot, numbers, targets, visit):
                return target_key(slot, numbers, targets), bed
    return None
