"""Checkout suggestions for X01, aimed the way darts players aim.

With double out, a route follows the principles of the professional checkout
charts, in this order: the fewest darts; no double to set up; a double before
the bullseye; a first treble that still leaves a two-dart finish when it lands
in its single; the biggest first treble; a setup on the treble 20 or 19 or on
a single towards one of the first seven doubles below (with two darts left,
on 20 or 19 also any double whose single still leaves a one-dart finish);
then any setup towards one of the first five; fewer trebles; bigger trebles;
and the finishing double in the order below.

With master out, a route finishes on a double as with double out wherever
that takes no more darts, and on a treble only where it saves a dart. Without
double out, the biggest bed wins. With the bull mode 50/50, the whole bull
scores 50: routes aim at the bull for 50, though only the bullseye is a double.

When the darts left cannot finish, a setup leaves the next visit a finish of
one or two darts, a preferred double first; see `setup`.
"""

from __future__ import annotations

from functools import lru_cache
from itertools import combinations_with_replacement, product
from typing import NamedTuple

from .scoring import BULL, BULL_25_50, BULL_50_50, DOUBLE, MASTER, STRAIGHT


class Bed(NamedTuple):
    name: str
    score: int
    multiplier: int
    # The number of the bed: 20 for T20, 25 for the bulls.
    number: int


SINGLES = [Bed(f"S{number}", number, 1, number) for number in range(1, 21)] + [
    Bed("25", BULL, 1, BULL)
]
DOUBLES = [Bed(f"D{number}", 2 * number, 2, number) for number in range(1, 21)] + [
    Bed("BULL", 2 * BULL, 2, BULL)
]
TREBLES = [Bed(f"T{number}", 3 * number, 3, number) for number in range(1, 21)]
BEDS = [*SINGLES, *DOUBLES, *TREBLES]
# With the bull mode 50/50, the outer bull scores 50 as well: a dart at the bull,
# which sets up and, without double out, finishes, though it is no double.
BULL_SINGLE = Bed("BULL", 2 * BULL, 1, BULL)
BEDS_BY_BULL = {
    BULL_25_50: BEDS,
    BULL_50_50: [BULL_SINGLE if bed.name == "25" else bed for bed in BEDS],
}
# Every score a double finishes, with that double, and the other way round.
FINISHING = {bed.score: bed for bed in DOUBLES}
FINISHING_SCORE = {bed.name: bed.score for bed in DOUBLES}
# The trebles a master out finishes on, by their score.
TREBLE_FINISHING = {bed.score: bed for bed in TREBLES}

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
HIGHEST = {DOUBLE: 170, MASTER: 180, STRAIGHT: 180}


def finishes(need: int, out_mode: str, beds: list[Bed]) -> list[Bed]:
    """The beds a dart finishes `need` on with this Out mode."""
    if out_mode == STRAIGHT:
        return [bed for bed in beds if bed.score == need]
    found = [FINISHING[need]] if need in FINISHING else []
    if out_mode == MASTER and need in TREBLE_FINISHING:
        found.append(TREBLE_FINISHING[need])
    return found


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
    route: tuple[Bed, ...],
    remaining: int,
    darts: int,
    preferred: tuple[str, ...],
    out_mode: str = DOUBLE,
    bull_mode: str = BULL_25_50,
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
            and not checkout(remaining - dart.number, 2, out_mode, (), bull_mode)
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


