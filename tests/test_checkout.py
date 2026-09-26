"""Checkout routes: the ones players aim for, and never an impossible one."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custom_components.autodarts.checkout import BEDS, DOUBLES, checkout

BY_NAME = {bed.name: bed for bed in BEDS}


def reachable(darts: int, double_out: bool) -> set[int]:
    """Every score that can be finished with up to this many darts."""
    finishes = {bed.score for bed in (DOUBLES if double_out else BEDS)}
    scores = {bed.score for bed in BEDS}
    result, setups = set(), {0}
    for _ in range(darts):
        result |= {setup + finish for setup in setups for finish in finishes}
        setups = {setup + score for setup in setups for score in scores}
    return result


# Routes of the professional checkout charts, with three darts in hand.
CHART = {
    170: "T20 T20 BULL",
    167: "T20 T19 BULL",
    164: "T20 T18 BULL",
    161: "T20 T17 BULL",
    160: "T20 T20 D20",
    158: "T20 T20 D19",
    157: "T20 T19 D20",
    156: "T20 T20 D18",
    155: "T20 T19 D19",
    154: "T20 T18 D20",
    153: "T20 T19 D18",
    152: "T20 T20 D16",
    151: "T20 T17 D20",
    150: "T20 T18 D18",
    149: "T20 T19 D16",
    148: "T20 T16 D20",
    147: "T20 T17 D18",
    146: "T20 T18 D16",
    145: "T20 T15 D20",
    144: "T20 T20 D12",
    143: "T20 T17 D16",
    142: "T20 T14 D20",
    141: "T20 T19 D12",
    140: "T20 T20 D10",
    138: "T20 T18 D12",
    137: "T20 T19 D10",
    136: "T20 T20 D8",
    135: "T20 T17 D12",
    134: "T20 T14 D16",
    133: "T20 T19 D8",
    132: "T20 T16 D12",
    131: "T20 T13 D16",
    130: "T20 T20 D5",
    129: "T19 T16 D12",
    128: "T18 T14 D16",
    127: "T20 T17 D8",
    126: "T19 T19 D6",
    124: "T20 T16 D8",
    122: "T18 T20 D4",
    120: "T20 S20 D20",
    119: "T19 T10 D16",
    118: "T20 S18 D20",
    115: "T20 S15 D20",
    112: "T20 S12 D20",
    110: "T20 BULL",
    107: "T19 BULL",
    104: "T18 BULL",
    103: "T20 S3 D20",
    101: "T17 BULL",
    100: "T20 D20",
    98: "T20 D19",
    97: "T19 D20",
    96: "T20 D18",
    95: "T19 D19",
    94: "T18 D20",
    93: "T19 D18",
    92: "T20 D16",
    91: "T17 D20",
    89: "T19 D16",
    88: "T16 D20",
    87: "T17 D18",
    86: "T18 D16",
    85: "T15 D20",
    84: "T20 D12",
    83: "T17 D16",
    82: "T14 D20",
    81: "T19 D12",
    80: "T20 D10",
    78: "T18 D12",
    77: "T19 D10",
    76: "T20 D8",
    75: "T17 D12",
    74: "T14 D16",
    73: "T19 D8",
    72: "T16 D12",
    71: "T13 D16",
    69: "T15 D12",
    68: "T20 D4",
    67: "T17 D8",
    65: "25 D20",
    64: "T16 D8",
    63: "T13 D12",
    62: "T10 D16",
    61: "25 D18",
    60: "S20 D20",
    57: "S17 D20",
    50: "BULL",
    41: "S1 D20",
    40: "D20",
    39: "S7 D16",
    36: "D18",
    33: "S1 D16",
    32: "D16",
    31: "S15 D8",
    25: "S9 D8",
    17: "S1 D8",
    16: "D8",
    15: "S7 D4",
    9: "S1 D4",
    5: "S1 D2",
    3: "S1 D1",
    2: "D1",
}


@pytest.mark.parametrize(("remaining", "route"), CHART.items())
def test_routes_of_the_checkout_chart(remaining, route):
    assert " ".join(checkout(remaining)) == route


def test_a_missed_first_treble_still_leaves_a_finish():
    # A single 20 would leave 109, 108 or 99, which two darts cannot finish.
    assert checkout(129)[0] == "T19"  # a single 19 leaves 110: T20 BULL
    assert checkout(128)[0] == "T18"
    assert checkout(119)[0] == "T19"
    # With two darts in hand, the first dart is the setup: its miss is lost anyway.
    assert checkout(69, 2) == ("T19", "D6")


def test_two_darts_left_stay_on_the_treble_with_the_bull_behind():
    # A single 20 leaves the bull; with three darts, the single leaves two darts.
    assert checkout(70, 2) == ("T20", "D5")
    assert checkout(70) == ("T18", "D8")
    assert checkout(130) == ("T20", "T20", "D5")


def test_bogey_numbers_limits_and_darts_left():
    impossible = [score for score in range(1, 200) if not checkout(score)]
    assert impossible == [1, 159, 162, 163, 165, 166, 168, 169, *range(171, 200)]
    assert checkout(0) == checkout(-5) == checkout(50, 0) == ()
    assert checkout(40, 1) == ("D20",)
    assert checkout(41, 1) == checkout(100, 1) == ()
    assert checkout(100, 2) == ("T20", "D20")


def test_preferred_doubles_win_among_routes_of_the_same_darts():
    assert checkout(70, 3, True, ("D20",)) == ("T10", "D20")
    assert checkout(70, 2, True, ("D8",)) == ("T18", "D8")
    assert checkout(90, 3, True, ("D15",)) == ("T20", "D15")
    # Fewer darts still come first, and a double never sets up.
    assert checkout(40, 3, True, ("D8",)) == ("D20",)
    assert checkout(60, 3, True, ("D16",)) == ("S20", "D20")
    # The bull comes last, even for a player who hits it best.
    assert checkout(100, 3, True, ("BULL", "D5")) == ("T20", "D20")


def test_single_out_finishes_on_any_bed():
    assert checkout(20, 1, double_out=False) == ("S20",)
    assert checkout(60, 3, double_out=False) == ("T20",)
    assert checkout(180, 3, double_out=False) == ("T20", "T20", "T20")
    assert checkout(181, 3, double_out=False) == ()


@given(st.integers(-5, 190), st.integers(1, 3), st.booleans())
def test_a_route_adds_up_ends_right_and_exists_whenever_possible(
    remaining, darts, double_out
):
    route = checkout(remaining, darts, double_out)
    assert bool(route) == (remaining in reachable(darts, double_out))
    if route:
        beds = [BY_NAME[name] for name in route]
        assert sum(bed.score for bed in beds) == remaining
        assert len(beds) <= darts
        assert not double_out or beds[-1].multiplier == 2
        # No route with fewer darts exists.
        assert remaining not in reachable(len(beds) - 1, double_out)


@given(
    st.integers(2, 170),
    st.integers(1, 3),
    st.lists(st.sampled_from([bed.name for bed in DOUBLES]), unique=True),
)
def test_preferred_doubles_never_change_what_is_possible(remaining, darts, preferred):
    route = checkout(remaining, darts, True, tuple(preferred))
    usual = checkout(remaining, darts)
    assert len(route) == len(usual)
    if route:
        beds = [BY_NAME[name] for name in route]
        assert sum(bed.score for bed in beds) == remaining
        assert beds[-1].multiplier == 2
        # A double sets up only when the usual route needs one as well.
        doubles = sum(BY_NAME[name].multiplier == 2 for name in usual[:-1])
        assert sum(bed.multiplier == 2 for bed in beds[:-1]) == doubles
