"""Checkout suggestions for X01, aimed the way darts players aim.

With double out, a route follows the principles of the professional checkout
charts, in this order: the fewest darts; no double to set up; a double before
the bullseye; a first treble that still leaves a two-dart finish when it lands
in its single; the biggest first treble; a setup on the treble 20 or 19 or a
single towards a good double (and on 20 or 19 with two darts left, also any
double whose single still leaves one dart at a finish); a good double; fewer
trebles; bigger trebles; and the finishing double in the order below.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import NamedTuple


class Bed(NamedTuple):
    name: str
    score: int
    multiplier: int

    @property
    def number(self) -> int:
        """The number of the bed: 20 for T20, 25 for the bull."""
        return self.score // self.multiplier


SINGLES = [Bed(f"S{number}", number, 1) for number in range(1, 21)] + [Bed("25", 25, 1)]
DOUBLES = [Bed(f"D{number}", 2 * number, 2) for number in range(1, 21)] + [
    Bed("BULL", 50, 2)
]
TREBLES = [Bed(f"T{number}", 3 * number, 3) for number in range(1, 21)]
BEDS = [*SINGLES, *DOUBLES, *TREBLES]
# Every score a double finishes, with that double.
FINISHING = {bed.score: bed for bed in DOUBLES}

# Doubles that halve into further doubles come first, the bull last.
FINISH_ORDER = (
    *("D20", "D16", "D8", "D18", "D12", "D10", "D4", "D14", "D6", "D2"),
    *("D19", "D17", "D15", "D13", "D11", "D9", "D7", "D5", "D3", "D1"),
    "BULL",
)
# The first five doubles are good to finish on; on the big trebles, which
# players aim at anyway, the next two are fine as well.
GOOD_DOUBLES = frozenset(FINISH_ORDER[:5])
ACCEPTED_DOUBLES = frozenset(FINISH_ORDER[:7])
BIG_TREBLES = (20, 19)
# Highest possible checkout: two trebles 20 and the bull, or three trebles 20.
HIGHEST = {True: 170, False: 180}


def _setup_rank(
    remaining: int, setup: tuple[Bed, ...], finish: Bed, darts: int
) -> tuple[object, ...]:
    """How players rate a finish of up to two darts, `darts` in hand."""
    easy = all(
        bed.multiplier == 1 or (bed.multiplier == 3 and bed.number in BIG_TREBLES)
        for bed in setup
    )
    # With two darts left, a single 20 or 19 still leaves one dart at a finish.
    backup = (
        darts == 2
        and easy
        and bool(setup)
        and setup[-1].multiplier == 3
        and remaining - setup[-1].number in FINISHING
    )
    if easy and (finish.name in ACCEPTED_DOUBLES or backup):
        level = 0
    elif finish.name in GOOD_DOUBLES:
        level = 1
    else:
        level = 2
    return (
        level,
        sum(bed.multiplier == 3 for bed in setup),
        tuple(-bed.score if bed.multiplier == 3 else 0 for bed in setup),
        FINISH_ORDER.index(finish.name),
    )


def _double_out_rank(
    route: tuple[Bed, ...], remaining: int, darts: int, preferred: tuple[str, ...]
) -> tuple[object, ...]:
    *setup, finish = route
    first: tuple[object, ...] = ()
    if len(setup) == 2:
        dart = setup.pop(0)
        # With a full visit, a first treble that lands in its single still
        # leaves two darts at a finish.
        missed = (
            darts == 3
            and dart.multiplier == 3
            and not checkout(remaining - dart.number, 2)
        )
        first = (missed, -dart.score)
        remaining, darts = remaining - dart.score, darts - 1
    # A player's strongest doubles come before the usual choice.
    personal = (
        preferred.index(finish.name) if finish.name in preferred else len(preferred)
    )
    return (
        sum(bed.multiplier == 2 for bed in route[:-1]),
        finish.name == "BULL",
        *first[:1],
        personal,
        *first[1:],
        *_setup_rank(remaining, tuple(setup), finish, darts),
    )


def _single_out_rank(route: tuple[Bed, ...]) -> tuple[object, ...]:
    """Without double out, the biggest target wins: a single before a double."""
    *setup, finish = route
    return (
        sum(bed.multiplier == 2 for bed in setup),
        finish.name == "BULL",
        sum(bed.multiplier == 3 for bed in setup),
        finish.multiplier,
        *(-bed.score for bed in setup),
    )


@lru_cache(maxsize=2048)
def checkout(
    remaining: int,
    darts: int = 3,
    double_out: bool = True,
    preferred: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """The preferred way to finish, or an empty tuple when none exists.

    Fewer darts always come first. Preferred doubles, a player's strongest,
    win over the usual route whenever the same number of darts reaches them
    without a double to set up.
    """
    if not 0 < remaining <= HIGHEST[double_out] or not 0 < darts <= 3:
        return ()
    for count in range(darts):
        routes: list[tuple[Bed, ...]] = []
        for setup in product(BEDS, repeat=count):
            need = remaining - sum(bed.score for bed in setup)
            if double_out:
                finishes = [FINISHING[need]] if need in FINISHING else []
            else:
                finishes = [bed for bed in BEDS if bed.score == need]
            routes.extend((*setup, finish) for finish in finishes)
        if not routes:
            continue
        if double_out:
            best = min(
                routes,
                key=lambda route: _double_out_rank(route, remaining, darts, preferred),
            )
        else:
            best = min(routes, key=_single_out_rank)
        return tuple(bed.name for bed in best)
    return ()