def _treble_out_rank(route: tuple[Bed, ...]) -> tuple[object, ...]:
    """With master out, where only a treble finishes in as few darts: no
    double to set up, fewer trebles to set up, the bigger setup darts first,
    then the bigger treble to finish on: T20 T20 T17 for 171."""
    *setup, finish = route
    return (
        sum(bed.multiplier == 2 for bed in setup),
        sum(bed.multiplier == 3 for bed in setup),
        *(-bed.score for bed in setup),
        -finish.score,
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


def _uncached_checkout(
    remaining: int,
    darts: int = 3,
    out_mode: str = DOUBLE,
    preferred: tuple[str, ...] = (),
    bull_mode: str = BULL_25_50,
) -> tuple[str, ...]:
    """The preferred way to finish, or an empty tuple when none exists.

    Fewer darts always come first. Preferred doubles, a player's strongest,
    win over the usual route whenever the same number of darts reaches them
    without a double to set up. With master out, a route on a double comes
    before one on a treble with as many darts.
    """
    if not 0 < remaining <= HIGHEST[out_mode] or not 0 < darts <= 3:
        return ()
    beds = BEDS_BY_BULL[bull_mode]
    for count in range(darts):
        routes: list[tuple[Bed, ...]] = []
        for setup in product(beds, repeat=count):
            need = remaining - sum(bed.score for bed in setup)
            routes.extend((*setup, bed) for bed in finishes(need, out_mode, beds))
        doubles = [route for route in routes if route[-1].multiplier == 2]
        if out_mode != STRAIGHT and doubles:
            best = min(
                doubles,
                key=lambda route: _double_out_rank(
                    route, remaining, darts, preferred, out_mode, bull_mode
                ),
            )
        elif out_mode == MASTER and routes:
            best = min(routes, key=_treble_out_rank)
        elif out_mode == STRAIGHT and routes:
            best = min(routes, key=_single_out_rank)
        else:
            continue
        return tuple(bed.name for bed in best)
    return ()


# A bot of the lowest level asks for about 2,800 different checkouts and 1,200
# setups: smaller caches keep evicting what it needs again, and every miss
# costs milliseconds in the event loop. The caches wrap their functions instead
# of decorating them, because mutmut leaves decorated functions unchanged (see
# docs/development.md#mutation-tests).
checkout = lru_cache(maxsize=8192)(_uncached_checkout)


# Scores to leave for the next visit, best first: 32 halves down to D1 when a
# dart lands in the single, 40 twice, 36 and 16 as well. The other doubles
# follow in the order routes finish on them, the bull last.
PREFERRED_LEAVES = (32, 40, 36, 16)
LEAVE_ORDER = (
    *PREFERRED_LEAVES,
    *(
        score
        for score in (FINISHING_SCORE[name] for name in FINISH_ORDER)
        if score not in PREFERRED_LEAVES
    ),
)
# Setup darts go at singles, trebles and the outer bull, never at a double.
SETUP_BEDS = [*SINGLES, *TREBLES]


class Setup(NamedTuple):
    """The darts that set up a finish, and the score they leave."""

    route: tuple[str, ...]
    leave: int


def _hard(bed: Bed) -> bool:
    """Small beds a setup rather avoids: the outer bull and the small trebles."""
    return (bed.number == BULL and bed.multiplier == 1) or (
        bed.multiplier == 3 and bed.number not in BIG_TREBLES
    )


# Setup beds as the search needs them, for every bull mode: score, small or
# not, treble or not; trebles first and bigger beds first, the order a setup is
# thrown in.
_SETUP = {
    mode: sorted(
        (
            (bed.score, _hard(bed), bed.multiplier == 3, bed.name)
            for bed in beds
            if bed.multiplier != 2
        ),
        key=lambda bed: (not bed[2], -bed[0]),
    )
    for mode, beds in BEDS_BY_BULL.items()
}


def _uncached_leave_ranks(
    preferred: tuple[str, ...],
    out_mode: str = DOUBLE,
    bull_mode: str = BULL_25_50,
) -> dict[int, tuple[int, int]]:
    """How good every score is to start the next visit with.

    Tier 0 are the preferred doubles, the player's strongest and then 32, 40,
    36 and 16, in that order; tier 1 the other doubles and, with master out,
    the trebles, the bigger first. Tier 2 are the finishes of two darts and
    the bull, the smaller the better. Scores that need three darts are missing.
    """
    first = tuple(
        FINISHING_SCORE[name] for name in preferred if name in FINISHING_SCORE
    )
    order = (*first, *(score for score in LEAVE_ORDER if score not in first))
    ranks: dict[int, tuple[int, int]] = {}
    for leave in range(2, HIGHEST[out_mode]):
        if leave in FINISHING and leave != FINISHING_SCORE["BULL"]:
            tier = 0 if leave in (*first, *PREFERRED_LEAVES) else 1
            ranks[leave] = (tier, order.index(leave))
        elif out_mode == MASTER and leave in TREBLE_FINISHING:
            ranks[leave] = (1, len(order) + 60 - leave)
        elif checkout(leave, 2, out_mode, (), bull_mode):
            ranks[leave] = (2, leave)
    return ranks


_leave_ranks = lru_cache(maxsize=16)(_uncached_leave_ranks)


def _uncached_setup(
    remaining: int,
    darts: int = 3,
    preferred: tuple[str, ...] = (),
    out_mode: str = DOUBLE,
    bull_mode: str = BULL_25_50,
) -> Setup | None:
    """Where to aim when the darts left cannot check out with double or master out.

    Above the highest checkout, at a score without a route such as 169, or
    with too few darts left, the darts in hand set up the next visit. They
    leave the best score to finish from (see `_leave_ranks`) with as few small
    beds as possible, then the better leave, then fewer and bigger trebles. The
    trebles come first, the single that sets up the double last. Above the
    highest checkout with three darts, only a finish of one dart is worth
    setting up; below, a finish of two darts, too. None without double or
    master out, when a checkout exists, or when nothing worth setting up can be
    left.
    """
    if (
        remaining < 2
        or not 0 < darts <= 3
        or out_mode == STRAIGHT
        or checkout(remaining, darts, out_mode, (), bull_mode)
    ):
        return None
    ranks = _leave_ranks(preferred, out_mode, bull_mode)
    tiers = 1 if darts == 3 and remaining > HIGHEST[out_mode] else 2
    best: tuple[tuple[object, ...], tuple[str, ...], int] | None = None
    for beds in combinations_with_replacement(_SETUP[bull_mode], darts):
        leave = remaining - sum(bed[0] for bed in beds)
        if (rank := ranks.get(leave)) is None or rank[0] > tiers:
            continue
        key = (
            rank[0],
            sum(bed[1] for bed in beds),
            rank[1],
            sum(bed[2] for bed in beds),
            tuple(-bed[0] for bed in beds),
        )
        if best is None or key < best[0]:
            best = (key, tuple(bed[3] for bed in beds), leave)
    return None if best is None else Setup(best[1], best[2])


setup = lru_cache(maxsize=4096)(_uncached_setup)
